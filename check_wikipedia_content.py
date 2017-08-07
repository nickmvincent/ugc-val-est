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
from url_helpers import extract_urls


class MissingRevisionId(Exception):
    """Used to catch MissingRevision Media Wiki"""
    pass


class ContextNotSupported(Exception):
    """Used to catch MissingRevision Media Wiki"""
    pass

class BrokenLinkError(Exception):
    """Used to catch Broken Links"""
    pass


def generate_revid_endpoint(prefix, title, wiki_timestamp):
    """
    Returns an endpoint that will give us a revid in json format
    closest to the timestamp, but prior to to the timestamp.
    """
    print(prefix)
    base = 'https://{}.wikipedia.org/w/api.php?action=query&'.format(prefix)
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


def check_posts(model, field):
    """
    Run through sampled threads and get corresponding Wiki data
    """
    ores_ep_template = 'https://ores.wikimedia.org/v2/scores/{context}/wp10?revids={revid}'
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
        try:
            for url in urls:
                try:
                    dja_link, _ = WikiLink.objects.get_or_create(url=url)
                except:
                    err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
                    err_log.msg = '#001: BrokenLinkError'
                    err_log.save()
                    raise BrokenLinkError
                post.wiki_links.add(dja_link)
                post.has_wiki_link = True
                post.num_wiki_links += 1
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
                    endpoint = generate_revid_endpoint(
                        dja_link.language_code, dja_link.title, wiki_timestamp)
                    resp = requests.get(endpoint)
                    pages = resp.json()['query']['pages']
                    for _, val in pages.items():
                        try:
                            rev_obj = val['revisions'][0]
                        except KeyError:
                            alt_endpoint = endpoint.replace(
                                'rvdir=older', 'rvdir=newer')
                            resp = requests.get(alt_endpoint)
                            pages = resp.json()['query']['pages']
                            try:
                                for _, val in pages.items():
                                    rev_obj = val['revisions'][0]
                            except KeyError as err:
                                err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
                                err_log.msg = '#002: MissingRevisionId: {}'.format(alt_endpoint)
                                err_log.save()
                                raise MissingRevisionId
                        revid = rev_obj['revid']
                        rev_timestamp = rev_obj['timestamp']
                    try:
                        dja_score = RevisionScore.objects.get(revid=revid)
                    except RevisionScore.DoesNotExist:
                        ores_context = dja_link.language_code + 'wiki'
                        ores_ep = ores_ep_template.format(**{
                            'context': ores_context,
                            'revid': revid
                        })
                        ores_resp = requests.get(ores_ep).json()
                        try:
                            scores = ores_resp['scores'][ores_context]['wp10']['scores']
                        except KeyError:
                            raise ContextNotSupported
                        try:
                            predicted_code = scores[str(revid)]['prediction']
                        except KeyError:
                            print(scores)
                            return
                        score_as_int = map_ores_code_to_int(predicted_code)
                        dja_score = RevisionScore.objects.create(
                            revid=revid, timestamp=rev_timestamp,
                            score=score_as_int, wiki_link=dja_link
                        )
                    scores_by_offset[offset] = dja_score
                dja_post_specific_link = PostSpecificWikiScores.objects.create(
                    **scores_by_offset)
            post.post_specific_wiki_links.add(dja_post_specific_link)
            post.wiki_content_analyzed = True
            post.save()
        except MissingRevisionId:
            continue
        except ContextNotSupported:
            continue
        except BrokenLinkError:
            continue


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
        PostSpecificWikiScores, WikiLink, RevisionScore, ErrorLog
    )
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "C:\\Users\\nickm\\Desktop\\research\\wikipedia_and_stack_overflow\\client_secrets.json"
    print('Django settings initialized, running "check_sampled_threads"')
    if sys.argv[1] == 'r':
        check_posts(SampledRedditThread, 'url')
    elif sys.argv[1] == 's':
        check_posts(SampledStackOverflowPost, 'body')
    else:
        print('Please choose either "r" for reddit or "s" for Stack Overflow')