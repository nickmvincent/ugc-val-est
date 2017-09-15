def tmp():
    from portal.models import SampledRedditThread
    from portal.models import SampledStackOverflowPost

    qs_r = SampledRedditThread.objects.filter(has_wiki_link=True)[:5]
    qs_s = SampledStackOverflowPost.objects.filter(has_wiki_link=True)[:5]
    for obj in qs_r:
        print(obj.num_edits_prev_week, obj.num_edits, obj.timestamp)
        for link in obj.wiki_links.all():
            print(link.url)
        print('---')
        input()
    for obj in qs_s:
        print(obj.num_edits_prev_week, obj.num_edits, obj.timestamp)
        for link in obj.wiki_links.all():
            print(link.url)
        print('---')
        input()
tmp()