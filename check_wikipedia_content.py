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


def handle_err(post, err_num):
    post.wiki_content_error = err_num
    post.save()


class MissingRevisionId(Exception):
    """Used to catch MissingRevision Media Wiki"""
    def __init__(self, post, endpoint):
        err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
        err_log.msg = '#2: MissingRevisionId: {}'.format(endpoint)[:500]
        err_log.save()
        handle_err(post, 2)


class ContextNotSupported(Exception):
    """Used to catch MissingRevision Media Wiki"""
    def __init__(self, post, ores_context):
        err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
        err_log.msg = '#3: ContextNotSupported: {}'.format(ores_context)[:500]
        err_log.save()
        handle_err(post, 3)

class BrokenLinkError(Exception):
    """Used to catch Broken Links"""
    def __init__(self, post, url):
        err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
        err_log.msg = '#1: BrokenLinkError: {}'.format(url)[:500]
        err_log.save()
        handle_err(post, 1)


class MissingOresResponse(Exception):
    """Used to catch missing ores response"""
    def __init(self, post, url):
        err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
        err_log.msg = '#4: MissingOresResponse: {}'.format(url)[:500]
        err_log.save()
        handle_err(post, 4)


# 5 is mystery
def generate_revid_endpoint(prefix, title, start, end):
    """
    Returns an endpoint that will give us a revid in json format
    closest to the timestamp, but prior to to the timestamp.
    """
    base = 'https://{}.wikipedia.org/w/api.php?action=query&'.format(prefix)
    rvprop_params = ['ids', 'timestamp', 'flags', 'user', ]
    query_params = {
        'format': 'json',
        'prop': 'revisions',
        'rvprop': '|'.join(rvprop_params),
        'rvdir': 'newer',
        'rvlimit': '500',
    }
    query_pairs = ['{}={}'.format(key, val)
                   for key, val in query_params.items()]
    rev_endpoint = base + '&'.join(query_pairs) + '&titles={}&rvstart={}&rvend={}'
    return rev_endpoint.format(title, start, end)


def generate_user_endpoint(prefix, user):
    """
    Returns an endpoint that will give us a revid in json format
    closest to the timestamp, but prior to to the timestamp.
    """
    base = 'https://{}.wikipedia.org/w/api.php?action=query&'.format(prefix)
    usprop_params = ['editcount', 'registration', ]
    query_params = {
        'format': 'json',
        'list': 'users',
        'usprop': '|'.join(usprop_params),
    }
    query_pairs = ['{}={}'.format(key, val)
                   for key, val in query_params.items()]
    rev_endpoint = base + '&'.join(query_pairs) + '&ususers={}'
    return rev_endpoint.format(user)


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
    count = 0
    for post in filtered:
        if count % 100 == 0:
            print(count)
        count += 1
        if field == 'body':
            urls = extract_urls(post.body, w)
        else:
            urls = [post.url]
        try:
            for url in urls:
                try:
                    dja_link, _ = WikiLink.objects.get_or_create(url=url)
                except:
                    raise BrokenLinkError(post, url)

                post.wiki_links.add(dja_link)
                if dja_link.language_code != 'en':
                    raise ValueError
                post.has_wiki_link = True
                post.num_wiki_links += 1
                wiki_api_str_fmt = '%Y%m%d%H%M%S'
                month_before_post = post.timestamp - datetime.timedelta(days=30)
                month_after_post = post.timestamp + datetime.timedelta(days=30)
                month_before_post = month_before_post.strftime(wiki_api_str_fmt)
                month_after_post = month_after_post.strftime(wiki_api_str_fmt)
                endpoint = generate_revid_endpoint(
                        dja_link.language_code, dja_link.title, month_before_post,
                        month_after_post)
                resp = requests.get(endpoint)
                try:
                    print(resp.json())
                    pages = resp.json()['query']['pages']
                except:
                    raise ValueError
                for _, val in pages.items():
                    for rev_obj in val['revisions']:
                        print(rev_obj)
                        rev_kwargs = {}
                        for field in Revision._meta.get_fields():
                            if rev_obj.get(field.name):
                                rev_kwargs[field.name] = rev_obj[field.name]
                        if rev_kwargs.get('user'):
                            endpoint = generate_user_endpoint(dja_link.language_code, rev_kwargs.get('user'))
                            print(endpoint)
                            resp = requests.get(endpoint)
                            try:
                                print(resp.json())
                                user = resp.json()['query']['users'][0]
                                rev_kwargs['editcount'] = user.get('editcount', 0)
                                rev_kwargs['registration'] = user.get('registration', None)
                            except Exception as err:
                                print('err with getting user info')
                                print(err)
                        rev_kwargs['wiki_link'] = dja_link
                        dja_rev, created = Revision.objects.get_or_create(**rev_kwargs)
                        if created or dja_rev.score == -1:
                            ores_context = dja_link.language_code + 'wiki'
                            ores_ep = ores_ep_template.format(**{
                                'context': ores_context,
                                'revid': rev_obj['revid']
                            })
                            ores_resp = requests.get(ores_ep).json()
                            try:
                                scores = ores_resp['scores'][ores_context]['wp10']['scores']
                            except KeyError:
                                raise ContextNotSupported(post, ores_context)
                            try:
                                predicted_code = scores[str(rev_obj['revid'])]['prediction']
                            except KeyError:
                                raise MissingOresResponse(post, rev_obj['revid'])
                            dja_rev.score = map_ores_code_to_int(predicted_code)
        except (MissingRevisionId, ContextNotSupported, BrokenLinkError, MissingOresResponse):
            continue
        except ValueError:
            continue
        finally:
            post.wiki_content_analyzed = True
            post.save()


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
        WikiLink, Revision, ErrorLog
    )
    print('Django settings initialized, running "check_posts"')
    if sys.argv[1] == 'r':
        check_posts(SampledRedditThread, 'url')
    elif sys.argv[1] == 's':
        check_posts(SampledStackOverflowPost, 'body')
    else:
        print('Please choose either "r" for reddit or "s" for Stack Overflow')