"""
This module runs through all posts in the DB,
checks for Wikipedia content, and get ORES score
"""

import datetime
import os
import time
import argparse

from urllib.parse import unquote
from itertools import zip_longest
import requests

from scoring_helpers import map_ores_code_to_int
from url_helpers import extract_urls

WIK = 'wikipedia.org/wiki/'




def grouper(iterable, groupsize, fillvalue=None):
    """Separate an iterable into groups of size groupsize"""
    args = [iter(iterable)] * groupsize
    return zip_longest(*args, fillvalue=fillvalue)


def handle_err(post, err_num):
    """handles an error by add the err_num to Post table"""
    post.wiki_content_error = err_num
    post.save()


class MissingRevisionId(Exception):
    """
    Used to catch MissingRevision Media Wiki
    Get a list of all such errors by querying for wiki_error_content=2
    """
    def __init__(self, post, info):
        err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
        err_log.msg = '#2: MissingRevisionId: {}'.format(info)[:500]
        err_log.save()
        handle_err(post, 2)
        super(MissingRevisionId, self).__init__(self)


class ContextNotSupported(Exception):
    """Used to catch MissingRevision Media Wiki"""
    def __init__(self, post, ores_context):
        err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
        err_log.msg = '#3: ContextNotSupported: {}'.format(ores_context)[:500]
        err_log.save()
        handle_err(post, 3)
        super(ContextNotSupported, self).__init__(self)

class BrokenLinkError(Exception):
    """Used to catch Broken Links"""
    def __init__(self, post, url):
        err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
        err_log.msg = '#1: BrokenLinkError: {}'.format(url)[:500]
        err_log.save()
        handle_err(post, 1)
        super(BrokenLinkError, self).__init__(self)


class PostMissingValidLink(Exception):
    """Used to catch missing article, improperly formatted links, etc"""
    def __init__(self, post, link):
        post.wiki_links.remove(link)
        post.num_wiki_links -= 1
        if post.num_wiki_links == 0:
            post.has_wiki_link = False
        post.save()
        super(PostMissingValidLink, self).__init__(self)


class MissingOresResponse(Exception):
    """Used to catch missing ores response"""
    def __init(self, post, url):
        err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
        err_log.msg = '#4: MissingOresResponse: {}'.format(url)[:500]
        err_log.save()
        handle_err(post, 4)
        super(MissingOresResponse, self).__init__(self)

# 5 is mystery


def make_mediawiki_request(session, base, params, verbose=False):
    """
    Args:
        endpoint - a mediawiki api endpoint, fully formated (not template)
    Returns:
        full results, with pagination processed
    """
    results = []
    last_continue = {}
    while True:
        # Clone original request
        req = params.copy()
        # Modify it with the values returned in the 'continue' section of the last result.
        req.update(last_continue)
        # Call API
        if verbose:
            print(base + '?' + '&'.join(
                ['{}={}'.format(key, val) for key, val in req.items()]
            ))
        result = session.get(base, params=req).json()
        if verbose:
            print(result)
        if 'error' in result:
            print('err', result['error'])
        if 'warnings' in result:
            print('warning', result['warnings'])
        if 'query' in result:
            results.append(result['query'])
        if 'continue' not in result:
            break
        if 'end' not in req:
            break
        last_continue = result['continue']
    return results


def make_pageview_request(session, **kwargs):
    """
    example:  http://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/Albert_Einstein/daily/2015100100/2015103100
    """
    base = 'http://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{title}/daily/{start}/{end}'
    endpoint = base.format(**kwargs)
    result = session.get(endpoint).json()
    try:
        result = result['items']
    except KeyError:
        result = []
    return result

def make_lastrev_request(session, prefix, user):
    """
    Returns the last revision a user made.
    """
    base = 'https://{}.wikipedia.org/w/api.php'.format(prefix)
    params = {
        'format': 'json',
        'action': 'query',
        'list': 'usercontribs',
        'rvlimit': 1,
        'ucprop': 'timestamp',
        'ucuser': user,
    }
    return make_mediawiki_request(session, base, params, verbose=True)


def make_revid_request(session, prefix, title, start, end=None):
    """
    Returns an endpoint that will give us a revid in json format
    closest to the timestamp, but prior to to the timestamp.
    """
    base = 'https://{}.wikipedia.org/w/api.php'.format(prefix)
    rvprop_params = ['ids', 'timestamp', 'flags', 'user', ]
    params = {
        'format': 'json',
        'action': 'query',
        'prop': 'revisions',
        'rvdir': 'newer',
        'rvlimit': 500,
        'rvprop': '|'.join(rvprop_params),
        'rvstart': start,
        'titles': unquote(title),
        'redirects': 1,
    }
    if end is None:
        params['rvdir'] = 'older'
        params['rvlimit'] = 1
    else:
        params['rvend'] = end
    return make_mediawiki_request(session, base, params)


def make_user_request(session, prefix, users):
    """
    Returns an endpoint that will give us a revid in json format
    closest to the timestamp, but prior to to the timestamp.
    """
    base = 'https://{}.wikipedia.org/w/api.php?action=query&'.format(prefix)
    usprop_params = ['editcount', 'registration', ]
    params = {
        'format': 'json',
        'list': 'users',
        'usprop': '|'.join(usprop_params),
        'ususers': '|'.join(users)
    }
    return make_mediawiki_request(session, base, params)


def check_single_post(post, ores_ep_template, session):
    """check a single post"""
    dja_links = post.wiki_links.all()
    username_cache = {}
    for dja_link in dja_links:
        if dja_link.language_code != 'en':
            continue
        wiki_api_str_fmt = '%Y%m%d%H%M%S'
        pageview_api_str_fmt = '%Y%m%d'
        week_before_post = post.timestamp - datetime.timedelta(days=7)
        week_after_post = post.timestamp + datetime.timedelta(days=7)
        week_before_post_str = week_before_post.strftime(wiki_api_str_fmt)
        week_after_post_str = week_after_post.strftime(wiki_api_str_fmt)

        day_of_post_short_str = post.timestamp.strftime(pageview_api_str_fmt)
        hashtag_index = dja_link.title.find('#')
        if hashtag_index != -1:
            norm_title = dja_link.title[:hashtag_index]
        else:
            norm_title = dja_link.title
        if len(norm_title) >= 2:
            norm_title = norm_title[0].upper() + norm_title[1:]
        norm_title = norm_title.replace(' ', '_')
        norm_title = norm_title.replace('/', '%2F')
        pageviews_prev_week = make_pageview_request(
            session,
            title=norm_title, start=week_before_post.strftime(pageview_api_str_fmt) + '00',
            end=day_of_post_short_str + '00')
        pageviews = make_pageview_request(
            session,
            title=norm_title, start=day_of_post_short_str + '00',
            end=week_after_post.strftime(pageview_api_str_fmt) + '00')
        post.num_wiki_pageviews_prev_week = sum([entry['views'] for entry in pageviews_prev_week])    
        post.num_wiki_pageviews = sum([entry['views'] for entry in pageviews])
        revisions = []
        revid_result_pages = make_revid_request(
            session, dja_link.language_code, dja_link.title, week_before_post_str,
            week_after_post_str)
        for result_page in revid_result_pages:
            pages = result_page['pages']
            for _, page in pages.items():
                if 'missing' in page:
                    raise PostMissingValidLink(post, dja_link)
                if 'revisions' in page:
                    revisions += page['revisions']
        if not revisions:
            revid_result_pages = make_revid_request(
                session, dja_link.language_code,
                dja_link.title, week_before_post_str)
            for result_page in revid_result_pages:
                pages = result_page['pages']
                for _, page in pages.items():
                    if 'revisions' in page:
                        revisions += page['revisions']
        if not revisions:  # STILL???
            info = '{}_{}_{}'.format(
                dja_link.title, week_before_post, week_after_post
            )
            print('No revisions for {}'.format(info))
            raise MissingRevisionId(post, info)
        username_to_user_kwargs = {}
        rev_kwargs_lst = []
        revids = []
        for rev_obj in revisions:
            rev_kwargs = {}
            for rev_field in Revision._meta.get_fields():
                if rev_obj.get(rev_field.name):
                    rev_kwargs[rev_field.name] = rev_obj[rev_field.name]
            rev_kwargs['wiki_link'] = dja_link
            if 'user' in rev_kwargs:
                username_to_user_kwargs[rev_kwargs['user']] = username_cache.get('user', {})
            rev_kwargs_lst.append(rev_kwargs)
            revids.append(rev_kwargs['revid'])

        for userbatch in grouper(username_to_user_kwargs.keys(), 50):
            userbatch = [user for user in userbatch if user and not username_to_user_kwargs[user]]
            users = []
            user_result_pages = make_user_request(
                session, dja_link.language_code, userbatch)
            for page in user_result_pages:
                users += page['users']
            for user in users:
                user_kwargs = username_to_user_kwargs[user['name']]
                user_kwargs['editcount'] = user.get('editcount', 0)
                if user.get('registration'):
                    user_kwargs['registration'] = user.get('registration')
                lastrev_pages = make_lastrev_request(
                    session, dja_link.language_code,
                    user['name'])
                for result_page in lastrev_pages:
                    pages = result_page['pages']
                    for _, page in pages.items():
                        if 'revisions' in page:
                            lastrev = page['revisions'][0]
                            user_kwargs['lastrev_date'] = lastrev['timestamp']
                username_cache[user['name']] = user_kwargs
        revs_made = 0
        for rev_kwargs in rev_kwargs_lst:
            if 'user' in rev_kwargs:
                for key, val in username_to_user_kwargs.get(rev_kwargs['user'], {}).items():
                    rev_kwargs[key] = val
            try:
                if 'lastrev_date' not in rev_kwargs:
                    rev_kwargs['lastrev_date'] = rev_kwargs['timestamp']
                Revision.objects.create(**rev_kwargs)
                revs_made += 1
            except IntegrityError as err:
                print('integrity error occurred')
                print(err)
                print(rev_kwargs)
                pass
        print('revs_made', revs_made)
        dja_revs = Revision.objects.filter(revid__in=revids)
        if not dja_revs.exists():
            print('no revs found, so returning!!!')
            return
        for timestamp in [post.timestamp, week_after_post, ]:
            closest_rev = get_closest_to(dja_revs, timestamp)
            ores_context = dja_link.language_code + 'wiki'
            ores_ep = ores_ep_template.format(**{
                'context': ores_context,
                'revid': closest_rev.revid
            })
            ores_resp = session.get(ores_ep)
            ores_resp = ores_resp.json()
            try:
                scores = ores_resp['scores'][ores_context]['wp10']['scores']
            except KeyError:
                raise ContextNotSupported(post, ores_context)
            try:
                predicted_code = scores[str(closest_rev.revid)]['prediction']
            except KeyError:
                print('Raising MissingOresResponse')
                print(scores)
                raise MissingOresResponse(post, closest_rev.revid)
            closest_rev.score = map_ores_code_to_int(predicted_code)
            closest_rev.save()



def identify_links(filtered, field):
    """identify links in post and mark it in the db"""
    count = 0
    filtered.update(has_wiki_link=False, num_wiki_links=0)
    for post in filtered:
        post.wiki_links.clear()
        if count % 500 == 0:
            print('{}'.format(count), end='|')
        count += 1
        urls = extract_urls(post.body, WIK) if field == 'body' else [post.url]
        for url in urls:
            if 'File:' in url:
                continue
            try:
                dja_link, _ = WikiLink.objects.get_or_create(url=url)
            except Exception:
                print(url)
                continue
            post.wiki_links.add(dja_link)
            post.has_wiki_link = True
            post.num_wiki_links += 1
            post.save()
    print('\n')

def retrieve_links_info(filtered):
    """
    Run through sampled threads and get corresponding Wiki data
    """
    ores_ep_template = 'https://ores.wikimedia.org/v2/scores/{context}/wp10?revids={revid}'
    print('About to run through {} threads'.format(len(filtered)))
    session = requests.Session()
    session.headers.update(
        {'User-Agent': 'ugc-val-est; nickvincent@u.northwestern.edu; research tool'})

    count = 0
    err_count = 0
    process_start = time.time()
    for post in filtered:
        if count % 100 == 0:
            print('Finished: {}, Errors: {}, Time: {}'.format(count, err_count, time.time() - process_start))
        count += 1
        try:
            check_single_post(post, ores_ep_template, session)
            post.wiki_content_analyzed = True
            post.save()
        except (
                MissingRevisionId, ContextNotSupported, BrokenLinkError,
                MissingOresResponse, PostMissingValidLink
        ):
            err_count += 1
            post.wiki_content_analyzed = True
            post.save()



def parse():
    """
    Parse args and do the appropriate analysis
    """
    parser = argparse.ArgumentParser(
        description='Identify wikipedia links and get info about them')
    parser.add_argument(
        '--platform', help='the platform to use. "r" for reddit and "s" for stack overflow')
    parser.add_argument(
        '--mode', help='identify, retrieve, full (performs both in sequence)')
    parser.add_argument(
        '--clear_first', action='store_true', default=False,
        help='identify, retrieve, full (performs both in sequence)')
    args = parser.parse_args()
    if args.platform == 'r':
        field = 'url'
        model = SampledRedditThread
    else:
        field = 'body'
        model = SampledStackOverflowPost
    if args.clear_first:
        for obj in model.objects.filter(wiki_content_analyzed=True):
            for wiki_link in obj.wiki_links.all():
                Revision.objects.filter(wiki_link=wiki_link).delete()
            obj.wiki_links.all().delete()
            ErrorLog.objects.filter(uid=obj.uid).delete()
        model.objects.filter(wiki_content_analyzed=True).update(
            has_wiki_link=False,
            wiki_content_error=0,
            num_wiki_links=0,
            wiki_content_analyzed=False,
        )
    if args.mode == 'identify' or args.mode == 'full':
        filtered = model.objects.filter(**{field + '__contains': WIK})
        print('Going to IDENTIFY {} items'.format(len(filtered)))
        identify_links(filtered, field)
    if args.mode == 'retrieve' or args.mode == 'full':
        filtered = model.objects.filter(has_wiki_link=True, wiki_content_analyzed=False)
        print('Going to RETRIEVE INFO for {} items'.format(len(filtered)))
        retrieve_links_info(filtered)
    

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    from django.db.utils import IntegrityError
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
        WikiLink, Revision, ErrorLog,
        get_closest_to
    )
    parse()
