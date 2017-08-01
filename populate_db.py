"""native imports"""
import json
import os
import time
import datetime
from pprint import pprint

import pytz
import praw
from prawcore.exceptions import Forbidden, NotFound
from google.cloud import bigquery



def extract_reddit_kwargs(post):
    """Extract needed kwargs to make a db entry for a reddit post"""
    ret = {}
    for key in ['uid', 'body', 'score', 'is_root', 'context', ]:
        ret[key] = post[key]
    for key in ['user_comment_karma', 'user_link_karma', 'user_is_mod', 'user_is_deleted']:
        ret[key] = post.get(key, 0)
    ret['timestamp'] = datetime.datetime.fromtimestamp(post['timestamp']).replace(tzinfo=pytz.UTC)
    
    if post.get('created_utc'):
        ret['user_created_utc'] = datetime.datetime.fromtimestamp(
            post['created_utc']).replace(tzinfo=pytz.UTC)
    if post.get('discourse_type'):
        ret['discourse_type'] = post.get('majority_type')
    if post.get('url'):
        ret['url'] = post['url']
    return ret

# PURITY LOVERS BEWARE
# this function is REMARKABLY IMPURE
# returns nothing...
def extract_reddit_author_info(holder, author):
    """
    Args:
        holder - the dict to store stuff in
        author - the PRAW author object
    Returns:
        holder - the dict
    """
    def grab_author_attrib():
        """Grab the properties and put them into the dict"""
        holder['user_comment_karma'] = author.comment_karma
        holder['user_link_karma'] = author.link_karma
        holder['user_created_utc'] = author.created_utc
        holder['user_is_mod'] = author.is_mod

    if author:
        holder['author'] = author.name
        try:
            grab_author_attrib()
        except NotFound as err:
            pass
        except AttributeError as err:
            if 'is_suspended' in author.__dict__ and author.is_suspended:
                holder['user_is_suspended'] = True
            else:
                time.sleep(2)
                try:
                    grab_author_attrib()
                    print('Sleep for 2 second worked!!!')
                except:
                    pass
    else:
        holder['user_is_deleted'] = True


def init_count():
    """Initialize a counter dict to keep track of successes/errors"""
    count = {}
    count['posts_attempted'] = 0
    count['already_in_db'] = 0
    count['already_in_errors'] = 0
    count['rows_added'] = 0
    count['errors_added'] = 0
    return count


def process_so_rows(lines, table='Sampled'):
    """
    Args:
        lines - a list of of dicts, each corresponds to a row of data
    Returns:
        None
    """
    if table == 'Annotated':
        model = AnnotatedRedditPost
    else:
        model = SampledRedditThread
    count = init_count()
    for index, line in enumerate(lines):
        print(line)
        uid = line.get('id')
        try:
            model.objects.get_or_create(**line)
        except Exception as err:
            msg = 'Err loading SO post: {}'.format(err)
            ErrorLog.objects.get_or_create(uid=uid, msg=msg)


def process_reddit_rows(lines, reddit=None, parse_comments=False, table='Annotated'):
    """
    Args:
        lines:
            list of parsable json that will be converted to dicts
            OR
            list of dicts, each corresponding to a row of data

        Each row should have the following keys populated:
            'posts'
            'url'
    Returns:
        None
    """
    if table == 'Annotated':
        model = AnnotatedRedditPost
    else:
        model = SampledRedditThread
    count = init_count()
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            reader = json.loads(line)
        else:
            reader = line
        if reddit is None:
            raise ValueError('reddit API credentials do not work')
        post_id_dict = {}
        sub = {}
        if parse_comments:
            submission = reddit.submission(url=reader['url'])
            sub['id'] = submission.id
            sub['author'] = submission.author
            sub['body'] = submission.selftext
            sub['url'] = submission.url
            sub['score'] = submission.score
            sub['timestamp'] = submission.created_utc
            sub['context'] = submission.subreddit

            for post in reader['posts']:
                post_id_dict[post['id']] = post
                count['posts_attempted'] += 1
            submission.comment_sort = 'best'
            submission.comment_limit = 40 # only top 40 annotated
        else:
            sub['id'] = line['id']
            sub['author'] = reddit.redditor(line['author'])
            sub['body'] = line.get('selftext', "")
            sub['url'] = line.get('url')
            sub['score'] = line.get('score')
            sub['timestamp'] = line.get('created_utc')
            sub['context'] = line.get('subreddit')

        full_submission_id = 't3_' + sub['id']
        if full_submission_id not in post_id_dict:
            post_id_dict[full_submission_id] = {}
            count['posts_attempted'] += 1
        thread_in_db = ThreadLog.objects.filter(uid=full_submission_id)
        if thread_in_db.exists() and thread_in_db[0].complete:
            continue
        try:
            for key in ['body', 'url', 'score', 'timestamp', 'context']:
                post_id_dict[full_submission_id][key] = sub[key]
            post_id_dict[full_submission_id]['is_root'] = True
            extract_reddit_author_info(post_id_dict[full_submission_id], sub['author'])
        except Forbidden:
            print('Skipping Forbidden thread')
            continue

        if parse_comments:
            submission.comments.replace_more(limit=0)
            try:
                bfs_comments = submission.comments.list() # performs BFS!!
            except Exception as err:
                print('bfs comments.list() failed: {}'.format(err))
                bfs_comments = []
            for comment in bfs_comments:
                full_comment_id = 't1_' + comment.id
                if full_comment_id in post_id_dict:
                    post_id_dict[full_comment_id]['body'] = comment.body
                    post_id_dict[full_comment_id]['score'] = comment.score
                    post_id_dict[full_comment_id]['timestamp'] = comment.created_utc
                    post_id_dict[full_comment_id]['context'] = comment.subreddit
                    extract_reddit_author_info(
                        post_id_dict[full_comment_id], comment.author)

        for full_id, post in post_id_dict.items():
            post['uid'] = full_id
            in_db = model.objects.filter(uid=full_id).exists()
            in_error_logs = ErrorLog.objects.filter(uid=full_id).exists()
            if not in_db and not in_error_logs:
                try:
                    kwargs = extract_reddit_kwargs(post)
                    model.objects.create(**kwargs)
                    count['rows_added'] += 1
                except KeyError as err:
                    msg = 'Missing key: {}'.format(err)
                    ErrorLog.objects.get_or_create(uid=full_id, msg=msg)
                    count['errors_added'] += 1
            else:
                if in_db:
                    count['already_in_db'] += 1
                else:
                    count['already_in_errors'] += 1
        ThreadLog.objects.create(uid=full_submission_id, complete=True)



def read_from_discourse():
    """Populate sample from the reddit annotated dataset"""
    try:
        reddit = praw.Reddit(client_id=os.environ["CLIENT_ID"],
                             client_secret=os.environ["CLIENT_SECRET"],
                             user_agent=os.environ["UA"])
    except Exception as err:
        print(err)        
        raise ValueError('Authentication failed')


    with open('coarse_discourse_dataset.json') as jsonfile:
        lines = jsonfile.readlines()
        process_reddit_rows(lines, reddit, parse_comments=True, table='Annotated')


def sample_reddit_threads_from_bq():
    try:
        reddit = praw.Reddit(client_id=os.environ["CLIENT_ID"],
                             client_secret=os.environ["CLIENT_SECRET"],
                             user_agent=os.environ["UA"])
    except Exception as err:
        print(err)
        raise ValueError('Authentication failed')

    client = bigquery.Client()
    template = "SELECT {columns} FROM {table} WHERE RAND() < {fraction} LIMIT {limit};"
    cols = ['id', 'url', 'score', 'created_utc', 'author', 'subreddit', ]
    query_kwargs = {
        'columns': ', '.join(cols),
        'table': '`fh-bigquery.reddit_posts.2016_01`',
        'fraction': 0.001,
        'limit': 1000,
    }
    query = template.format(**query_kwargs)

    t_init = time.time()
    for i in range(0, 20):
        t_start = time.time()
        query_results = client.run_sync_query(query)
        query_results.use_legacy_sql = False
        query_results.run()

        resp = query_results.fetch_data(max_results=1000)
        
        row_dicts = []
        for row in resp:
            row_dict = {}
            for i, col in enumerate(cols):
                row_dict[col] = row[i]
            row_dicts.append(row_dict)
        process_reddit_rows(row_dicts, reddit, parse_comments=False, table='Sampled')
        t_end = time.time()
        print('Runtime for iteration {} was {}'.format(i, t_end - t_start))
    print('Total runtime was {}'.format(t_end - t_init))


# TODO
def sample_so_answers_from_bq():
    """
    Populate DB with random samples of SO answers from BigQuery
    """
    client = bigquery.Client()
    """
        SELECT
            FROM 
            LEFT JOIN `bigquery-public-data.stackoverflow.users`
            ON
            `bigquery-public-data.stackoverflow.posts_answers`.owner_user_id = `bigquery-public-data.stackoverflow.users`.id
            LIMIT 100;
    """
    # BigQuery columns to grab
    columns = [
        '`bigquery-public-data.stackoverflow.posts_answers`.body',
        '`bigquery-public-data.stackoverflow.posts_answers`.owner_user_id',
        '`bigquery-public-data.stackoverflow.users`.reputation',
        '`bigquery-public-data.stackoverflow.users`.creation_date',

    ]
    table = '`bigquery-public-data.stackoverflow.posts_answers`'
    template = "SELECT {columns} FROM {table} WHERE RAND() < {fraction} LIMIT {limit};"
    cols = ['id', 'url', 'score', 'created_utc', 'author', 'subreddit', ]
    query_kwargs = {
        'columns': ', '.join(cols),
        'table': '`fh-bigquery.reddit_posts.2016_01`',
        'fraction': 0.001,
        'limit': 1000,
    }
    query = template.format(**query_kwargs)

    t_init = time.time()
    for i in range(0, 20):
        t_start = time.time()
        query_results = client.run_sync_query(query)
        query_results.use_legacy_sql = False
        query_results.run()

        resp = query_results.fetch_data(max_results=1000)
        
        row_dicts = []
        for row in resp:
            row_dict = {}
            for i, col in enumerate(cols):
                row_dict[col] = row[i]
            row_dicts.append(row_dict)
        process_so_rows(row_dicts, table='Sampled')
        t_end = time.time()
        print('Runtime for iteration {} was {}'.format(i, t_end - t_start))
    print('Total runtime was {}'.format(t_end - t_init))




if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        Post, AnnotatedRedditPost, ErrorLog, ThreadLog, SampledRedditThread
    )
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "C:\\Users\\nickm\\Desktop\\research\\wikipedia_and_stack_overflow\\client_secrets.json"
    # read_from_discourse()
    sample_reddit_threads_from_bq()
