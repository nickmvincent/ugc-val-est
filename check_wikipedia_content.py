"""
This module runs through all posts in the DB,
checks for Wikipedia content, and get ORES score
"""

import sys
import re
import datetime
import os
from pprint import pprint

import requests

from scoring_helpers import map_ores_code_to_int


class MissingRevisionId(Exception):
    """Used to catch MissingRevision Media Wiki"""
    pass


def generate_revid_endpoint(title, wiki_timestamp):
    """
    Returns an endpoint that will give us a revid in json format
    closest to the timestamp, but prior to to the timestamp.
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
    return rev_endpoint.format(title, wiki_timestamp)


def test_extract_urls():
    """Test func"""
    w = 'wikipedia.org/wiki/'
    test_so = """
    asd <a href="https://en.wikipedia.org/wiki/Imbolc"> asd <a href="https://en.wikipedia.org/wiki/Imbolc"
    asd asd aasd
    ahref=asdasd
    <a href="https://www.google.com">
    <a href="https://www.wikipedia.org/wiki/">
    """

    
    print(extract_urls(w, test_so))


def extract_urls(base_url, text):
    """
    Extract all urls matching base_url from `text`
    Returns a list of strings
    """
    return [x for x in re.findall('<a href="?\'?([^"\'>]*)', text) if base_url in x]
    # index = 0
    # ret = []
    # while index < len(text):
    #     index = text.find(base_url, index)
    #     if index == -1:
    #         return ret
    #     print('link found at', index)
    #     end_index = text.find()
    #     index += len(base_url)



def check_posts(model, field):
    """
    Run through sampled threads and get corresponding Wiki data
    """
    ores_endpoint = 'https://ores.wikimedia.org/v2/scores/enwiki/wp10?revids={}'
    w = 'wikipedia.org/wiki/'
    if field == 'url':
        filtered = model.objects.filter(
            wiki_content_analyzed=False, url__contains=w)
    elif field == 'body':
        filtered = model.objects.filter(
            wiki_content_analyzed=False, body__contains=w)
    else:
        raise ValueError('Invalid choice of field... try "url" or "body"')
    print('About to run through {} threads'.format(len(filtered)))
    for post in filtered:
        if post.wiki_links.all().count() >= 1:
            print('Skipping already processed one...')
            post.wiki_content_analyzed = True
            post.save()
            continue
        if field == 'body':
            urls = extract_urls(w, post.body)
        else:
            urls = [post.url]
        for url in urls:
            dja_link, _ = WikiLink.objects.get_or_create(url=url)
            post.wiki_links.add(dja_link)

            scores_by_offset = {}
            dt = post.timestamp
            for offset in ['day_prior', 'day_of', 'week_after']:
                if offset == 'day_prior':
                    offset_dt = dt - datetime.timedelta(days=1)
                elif offset == 'day_of':
                    offset_dt = dt
                elif offset == 'week_after':
                    offset_dt = dt + datetime.timedelta(days=7)
                wiki_timestamp = offset_dt.strftime('%Y%m%d%H%M%S')
                i = url.find(w) + len(w)
                title = url[i:]
                resp = requests.get(generate_revid_endpoint(title, wiki_timestamp))
                pages = resp.json()['query']['pages']
                try:
                    for _, val in pages.items():
                        try:
                            rev_obj = val['revisions'][0]
                        except KeyError:
                            pprint(pages)
                            input()
                            raise MissingRevisionId
                        rev_id = rev_obj['revid']
                        rev_timestamp = rev_obj['timestamp']
                        print(rev_id, rev_timestamp)
                except MissingRevisionId:
                    continue
                ores_resp = requests.get(ores_endpoint.format(rev_id))
                scores = ores_resp.json()['scores']['enwiki']['wp10']['scores']
                predicted_code = scores[str(rev_id)]['prediction']
                score_as_int = map_ores_code_to_int(predicted_code)
                dja_score, _ = RevisionScore.objects.get_or_create(
                    rev_id=rev_id, timestamp=rev_timestamp,
                    score=score_as_int, wiki_link=dja_link
                )
                scores_by_offset[offset] = dja_score
            dja_post_specific_link = PostSpecificWikiLink.objects.create(
                **scores_by_offset)
            post.post_specific_wiki_links.add(dja_post_specific_link)
            post.wiki_content_analyzed = True
            post.save()


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
        PostSpecificWikiLink, WikiLink, RevisionScore
    )
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "C:\\Users\\nickm\\Desktop\\research\\wikipedia_and_stack_overflow\\client_secrets.json"
    print('Django settings initialized, running "check_sampled_threads"')
    if sys.argv[1] == 'r':
        check_posts(SampledRedditThread, 'url')
    elif sys.argv[1] == 's':
        check_posts(SampledStackOverflowPost, 'body')
    elif sys.argv[1] == 'test':
        test_extract_urls()
    else:
        print('Please choose either "r" for reddit or "s" for Stack Overflow')