"""
This module runs through all posts in the DB,
checks for Wikipedia content, and get ORES score
"""


import datetime
import os

import requests

from scoring_helpers import map_ores_code_to_int
from pprint import pprint


class MissingRevisionId(Exception): pass # Custom exception

def check_sampled_threads():
    """
    Run through sampled threads and get corresponding Wiki data
    """
    base = 'https://en.wikipedia.org/w/api.php?action=query&'
    query_params = {
        'format': 'json',
        'prop': 'revisions',
        'rvprop': 'ids%7Ctimestamp',
        'rvdir': 'older',
        'rvlimit': '1',
    }
    query_pairs = ['{}={}'.format(key, val)
                   for key, val in query_params.items()]
    rev_endpoint = base + '&'.join(query_pairs) + '&titles={}&rvstart={}'
    ores_endpoint = 'https://ores.wikimedia.org/v2/scores/enwiki/wp10?revids={}'
    w = 'wikipedia.org/wiki/'
    filtered = SampledRedditThread.objects.filter(
        wiki_content_analyzed=False, url__contains=w)
    print('About to run through {} threads'.format(len(filtered)))
    for thread in filtered:
        if thread.wiki_links.all().count() >= 1:
            print ('Skipping already processed one...')
            thread.wiki_content_analyzed = True
            thread.save()
            continue
        dja_link, _ = WikiLink.objects.get_or_create(url=thread.url)
        thread.wiki_links.add(dja_link)

        scores_by_offset = {}
        dt = thread.timestamp
        for offset in ['day_prior', 'day_of', 'week_after']:
            if offset == 'day_prior':
                offset_dt = dt - datetime.timedelta(days=1)
            elif offset == 'day_of':
                offset_dt = dt
            elif offset == 'week_after':
                offset_dt = dt + datetime.timedelta(days=7)
            wiki_timestamp = offset_dt.strftime('%Y%m%d%H%M%S')
            i = thread.url.find(w) + len(w)
            title = thread.url[i:]
            full_rev_endpoint = rev_endpoint.format(
                title, wiki_timestamp
            )
            resp = requests.get(full_rev_endpoint)
            pages = resp.json()['query']['pages']
            try:
                for _, val in pages.items():
                    try:
                        rev_obj = val['revisions'][0]
                    except KeyError:
                        pprint(pages)
                        input()
                        raise(MissingRevisionId)
                    rev_id = rev_obj['revid']
                    rev_timestamp = rev_obj['timestamp']
                    print(rev_id, rev_timestamp)
            except MissingRevisionId:
                continue
            ores_resp = requests.get(ores_endpoint.format(rev_id))
            scores = ores_resp.json()['scores']['enwiki']['wp10']['scores']
            print(scores)
            predicted_code = scores[str(rev_id)]['prediction']
            print(predicted_code)
            score_as_int = map_ores_code_to_int(predicted_code)
            print(score_as_int)
            dja_score, _ = RevisionScore.objects.get_or_create(
                rev_id=rev_id, timestamp=rev_timestamp,
                score=score_as_int, wiki_link=dja_link
            )
            scores_by_offset[offset] = dja_score
        dja_post_specific_link = PostSpecificWikiLink.objects.create(
            **scores_by_offset)
        thread.post_specific_wiki_links.add(dja_post_specific_link)
        thread.wiki_content_analyzed = True
        thread.save()


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        SampledRedditThread,
        PostSpecificWikiLink, WikiLink, RevisionScore
    )
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "C:\\Users\\nickm\\Desktop\\research\\wikipedia_and_stack_overflow\\client_secrets.json"
    print('Django settings initialized, running "check_sampled_threads"')
    check_sampled_threads()
