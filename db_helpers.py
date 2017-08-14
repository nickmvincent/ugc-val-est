"""
Helper functions to interface with DB so we don't have to use pgadmin...
"""
import os
import sys
from pprint import pprint



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


def reset_wiki_links():
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
    RevisionScore.objects.all().delete()
    PostSpecificWikiScores.objects.all().delete()
    WikiLink.objects.all().delete()
    ErrorLog.objects.all().delete()


def show_samples():
    """Show samples of reddit threads"""
    samples = SampledRedditThread.objects.all()[:10]
    for sample in samples.values():
        print(sample)
    
    so_samples = SampledStackOverflowPost.objects.all()[:10]
    for sample in so_samples.values():
        print(sample)


def calc_avg_scores():
    """
    Calculates average wiki scores at various time intervals
    """
    fields = ['day_prior',  'day_of', 'week_after', ]
    reddit_threads = SampledRedditThread.objects.filter(has_wiki_link=True).order_by('uid')
    stack_posts = SampledStackOverflowPost.objects.filter(has_wiki_link=True).order_by('uid')
    for qs in [reddit_threads, stack_posts]:
        num_errors = 0
        for start, end, total, batch in batch_qs(qs):
            print(start, end, total)
            for thread in batch:
                num_links = 0
                field_to_score = {field: 0 for field in fields}
                for link_obj in thread.post_specific_wiki_links.all():
                    for field in fields:
                        field_to_score[field] += getattr(link_obj, field).score
                    num_links += 1
                if num_links == 0:
                    print(thread.wiki_content_error, end='|')
                    num_errors += 1
                    continue
                output_field_to_val = {field + '_avg_score': val / num_links for field, val in field_to_score.items()}
                for output_field, val in output_field_to_val.items():
                    setattr(thread, output_field, val)
                thread.save()
        print('\n num_errors', num_errors)


def bulk_save():
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




if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        ErrorLog, ThreadLog, SampledRedditThread,
        SampledStackOverflowPost,
        WikiLink, RevisionScore, PostSpecificWikiScores,
        RedditPost, StackOverflowAnswer, StackOverflowQuestion, StackOverflowUser
    )
    from queryset_helpers import batch_qs
    if len(sys.argv) > 1:
        if sys.argv[1] == 'delete':
            delete_old_errors()
        elif sys.argv[1] == 'reset':
            reset_wiki_links()
        elif sys.argv[1] == 'show':
            show_samples()
        elif sys.argv[1] == 'calc_avg_scores':
            calc_avg_scores()
        elif sys.argv[1] == 'bulk_save':
            bulk_save()
        elif sys.argv[1] == 'clear_json2db':
            clear_json2db()