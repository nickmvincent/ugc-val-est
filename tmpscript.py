def tmp():
    from portal.models import SampledRedditThread, WikiLink, Revision
    from django.db import models
    import datetime
    thread = SampledRedditThread.objects.get(uid='3z09iu')
    for link_obj in thread.wiki_links.all():
        print(link_obj.title)
        all_possible_links = WikiLink.objects.filter(
            models.Q(title__in=[link_obj.title, link_obj.alt_title]) | models.Q(alt_title__in=[link_obj.title, link_obj.alt_title])
        )
        starttime = thread.timestamp - datetime.timedelta(days=7)
        endtime = thread.timestamp + datetime.timedelta(days=7)
        revisions = Revision.objects.filter(
            wiki_link__in=all_possible_links,
            timestamp__gte=starttime, timestamp__lte=endtime)
        print(revisions)
        for rev in revisions:
            print(rev.score)