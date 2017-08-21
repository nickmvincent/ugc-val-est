"""
Helper functions to interface with DB so we don't have to use pgadmin...
"""
import os
import sys



def delete_old_errors():
    """one off script"""
    ErrorLog.objects.filter(msg__contains="not-null").delete()
    ErrorLog.objects.filter(msg="").delete()


def clear_json2db():
    """Delete entries populated by the json2db script"""
    for model in [
            RedditPost, StackOverflowAnswer, StackOverflowQuestion, StackOverflowUser
    ]:
        qs = model.objects.all()
        print('Going to delete {} entries from model {}'.format(qs.count(), model))
        print('Enter y to continue')
        if input() == 'y':
            qs.delete()


def reset_revision_info():
    """Reset"""
    for model in [SampledRedditThread, SampledStackOverflowPost]:
        model.objects.filter(wiki_content_analyzed=True).update(
            has_wiki_link=False,
            num_wiki_links=0,
            day_prior_avg_score=None,
            day_of_avg_score=None,
            week_after_avg_score=None,
            wiki_content_analyzed=False,
        )
    WikiLink.objects.all().delete()
    Revision.objects.all().delete()
    ErrorLog.objects.all().delete()


def show_samples():
    """Show samples of reddit threads"""
    samples = SampledRedditThread.objects.all()[:10]
    for sample in samples.values():
        print(sample)

    so_samples = SampledStackOverflowPost.objects.all()[:10]
    for sample in so_samples.values():
        print(sample)




def bulk_save():
    """Runs through all the rows and re-saves to trigger
    computation"""
    reddit = SampledRedditThread.objects.all().order_by('uid')
    stack = SampledStackOverflowPost.objects.all().order_by('uid')

    for start, end, total, batch in batch_qs(reddit):
        print('reddit', start, end, total)
        for item in batch:
            item.save()
    for start, end, total, batch in batch_qs(stack):
        print('stack', start, end, total)
        for item in batch:
            item.save()


def link_save():
    """
    Runs through all the rows and re-saves to trigger
    computation
    """
    reddit = SampledRedditThread.objects.filter(has_wiki_link=True).order_by('uid')
    stack = SampledStackOverflowPost.objects.filter(has_wiki_link=True).order_by('uid')

    for start, end, total, batch in batch_qs(reddit):
        print('reddit', start, end, total)
        for item in batch:
            item.save()
    for start, end, total, batch in batch_qs(stack):
        print('stack', start, end, total)
        for item in batch:
            item.save()


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        ErrorLog, SampledRedditThread,
        SampledStackOverflowPost,
        WikiLink, Revision,
        RedditPost, StackOverflowAnswer, StackOverflowQuestion, StackOverflowUser,
    )
    from queryset_helpers import batch_qs
    if len(sys.argv) > 1:
        if sys.argv[1] == 'delete':
            delete_old_errors()
        elif sys.argv[1] == 'reset_revision_info':
            reset_revision_info()
        elif sys.argv[1] == 'show':
            show_samples()
        elif sys.argv[1] == 'bulk_save':
            bulk_save()
        elif sys.argv[1] == 'link_save':
            link_save()
        elif sys.argv[1] == 'clear_json2db':
            clear_json2db()
