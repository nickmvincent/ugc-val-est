"""native imports"""
import json
import os
import time
import datetime

import pytz
import praw
from prawcore.exceptions import Forbidden, NotFound
from google.cloud import bigquery
from explore import get_reddit_tables


def utcstamp_to_utcdatetime(timestamp):
    """Takes a UTC stamp and returns UTC datetime"""
    return datetime.datetime.fromtimestamp(timestamp).replace(tzinfo=pytz.UTC)


def default_to_zero(val):
    """Return zero if val is None"""
    return 0 if val is None else val

def extract_reddit_kwargs(post):
    """Extract needed kwargs to make a db entry for a reddit post"""
    ret = {}
    for key in ['uid', 'body', 'score', 'is_root', 'context', 'num_comments',]:
        ret[key] = post[key]
    for key in ['user_comment_karma', 'user_link_karma', 'user_is_mod', 'user_is_deleted']:
        ret[key] = post.get(key, 0)
    ret['timestamp'] = utcstamp_to_utcdatetime(post['timestamp'])

    if post.get('user_created_utc'):
        ret['user_created_utc'] = utcstamp_to_utcdatetime(post['user_created_utc'])
    else: # if a user 
        ret['user_created_utc'] = ret['timestamp']
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
        except NotFound:
            pass
        except AttributeError:
            if 'is_suspended' in author.__dict__ and author.is_suspended:
                holder['user_is_suspended'] = True
            else:
                time.sleep(2)
                try:
                    grab_author_attrib()
                    print('Sleep for 2 second worked!!!')
                except AttributeError:
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


def process_reddit_rows(lines, model, reddit=None, parse_comments=False):
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
    count = init_count()
    for line in lines:
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
            submission.comment_limit = 40  # only top 40 annotated
        else:
            sub['id'] = line['id']
            sub['author'] = reddit.redditor(line['author'])
            sub['body'] = line.get('selftext', "")
            sub['url'] = line.get('url')
            sub['score'] = line.get('score')
            sub['num_comments'] = line.get('num_comments')
            sub['timestamp'] = line.get('created_utc')
            sub['context'] = line.get('subreddit')

        full_submission_id = 't3_' + sub['id']
        if full_submission_id not in post_id_dict:
            post_id_dict[full_submission_id] = {}
            count['posts_attempted'] += 1
        thread_in_db = ThreadLog.objects.filter(uid=full_submission_id)
        if thread_in_db.exists() and thread_in_db[0].complete:
            count['already_in_db'] += 1
            continue
        try:
            for key in ['body', 'url', 'score', 'num_comments', 'timestamp', 'context']:
                post_id_dict[full_submission_id][key] = sub[key]
            post_id_dict[full_submission_id]['is_root'] = True
            extract_reddit_author_info(
                post_id_dict[full_submission_id], sub['author'])
        except Forbidden:
            print('Skipping Forbidden thread')
            continue

        if parse_comments:
            submission.comments.replace_more(limit=0)
            try:
                bfs_comments = submission.comments.list()  # performs BFS!!
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
                    print(msg)
                    ErrorLog.objects.get_or_create(uid=full_id, msg=msg)
                    count['errors_added'] += 1
            else:
                if in_db:
                    count['already_in_db'] += 1
                else:
                    count['already_in_errors'] += 1
        ThreadLog.objects.create(uid=full_submission_id, complete=True)
    print(count)




def sample_reddit_threads_from_bq():
    """
    Randomly sample rows from BigQuery corresponding the reddit threads,
    aka submissions (NOT COMMENT)
    """
    try:
        reddit = praw.Reddit(client_id=os.environ["CLIENT_ID"],
                             client_secret=os.environ["CLIENT_SECRET"],
                             user_agent=os.environ["UA"])
    except Exception as err:
        print(err)
        raise ValueError('Authentication failed')

    client = bigquery.Client()
    template = "SELECT {columns} FROM {table} WHERE RAND() < {fraction} LIMIT {limit};"
    cols = ['id', 'url', 'score', 'created_utc', 'author', 'subreddit', 'num_comments',]
    # table = '`fh-bigquery.reddit_posts.2016_01`'
    tables = get_reddit_tables()
    times = {}    
    times['init'] = time.time()
    rows_to_sample = 12000
    rows_per_query = 1000

    rows_per_iteration = rows_per_query * len(tables)
    iterations_needed = int(rows_to_sample / rows_per_iteration)
    print('To sample {} rows, will use {} iterations with {} rows per iteration'.format(
        rows_to_sample, iterations_needed, rows_per_iteration
    ))
    for iteration in range(0, iterations_needed):
        times['start'] = time.time()
        for table in tables:
            query_kwargs = {
                'columns': ', '.join(cols),
                'table': table,
                'fraction': 0.1,
                'limit': rows_per_query,
            }
            query = template.format(**query_kwargs)
            query_results = client.run_sync_query(query)
            query_results.use_legacy_sql = False
            query_results.run()
            row_dicts = []
            for row in query_results.fetch_data(max_results=1000):
                row_dict = {}
                for i, col in enumerate(cols):
                    row_dict[col] = row[i]
                row_dicts.append(row_dict)
            process_reddit_rows(row_dicts, SampledRedditThread, reddit,
                                parse_comments=False)
            print(table)
        times['end'] = time.time()
        print('Runtime for iteration {} was {}'.format(
            iteration, times['end'] - times['start']))
    print(times['end'] - times['init'])
    # 894


def process_so_rows(lines, model):
    """
    Args:
        lines - a list of of dicts, each corresponds to a row of data
    Returns:
        None
    """
    count = init_count()
    for line in lines:
        uid = line.get('uid')
        count['posts_attempted'] += 1
        try:
            _, created = model.objects.get_or_create(**line)
            if created:
                count['rows_added'] += 1
            else:
                count['already_in_db'] += 1
        except Exception as err:
            msg = 'Err loading SO post: {}'.format(err)
            log, created = ErrorLog.objects.get_or_create(uid=uid)
            log.msg = msg[:254]
            log.save()
            if created:
                count['errors_added'] += 1
            else:
                count['already_in_errors'] += 1
    print(count)


SO_ANSWERS_TABLE = '`bigquery-public-data.stackoverflow.posts_answers`'
SO_USERS_TABLE = '`bigquery-public-data.stackoverflow.users`'

def sample_so_answers_from_bq():
    """
    Populate DB with random samples of SO answers from BigQuery
    """
    print('Going to populate SO Answers from BigQuery...')
    client = bigquery.Client()
    col_objects = [
        {
            'bq_name': SO_ANSWERS_TABLE + '.body',
            'dja_name': 'body',
        },
        {
            'bq_name': SO_ANSWERS_TABLE + '.id',
            'dja_name': 'uid',
        },
        {
            'bq_name': SO_ANSWERS_TABLE + '.score',
            'dja_name': 'score',
        },
        {
            'bq_name': SO_ANSWERS_TABLE + '.creation_date',
            'dja_name': 'timestamp',
        },
        {
            'bq_name': SO_USERS_TABLE + '.reputation',
            'dja_name': 'user_reputation',
            'processing': default_to_zero,
        },
        {
            'bq_name': SO_USERS_TABLE + '.creation_date as user_created_utc',
            'dja_name': 'user_created_utc',
        },
    ]
    table = "{answers} LEFT JOIN {users} ON {answers}.owner_user_id = {users}.id".format(
        **{'answers': SO_ANSWERS_TABLE, 'users': SO_USERS_TABLE})
    template = "SELECT {columns} FROM {table} WHERE RAND() < {fraction} LIMIT {limit};"
    query_kwargs = {
        'columns': ', '.join([x['bq_name'] for x in col_objects]),
        'table': table,
        'fraction': 0.001,
        'limit': 1000,
    }
    query = template.format(**query_kwargs)
    print(query)
    t_init = time.time()
    for iteration in range(0, 20):
        t_start = time.time()
        query_results = client.run_sync_query(query)
        query_results.use_legacy_sql = False
        query_results.run()

        resp = query_results.fetch_data(max_results=1000)

        row_dicts = []
        for row in resp:
            row_dict = {}
            for i, obj in enumerate(col_objects):
                val = row[i]
                if obj.get('processing'):
                    val = obj['processing'](val)
                row_dict[obj['dja_name']] = val
            if row_dict['user_created_utc'] is None:
                row_dict['user_created_utc'] = row_dict['timestamp']
            row_dicts.append(row_dict)
        process_so_rows(row_dicts, model=SampledStackOverflowPost)
        t_end = time.time()
        print('Runtime for iteration {} was {}'.format(
            iteration, t_end - t_start))
    print('Total runtime was {}'.format(t_end - t_init))


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        ErrorLog, ThreadLog, SampledRedditThread,
        SampledStackOverflowPost,
    )
    print('Ready to begin "populate_db" script')
    sample_reddit_threads_from_bq()
    # sample_so_answers_from_bq()
