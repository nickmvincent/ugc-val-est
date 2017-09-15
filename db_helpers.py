"""
Helper functions to interface with DB so we don't have to use pgadmin...
"""
import os
import sys
import time
from collections import defaultdict
from pprint import pprint
import datetime
from queryset_helpers import (
    list_common_features,
    list_stack_specific_features,
    list_reddit_specific_features
)
import pytz


def clear_fixed_errors():
    """one off script"""
    count = 0
    for obj in ErrorLog.objects.all():
        if (
            SampledRedditThread.objects.filter(uid=obj.uid).exists() or
            SampledStackOverflowPost.objects.filter(uid=obj.uid).exists()):
            obj.delete()
            count += 1
    print('Deleted', count)
    for obj in ErrorLog.objects.all():
        print(obj)
        input()

def show_missing_errors():
    """one off script"""
    counter = defaultdict(int)
    qs = ErrorLog.objects.all().values()
    for obj in qs:
        if not (
            SampledRedditThread.objects.filter(uid=obj['uid']).exists() or
            SampledStackOverflowPost.objects.filter(uid=obj['uid']).exists()):
            counter[obj['msg']] += 1
            try:
                dic = SampledStackOverflowPost.objects.filter(id=obj['uid']).values()[0]
                print(obj)
            except:
                pass
            print('enter to continue')
            input()
    print(counter)
    print(len(qs))

def show_wiki_errors():
    for model in (SampledRedditThread, SampledStackOverflowPost):
        counter = defaultdict(int)
        qs = model.objects.exclude(wiki_content_error=0)
        for obj in qs:
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
        model.objects.filter(all_revisions_pulled=True).update(
            has_wiki_link=False,
            wiki_content_error=0,
            num_wiki_links=0,
            day_of_avg_score=None,
            week_after_avg_score=None,
            all_revisions_pulled=False,
        )
    WikiLink.objects.all().delete()
    Revision.objects.all().delete()
    ErrorLog.objects.all().delete()


def fix_bad_registration_time():
    fixed_time = datetime.datetime(year=2017, month=5, day=1).astimezone(pytz.UTC)
    Revision.objects.filter(registration__gte=fixed_time).update(
        registration=None
    )


def show_samples():
    """Show samples of reddit threads"""
    for model in [SampledRedditThread, ]: #SampledStackOverflowPost]:
        samples1 = model.objects.all().values()[:5]
        samples2 = model.objects.filter(has_wiki_link=True).values()[:5]
        for samples in [samples1, samples2]:
            for sample in samples:
                print(model.__name__)
                pprint(sample)
                print('====\n')



def bulk_save():
    """Runs through all the rows and re-saves to trigger
    computation"""
    reddit = SampledRedditThread.objects.all().order_by('uid')
    stack = SampledStackOverflowPost.objects.all().order_by('uid')

    start_time = time.time()
    for start, end, total, batch in batch_qs(reddit, batch_size=10000):
        print('reddit', start, end, total, time.time() - start_time)
        for item in batch:
            item.save()
    start = time.time()
    for start, end, total, batch in batch_qs(stack, batch_size=10000):
        print('stack', start, end, total, time.time() - start_time)
        for item in batch:
            item.save()


def bulk_save_rev():
    for obj in Revision.objects.all():
        obj.save()
    qs = Revision.objects.filter(user_retained_180=True)
    print(qs.count())

def link_save():
    """
    Runs through all the rows and re-saves to trigger
    computation
    """
    for link in WikiLink.objects.all():
        link.save()
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
    num_samples = 10
    models = [
        SampledRedditThread,
        SampledStackOverflowPost]
    for model in models:
        qs = model.objects.filter(has_wiki_link=True).order_by('?')[:num_samples]
        counter = 0
        for obj in qs:
            for wiki_link in obj.wiki_links.all():
                outfilename = 'html/{}_sample{}of{}.html'.format(
                    model.__name__, counter, num_samples
                )
                counter += 1
                if model == SampledRedditThread:
                    fields = [
                        obj.title, obj.context, str(obj.timestamp), wiki_link.title
                    ]
                else:
                    body = obj.body
                    body_as_list = body.split('<a')
                    final_body = 'Answered posted on: ' + str(obj.timestamp) + '\n'
                    for component in body_as_list:
                        if 'wikipedia.org/wiki/' in component:
                            final_body += '***'
                        final_body += '<a' + component
                    final_body = final_body[:-2]
                    fields = [final_body]

                line = ', '.join(fields)
                with open(outfilename, 'w') as outfile:
                    outfile.write(line + '\n')
                if model == SampledStackOverflowPost:
                    break # don't need to repeat for all links

def extract_pairs(first, second):
    filename = 'pair_{}_{}'.format(first, second)
    try:
        treated = SampledRedditThread.objects.get(uid=first)
        control = SampledRedditThread.objects.get(uid=second)
        url_template = 'https://www.reddit.com/by_id/t3_{}'
        features = list_common_features() + list_reddit_specific_features()
    except Exception:
        treated = SampledStackOverflowPost.objects.get(uid=first)
        control = SampledStackOverflowPost.objects.get(uid=second)
        url_template = 'https://stackoverflow.com/questions/{}'
        features = list_common_features() + list_stack_specific_features()
    
    treated_vals_string = '|'.join(['{}:{}'.format(
        feature, getattr(treated, feature)) for feature in features
    ])
    control_vals_string = '|'.join(['{}:{}'.format(
        feature, getattr(control, feature)) for feature in features
    ])
    treated_output = 'Treatment\n{}\n{}\n'.format(
        url_template.format(first),
        treated_vals_string
    )
    control_output = 'Control\n{}\n{}\n'.format(
        url_template.format(second),
        control_vals_string
    )
    with open(filename, 'w') as outfile:
        outfile.write(treated_output)
        outfile.write(control_output)

def clear_pre2016_so_pageviews():
    cutoff = datetime.datetime(year=2016, day=1, month=1, hour=0, minute=0, second=0)
    qs = SampledStackOverflowPost.objects.filter(timestamp__lt=cutoff)
    qs.update(num_wiki_pageviews=None, num_wiki_pageviews_prev_week=None)



def mark_top_answers():
    """marks top answers"""
    qs = SampledStackOverflowPost.objects.all().order_by('uid')
    for start, end, total, batch in batch_qs(qs, batch_size=10000):
        print(start, end, total)
        for answer in batch:
            try:
                question_id = StackOverflowAnswer.objects.using('secondary').filter(id=answer.uid).values('parent_id')[0]['parent_id']
                other_answers = StackOverflowAnswer.objects.using('secondary').filter(parent_id=question_id)
                max_score = other_answers.aggregate(Max('score'))['score__max']
                print(max_score)
                if answer.score == max_score:
                    print('marking top answer as true woohoo!')
                    answer.is_top = True
                    answer.save()
            except Exception as err:
                print(err)
                print('MISSING QUESTION UH OH')


def quick_helper():
    from portal.models import SampledRedditThread
    from portal.models import SampledStackOverflowPost

    # qs_r = SampledRedditThread.objects.filter(has_wiki_link=True)
    # for obj in qs_r:
    #     obj.save()
    #     if obj.num_edits > 3:
    #         print(obj.num_edits_prev_week, obj.num_edits, obj.timestamp)
    #         for link in obj.wiki_links.all():
    #             print(link.url)
    #         print('---')
    #         x = input()
    #         if x == 'y':
    #             print('breaking')
    #             break
    # for obj in qs_s:
    #     obj.save()
    #     if obj.num_edits > 25:
    #         print(obj.num_edits_prev_week, obj.num_edits, obj.timestamp)
    #         for link in obj.wiki_links.all():
    #             print(link.url)
    #         print('---')
    #         x = input()
    #         if x == 'y':
    #             break
    wiki_links = WikiLink.objects.filter(title='SQL_injection')
    for link in wiki_links:
        posts = SampledStackOverflowPost.objects.filter(wiki_links=link)
        for post in posts:
            post.save()
            print(post.num_edits, post.num_edits_prev_week)
            input()
    
    


def check_dupe_wikilinks():
    from portal.models import SampledRedditThread
    from portal.models import SampledStackOverflowPost

    cache = {}
    qs_r = SampledRedditThread.objects.filter(has_wiki_link=True)
    qs_s = SampledStackOverflowPost.objects.filter(has_wiki_link=True)
    count = 0
    for obj in qs_r:
        has_err = False
        links = obj.wiki_links.all()
        for link in links:
            matching_links = WikiLink.objects.filter(title=link.title)
            for matching_link in matching_links:
                matching_reddit_posts = SampledRedditThread.objects.filter(wiki_links=matching_link)
                matching_so_posts = SampledRedditThread.objects.filter(wiki_links=matching_link)
                for matching_qs in [matching_reddit_posts, matching_so_posts]:
                    for post in matching_qs:
                        if post.uid == obj.uid:
                            continue
                        elif post.uid in cache:
                            continue
                        else:
                            cache[post.uid] = True
                            dt = obj.timestamp - post.timestamp
                            val = abs(dt.total_seconds())
                            if val < 1.21e6: # 14 days
                                has_err = True
                                before = post.num_edits, post.num_edits_prev_week
                                post.save()
                                after = post.num_edits, post.num_edits_prev_week
                                if after[0] - before[0] != 0 or after[1] - before[1] != 0:
                                    print(before, after)
                                    count += 1
        if has_err:
            obj.save()
            cache[obj.uid] = True
    print(count)




if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from django.db.models import Max

    from portal.models import (
        ErrorLog, SampledRedditThread,
        SampledStackOverflowPost,
        WikiLink, Revision,
        RedditPost, StackOverflowAnswer, StackOverflowQuestion, StackOverflowUser,
    )
    from queryset_helpers import batch_qs
    if len(sys.argv) > 1:
        if sys.argv[1] == 'clear_fixed_errors':
            clear_fixed_errors()
        elif sys.argv[1] == 'reset_revision_info':
            reset_revision_info()
        elif sys.argv[1] == 'show_samples':
            show_samples()
        elif sys.argv[1] == 'bulk_save':
            bulk_save()
        elif sys.argv[1] == 'bulk_save_rev':
            bulk_save_rev()
        elif sys.argv[1] == 'link_save':
            link_save()
        elif sys.argv[1] == 'clear_json2db':
            clear_json2db()
        elif sys.argv[1] == 'show_wiki_errors':
            show_wiki_errors()
        elif sys.argv[1] == 'show_missing_errors':
            show_missing_errors()
        elif sys.argv[1] == 'sample_articles':
            sample_articles()
        elif sys.argv[1] == 'extract_pairs':
            extract_pairs(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == 'fix_bad_registration_time':
            fix_bad_registration_time()
        elif sys.argv[1] == 'mark_top_answers':
            mark_top_answers()
        elif sys.argv[1] == 'quick_helper':
            quick_helper()
        elif sys.argv[1] == 'check_dupe_wikilinks':
            check_dupe_wikilinks()
