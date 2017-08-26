"""
Performs statistical analysis on sampled data
"""
# pylint: disable=E0401
import argparse
import csv
import operator
import os
from collections import defaultdict
from pprint import pprint
import time
from queryset_helpers import (
    batch_qs,
    list_common_features,
    list_stack_specific_features,
    list_reddit_specific_features
)
from url_helpers import extract_urls

import matplotlib
matplotlib.use('Agg')
# pylint:disable=C0413
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


def percent_bias(x_arr, y_arr):
    """Calculate the percent bias for two groups
    Inputs should be numerical arrays corresponding to the two groups
    """
    delta = np.mean(x_arr) - np.mean(y_arr)
    denom = np.sqrt((np.var(x_arr) + np.var(y_arr)) / 2.0)
    return 100.0 * delta / denom


def alt_cohen_d(x_arr, y_arr):
    """
    Takes two lists and returns cohen's d effect size calculatins
    This version uses simple calculation for pooled_Std
    """
    delta = np.mean(x_arr) - np.mean(y_arr)
    pooled_std = np.sqrt((np.std(x_arr, ddof=1) ** 2 +
                          np.std(y_arr, ddof=1) ** 2) / 2.0)
    return delta / pooled_std


def cohen_d(x_arr, y_arr):
    """
    Takes two lists and returns cohen's d effect size calculation
    This version uses more involved calculation for pooled_std
    Uses the length of both arrays
    """
    delta = np.mean(x_arr) - np.mean(y_arr)
    pooled_std = np.sqrt(
        (
            (len(x_arr) - 1) * np.std(x_arr, ddof=1) ** 2 +
            (len(y_arr) - 1) * np.std(y_arr, ddof=1) ** 2
        ) / (len(x_arr) + len(y_arr))
    )
    return delta / pooled_std


def cles(lessers, greaters):
    """
    Common-Language Effect Size
    Probability that a random draw from `greater` is in fact greater
    than a random draw from `lesser`.
    Args:
      lesser, greater: Iterables of comparables.
    """
    numerator = 0
    lessers, greaters = sorted(lessers), sorted(greaters)
    lesser_index = 0
    for _, greater in enumerate(greaters):
        while lesser_index < len(lessers) and lessers[lesser_index] < greater:
            lesser_index += 1
        numerator += lesser_index  # the count less than the greater
    # total combinations of 1 treatment and 1 control
    denominator = len(lessers) * len(greaters)
    return float(numerator) / denominator


def plot_bar(counter, title="", filename="tmp.png"):
    """"
    This function creates a bar plot from a counter.

    :param counter: This is a counter object, a dictionary with the item as the key
     and the frequency as the value
    :param ax: an axis of matplotlib
    :return: the axis wit the object in it
    """

    fig = plt.figure()
    axis = fig.add_subplot(111)

    if isinstance(counter, dict):
        frequencies = counter.values()
        names = counter.keys()
    elif isinstance(counter, list):
        frequencies = [x[1] for x in counter]
        names = [x[0] for x in counter]
    y_pos = np.arange(len(counter))
    axis.barh(y_pos, frequencies, align='center')
    axis.set_title(title)
    axis.set_yticks(y_pos)
    axis.set_yticklabels(list(names))
    axis.invert_yaxis()
    axis.set_xlabel('Frequency')
    print('going to save fig...')
    fig.savefig('png_files/' + filename.replace(".csv", ".png"))

    return axis


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
    filename = "{}_{}_{}.csv".format(field, qs_name, num_threads)
    print(title)
    val_to_count = defaultdict(int)
    qs = qs.order_by('uid')

    # start, end, total
    start_time = time.time()
    for start, end, total, batch in batch_qs(qs, num_threads, 10000):
        stamp = time.time()
        for thread in batch:
            vals = [getattr(thread, field)]
            if extractor is not None:
                vals = extractor(vals[0])
            for val in vals:
                val_to_count[val] += 1
        print('Finished threads {} to {} of {}. Took {}'.format(
            start, end, total, time.time() - stamp))
        print('Running time: {}'.format(time.time() - start_time))
        print(len(val_to_count.keys()))
    sorted_val_to_count = sorted(
        val_to_count.items(), key=operator.itemgetter(1), reverse=True)
    plot_bar(sorted_val_to_count[:20], title, filename)

    rows = []
    for i, val_tup in enumerate(sorted_val_to_count[:25]):
        count = val_to_count[val_tup[0]]
        percent = count / num_threads * 100
        print(i, val_tup, percent)
        rows.append([i, val_tup, percent])
    with open('csv_files/' + filename, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(rows)


def tags_frequency_distribution(qs):
    """
    Takes a qs and figure out which tags to links are found in

    This is more complicated than the generic frequency distribution
    because each post can have as many tags as desired by users
    """
    num_threads = qs.count()
    title = 'Identifying tag distribution for {} threads'.format(num_threads)
    print(title)
    tag_to_count = defaultdict(int)
    qs = qs.order_by('uid')

    # start, end, total
    for start, end, total, batch in batch_qs(qs, num_threads, 1000):
        print('Processing threads {} to {} of {}'.format(start, end, total))
        for thread in batch:
            tags = thread.tags_string.split('|')
            for tag in tags:
                tag_to_count[tag] += 1
    sorted_tag_to_count = sorted(
        tag_to_count.items(), key=operator.itemgetter(1), reverse=True)

    rows = []
    for i, val_tup in enumerate(sorted_tag_to_count[:25]):
        val = val_tup[0]
        count = tag_to_count[val]
        percent = count / num_threads * 100
        print(i, val_tup, percent)
        rows.append([i, val_tup, percent])
    with open(title, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(rows)


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


def univariate_analysis(groups):
    """Mean, median, variance"""
    groups_to_analyze = []
    basic = {}
    central_tendencies = {}
    dispersion = {}
    all_vals = np.array([])
    for group in groups:
        all_vals = np.concatenate((all_vals, group['vals']), axis=0)
        groups_to_analyze.append(group)
    groups_to_analyze.append({
        'name': 'All groups',
        'vals': all_vals
    })
    for group in groups_to_analyze:
        basic[group['name']] = {
            'num_items': len(group['vals']),
            'sum': sum(group['vals']),
        }
        central_tendencies[group['name']] = get_central_tendency_breakdown(
            group['vals'])
        dispersion[group['name']] = {
            'range': np.ptp(group['vals']),
            'standard deviation': np.std(group['vals']),
        }
    for group in groups_to_analyze:
        basic[group['name']]['percent_of_total_items'] = basic[group['name']
                                                              ]['num_items'] / len(all_vals) * 100
        basic[group['name']]['percent_of_total_sum'] = basic[group['name']
                                                            ]['sum'] / sum(all_vals) * 100
    return {
        'basic': basic,
        'central_tendencies': central_tendencies,
        'dispersion': dispersion
    }


def inferential_analysis(x_arr, y_arr, samples_related):
    """
    Performs t-test, cohen's d calculation, and mean difference calculations
    """
    delta = np.mean(x_arr) - np.mean(y_arr)
    if samples_related:
        _, pval = stats.ttest_rel(
            x_arr, y_arr)
    else:    
        _, pval = stats.ttest_ind(
            x_arr, y_arr, equal_var=False)  # _ = tstat
    cles_score_flipped = cles(x_arr, y_arr)
    cles_score = cles(y_arr, x_arr)
    return {
        'Hypothesis Testing': {
            'Treatment vs Control': {
                'Difference': delta,
                'p_value': pval,
                'percent_bias': percent_bias(x_arr, y_arr),
                'cohen\'s d effect size': cohen_d(x_arr, y_arr),
                'CLES': cles_score,
                'CLES flipped (treatment=lesser)': cles_score_flipped,
                'Wilcoxon rank-sum statistic': stats.ranksums(x_arr, y_arr),
            }
        }
    }


def get_links_from_body(body):
    """Return link base from a body"""
    return [get_base(url) for url in extract_urls(body)]


def get_links_from_url(url):
    """Returns link bases from a url"""
    return [get_base(url)]


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


def output_stats(output_filename, descriptive_stats, inferential_stats):
    """
    Takes descriptive and inferential and prints and writes to a file
    """
    # join stats dicts together for convenience in printing output
    output = {}
    for subset_name in descriptive_stats:
        output[subset_name] = {}
        for variable in descriptive_stats[subset_name]:
            output[subset_name][variable] = descriptive_stats[subset_name][variable].copy()
            output[subset_name][variable].update(
                inferential_stats[subset_name][variable])

    cols_captured = False
    rows = []
    first_row = ['', ]
    second_row = ['', ]
    for subset_name, variables in output.items():
        for variable, stat_categories in variables.items():
            # one row per subset/variable combo
            row_description = "Variable `{}` in subset `{}`".format(
                variable, subset_name)
            row = []
            row.append(row_description)
            for stat_category, subgroups in stat_categories.items():
                first_row_segment = []
                for subgroup, stat_names in subgroups.items():
                    for stat_name, stat_value in stat_names.items():
                        if not cols_captured:
                            first_row_segment.append('')
                            second_row.append(
                                '{}, {}'.format(subgroup, stat_name))
                        row.append(stat_value)
                if not cols_captured:
                    first_row_segment[0] = stat_category
                    first_row += first_row_segment
            if not cols_captured:
                cols_captured = True
            rows.append(row)
    rows = [first_row, second_row, ] + rows
    arr = np.array(rows, dtype=object)
    # arr = np.transpose(arr)
    with open('csv_files/' + output_filename, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(arr)
    return output


def make_ln_func(variable):
    """Take an qs and computed the natural log of a variable"""
    def safe_ln_queryset(qs):
        """Takes the natural log of a queryset's values and handles zeros"""
        vals = qs.values_list(variable, flat=True)
        ret = np.log(vals)
        ret[ret == -np.inf] = 0
        return ret
    return safe_ln_queryset


def make_method_getter(method_name):
    """todo"""
    def get_method_outputs(qs):
        """Call the model method and return list of results"""
        vals = []
        qs = qs.order_by('uid')
        for _, _, _, batch in batch_qs(qs):
            for item in batch:
                vals.append(getattr(item, method_name)())
        return vals

    return get_method_outputs


def main(platform='r', rq=1, calculate_frequency=False):
    """Driver"""
    csv_dir = 'csv_files'
    png_dir = 'png_files'
    for directory in [csv_dir, png_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
    variables = ['score', 'num_comments', ]
    variables += list_common_features()
    if rq == 1:
        subsample_kwargs = {}
        treatment_kwargs = {'has_wiki_link': True, }
    if rq == 2:
        subsample_kwargs = {
            'has_wiki_link': True,
            'day_of_avg_score__isnull': False,
            'week_after_avg_score__isnull': False,
        }
        treatment_kwargs = {'has_good_wiki_link': True, }
    if rq == 3:
        subsample_kwargs = {
            'has_wiki_link': True,
            'day_of_avg_score__isnull': False,
            'week_after_avg_score__isnull': False,
        }
        treatment_kwargs = None

    if platform == 'r':
        datasets = [{
            'qs': SampledRedditThread.objects.filter(**subsample_kwargs),
            'name': 'All',
        }]
        if rq == 1 or rq == 2:
            datasets += [{
                'qs': SampledRedditThread.objects.filter(context='todayilearned'),
                'name': 'TIL'
            }, {
                'qs': SampledRedditThread.objects.filter(context__in=TOP_TEN),
                'name': 'Top_Ten'
            }]
        if rq == 3:
            datasets += [{
                'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
                    has_good_wiki_link=True
                )
                'name': 'Good'
            }, {
                'qs': SampledRedditThread.objects.filter(**subsample_kwargs).exclude(
                    has_good_wiki_link=True
                )
                'name': 'Bad'
            }]
        # variables += list_reddit_specific_features()
        extractor = get_links_from_url
        extract_from = 'url'
    elif platform == 's':
        datasets = [{
            'qs': SampledStackOverflowPost.objects.filter(**subsample_kwargs),
            'name': 'All SO'
        }]
        if rq == 3:
            datasets += [{
                'qs': SampledStackOverflowPost.objects.filter(**subsample_kwargs).filter(
                    has_good_wiki_link=True
                )
                'name': 'Good'
            }, {
                'qs': SampledStackOverflowPost.objects.filter(**subsample_kwargs).exclude(
                    has_good_wiki_link=True
                )
                'name': 'Bad'
            }]
        variables += ['num_pageviews']
        extractor = get_links_from_body
        extract_from = 'body'
    if rq == 3:
        variables = [
            ('num_edits', 'num_edits_prev_week'),
            ('norm_change_edits', make_method_getter('norm_change_edits')),
            ('num_new_editors', 'num_new_editors_prev_week'),
            ('num_new_editors_retained', 'num_new_editors_retained_prev_week'),            
            ('percent_new_editors', make_method_getter('percent_new_editors')),
            ('percent_active_editors', make_method_getter('percent_active_editors')),
            ('percent_active_editors', make_method_getter('percent_active_editors')),
            ('percent_inactive_editors', make_method_getter('percent_inactive_editors')),
            ('num_active_edits', 'num_active_edits_prev_week'),
            ('num_inactive_edits', 'num_inactive_edits_prev_week'),
            ('num_major_edits', 'num_major_edits_prev_week'),
            ('num_minor_edits', 'num_minor_edits_prev_week'),
            ('percent_of_revs_preceding_post',
                make_method_getter('percent_of_revs_preceding_post')),
            ('week_after_avg_score', 'day_of_avg_score'),
            ('num_wiki_pageviews', 'num_wiki_pageviews_prev_week')
        ]
    output_filename = "{}_{}_stats.csv".format(platform, rq)
    descriptive_stats = {}
    inferential_stats = {}
    for dataset in datasets:
        name = dataset['name']
        qs = dataset['qs']
        if calculate_frequency:
            # extracts LINK BASES from URL
            frequency_distribution(
                qs, extract_from, name, extractor)
        if treatment_kwargs:
            treatment = {
                'name': 'Treatment',
                'qs': qs.filter(**treatment_kwargs)
            }
            control = {
                'name': 'Control',
                'qs': qs.exclude(**treatment_kwargs)
            }
        else:
            treatment = {
                'name': 'Treatment',
                'qs': qs
            }
            control = {
                'name': 'Control',
                'qs': qs
            }
        groups = [treatment, control]

        descriptive_stats[name] = {}
        inferential_stats[name] = {}
        for variable in variables:
            variable_name = variable
            treatment_var, control_var, method = None, None, None
            if isinstance(variable, tuple):
                if callable(variable[1]):
                    variable_name, method = variable
                else:
                    treatment_var, control_var = variable
                    variable_name = '{} vs {}'.format(treatment_var, control_var)
            print('processing variable {}'.format(variable_name))
            try:
                for group in groups:
                    if method:
                        group['vals'] = method(group['qs'])
                    elif treatment_var and control_var:
                        if group['name'] == 'Treatment':
                            group['vals'] = group['qs'].values_list(treatment_var, flat=True)
                        elif group['name'] == 'Control':
                            group['vals'] = group['qs'].values_list(control_var, flat=True)
                    else:
                        group['vals'] = group['qs'].values_list(variable, flat=True)
                    group['vals'] = [x for x in group['vals'] if x is not None]
                    group['vals'] = np.array(group['vals'])
                    if calculate_frequency:
                        if platform == 'r':
                            frequency_distribution(
                                group['qs'], 'context', name + '_' + group['name'])

                len1, len2 = len(treatment['vals']), len(control['vals'])
                if len1 == 0 or len2 == 0:
                    print('Skipping variable {} because {}, {}.'.format(
                        variable_name, len1, len2))
                try:
                    inferential_stats[name][variable_name] = inferential_analysis(
                        treatment['vals'], control['vals'], treatment_kwargs is None)
                    # groups = [group for group in groups if group['vals']]
                    descriptive_stats[name][variable_name] = univariate_analysis(groups)
                except TypeError as err:
                    print('analysis of variable {} failed because {}'.format(
                        variable_name, err
                    ))
            except ZeroDivisionError:
                print('Skipping variable {} bc zero division'.format(
                    variable_name
                ))
    pprint(descriptive_stats)
    output = output_stats(
        output_filename, descriptive_stats, inferential_stats)
    print(output)
    # plt.show()


def explain():
    """explain distribution"""
    for platform in [SampledRedditThread, SampledStackOverflowPost]:
        print('==={}==='.format(platform.__name__))
        qs = platform.objects.filter(has_wiki_link=True, day_of_avg_score__isnull=False)
        counter = defaultdict(int)
        for obj in qs:
            counter[obj.day_of_avg_score] += 1
        vals = [str(counter[key]) for key in sorted(counter.keys())]
        print(','.join(vals))
        pprint(counter)


def parse():
    """
    Parse args and do the appropriate analysis
    """
    parser = argparse.ArgumentParser(
        description='Calculates statistics of sampled data')
    parser.add_argument(
        '--platform', default=None,
        help='the platform to use. "r" for reddit and "s" for stack overflow. Leave blank to do both')
    parser.add_argument(
        '--rq', default=None,
        help='the research question to answer. 1, 2, or 3', type=int)
    parser.add_argument(
        '--frequency',
        action='store_true',
        help='Compute the frequency distributions of urls, subreddits, and tags (slow)')
    parser.add_argument(
        '--tags',
        action='store_true',
        help='Only compute tags frequency dist. Overrides other options.')
    parser.add_argument(
        '--explain',
        action='store_true',
        help='custom helper. Check code not docs.')
    args = parser.parse_args()
    if args.tags:
        tags_frequency_distribution(
            SampledStackOverflowPost.objects.all())
        tags_frequency_distribution(
            SampledStackOverflowPost.objects.filter(has_wiki_link=True))
    elif args.explain:
        explain()
    else:
        if args.platform is None:
            platforms = ['r', 's', ]
        else:
            platforms = [args.platform]
        if args.rq is None:
            rqs = [1, 2, 3]
        else:
            rqs = [args.rq]
        for platform in platforms:
            for rq in rqs:
                main(platform, rq, args.frequency)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
    )
    parse()
