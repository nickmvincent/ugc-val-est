"""
Helper functions to interface with DB so we don't have to use pgadmin...
"""
import os
import sys
from collections import defaultdict
from pprint import pprint


def delete_old_errors():
    """one off script"""
    ErrorLog.objects.filter(msg__contains="not-null").delete()
    ErrorLog.objects.filter(msg="").delete()


def show_wiki_errors():
    for model in (SampledRedditThread, SampledStackOverflowPost):
        counter = defaultdict(int)
        qs = model.objects.exclude(wiki_content_error=0)
        for obj in qs.values():
            if obj.get('url'):
                print(obj['url'])
            else:
                print(obj['body'])
            print(obj['wiki_content_error'])
            counter[obj['wiki_content_error']] += 1
        pprint(counter)


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
            wiki_content_error=0,
            num_wiki_links=0,
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

def sample_articles():
    """Prints out a sample of URLs to text file"""
    num_samples = 50
    models = [SampledRedditThread, SampledStackOverflowPost]
    for model in models:
        outfilename = '{}_{}_articles.txt'.format(
            model.__name__, num_samples
        )
        with open(outfilename, 'w') as outfile:
            qs = model.objects.filter(has_wiki_link=True).exclude(context='todayilearned').exclude(context__icontains='borntoday').order_by('?')[:num_samples]
            for obj in qs:
                for wiki_link in obj.wiki_links.all():
                    if model == SampledRedditThread:
                        fields = [
                            obj.title, obj.context, str(obj.timestamp), wiki_link.title
                        ]
                    else:
                        fields = [wiki_link.title, str(obj.timestamp)]
                    line = ', '.join(fields)
                    print(line)
                    outfile.write(line + '\n')


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
        elif sys.argv[1] == 'show_wiki_errors':
            show_wiki_errors()
        elif sys.argv[1] == 'sample_articles':
            sample_articles()
