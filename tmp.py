def tmp():
    from portal.models import SampledStackOverflowPost
    base = SampledStackOverflowPost.objects.all()
    qs1 = base.filter(has_wiki_link=True)
    qs2 = base.filter(has_other_link=True)
    qs3 = base.filter(has_no_link=True)
    n1, n2, n3 = qs1.count(), qs2.count(), qs3.count()
    x = sum([n1, n2, n3])
    print(n1, n2, n3, x, base.count())