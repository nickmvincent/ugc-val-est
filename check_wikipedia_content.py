"""
This module runs through all posts in the DB,
checks for Wikipedia content, and get ORES score
"""

import datetime
import os
import time
import argparse
from collections import defaultdict

from urllib.parse import unquote
from itertools import zip_longest
from json.decoder import JSONDecodeError


from scoring_helpers import map_ores_code_to_int
from url_helpers import extract_urls
import pytz
from requests.exceptions import ConnectionError
import requests
import mwapi
import mwreverts.api

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
    first = True
    while True:
        # if first:
        #     first = False
        # else:
        #     print('redoing this one...')
        #     verbose = True
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
        if 'rvlimit' in req and req['rvlimit'] == 1:
            break
        if 'uclimit' in req and req['uclimit'] == 1:
            break
        # if 'end' not in req:
        #     break
        last_continue = result['continue']
    return results


def make_pageview_request(session, **kwargs):
    """
    example:  http://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/
    all-access/all-agents/Albert_Einstein/daily/2015100100/2015103100
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
    make a user request
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


def get_scores_for_posts(posts, session):
    """Gets two scores for posts passed in"""
    ores_ep_template = 'https://ores.wikimedia.org/v3/scores/{context}?models=wp10&revids={revids}'
    revid_to_rev = {}
    for post in posts:
        dja_links = post.wiki_links.all()
        for dja_link in dja_links:
            if dja_link.language_code != 'en':
                print('skipping non english version')
                continue
            dja_revs = Revision.objects.filter(wiki_link=dja_link)
            try:
                for timestamp in [post.timestamp, post.timestamp + datetime.timedelta(days=7)]:
                    closest_rev = get_closest_to(dja_revs, timestamp)
                    revid_to_rev[closest_rev.revid] = closest_rev
            except IndexError:
                continue
        ores_context = 'en' + 'wiki'
    counter, start = 0, time.time()
    completed = 0
    num_revs = len(revid_to_rev.keys())
    for revbatch in grouper(revid_to_rev.keys(), 50):
        revbatch = [rev for rev in revbatch if rev]
        ores_ep = ores_ep_template.format(**{
            'context': ores_context,
            'revids': '|'.join(revbatch)
        })
        ores_resp = session.get(ores_ep)
        ores_resp = ores_resp.json()
        scores = ores_resp[ores_context]['scores']
        for revid in revbatch:
            rev = revid_to_rev[revid]
            try:
                predicted_code = scores[str(revid)]['wp10']['score']['prediction']
                rev.score = map_ores_code_to_int(predicted_code)
            except KeyError:
                rev.err_code = 4  # missingOresResponse
            rev.save()
        completed += len(revbatch)
        counter += 1

        if counter == 10:
            counter = 0
            print('Finished {}/{} revs, time: {}'.format(
                completed, num_revs, time.time() - start
            ))
    for post in posts:
        post.save()


def get_damaging_likelihood(posts):
    """Gets two scores for posts passed in"""
    ores_ep_template = 'https://ores.wikimedia.org/v3/scores/{context}?models=damaging&revids={revids}'
    revid_to_rev = {}
    for post in posts:
        dja_links = post.wiki_links.all()
        for dja_link in dja_links:
            if dja_link.language_code != 'en':
                print('skipping non english version')
                continue
            dja_revs = Revision.objects.filter(wiki_link=dja_link)
            for rev in dja_revs:
                revid_to_rev[rev.revid] = rev
    ores_context = 'en' + 'wiki'
    damaging_count = 0
    completed = 0
    for revbatch in grouper(revid_to_rev.keys(), 50):
        revbatch = [rev for rev in revbatch if rev]
        ores_ep = ores_ep_template.format(**{
            'context': ores_context,
            'revids': '|'.join(revbatch)
        })
        ores_resp = requests.get(ores_ep)
        ores_resp = ores_resp.json()
        scores = ores_resp[ores_context]['scores']
        print(scores)
        for revid in revbatch:
            rev_resp = scores[revid]['damaging']
            if 'score' in rev_resp:
                pred = rev_resp['score']['prediction']
                completed += 1
                if pred:
                    damaging_count += 1
        completed += len(revbatch)

    print('{}/{} damaging posts'.format(damaging_count, completed))    


def check_reverted(qs1, qs2):
    """Check reverted"""
    session = mwapi.Session("https://en.wikipedia.org", user_agent='ugc-val-est; nickvincent@u.northwestern.edu; research tool')
    counts = []
    for qs in [qs1, qs2]:
        print('Going to do qs with {} posts'.format(len(qs)))
        count = defaultdict(int)
        counts.append(count)
        for post in qs:
            for link in post.wiki_links.all():
                revs = Revision.objects.filter(wiki_link=link)
                for rev in revs:
                    try:
                        count['total'] += 1
                        reverting, reverted, reverted_to = mwreverts.api.check(session, rev.revid)
                        if reverting:
                            count['reverting'] += 1
                        if reverted:
                            count['reverted'] += 1
                        if reverted_to:
                            count['reverted_to'] += 1
                    except Exception as err:
                        print(err)
    print(counts)
    send_mail(
        'Reverted counts :D',
        str(counts),
        settings.EMAIL_HOST_USER,
        ['nickmvincent@gmail.com'],
        fail_silently=False,
    )



def get_userinfo_for_all_revs(revs, session):
    """
    Gets the user information for revisions that still need it
    """
    user_to_revs = {}
    for rev in revs:
        if rev.user not in user_to_revs:
            user_to_revs[rev.user] = [rev]
        else:
            user_to_revs[rev.user].append(rev)
    num_users = len(user_to_revs.keys())
    counter = 0
    completed = 0
    start = time.time()    
    for userbatch in grouper(user_to_revs.keys(), 50):
        print('starting batch...')
        userbatch = [user for user in userbatch if user]
        users = []
        user_result_pages = make_user_request(
            session, 'en', userbatch)
        for page in user_result_pages:
            users += page.get('users', [])
        for user in users:
            lastrev_pages = make_lastrev_request(
                session, 'en',
                user['name'])
            lastrev_date = None
            for result_page in lastrev_pages:
                contribs = result_page['usercontribs']
                lastrev = contribs[0]
                lastrev_date = lastrev['timestamp']
            revs = user_to_revs[user['name']]
            for rev in revs:
                rev.editcount = user.get('editcount', 0)
                if user.get('registration'):
                    rev.registration = datetime.datetime.strptime(
                        user.get('registration'),
                        '%Y-%m-%dT%H:%M:%SZ').astimezone(pytz.UTC)
                if lastrev_date:
                    rev.lastrev_date = datetime.datetime.strptime(
                        lastrev_date,
                        '%Y-%m-%dT%H:%M:%SZ').astimezone(pytz.UTC)
                rev.save()
        completed += len(userbatch)
        counter += 1
        if counter == 2:
            counter = 0
            print('Finished {}/{} users, time: {}'.format(
                completed, num_users, time.time() - start))


def get_revs_for_single_post(post, session):
    """check a single post"""
    dja_links = post.wiki_links.all()
    total_revs = 0
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
        norm_title = dja_link.title
        if len(norm_title) >= 2:
            norm_title = norm_title[0].upper() + norm_title[1:]
        norm_title = norm_title.replace(' ', '_')
        norm_title = norm_title.replace('/', '%2F')
        pageviews_prev_week = make_pageview_request(
            session,
            title=norm_title, start=week_before_post.strftime(
                pageview_api_str_fmt),
            end=day_of_post_short_str)
        pageviews = make_pageview_request(
            session,
            title=norm_title, start=day_of_post_short_str,
            end=week_after_post.strftime(pageview_api_str_fmt))
        if pageviews_prev_week and pageviews:
            post.num_wiki_pageviews_prev_week = sum(
                [entry['views'] for entry in pageviews_prev_week])
            post.num_wiki_pageviews = sum(
                [entry['views'] for entry in pageviews])

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
        total_revs += len(rev_kwargs_lst)
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
                if 'duplicate key' not in str(err):
                    print(err)
    return total_revs    
        


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


def retrieve_links_info(posts_needing_revs, model):
    """
    Run through sampled threads and get corresponding Wiki data
    """
    session = requests.Session()
    session.headers.update(
        {'User-Agent': 'ugc-val-est; nickvincent@u.northwestern.edu; research tool'})

    count = 0
    total_revs = 0
    err_count = 0
    process_start = time.time()
    print('About to get revisions for {} posts'.format(len(posts_needing_revs)))
    for post in posts_needing_revs:
        if count % 10 == 0:
            print('Finished: {}, Revs: {}, Errors: {}, Time: {}'.format(
            count, total_revs, err_count, time.time() - process_start))
        count += 1
        try:
            total_revs += get_revs_for_single_post(post, session)
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

    revs_needing_userinfo = Revision.objects.filter(editcount=None, err_code=0)
    print('About to get users for {} revs'.format(len(revs_needing_userinfo)))    
    get_userinfo_for_all_revs(revs_needing_userinfo, session)

    posts_needing_score = model.objects.filter(
        has_wiki_link=True,
        day_of_avg_score=None, wiki_content_error=0
    )
    print('About to get scores for {} posts'.format(len(posts_needing_score)))
    get_scores_for_posts(posts_needing_score, session)


def test():
    """
    Test code
    """
    session = requests.Session()
    session.headers.update(
        {'User-Agent': 'ugc-val-est; nickvincent@u.northwestern.edu; research tool'})
    qsr = SampledRedditThread.objects.filter(has_wiki_link=True).order_by('?')[:200]
    qss = SampledStackOverflowPost.objects.filter(has_wiki_link=True).order_by('?')[:200]
    #qsdonald = SampledRedditThread.objects.filter(has_wiki_link=True, context='The_Donald')
    
    pageview_api_str_fmt = '%Y%m%d'
    for qs in [qsr, qss]:
        print('=====')
        for post in qs:
            day_of_post_short_str = post.timestamp.strftime(pageview_api_str_fmt)
            before_count = 0
            after_count = 0
            before_pageviews = 0
            after_pageviews = 0
            links = []
            for dja_link in post.wiki_links.all():
                if dja_link.language_code != 'en':
                    continue
                links.append('{} ({})'.format(dja_link.title, dja_link.id))
                revisions = []
                wiki_api_str_fmt = '%Y%m%d%H%M%S'
                week_before_post = post.timestamp - datetime.timedelta(days=7)
                week_after_post = post.timestamp + datetime.timedelta(days=7)
                week_before_post_str = week_before_post.strftime(wiki_api_str_fmt)
                week_after_post_str = week_after_post.strftime(wiki_api_str_fmt)
                revid_result_pages = make_revid_request(
                    session, dja_link.language_code, dja_link.title, week_before_post_str,
                    week_after_post_str)
                for result_page in revid_result_pages:
                    pages = result_page.get('pages', {})
                    for _, page in pages.items():
                        if 'missing' in page:
                            continue
                        if 'revisions' in page:
                            revisions += page['revisions']
                for rev_obj in revisions:
                    stamp = datetime.datetime.strptime(
                        rev_obj['timestamp'],
                        '%Y-%m-%dT%H:%M:%SZ').astimezone(pytz.UTC)
                    if stamp < post.timestamp:
                        before_count += 1
                    else:
                        after_count += 1
                norm_title = dja_link.title
                if len(norm_title) >= 2:
                    norm_title = norm_title[0].upper() + norm_title[1:]
                norm_title = norm_title.replace(' ', '_')
                norm_title = norm_title.replace('/', '%2F')
                pageviews_prev_week = make_pageview_request(
                    session,
                    title=norm_title, start=week_before_post.strftime(
                        pageview_api_str_fmt),
                    end=day_of_post_short_str)
                pageviews = make_pageview_request(
                    session,
                    title=norm_title, start=day_of_post_short_str,
                    end=week_after_post.strftime(pageview_api_str_fmt))
                if pageviews_prev_week and pageviews:
                    before_pageviews += sum(
                        [entry['views'] for entry in pageviews_prev_week])
                    after_pageviews += sum(
                        [entry['views'] for entry in pageviews])
            if before_count != post.num_edits_prev_week:
                print('before', before_count, '|', post.num_edits_prev_week, post.timestamp)
                for rev in revisions:
                    print(rev)
                    try:
                        rev_in_db = Revision.objects.filter(revid=rev.get('revid')).values()[0]
                        print('^^FROM DB:', rev_in_db)
                        wiki_link = WikiLink.objects.filter(id=rev_in_db.get('wiki_link_id'))[0]
                        print('Here is the wiki links we are on, and here is the wiki link this rev goes to...')
                        print(links, '{} ({})'.format(wiki_link.title, wiki_link.id))
                    except:
                        print('^^ rev missing...')
                    break
                input()
                for dja_link in post.wiki_links.all():
                    all_links = WikiLink.objects.filter(title=dja_link.title)
                    for link in all_links:
                        revs = Revision.objects.filter(wiki_link=link, timestamp__gte=week_before_post, timestamp__lte=week_after_post)
                        if link.id == dja_link.id:
                            print('**' + link.url,'|',revs.count())
                        else:
                            print(link.url, '|', revs.count())
            if after_count != post.num_edits:    
                print('after', after_count, '|', post.num_edits, post.timestamp)
                for rev in revisions:
                    print(rev)
                    try:
                        rev_in_db = Revision.objects.filter(revid=rev.get('revid')).values()[0]
                        print('^^FROM DB:', rev_in_db)
                        wiki_link = WikiLink.objects.filter(id=rev_in_db.get('wiki_link_id'))[0]
                        print('Here is the wiki link we are on, and here is the wiki link this rev goes to...')
                        print('{} ({})'.format(wiki_link.title, wiki_link.id), links)
                    except:
                        print('^^ rev missing...')
                    break
                input()
                for dja_link in post.wiki_links.all():
                    all_links = WikiLink.objects.filter(title=dja_link.title)
                    for link in all_links:
                        revs = Revision.objects.filter(wiki_link=link, timestamp__gte=week_before_post, timestamp__lte=week_after_post)
                        if link.id == dja_link.id:
                            print('**' + link.url, '|', revs.count())
                        else:
                            print(link.url, '|', revs.count())
            num_wiki_pageviews_prev_week = post.num_wiki_pageviews_prev_week if post.num_wiki_pageviews_prev_week else 0
            num_wiki_pageviews = post.num_wiki_pageviews if post.num_wiki_pageviews else 0
            if before_pageviews != num_wiki_pageviews_prev_week:
                print('error with before pageviews', before_pageviews, num_wiki_pageviews_prev_week)
                print(post.timestamp)
                input()
            if after_pageviews != num_wiki_pageviews:
                print('error with after pageviews', after_pageviews, num_wiki_pageviews)
                print(post.timestamp)
                input()
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
    parser.add_argument(
        '--test', action='store_true', default=False,
        help='test')
    parser.add_argument(
        '--start')
    parser.add_argument(
        '--end')
    args = parser.parse_args()
    if args.test:
        test()
    else:
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
                full =  model.objects.filter(
                    has_wiki_link=True).order_by('uid')
                print('fullcount', full.count())
                filtered = full[int(args.start):int(args.end)]
                filtered = [item for item in list(filtered) if item.all_revisions_pulled is False]
                print('Going to RETRIEVE INFO for {} items'.format(len(filtered)))
                retrieve_links_info(filtered, model)
            if args.mode == 'damaging':
                filtered = model.objects.filter(has_wiki_link=True)[:1000]
                print('checking on potentially damaging posts')
                get_damaging_likelihood(filtered)
            if args.mode == 'reverted':
                qs1 = model.objects.filter(has_wiki_link=True).order_by('?')[:816]
                qs2 = model.objects.filter(has_wiki_link=True, context="The_Donald").order_by('uid')
                print('reverted check')
                print(qs1.count(), qs2.count())
                check_reverted(qs1, qs2)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    from django.db.utils import IntegrityError
    from django.core.mail import send_mail
    from dja import settings
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
        WikiLink, Revision, ErrorLog,
        get_closest_to
    )
    parse()
