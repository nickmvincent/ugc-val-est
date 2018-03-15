def tmp():
    from portal.models import SampledStackOverflowPost
    noneng = SampledStackOverflowPost.objects.filter(has_wiki_link=True).exclude(body__contains='en.wikipedia').exclude(body__contains='en.m.wikipedia').exclude(body__contains='www.wikipedia').exclude(body__contains='//wikipedia')
    print(noneng.count())
    for x in noneng:
        print(x.body)
        input()

def tmp():
    from portal.models import SampledStackOverflowPost
    errs = SampledStackOverflowPost.objects.filter(has_wiki_link=True, wiki_content_error=2)
    print(errs.count())
    for x in errs:
        print(x.url)
        input()