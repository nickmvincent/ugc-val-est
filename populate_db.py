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
    return {
        'uid': post['id'],
        'timestamp': datetime.datetime.fromtimestamp(post['timestamp']).replace(tzinfo=pytz.UTC),
        'body': post['body'],
        'score': post['score'],
        'discourse_type': post['majority_type'],
        'user_comment_karma': post['comment_karma'],
        'user_link_karma': post['link_karma'],
        'user_created_utc':  datetime.datetime.fromtimestamp(
            post['created_utc']).replace(tzinfo=pytz.UTC),
        'user_is_mod': post['is_mod'],
    }
def extract_reddit_author_info(holder, author):
    """
    Args:
        dict - the dict to store stuff in
        author - the PRAW author object
    Returns:
        dict - the dict
    """
    holder['author'] = author.name
    holder['comment_karma'] = author.comment_karma
    holder['link_karma'] = author.link_karma
    holder['created_utc'] = author.created_utc
    holder['is_mod'] = author.is_mod



def process_reddit_rows(dict_rows, reddit=None):
    """
    Args:
        dict_rows - a list of dicts, each corresponding to a row of data
    Returns:
        None
    """
    comments_queried = 0
    found_count = 0
    link_posts = 0
    wiki_thread_count = 0
    for index, line in enumerate(dict_rows):
        if index % 100 == 0:
            print(index)
        reader = json.loads(line)
        if reader.get('is_self_post') is True:
            continue
        link_posts += 1

        if reddit is None:
            for post in reader.get('posts', []):
                pass
        else:
            submission = reddit.submission(url=reader['url'])
            # Annotators only annotated the 40 "best" comments determined by Reddit
            submission.comment_sort = 'best'
            submission.comment_limit = 40

            post_id_dict = {}
            for post in reader['posts']:
                post_id_dict[post['id']] = post
            full_submission_id = 't3_' + submission.id
            if full_submission_id in post_id_dict:
                post_id_dict[full_submission_id]['body'] = submission.selftext
                post_id_dict[full_submission_id]['url'] = submission.url
                post_id_dict[full_submission_id]['score'] = submission.score
                post_id_dict[full_submission_id]['timestamp'] = submission.created
                if submission.author:
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
                    if comment.author:
                        extract_reddit_author_info(
                            post_id_dict[full_comment_id], comment.author)
            say('Saving these comments to db')

            for post in reader['posts']:
                if post.get('body'):
                    found_count += 1
                    post['uid'] = post['id']
                    in_db=  AnnotatedRedditPost.objects.filter(uid=post['id']).exists()
                    in_error_logs = ErrorLog.objects.filter(uid=post['id']).exists()
                    if not in_db and not in_error_logs:
                        try:
                            kwargs = extract_reddit_kwargs(post)
                            AnnotatedRedditPost.objects.create(**kwargs)
                        except Exception as err:
                            msg = 'Msg: {}'.format(err)
                            ErrorLog.objects.create(
                                uid=post['uid'], msg=msg)
            comments_queried += len(reader['posts'])
            print('Found %s posts out of %s' % (found_count, len(reader['posts'])))
            # dump_with_reddit.write(json.dumps(reader) + '\n')
            time.sleep(1)
    print(wiki_thread_count)



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
    from portal.models import Post, AnnotatedRedditPost, ErrorLog

    populate_reddit_samples()
