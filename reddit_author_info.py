import os
import sys
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
                ret['user_link_karma'] = author.link_karma
                ret['user_created_utc'] = utcstamp_to_utcdatetime(author.created_utc)
                ret['user_is_mod'] = author.is_mod
        except Exception as err:
            ret['user_is_deleted'] = True
        return ret
    return author_processor

def main(do_all=False):
    """driver"""
    reddit = praw.Reddit(
        client_id=os.environ["CLIENT_ID"], 
        client_secret=os.environ["CLIENT_SECRET"], user_agent=os.environ["UA"])
    processor = give_author_processor(reddit)
    if do_all:
        print('Reprocessing all reddit authors')
        qs = SampledRedditThread.objects.all()
    else:
        print('will only process new samples')
        qs = SampledRedditThread.objects.filter(user_info_processed=False)

    qs = qs.order_by('uid')
    start_time = time.time()
    for start, end, total, batch in batch_qs(qs):
        print(start, end, total, time.time()-start_time)
        for thread in batch:
            author_dict = processor(thread.author)
            for key, val in author_dict.items():
                setattr(thread, key, val)
            thread.user_info_processed = True
            thread.save()




if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    from django.db.utils import IntegrityError
    django.setup()
    from portal.models import (
        ErrorLog, ThreadLog, SampledRedditThread,
        SampledStackOverflowPost,
    )
    if len(sys.argv) > 1:
        main(True)
    else:
        main(False)