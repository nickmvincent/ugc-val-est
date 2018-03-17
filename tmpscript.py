def tmp_so():
    from portal.models import SampledStackOverflowPost
    noneng = SampledStackOverflowPost.objects.filter(has_wiki_link=True, day_of_avg_score__gt=0)
    count = 0
    for post in noneng:
        for link in post.wiki_links.all():
            if link.language_code != 'en':
                count += 1
                print(count)
                break
                


def tmp_reddit():
    from portal.models import SampledRedditThread
    noneng = SampledRedditThread.objects.filter(has_wiki_link=True,  day_of_avg_score__gt=0).exclude(url__icontains='en.wikipedia').exclude(url__icontains='en.m.wikipedia').exclude(url__icontains='www.wikipedia').exclude(url__icontains='//wikipedia')
    print(noneng.count())
    # for x in noneng:
    #     print(x.url)
    #     for link in x.wiki_links.all():
    #         print(link.__dict__)
    #         input()
# 787

def tmp_deleted():
    from portal.models import SampledRedditThread
    deleted = SampledRedditThread.objects.filter(body='[deleted]', sample_num__in=[0,1,2])
    print(deleted.count())
    deleted_with_wiki_link = SampledRedditThread.objects.filter(has_wiki_link=True, body='[deleted]', sample_num__in=[0,1,2])
    print(deleted_with_wiki_link.count())
# 141775
# 7504


def tmp():
    from portal.models import SampledStackOverflowPost
    errs = SampledStackOverflowPost.objects.filter(has_wiki_link=True, wiki_content_error=2)
    print(errs.count())
    for x in errs:
        print(x.url)
        input()