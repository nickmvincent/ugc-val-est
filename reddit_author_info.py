import os
import time
from queryset_helpers import batch_qs, utcstamp_to_utcdatetime

import praw


def give_author_processor(reddit):
    """
    This function uses closures to
    take a "reddit" object and returns a function that will process author information using the reddit object
    """
    def author_processor(val):
        """Process author info"""
        ret = {}
        if val == '[deleted]':
            return {
                'user_is_deleted': True,
            }
        author = reddit.redditor(val)
        try:
            if getattr(author, 'is_suspended', None):
                ret['user_is_suspended'] = True
            else:
                ret['user_comment_karma'] = author.comment_karma
                ret['user_link_karma'] = author.comment_karma
                ret['user_created_utc'] = utcstamp_to_utcdatetime(author.created_utc)
                ret['user_is_mod'] = author.is_mod
        except:
            ret['user_is_deleted'] = True
        return ret
    return author_processor

def main():
    """driver"""
    reddit = praw.Reddit(
        client_id=os.environ["CLIENT_ID"], 
        client_secret=os.environ["CLIENT_SECRET"], user_agent=os.environ["UA"])
    processor = give_author_processor(reddit)
    qs = SampledRedditThread.objects.filter(user_info_processed=False)

    start_time = time.time()
    for start, end, total, batch in batch_qs(qs):
        batch_start_time = time.time()
        print(start, end, total)
        for thread in batch:
            print(thread.author)
            author_dict = processor(thread.author)
            for key, val in author_dict.items():
                setattr(thread, key, val)
            thread.user_info_processed = True
            thread.save()
        print('batch time was {}'.format(time.time() - batch_start_time))
        print('running time is {}'.format(time.time() - start_time))




if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    from django.db.utils import IntegrityError
    django.setup()
    from portal.models import (
        ErrorLog, ThreadLog, SampledRedditThread,
        SampledStackOverflowPost,
    )
    main()