"""native imports"""
import json
import os
import time
from pprint import pprint

import praw

def populate_reddit_samples():
    try:
        reddit = praw.Reddit(client_id=os.environ["CLIENT_ID"],
                            client_secret=os.environ["CLIENT_SECRET"],
                            user_agent=os.environ["UA"])
        print('Authentication successful!')
    except Exception as err:
        reddit = None
        print('Authentication failed, will not connect to actual API')
        print(err)


    wiki_link_patterns = {
        'thread': 'wikipedia.org/wiki/',
    }

    with open('coarse_discourse_dataset.json') as jsonfile:
        lines = jsonfile.readlines()
        dump_with_reddit = open('coarse_discourse_dump_reddit.json', 'w')

        comments_queried = 0
        found_count = 0
        link_posts = 0
        wiki_thread_count = 0
        wiki_post_count = 0
        for index, line in enumerate(lines):
            if index % 100 == 0:
                print(index)
            reader = json.loads(line)
            if reader.get('is_self_post') is True:
                continue
            link_posts += 1
            url = reader['url']
            


            if reddit is None:
                for post in reader.get('posts', []):
                    pass
            else:
                submission = reddit.submission(url=reader['url'])
                if wiki_link_patterns['thread'] in submission.url:
                    wiki_thread_count += 1
                    print('Found wikipedia article!')

                # Annotators only annotated the 40 "best" comments determined by Reddit
                submission.comment_sort = 'best'
                submission.comment_limit = 40

                post_id_dict = {}

                for post in reader['posts']:
                    post_id_dict[post['id']] = post

                
                full_submission_id = 't3_' + submission.id
                if full_submission_id in post_id_dict:
                    post_id_dict[full_submission_id]['body'] = submission.selftext

                    # For a self-post, this URL will be the same URL as the thread.
                    # For a link-post, this URL will be the link that the link-post is linking to.
                    post_id_dict[full_submission_id]['url'] = submission.url
                    if submission.author:
                        post_id_dict[full_submission_id]['author'] = submission.author.name

                submission.comments.replace_more(limit=0)
                try:
                    comments = submission.comments.list()
                except Exception as err:
                    print('comments.list() failed: {}'.format(err))
                    comments = []
                for comment in comments:
                    full_comment_id = 't1_' + comment.id
                    if full_comment_id in post_id_dict:
                        post_id_dict[full_comment_id]['body'] = comment.body
                        if comment.author:
                            post_id_dict[full_comment_id]['author'] = comment.author.name


                for post in reader['posts']:
                    if post.get('body'):
                        found_count += 1
                
                comments_queried += len(reader['posts'])
                # print('Found %s posts out of %s' % (found_count, len(reader['posts'])))

                dump_with_reddit.write(json.dumps(reader) + '\n')

                # To keep within Reddit API limits
                time.sleep(1)
        print(wiki_thread_count)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import Post
    Post.objects.get_or_create(body='test', score=5)
    for obj in Post.objects.all():
        print(obj)
