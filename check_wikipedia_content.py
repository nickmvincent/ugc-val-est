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
from json.decoder import JSONDecodeError

import requests

from scoring_helpers import map_ores_code_to_int
from url_helpers import extract_urls
import pytz
from requests.exceptions import ConnectionError

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


class PostMissingValidLink(Exception):
    """Used to catch missing article, improperly formatted links, etc"""
    def __init__(self, post, link):
        post.wiki_links.remove(link)
        post.num_wiki_links -= 1
        if post.num_wiki_links == 0:
            post.has_wiki_link = False
        post.save()
        super(PostMissingValidLink, self).__init__(self)


# class MissingOresResponse(Exception):
#     """Used to catch missing ores response"""
#     def __init(self, uid, url):
#         err_log, _ = ErrorLog.objects.get_or_create(uid=post.uid)
#         err_log.msg = '#4: MissingOresResponse: {}'.format(url)[:500]
#         err_log.save()
#         handle_err(post, 4)
#         super(MissingOresResponse, self).__init__(self)

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
    result = session.get(endpoint)
    result = result.json()
    try:
        result = result['items']
    except KeyError:
        result = None
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
        'uclimit': 1,
        'ucprop': 'timestamp',
        'ucuser': user,
    }
    return make_mediawiki_request(session, base, params)


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


def get_scores_for_all_links(links):
    revid_to_rev = {}
    for dja_link in links:
        if dja_link.language_code != 'en':
            print('skipping non english version')
            continue
        dja_revs = Revision.objects.filter(wiki_link=dja_link)
        for timestamp in [post.timestamp, week_after_post, ]:
            closest_rev = get_closest_to(dja_revs, timestamp)
            revid_to_rev[closest_rev.revid] = closest_rev
    ores_context = 'en' + 'wiki'
    for revbatch in grouper(revid_to_rev.keys(), 50):
        ores_ep = ores_ep_template.format(**{
            'context': ores_context,
            'revids': '|'.join(revbatch)
        })
        ores_resp = session.get(ores_ep)
        ores_resp = ores_resp.json()
        scores = ores_resp['scores'][ores_context]['wp10']['scores']
        for revid in revbatch:
            rev = revid_to_rev[revid]
            try:
                predicted_code = scores[str(revid)]['prediction']
            except KeyError:
                rev.err_code = 4 # missingOresResponse
            rev.score = map_ores_code_to_int(predicted_code)
            rev.save()


def get_userinfo_for_all_revs(revs):
    """
    Gets the user information for revisions that still need it
    """
    user_to_revs = {}
    for rev in revs:
        if rev.user not in user_to_revs:
            user_to_revs[rev.user] = [rev]
        else:
            user_to_revs[rev.user].append(rev)
    for userbatch in grouper(user_to_revs.keys(), 50):
        userbatch = [user for user in userbatch if user]
        users = []
        user_result_pages = make_user_request(
            session, dja_link.language_code, userbatch)
        for page in user_result_pages:
            users += page.get('users', [])
        for user in users:
            lastrev_pages = make_lastrev_request(
                session, dja_link.language_code,
                user['name'])
            for result_page in lastrev_pages:
                contribs = result_page['usercontribs']
                lastrev = contribs[0]
                lastrev_date = lastrev['timestamp']
            revs = user_to_revs[user['name']]
            for rev in revs:
                rev.editcount = user.get('editcount', 0)
                rev.registration = user.get('registration')
                rev.lastrev_date = lastrev_date
                rev.save()
            

def get_revs_for_single_post(post, ores_ep_template, session):
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
            title=norm_title, start=week_before_post.strftime(pageview_api_str_fmt),
            end=day_of_post_short_str)
        pageviews = make_pageview_request(
            session,
            title=norm_title, start=day_of_post_short_str,
            end=week_after_post.strftime(pageview_api_str_fmt))
        if pageviews_prev_week and pageviews:
            post.num_wiki_pageviews_prev_week = sum([entry['views'] for entry in pageviews_prev_week])    
            post.num_wiki_pageviews = sum([entry['views'] for entry in pageviews])
        
        # now get revids for the time window
        revisions = []
        revid_result_pages = make_revid_request(
            session, dja_link.language_code, dja_link.title, week_before_post_str,
            week_after_post_str)
        for result_page in revid_result_pages:
            pages = result_page.get('pages', {})
            for _, page in pages.items():
                if 'missing' in page:
                    raise PostMissingValidLink(post, dja_link)
                if 'revisions' in page:
                    revisions += page['revisions']
        
        # if no revs were found in the two week block, look backwards
        if not revisions:
            revid_result_pages = make_revid_request(
                session, dja_link.language_code,
                dja_link.title, week_before_post_str)
            for result_page in revid_result_pages:
                pages = result_page.get('pages', {})
                for _, page in pages.items():
                    if 'revisions' in page:
                        revisions += page['revisions']
        if not revisions:  # STILL???
            info = '{}_{}_{}'.format(
                dja_link.title, week_before_post, week_after_post
            )
            print('No revisions for {}'.format(info))
            raise MissingRevisionId(post, info)
        rev_kwargs_lst = []
        revids = []
        for rev_obj in revisions:
            rev_kwargs = {}
            for rev_field in Revision._meta.get_fields():
                if rev_obj.get(rev_field.name):
                    rev_kwargs[rev_field.name] = rev_obj[rev_field.name]
            rev_kwargs['wiki_link'] = dja_link
            rev_kwargs_lst.append(rev_kwargs)
            revids.append(rev_kwargs['revid'])

        
        revs_made = 0
        for rev_kwargs in rev_kwargs_lst:            
            if 'lastrev_date' not in rev_kwargs:
                rev_kwargs['lastrev_date'] = rev_kwargs['timestamp']
            for field in ['lastrev_date', 'timestamp']:
                rev_kwargs[field] = datetime.datetime.strptime(
                    rev_kwargs[field],
                    '%Y-%m-%dT%H:%M:%SZ').astimezone(pytz.UTC)
            try:
                Revision.objects.create(**rev_kwargs)
                revs_made += 1
            except IntegrityError as err:
                pass



def identify_links(filtered, field):
    """identify links in post and mark it in the db"""
    count = 0
    filtered.update(has_wiki_link=False, num_wiki_links=0)
    for post in filtered:
        post.wiki_links.clear()
        if count % 500 == 0:
            print('{}'.format(count))
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

def retrieve_links_info(posts_needing_revs):
    """
    Run through sampled threads and get corresponding Wiki data
    """
    ores_ep_template = 'https://ores.wikimedia.org/v2/scores/{context}/wp10?revids={revid}'
    session = requests.Session()
    session.headers.update(
        {'User-Agent': 'ugc-val-est; nickvincent@u.northwestern.edu; research tool'})

    count = 0
    err_count = 0
    process_start = time.time()
    print('About to get revisions for {} posts'.format(len(filtered))
    for post in posts_needing_revs:
        if count % 100 == 0:
            print('Finished: {}, Errors: {}, Time: {}'.format(count, err_count, time.time() - process_start))
        count += 1
        try:
            get_revs_for_single_post(post, ores_ep_template, session)
            post.all_revisions_pulled = True
            post.save()
        except (
                MissingRevisionId, PostMissingValidLink
        ):
            err_count += 1
            post.all_revisions_pulled = True
            post.save()
        except (ConnectionError, JSONDecodeError) as err:
            err_count += 1
            print('{} occurred so this result will NOT be saved'.format(err))
    
    revs_needing_userinfo = Revision.objects.filter(user=None, err_code=0)
    get_userinfo_for_all_revs(revs_needing_userinfo)
    print('About to get users for {} revs'.format(len(revs_needing_userinfo)))    
    links_needing_score = WikiLink.objects.filter(day_of_avg_score=None, err_code=0)
    print('About to get scores for {} links'.format(len(links_needing_score)))
    get_scores_for_all_links(links_needing_score)


def parse():
    """
    Parse args and do the appropriate analysis
    """
    parser = argparse.ArgumentParser(
        description='Identify wikipedia links and get info about them')
    parser.add_argument(
        '--platform', nargs='?',
        default=None, help='the platform to use. "r" for reddit and "s" for stack overflow')
    parser.add_argument(
        '--mode', help='identify, retrieve, full (performs both in sequence)')
    parser.add_argument(
        '--clear_first', action='store_true', default=False,
        help='identify, retrieve, full (performs both in sequence)')
    args = parser.parse_args()
    if args.platform is None:
        platforms = ['r', 's']
    else:
        platforms = [args.platform]
    for platform in platforms:
        if platform == 'r':
            field = 'url'
            model = SampledRedditThread
        else:
            field = 'body'
            model = SampledStackOverflowPost
        if args.clear_first:
            for obj in model.objects.filter(all_revisions_pulled=True):
                for wiki_link in obj.wiki_links.all():
                    Revision.objects.filter(wiki_link=wiki_link).delete()
                obj.wiki_links.all().delete()
                ErrorLog.objects.filter(uid=obj.uid).delete()
            model.objects.filter(all_revisions_pulled=True).update(
                has_wiki_link=False,
                day_of_avg_score=None,
                week_after_avg_score=None,
                wiki_content_error=0,
                num_wiki_links=0,
                all_revisions_pulled=False,
            )
        if args.mode == 'identify' or args.mode == 'full':
            filtered = model.objects.filter(**{field + '__contains': WIK})
            print('Going to IDENTIFY {} items'.format(len(filtered)))
            identify_links(filtered, field)
        if args.mode == 'retrieve' or args.mode == 'full':
            filtered = model.objects.filter(has_wiki_link=True, all_revisions_pulled=False)
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
