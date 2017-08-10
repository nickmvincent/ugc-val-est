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


def show_sample_threads():
    """Show samples of reddit threads"""
    samples = SampledRedditThread.objects.all()[:5]
    for sample in samples.values():
        print(sample)
    
    so_samples = SampledStackOverflowPost.objects.all()[:5]
    for sample in so_samples.values():
        print(sample)


def calc_avg_scores():
    """
    Calculates average wiki scores at various time intervals
    """
    fields = ['day_prior',  'day_of', 'week_after', ]
    qs = SampledRedditThread.objects.filter(has_wiki_link=True)
    print(qs.count())
    for start, end, total, batch in batch_qs(qs):
        print(start, end, total)
        for thread in batch:
            n = 0
            field_to_score = {field: 0 for field in fields}
            for link_obj in thread.post_specific_wiki_links.all():
                for field in fields:
                    field_to_score[field] += getattr(link_obj, field).score
                n += 1
            output_field_to_val = {field + '_avg_score': val / n for field, val in field_to_score.items()}
            for output_field, val in output_field_to_val.items():
                setattr(thread, output_field, val)
            thread.save()


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        ErrorLog, ThreadLog, SampledRedditThread,
        SampledStackOverflowPost,
        WikiLink, RevisionScore, PostSpecificWikiScores
    )
    from queryset_helpers import batch_qs
    if len(sys.argv) > 1:
        if sys.argv[1] == 'delete':
            delete_old_errors()
        elif sys.argv[1] == 'reset':
            reset_wiki_links()
        elif sys.argv[1] == 'show':
            show_sample_threads()
        elif sys.argv[1] == 'calc_avg_scores':
            calc_avg_scores()