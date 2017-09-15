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


def tmp2():
    from portal.models import SampledRedditThread, WikiLink, Revision, get_closest_to
    import datetime
    qs = SampledRedditThread.objects.filter(day_of_avg_score__isnull=True)
    for post in qs:
        for link_obj in post.wiki_links.all():
            all_possible_links = WikiLink.objects.filter(title=link_obj.title)
            field_to_dt = {
                'day_of': post.timestamp,
                'week_after': post.timestamp + datetime.timedelta(days=7),
            }
            for field, dt in field_to_dt.items():
                ores_rev = get_closest_to(
                    Revision.objects.filter(
                        wiki_link__in=all_possible_links), dt)
                if ores_rev:
                    rev_as_qs = Revision.objects.filter(revid=ores_rev.revid).values()[0]
                    print(rev_as_qs)
                else:
                    print('No ores_Rev')
                    