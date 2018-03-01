def tmp():
    from portal.models import SampledRedditThread
    noneng = SampledRedditThread.objects.filter(has_wiki_link=True).exclude(url__contains='en.wikipedia').exclude(url__contains='en.m.wikipedia').exclude(url__contains='www.wikipedia').exclude(url__contains='//wikipedia')
    print(noneng.count())
    for x in noneng:
        print(x.url)
        input()