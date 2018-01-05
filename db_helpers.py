"""
Helper functions to interface with DB so we don't have to use pgadmin...
"""
import os
import sys
import time
from collections import defaultdict
from pprint import pprint, pformat
import datetime
from queryset_helpers import (
    list_common_features,
    list_stack_specific_features,
    list_reddit_specific_features
)
import pytz


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


def show_samples():
    """Show samples of all posts"""
    out = []
    for model in [SampledRedditThread, SampledStackOverflowPost]:
        samples1 = model.objects.all().values()[:2]
        samples2 = model.objects.filter(has_wiki_link=True).values()[:2]
        for index, samples in enumerate([samples1, samples2]):
            for sample in samples:
                out.append(model.__name__ + str(index))
                out.append(pformat(sample))
                out.append('===')
    with open('show_samples.txt', 'w') as outfile:
        outfile.write('\n'.join(out))


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
    # start = time.time()
    # for start, end, total, batch in batch_qs(stack, batch_size=10000):
    #     print('stack', start, end, total, time.time() - start_time)
    #     for item in batch:
    #         item.save()


def bulk_save_rev():
    for obj in Revision.objects.all():
        obj.save()
    qs = Revision.objects.filter(user_retained_180=True)
    print(qs.count())

def save_links_and_posts():
    """
    Runs through all the rows and re-saves to trigger
    computation
    """
    # print('saving links... (slow)')
    # for link in WikiLink.objects.all():
    #     link.save()
    print('saving posts... (slow)')
    reddit = SampledRedditThread.objects.filter(has_wiki_link=True, sample_num__in=[0,1,2]).order_by('uid')
    for start, end, total, batch in batch_qs(reddit):
        print('reddit', start, end, total)
        for item in batch:
            item.save()
    # stack = SampledStackOverflowPost.objects.filter(has_wiki_link=True, sample_num__in=[0,1,2]).order_by('uid')
    # for start, end, total, batch in batch_qs(stack):
    #     print('stack', start, end, total)
    #     for item in batch:
    #         item.save()

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


def print_link_titles_and_redirects():
    links = WikiLink.objects.all().order_by('?')[:10]
    for link in links:
        print(link.url)
        print(link.title)
        print(link.alt_title)


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

WIK = 'wikipedia.org/wiki/'
def print_potential_wikilinks():
    from url_helpers import extract_urls
    import csv
    qs_r = SampledRedditThread.objects.filter(
        url__contains=WIK, has_wiki_link=False, sample_num__in=[0,1,2])
    qs_s = SampledStackOverflowPost.objects.filter(
        body__contains=WIK, has_wiki_link=False, sample_num__in=[0,1,2])
    url_list = []
    for index, qs in enumerate([qs_r, qs_s]):
        print('===')
        print(len(qs))
        for post in qs:
            urls = extract_urls(post.body, WIK) if index == 1 else [post.url]
            for url in urls:
                if 'File:' in url or 'File%3a' in url or 'File%3A' in url:
                    continue
                if 'www.google' in url:
                    continue
                else:
                    print(url)
                    url_list.append(url)
    print(len(url_list))
    with open('url_list.csv', 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        for url in url_list:
            writer.writerow([url])

    # write out links that had a 

    qs_r = SampledRedditThread.objects.filter(
        has_wiki_link=True, day_of_avg_score__isnull=True, sample_num__in=[0,1,2])
    qs_s = SampledStackOverflowPost.objects.filter(
        has_wiki_link=True, day_of_avg_score__isnull=True, sample_num__in=[0,1,2])
    has_link_but_no_ores = []
    errs = defaultdict(int)
    for index, qs in enumerate([qs_r, qs_s]):
        for post in qs:
            urls = extract_urls(post.body, WIK) if index == 1 else [post.url]
            if post.wiki_content_error == 0:
                has_link_but_no_ores.append(urls)
            else:
                errs[post.wiki_content_error] += 1
    with open('has_link_but_no_ores.csv', 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(has_link_but_no_ores)
    print(errs)
            

def clean_then_delete():
    ErrorLog.objects.delete()


def check_on_revisions():
    no_users = Revision.objects.filter(user__isnull=True)
    print('There are {} revs with null user field'.format(len(no_users)))
    print(no_users[:5])

    no_timestamps = Revision.objects.filter(timestamp__isnull=True)
    print('There are {} revs with null timestamp field'.format(len(no_timestamps)))
    print(no_timestamps[:5])    


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
        elif sys.argv[1] == 'save_links_and_posts':
            save_links_and_posts()
        elif sys.argv[1] == 'clear_json2db':
            clear_json2db()
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
        elif sys.argv[1] == 'clear_pre2016_so_pageviews':
            clear_pre2016_so_pageviews()
        elif sys.argv[1] == 'print_potential_wikilinks':
            print_potential_wikilinks()
        elif sys.argv[1] == 'clean_then_delete':
            clean_then_delete()
        elif sys.argv[1] == 'check_on_revisions':
            check_on_revisions() 