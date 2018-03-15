def tmp_so():
    from portal.models import SampledStackOverflowPost
    noneng = SampledStackOverflowPost.objects.filter(has_wiki_link=True)
    count = 0
    for post in noneng:
        for link in post.wiki_links.all():
            if link.language_code != 'en':
                count += 1
                print(count)


def tmp_reddit():
    from portal.models import SampledRedditThread
    noneng = SampledRedditThread.objects.filter(has_wiki_link=True, has_good_wiki_link=True).exclude(url__contains='en.wikipedia').exclude(url__contains='en.m.wikipedia').exclude(url__contains='www.wikipedia').exclude(url__contains='//wikipedia')
    print(noneng.count())
    for x in noneng:
        print(x.url)
        for link in x.wiki_links.all():
            print(link.__dict__)
            input()

def tmp():
    from portal.models import SampledStackOverflowPost
    errs = SampledStackOverflowPost.objects.filter(has_wiki_link=True, wiki_content_error=2)
    print(errs.count())
    for x in errs:
        print(x.url)
        input()