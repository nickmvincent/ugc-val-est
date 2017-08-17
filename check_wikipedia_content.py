"""
This module runs through all posts in the DB,
checks for Wikipedia content, and get ORES score
"""

import datetime
import os
import time
import argparse

import requests

from scoring_helpers import map_ores_code_to_int
from url_helpers import extract_urls

WIK = 'wikipedia.org/wiki/'

def handle_err(post, err_num):
    """handles an error by add the err_num to Post table"""
    post.wiki_content_error = err_num
    post.save()


class MissingRevisionId(Exception):
    """Used to catch MissingRevision Media Wiki"""
    def __init__(self, post, endpoint):
        err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
        err_log.msg = '#2: MissingRevisionId: {}'.format(endpoint)[:500]
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


class MissingOresResponse(Exception):
    """Used to catch missing ores response"""
    def __init(self, post, url):
        err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
        err_log.msg = '#4: MissingOresResponse: {}'.format(url)[:500]
        err_log.save()
        handle_err(post, 4)
        super(MissingOresResponse, self).__init__(self)

# 5 is mystery


def make_mediawiki_request(session, base, params):
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
        result = session.get(base, params=req).json()
        if 'error' in result:
            print('err', result['error'])
        if 'warnings' in result:
            print('warning', result['warnings'])
        if 'query' in result:
            results.append(result['query'])
        if 'continue' not in result:
            break
        last_continue = result['continue']
    return results


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
        'titles': title,
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
    print('making user request with {} users...'.format(len(users)))
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
    for dja_link in dja_links:
        if dja_link.language_code != 'en':
            continue
        wiki_api_str_fmt = '%Y%m%d%H%M%S'
        day_before_post = post.timestamp - datetime.timedelta(days=1)
        week_after_post = post.timestamp + datetime.timedelta(days=7)
        day_before_post_str = day_before_post.strftime(wiki_api_str_fmt)
        week_after_post_str = week_after_post.strftime(wiki_api_str_fmt)
        tic = time.time()

        revisions = []
        revid_result_pages = make_revid_request(
            session, dja_link.language_code, dja_link.title, day_before_post_str,
            week_after_post_str)
        for result_page in revid_result_pages:
            pages = result_page['pages']
            for _, page in pages.items():
                if 'revisions' in page:
                    revisions += page['revisions']
        if not revisions:
            revid_result_pages = make_revid_request(
                session, dja_link.language_code,
                dja_link.title, day_before_post_str)
            for result_page in revid_result_pages:
                pages = result_page['pages']
                for _, page in pages.items():
                    if 'revisions' in page:
                        revisions += page['revisions']
        if not revisions:  # STILL???
            print('Could NOT find a revision for this article')
            info = '{}_{}_{}'.format(
                dja_link.title, day_before_post, week_after_post
            )
            raise MissingRevisionId(post, info)
        tic = time.time()
        print('About to process {} revisions'.format(len(revisions)))
        username_to_user_kwargs = {}
        rev_kwargs_lst = []
        for rev_obj in revisions:
            rev_kwargs = {}
            for rev_field in Revision._meta.get_fields():
                if rev_obj.get(rev_field.name):
                    rev_kwargs[rev_field.name] = rev_obj[rev_field.name]
            rev_kwargs['wiki_link'] = dja_link
            if 'user' in rev_kwargs:
                username_to_user_kwargs[rev_kwargs['user']] = {}
            rev_kwargs_lst.append(rev_kwargs)

        users = []
        user_result_pages = make_user_request(
            session, dja_link.language_code, username_to_user_kwargs.keys())
        for page in user_result_pages:
            users += page['users']
        for user in users:
            user_kwargs = username_to_user_kwargs[user['name']]
            user_kwargs['editcount'] = user.get('editcount', 0)
            if user.get('registration'):
                user_kwargs['registration'] = user.get('registration')
        for rev_kwargs in rev_kwargs_lst:
            if 'user' in rev_kwargs:
                for key, val in username_to_user_kwargs.get(rev_kwargs['user'], {}):
                    rev_kwargs[key] = val
            try:
                Revision.objects.create(**rev_kwargs)
            except IntegrityError:
                pass
        dja_revs = Revision.objects.filter(wiki_link=dja_link)
        for timestamp in [day_before_post, post.timestamp, week_after_post, ]:
            closest_rev = get_closest_to(dja_revs, timestamp)
            ores_context = dja_link.language_code + 'wiki'
            ores_ep = ores_ep_template.format(**{
                'context': ores_context,
                'revid': closest_rev.revid
            })
            ores_resp = session.get(ores_ep).json()
            try:
                scores = ores_resp['scores'][ores_context]['wp10']['scores']
            except KeyError:
                raise ContextNotSupported(post, ores_context)
            try:
                predicted_code = scores[str(closest_rev.revid)]['prediction']
            except KeyError:
                raise MissingOresResponse(post, closest_rev.revid)
            closest_rev.score = map_ores_code_to_int(predicted_code)
            closest_rev.save()
        print('Took {}'.format(time.time() - tic))



def identify_links(filtered, field):
    """identify links in post and mark it in the db"""
    count = 0
    for post in filtered:
        if count % 100 == 0:
            print('{}'.format(count), end='|')
        count += 1
        urls = extract_urls(post.body, WIK) if field == 'body' else [post.url]
        for url in urls:
            try:
                dja_link, _ = WikiLink.objects.get_or_create(url=url)
            except Exception as err:
                print(err)
                print(url)
            post.wiki_links.add(dja_link)
            post.has_wiki_link = True
            post.num_wiki_links += 1
            post.save()

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
    process_start = time.time()
    for post in filtered:
        if count % 100 == 0:
            print('Posts processed: {}'.format(count))
            print('total runtime: {}'.format(time.time() - process_start))
        count += 1
        try:
            check_single_post(post, ores_ep_template, session)
            post.wiki_content_analyzed = True
            tic = time.time()
            post.save()
        except (
                MissingRevisionId, ContextNotSupported, BrokenLinkError,
                MissingOresResponse, ValueError
        ):
            post.wiki_content_analyzed = True
            post.save()
        print('Saving post took: {}'.format(time.time() - tic))


def parse():
    """
    Parse args and do the appropriate analysis
    """
    parser = argparse.ArgumentParser(
        description='Identify wikipedia links and get info about them')
    parser.add_argument(
        '--platform', help='the platform to use. "r" for reddit and "s" for stack overflow')
    parser.add_argument(
        '--mode', help='identify or retrieve')
    args = parser.parse_args()
    if args.platform == 'r':
        field = 'url'
        model = SampledRedditThread
    else:
        field = 'body'
        model = SampledStackOverflowPost
    filter_kwargs = {field + '__contains': WIK}
    if args.mode == 'retrieve':
        filter_kwargs['has_wiki_link'] = True
    filtered = model.objects.filter(**filter_kwargs)
    print('Using kwargs {}, {} items were found to be processed'.format(
        str(filter_kwargs), len(filtered)
    ))

    if args.mode == 'identify':
        identify_links(filtered, field)
    elif args.mode == 'retrieve':
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
