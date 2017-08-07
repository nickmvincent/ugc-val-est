import argparse
import csv
import operator
import os
from collections import defaultdict
from pprint import pprint

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

WIKI = 'wikipedia.org/wiki/'


def merge_dicts(first, second):
    """
    Merge two nested dictionfirstriseconds
    Both dicts must be of depth 2 and have the SAME keys on level 0
    The point is the get a single output with union of keys on level 1
    Args:
        first - dict with depth 2
        second - dict with depth 2
    Returns:
        ret - a dict with depth 2
    """
    ret = {}
    for key in first.keys():
        ret[key] = {}
        for nested_key in first[key].keys():
            ret[key][nested_key] = first[key][nested_key]
        for nested_key in second[key].keys():
            ret[key][nested_key] = second[key][nested_key]
    return ret


def batch_qs(qs, total=None, batch_size=1000):
    """
    Returns a (start, end, total, queryset) tuple for each batch in the given
    queryset.

    The purpose of the `total` parameter is to save memory/query time
    if the length of the queryset has already been determined in
    the parent code.

    Usage:
        # Make sure to order your querset
        article_qs = Article.objects.order_by('id')
        total = article_qs.count()
        for start, end, total, qs in batch_qs(article_qs, total, 1500):
            print "Now processing %s - %s of %s" % (start + 1, end, total)
            for article in qs:
                print article.body
    """
    if total is None:
        total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield (start, end, total, qs[start:end])


def plot_bar(counter, title="", ax=None):
    """"
    This function creates a bar plot from a counter.

    :param counter: This is a counter object, a dictionary with the item as the key
     and the frequency as the value
    :param ax: an axis of matplotlib
    :return: the axis wit the object in it
    """

    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(111)

    if isinstance(counter, dict):
        frequencies = counter.values()
        names = counter.keys()
    elif isinstance(counter, list):
        frequencies = [x[1] for x in counter]
        names = [x[0] for x in counter]
    y_pos = np.arange(len(counter))
    ax.barh(y_pos, frequencies, align='center')
    ax.set_title(title)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(list(names))
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Frequency')

    return ax


TOP_TEN = [
    'announcements',
    'funny',
    'AskReddit',
    'todayilearned',
    'science',
    'worldnews',
    'pics',
    'IAmA',
    'gaming',
    'videos',
]


def frequency_distribution(qs, field, qs_name, extractor=None):
    """
    Takes a qs a figure out which base urls the links go to
    """
    num_threads = qs.count()
    title = 'Frequency Distribution of {} in subset "{}" ({} threads)'.format(
        field, qs_name, num_threads
    )
    print(title)
    val_to_count = defaultdict(int)
    qs = qs.order_by('uid')

    for start, end, total, batch in batch_qs(qs, num_threads, 1000):
        for thread in batch:
            val = getattr(thread, field)
            if extractor is not None:
                val = extractor(val)
            val_to_count[val] += 1
        sorted_val_to_count = sorted(
            val_to_count.items(), key=operator.itemgetter(1), reverse=True)
    plot_bar(sorted_val_to_count[:20], title)

    for i, val_tup in enumerate(sorted_val_to_count[:25]):
        val = val_tup[0]
        count = val_to_count[val]
        percent = count / num_threads * 100
        print(i, val_tup, percent)


def tags_frequency_distribution(qs):
    """
    Takes a qs and figure out which tags to links are found in

    This is more complicated than the generic frequency distribution
    because each post can have as many tags as desired by users
    """
    num_threads = qs.count()
    print('Identifying tagdistribution for {} threads'.format(num_threads))
    tag_to_count = defaultdict(int)
    qs = qs.order_by('uid')

    for start, end, total, batch in batch_qs(qs, num_threads, 1000):
        for thread in batch:
            tags = thread.tags_string.split('|')
            for tag in tags:
                tag_to_count[tag] += 1
        sorted_tag_to_count = sorted(
            tag_to_count.items(), key=operator.itemgetter(1), reverse=True)

    for i, val_tup in enumerate(sorted_tag_to_count[:25]):
        val = val_tup[0]
        count = tag_to_count[val]
        percent = count / num_threads * 100
        print(i, val_tup, percent)


def get_central_tendency_breakdown(vals):
    """
    Takes a queryset and breaks into to lists:
        has wikipedia and doesn't have wikipedia
    Return a mean score for both.
    """
    return {
        'mean': np.mean(vals),
        'median': np.median(vals),
    }


def univariate_analysis(vals, groups):
    """Mean, median, variance"""
    central_tendencies = {}
    for group in groups:
        central_tendencies[group['name']] = get_central_tendency_breakdown(
            group['vals'])
    dispersion = {
        'Peak to peak range': np.ptp(vals),
        'Standard Deviation': np.std(vals),
    }
    return {
        'central_tendencies': central_tendencies,
        'dispersion': dispersion
    }


def get_base(url):
    """Return the base of a given url"""
    aliases = {
        'youtu.be': 'youtube.com',
        'i.reddituploads.com': 'reddit.com',
        'i.redd.it': 'reddit.com',
        'np.reddit.com': 'reddit.com',
        'redd.it': 'reddit.com',
        'i.sli.mg': 'imgur.com',
        'i.imgur.com': 'imgur.com',
    }
    double_slash = url.find('//')
    single_slash = url.find('/', double_slash + 2)
    base = url[double_slash + 2:single_slash]
    base = base.replace('www.', '')
    base = base.replace('.m.', '.')
    if base[0:2] == 'm.':
        base = base.replace('m.', '')
    if 'wikipedia.org' in base:
        return 'wikipedia.org'
    for alias_domain, actual_domain in aliases.items():
        if base == alias_domain:
            return actual_domain
    return base


def main(platform='r', calculate_frequency=False):
    """Driver"""
    # subreddits = list(SampledRedditThread.objects.filter(url__contains='wikipedia.org/wiki/').values_list('context', flat=True))
    # subreddit_counts = Counter(subreddits)
    # plot_bar_from_counter(subreddit_counts, label=False)
    # key_list = list(subreddit_counts.keys())
    # index_to_key = {i: key for i, key in enumerate(key_list)}
    if platform == 'r':
        datasets = [{
            'qs': SampledRedditThread.objects.filter(context='todayilearned'),
            'name': 'TIL'
        },
            {
                'qs': SampledRedditThread.objects.filter(context__in=TOP_TEN),
                'name': 'TOP TEN'
        },
            {
                'qs': SampledRedditThread.objects.all(),
                'name': 'ALL',
        }
        ]
        variables = ['score', 'num_comments']
        filter_kwargs = {
            'url__contains': WIKI
        }
        output_fn = "reddit_stats.csv"
    else:
        datasets = [{
            'qs': SampledStackOverflowPost.objects.all(),
            'name': 'All SO'
        },
        ]
        variables = ['score', ]
        filter_kwargs = {
            'body__contains': WIKI
        }
        output_fn = "stack_overflow_stats.csv"
    descriptive_stats = {}
    inferential_stats = {}
    for dataset in datasets:
        name = dataset['name']
        qs = dataset['qs']
        if calculate_frequency:
            frequency_distribution(
                qs, 'url', name, get_base)
        has_wikilink_group = {
            'name': 'Has Wikipedia Link',
            'qs': qs.filter(**filter_kwargs)
        }
        no_wikilink_group = {
            'name': 'No Wikipedia Link',
            'qs': qs.exclude(**filter_kwargs)
        }
        groups = [has_wikilink_group, no_wikilink_group, {
            'name': 'All',
            'qs': qs,
        }]

        descriptive_stats[name] = {}
        inferential_stats[name] = {}
        for variable in variables:
            for group in groups:
                group['vals'] = np.array(
                    group['qs'].values_list(variable, flat=True))
                if calculate_frequency:
                    if platform == 'r':
                        frequency_distribution(
                            group['qs'], 'context', name)
                    else:
                        # tags_frequency_distribution(group['qs'])
                        pass
            tmp = inferential_stats[name][variable] = {}
            tmp['t'], tmp['p'] = stats.ttest_ind(
                has_wikilink_group['vals'], no_wikilink_group['vals'])
            vals = dataset['qs'].values_list(variable, flat=True)
            descriptive_stats[name][variable] = univariate_analysis(
                vals, groups)
    pprint(inferential_stats)
    pprint(descriptive_stats)
    # join stats dicts together for convenience in printing output

    output = merge_dicts(descriptive_stats, inferential_stats)
    pprint(output)

    rows = []
    for key0, val0 in output.items():
        for key1, val1 in val0.items():
            rows.append([key1, val1])
    with open(output_fn, 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    # print(index_to_key)
    plt.show()


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import SampledRedditThread, SampledStackOverflowPost
    parser = argparse.ArgumentParser(
        description='Calculates statistics of sampled data')
    parser.add_argument(
        'platform', help='the platform to use. "r" for reddit and "s" for stack overflow')
    parser.add_argument(
        '--frequency',
        action='store_true',
        help='Compute the frequency distributions of urls, subreddits, and tags (slow)')
    parser.add_argument(
        '--tags',
        action='store_true',
        help='Only compute tags frequency dist')
    args = parser.parse_args()
    if args.tags:
        tags_frequency_distribution(
            SampledStackOverflowPost.objects.all())
        tags_frequency_distribution(
            SampledStackOverflowPost.objects.filter(body__contains=WIKI))
    else:
        main(args.platform, args.frequency)
