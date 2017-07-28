"""native imports"""
import json
import os
import time
import datetime
from pprint import pprint

import pytz
import praw

VERBOSE = True
def say(msg):
    """Print only if VERBOSE is True"""
    if VERBOSE:
        print(msg)

# PURITY LOVERS BEWARE
# this function is REMARKABLY IMPURE
def extract_reddit_kwargs(post):
    """Extract needed kwargs to make a db entry for a reddit post"""
    ret = {
        'uid': post['id'],
        'timestamp': datetime.datetime.fromtimestamp(post['timestamp']).replace(tzinfo=pytz.UTC),
        'body': post['body'],
        'score': post['score'],
        'discourse_type': post.get('majority_type', 'root'),
        'user_comment_karma': post.get('comment_karma', 0),
        'user_link_karma': post.get('link_karma', 0),
        'user_is_mod': post.get('is_mod', False),
        'user_is_deleted': post.get('user_is_deleted', False),
    }
    if post.get('created_utc'):
        ret['user_created_utc'] = datetime.datetime.fromtimestamp(
            post['created_utc']).replace(tzinfo=pytz.UTC)
    return ret


def extract_reddit_author_info(holder, author):
    """
    Args:
        dict - the dict to store stuff in
        author - the PRAW author object
    Returns:
        dict - the dict
    """
    if author:
        holder['author'] = author.name
        try:
            holder['comment_karma'] = author.comment_karma
            holder['link_karma'] = author.link_karma
            holder['created_utc'] = author.created_utc
            holder['is_mod'] = author.is_mod
        except Exception as err:
            print(err)
            if 'is_suspended' in author.__dict__ and author.is_suspended:
                holder['is_mod'] = False
                print('author is suspended, moving on...')
            else:
                print(author.__dict__)
                time.sleep(2)
                try:
                    holder['comment_karma'] = author.comment_karma
                    holder['link_karma'] = author.link_karma
                    holder['created_utc'] = author.created_utc
                    holder['is_mod'] = author.is_mod
                    print('Sleep for 1 second worked!!!')
                except:
                    print('Really cannot get comment_karma...')
    else:
        holder['user is_deleted'] = True


def process_reddit_rows(dict_rows, reddit=None):
    """
    Args:
        dict_rows - a list of dicts, each corresponding to a row of data
    Returns:
        None
    """
    count = {}
    count['posts_attempted'] = 0
    count['already_in_db'] = 0
    count['already_in_errors'] = 0
    count['rows_added'] = 0
    count['errors_added'] = 0

    for index, line in enumerate(dict_rows):
        if index % 10 == 0:
            print('Threads analyzed: {}'.format(index))
            pprint(count)
        reader = json.loads(line)

        if reddit is None:
            pass
        else:
            submission = reddit.submission(url=reader['url'])
            # Annotators only annotated the 40 "best" comments determined by Reddit
            submission.comment_sort = 'best'
            submission.comment_limit = 40

            post_id_dict = {}
            for post in reader['posts']:
                post_id_dict[post['id']] = post
                count['posts_attempted'] += 1
            full_submission_id = 't3_' + submission.id
            thread_in_db = ThreadLog.objects.filter(uid=full_submission_id)
            if thread_in_db.exists() and thread_in_db[0].complete:
                continue
            if full_submission_id in post_id_dict:
                post_id_dict[full_submission_id]['body'] = submission.selftext
                post_id_dict[full_submission_id]['url'] = submission.url
                post_id_dict[full_submission_id]['score'] = submission.score
                post_id_dict[full_submission_id]['timestamp'] = submission.created
                post_id_dict[full_submission_id]['is_root'] = reader.get('is_self_post', False)
                extract_reddit_author_info(
                    post_id_dict[full_submission_id], submission.author)
                        
            else:
                say('Cannot find root post')

            submission.comments.replace_more(limit=0)
            try:
                bfs_comments = submission.comments.list() # performs BFS!!
            except Exception as err:
                say('comments.list() failed: {}'.format(err))
                bfs_comments = []
            for comment in bfs_comments:
                full_comment_id = 't1_' + comment.id
                if full_comment_id in post_id_dict:
                    post_id_dict[full_comment_id]['body'] = comment.body
                    post_id_dict[full_comment_id]['score'] = comment.score
                    post_id_dict[full_comment_id]['timestamp'] = comment.created
                    extract_reddit_author_info(
                        post_id_dict[full_comment_id], comment.author)
            say('Saving these comments to db')

            for post in reader['posts']:
                
                post['uid'] = post['id']
                in_db = AnnotatedRedditPost.objects.filter(uid=post['id']).exists()
                in_error_logs = ErrorLog.objects.filter(uid=post['id']).exists()
                if not in_db and not in_error_logs:
                    try:
                        kwargs = extract_reddit_kwargs(post)
                        AnnotatedRedditPost.objects.create(**kwargs)
                        count['rows_added'] += 1
                    except Exception as err:
                        msg = 'Msg: {}'.format(err)
                        pprint(post)
                        print(msg)
                        input()

                        ErrorLog.objects.get_or_create(
                            uid=post['id'], msg=msg)
                        count['errors_added'] += 1
                else:
                    if in_db:
                        count['already_in_db'] += 1
                    else:
                        count['already_in_errors'] += 1
            ThreadLog.objects.create(uid=full_submission_id, complete=True)

            # dump_with_reddit.write(json.dumps(reader) + '\n')



def populate_reddit_samples():
    """Populate sample from the reddit annotated dataset"""
    try:
        reddit = praw.Reddit(client_id=os.environ["CLIENT_ID"],
                             client_secret=os.environ["CLIENT_SECRET"],
                             user_agent=os.environ["UA"])
        print('Authentication successful!')
    except Exception as err:
        reddit = None
        print('Authentication failed, will not connect to actual API')
        print(err)


    with open('coarse_discourse_dataset.json') as jsonfile:
        lines = jsonfile.readlines()
        process_reddit_rows(lines, reddit)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import Post, AnnotatedRedditPost, ErrorLog, ThreadLog

    populate_reddit_samples()
