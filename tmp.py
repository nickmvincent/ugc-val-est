def tmp():
    from portal.models import SampledRedditThread
    from portal.models import Revision
    import datetime
    qs_r = SampledRedditThread.objects.filter(has_wiki_link=True)
    for post in qs_r:
        starttime = post.timestamp - datetime.timedelta(days=7)
        endtime = post.timestamp + datetime.timedelta(days=7)
        for link in post.wiki_links.all():
            num_revs = len(Revision.objects.filter(
                wiki_link=link,timestamp__gte=starttime, timestamp__lte=endtime))
            if num_revs > 500:
                print(link.url, post.timestamp)