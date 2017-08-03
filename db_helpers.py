"""
Helper functions to interface with DB so we don't have to use pgadmin...
"""
import os
import sys
from pprint import pprint


def show_errors():
    """Show error messages"""
    logs = ErrorLog.objects.all()
    print('There are {} total errors logged'.format(len(logs)))
    message_cache = {}
    for error_log in logs:
        msg = error_log.msg
        if msg not in message_cache:
            print(msg)
            message_cache[msg] = 0
        else:
            message_cache[msg] += 1
    pprint(message_cache)


def delete_old_errors():
    """one off script"""
    ErrorLog.objects.filter(msg__contains="not-null").delete()
    ErrorLog.objects.filter(msg="").delete()


def reset_wiki_checking():
    """Reset"""
    print('Resetting the wiki_analysis_done falg to False')
    SampledRedditThread.objects.filter(wiki_content_analyzed=True).update(
        wiki_content_analyzed=False)
    WikiLink.objects.all().delete()
    RevisionScore.objects.all().delete()
    PostSpecificWikiScores.objects.all().delete()

def show_sample_threads():
    """Show samples of reddit threads"""
    samples = SampledRedditThread.objects.all()[:5]
    for sample in samples.values():
        print(sample)
    
    so_samples = SampledStackOverflowPost.objects.all()[:5]
    for sample in so_samples.values():
        print(sample)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        ErrorLog, ThreadLog, SampledRedditThread,
        SampledStackOverflowPost,
        WikiLink, RevisionScore, PostSpecificWikiScores
    )
    if len(sys.argv) > 1:
        if sys.argv[1] == 'delete':
            delete_old_errors()
        elif sys.argv[1] == 'reset':
            reset_wiki_checking()
        elif sys.argv[1] == 'show':
            show_sample_threads()
    else:
        show_errors()