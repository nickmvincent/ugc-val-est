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
from django.db.models import Q

import tldextract


# set this manually for now
FILTER_LANG = False
EXCLUDE_NO_ORES = False

def so_special(treatment_feature, extra_filter):
    """helper"""
    if extra_filter:
        qs1 = SampledStackOverflowPost.objects.filter(
            has_wiki_link=True, sample_num__in=[0,1,2], has_c_wiki_link=True).order_by('uid')
        qs2 = SampledStackOverflowPost.objects.filter(
            has_wiki_link=True, sample_num__in=[0,1,2], has_c_wiki_link=False).order_by('uid')
    else:
        qs1 = SampledStackOverflowPost.objects.filter(
            sample_num=0, has_wiki_link=True).order_by('uid')
        qs2 = SampledStackOverflowPost.objects.filter(
            sample_num=0, has_wiki_link=False).order_by('uid')

    treat_question_ids = []
    control_question_ids = []
    start_time = time.time()
    count = defaultdict(int)
    treat = []
    control = []

    for start, end, total, batch in batch_qs(qs1, batch_size=10000):
        print('qs1', start, end, total, time.time() - start_time)
        for obj in batch:
            ans = StackOverflowAnswer.objects.using('secondary').get(id=obj.uid)
            question_id = ans.parent_id
            if question_id not in treat_question_ids:
                treat.append(obj.num_pageviews)
                count['treatment_total'] += obj.num_pageviews
                count['treatment_count'] += 1
                treat_question_ids.append(question_id)

            else:
                count['dropped_treatment_total'] += obj.num_pageviews
                count['dropped_treatment_count'] += 1
    for start, end, total, batch in batch_qs(qs2, batch_size=10000):
        print('qs2', start, end, total, time.time() - start_time)
        for obj in batch:
            ans = StackOverflowAnswer.objects.using('secondary').get(id=obj.uid)
            question_id = ans.parent_id
            if question_id in treat_question_ids:
                count['dropped_control_total'] += obj.num_pageviews
                count['dropped_control_count'] += 1
                continue
            if question_id not in control_question_ids:
                control.append(obj.num_pageviews)
                count['control_total'] += obj.num_pageviews
                count['control_count'] += 1
                control_question_ids.append(question_id)
            else:
                count['dropped_control_total'] += obj.num_pageviews
                count['dropped_control_count'] += 1
    print(count)
    return treat, control

def percent_bias(x_arr, y_arr):
    """
    Calculate the percent bias for two groups
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
    for i, val_tup in enumerate(sorted_val_to_count):
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
    return {
        'Hypothesis Testing': {
            'Treatment vs Control': {
                'Difference': delta,
                'p_value': pval,
                'percent_bias': percent_bias(x_arr, y_arr),
                # 'cohen\'s d effect size': cohen_d(x_arr, y_arr),
                # 'Wilcoxon rank-sum statistic': stats.ranksums(x_arr, y_arr),
            }
        }
    }


def get_links_from_body(body):
    """Return link base from a body"""
    return [get_base(url) for url in extract_urls(body)]


def get_links_from_url(url):
    """Returns link bases from a url"""
    return [get_base(url)]


# def get_base(url):
#     """Return the base of a given url"""
#     aliases = {
#         'youtu.be': 'youtube.com',
#         'i.reddituploads.com': 'reddit.com',
#         'i.redd.it': 'reddit.com',
#         'np.reddit.com': 'reddit.com',
#         'redd.it': 'reddit.com',
#         'i.sli.mg': 'imgur.com',
#         'i.imgur.com': 'imgur.com',
#     }
#     double_slash = url.find('//')
#     if double_slash == -1:
#         double_slash = -2
#     single_slash = url.find('/', double_slash + 2)
#     if single_slash == -1:
#         base = url[double_slash + 2:]
#     else:
#         base = url[double_slash + 2:single_slash]
#     base = base.replace('www.', '')
#     base = base.replace('.m.', '.')
#     if base[0:2] == 'm.':
#         base = base.replace('m.', '')
#     if 'wikipedia.org' in base:
#         return 'wikipedia.org'
#     for alias_domain, actual_domain in aliases.items():
#         if base == alias_domain:
#             return actual_domain
#     return base


def get_base(url):
    return tldextract.extract(url).domain


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
            row_description = "`{}` in `{}`".format(
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
    if output_filename:  # make sure not to write over file when doing bootstrapping!
        if FILTER_LANG:
            output_filename = 'lang_filtered_' + output_filename
        if EXCLUDE_NO_ORES:
            output_filename = 'exclude_no_ores_' + output_filename
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
    """This uses closures to return a function that gets
    method outputs for a queryset. The method called
    is determined by the input argument."""
    def get_method_outputs(qs):
        """Call the model method and return list of results"""
        vals = []
        qs = qs.order_by('uid')
        for _, _, _, batch in batch_qs(qs):
            for item in batch:
                vals.append(getattr(item, method_name)())
        return vals

    return get_method_outputs


def main(platform='r', rq=1, calculate_frequency=False, bootstrap=None, sample_num=None):
    """Driver"""
    csv_dir = 'csv_files'
    png_dir = 'png_files'
    for directory in [csv_dir, png_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
    variables = ['score', 'num_comments', ]
    variables += list_common_features()

    # compare has_wiki_link to has_no_wiki_link
    if rq == 10:
        subsample_kwargs = {}
        treatment_kwargs = {'has_wiki_link': True, }

    # only compare wiki links to no links
    elif rq == 12:
        subsample_kwargs = {'has_other_link': False}
        treatment_kwargs = {'has_wiki_link': True, }

    # only compare other link to no link
    elif rq == 11:
        subsample_kwargs = {'has_wiki_link': False}
        treatment_kwargs = {'has_other_link': True, }    

    # rq == 13: special so pageviews analysis
    # rq == 14: special so pageviews analysis comparing quality
    elif rq == 13 or rq == 14 or rq == 15:
        subsample_kwargs = {}
        treatment_kwargs = {}
    elif rq == 2:
        subsample_kwargs = {
            'has_wiki_link': True,
            'day_of_avg_score__isnull': False,
        }
        treatment_kwargs = {'has_c_wiki_link': True, }
    elif rq == 3:
        subsample_kwargs = {
            'has_wiki_link': True,
        }
        treatment_kwargs = None
        if EXCLUDE_NO_ORES:
            subsample_kwargs['day_of_avg_score__isnull'] = False
    elif rq == 32:
        subsample_kwargs = {
            'has_wiki_link': True,
        }
        treatment_kwargs = None
    elif rq == 33:
        subsample_kwargs = {
            'has_wiki_link': True,
            'num_wiki_pageviews__gt': 0,
            'num_wiki_pageviews_prev_week__gt': 0,
        }
        treatment_kwargs = None
    if sample_num is None:
        subsample_kwargs['sample_num__in'] = [0, 1, 2]
    else:
        subsample_kwargs['sample_num__in'] = [int(x) for x in sample_num.split(',')]
    print(subsample_kwargs)

    if platform == 'r':
        datasets = [{
            'qs': SampledRedditThread.objects.filter(**subsample_kwargs),
            'name': 'All',
        }]
        if not bootstrap:
            datasets += [{
                'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
                    context='todayilearned'),
                'name': 'todayilearned'
            },
            #{    'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
            #         context__in=TOP_TEN),
            #     'name': 'TOP TEN'
            # }, {
            #     'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
            #         context='borntoday'),
            #     'name': 'borntoday'
            # }, {
            #     'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
            #         context='wikipedia'),
            #     'name': 'wikipedia'
            # }, {
            #     'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
            #         context='CelebrityBornToday'),
            #     'name': 'CelebrityBornToday'
            # }, {
            #     'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
            #         context='The_Donald'),
            #     'name': 'The_Donald'
            # }, {
            #     'qs': SampledRedditThread.objects.filter(**subsample_kwargs).exclude(
            #         context__in=[
            #             'The_Donald', 'CelebrityBornToday', 'wikipedia', 'borntoday', 'todayilearned',
            #         ]),
            #     'name': 'OTHER'
            # }
            
            ]
        if rq == 3:
            datasets += [{
                'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
                    day_of_avg_score__gte=4),
                'name': 'GA'
            }, {
                'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
                    day_of_avg_score__gte=3, day_of_avg_score__lt=4),
                'name': 'B'
            }, {
                'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
                    day_of_avg_score__gte=2, day_of_avg_score__lt=3),
                'name': 'C'
            },{
                'qs': SampledRedditThread.objects.filter(**subsample_kwargs).filter(
                    day_of_avg_score__lt=2),
                'name': 'other'
            }]
        variables += list_reddit_specific_features()
        extractor = get_links_from_url
        extract_from = 'url'
    elif platform == 's':
        datasets = [{
            'qs': SampledStackOverflowPost.objects.filter(**subsample_kwargs),
            'name': 'All'
        }]
        if rq == 3:
            datasets += [{
                'qs': SampledStackOverflowPost.objects.filter(**subsample_kwargs).filter(
                    day_of_avg_score__gte=4),
                'name': 'GA'
            }, {
                'qs': SampledStackOverflowPost.objects.filter(**subsample_kwargs).filter(
                    day_of_avg_score__gte=3, day_of_avg_score__lt=4),
                'name': 'B'
            }, {
                'qs': SampledStackOverflowPost.objects.filter(**subsample_kwargs).filter(
                    day_of_avg_score__gte=2, day_of_avg_score__lt=3),
                'name': 'C'
            }, {
                'qs': SampledStackOverflowPost.objects.filter(**subsample_kwargs).filter(
                    day_of_avg_score__lt=2),
                'name': 'other'
            }]
        variables += list_stack_specific_features()
        variables += ['num_pageviews', 'num_wiki_increased_pageviews_day_of']
        extractor = get_links_from_body
        extract_from = 'body'
            
    if rq == 3:
        variables = [
            ('num_edits', 'num_edits_prev_week'),
            ('num_new_editors', 'num_new_editors_prev_week'),
            ('num_new_editors_retained', 'num_new_editors_retained_prev_week'),
            ('num_new_editors_retained_180', 'num_new_editors_retained_prev_week_180'),
            ('percent_of_revs_preceding_post',
             make_method_getter('percent_of_revs_preceding_post')),
            ('week_after_avg_score', 'day_of_avg_score'),
            ('num_wiki_pageviews', 'num_wiki_pageviews_prev_week')
        ]
    # day of page views
    if rq == 15:
        variables = ['num_wiki_increased_pageviews_day_of']
    if rq == 32:
        variables = [
            ('num_edits', 'num_edits_prev_week'),
            ('num_wiki_pageviews', 'num_wiki_pageviews_prev_week')
        ]
    if rq == 33:
        variables = [
            ('num_wiki_pageviews', 'num_wiki_pageviews_prev_week')
        ]
    db_name = connection.settings_dict['NAME']
    output_filename = "STATS_on_{}_rq_{}_{}_samples{}.csv".format(
        platform, rq, db_name,
        sample_num if sample_num else '0,1,2')
    iterations = bootstrap if bootstrap else 1
    outputs = {}
    goal = 0.1
    for index in range(iterations):
        descriptive_stats = {}
        inferential_stats = {}
        for dataset in datasets:
            name = dataset['name']
            if calculate_frequency:
                # extracts LINK BASES from URL
                frequency_distribution(
                    dataset['qs'], extract_from, name, extractor)
            if bootstrap:
                samples = []
                if dataset.get('ordered_vals') is None:
                    dataset['ordered_vals'] = list(
                        dataset['qs'].order_by('uid').values())
                len_vals = len(dataset['ordered_vals'])
                for _ in range(len_vals):
                    rand_index = np.random.randint(0, len_vals - 1)
                    samples.append(dataset['ordered_vals'][rand_index])
                treatment_var_to_vec = defaultdict(list)
                control_var_to_vec = defaultdict(list)
                for sample in samples:
                    if treatment_kwargs is None:
                        for key, val in sample.items():
                            treatment_var_to_vec[key].append(val)
                            control_var_to_vec[key].append(val)
                    else:
                        treatment = True
                        for key, val in treatment_kwargs.items():
                            if sample[key] != val:
                                treatment = False
                                break
                        for key, val in sample.items():
                            if treatment:
                                treatment_var_to_vec[key].append(val)
                            else:
                                control_var_to_vec[key].append(val)
                treatment = {
                    'name': 'Treatment',
                    'var_to_vec': treatment_var_to_vec,
                }
                control = {
                    'name': 'Control',
                    'var_to_vec': control_var_to_vec,
                }
            else:
                qs = dataset['qs']
                # FLAG
                # quick comparison test to see if manually restricting urls to these 4 prefixes changed the results
                # it did not change the results.
                if FILTER_LANG:
                    if platform == 'r':
                        qs = qs.filter(
                            Q(has_wiki_link=False) | (
                                Q(url__icontains='en.wikipedia') | Q(url__icontains='en.m.wikipedia')  | Q(url__icontains='www.wikipedia')  | Q(url__icontains='//wikipedia')
                            )
                        )
                        qs = qs.filter(wiki_content_error=0)
                    
                    elif platform == 's':
                        qs = qs.filter(
                            Q(has_wiki_link=False) | (
                                Q(body__icontains='en.wikipedia') | Q(body__icontains='en.m.wikipedia')  | Q(body__icontains='www.wikipedia')  | Q(body__icontains='//wikipedia')
                            )
                        )
                        qs = qs.filter(wiki_content_error=0)
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

            descriptive_stats[name] = {}
            inferential_stats[name] = {}
            # Conservative page view estimates for WP vs no WP
            if rq == 13:
                treat, control = so_special('has_wiki_link', 0)
            # conservative page view estimate for good WP vs bad WP
            elif rq == 14:
                treat, control = so_special('has_c_wiki_link', 1)
            if rq == 13 or rq == 14:
                treatment = {
                    'name': 'Treatment',
                    'var_to_vec': {
                        'num_pageviews': treat   
                    }
                }
                control = {
                    'name': 'Control',
                    'var_to_vec': {
                        'num_pageviews': control   
                    }
                }
                variables = ['num_pageviews']
            groups = [treatment, control]
            
            for variable in variables:
                variable_name = variable
                treatment_var, control_var, method = None, None, None
                if isinstance(variable, tuple):
                    if callable(variable[1]):
                        variable_name, method = variable
                    else:
                        treatment_var, control_var = variable
                        variable_name = '{} vs {}'.format(
                            treatment_var, control_var)
                try:
                    for group in groups:
                        if method:
                            if group.get('var_to_vec'):
                                continue
                            else:
                                group['vals'] = method(group['qs'])
                        elif treatment_var and control_var:
                            if group['name'] == 'Treatment':
                                if group.get('var_to_vec'):
                                    group['vals'] = group['var_to_vec'][treatment_var]
                                else:
                                    group['vals'] = group['qs'].values_list(
                                        treatment_var, flat=True)
                            elif group['name'] == 'Control':
                                if group.get('var_to_vec'):
                                    group['vals'] = group['var_to_vec'][control_var]
                                else:
                                    group['vals'] = group['qs'].values_list(
                                        control_var, flat=True)
                        else:
                            if group.get('var_to_vec'):
                                group['vals'] = group['var_to_vec'][variable]
                            else:
                                group['vals'] = group['qs'].values_list(
                                    variable, flat=True)
                        group['vals'] = [
                            x for x in group['vals'] if x is not None]
                        group['vals'] = np.array(group['vals'])
                        if calculate_frequency:
                            if platform == 'r':
                                frequency_distribution(
                                    group['qs'], 'context', name + '_' + group['name'])

                    len1, len2 = len(treatment['vals']), len(control['vals'])
                    print(len1, len2)
                    if len1 == 0 or len2 == 0 and not bootstrap:
                        print('Skipping variable {} because {}, {}.'.format(
                           variable_name, len1, len2))
                        continue
                    try:
                        inferential_stats[name][variable_name] = inferential_analysis(
                            treatment['vals'], control['vals'], treatment_kwargs is None)
                        # groups = [group for group in groups if group['vals']]
                        descriptive_stats[name][variable_name] = univariate_analysis(
                            groups)
                    except (TypeError, ValueError) as err:
                        print('analysis of variable {} failed because {}'.format(
                            variable_name, err
                        ))
                except ZeroDivisionError:
                    print('Skipping variable {} bc zero division'.format(
                        variable_name
                    ))
        output = output_stats(
            None if bootstrap else output_filename, descriptive_stats, inferential_stats)
        if float(index) / iterations > goal:
            print('{}/{}|'.format(index, iterations), end='')
            goal += 0.1
        if index == 0:  # is first iteration
            outputs = output.copy()
            for subset_name, computed_vars in outputs.items():
                for computed_var, stat_categories in computed_vars.items():
                    for stat_category, subgroups in stat_categories.items():
                        for subgroup, stat_names in subgroups.items():
                            for stat_name, stat_value in stat_names.items():
                                stat_names[stat_name] = [stat_value]
        else:
            for subset_name, computed_vars in outputs.items():
                for computed_var, stat_categories in computed_vars.items():
                    if computed_var not in output[subset_name]:
                        continue
                    for stat_category, subgroups in stat_categories.items():
                        for subgroup, stat_names in subgroups.items():
                            for stat_name in stat_names.keys():
                                val = output[
                                    subset_name][computed_var][
                                        stat_category][subgroup].get(stat_name)
                                if val:
                                    stat_names[stat_name].append(val)
    if iterations > 1:
        boot_rows = [
            ['Bootstrap results for {} iterations of full resampling'.format(
                iterations), str(0.005), str(0.995)]
        ]
        for subset_name, computed_vars in outputs.items():
            for computed_var, stat_categories in computed_vars.items():
                for stat_category, subgroups in stat_categories.items():
                    if stat_category not in [
                        'Hypothesis Testing',
                    ]:
                        continue
                    for subgroup, stat_names in subgroups.items():
                        for stat_name, stat_values in stat_names.items():
                            if stat_name in [
                                "cohen's d effect size",
                                'p_value',
                            ]:
                                continue
                            n = len(stat_values)
                            sor = sorted(stat_values)
                            bot = int(0.005 * n)
                            top = int(0.995 * n)
                            desc = "{}|{}|{}|{}|{}".format(
                                subset_name, computed_var, stat_category, subgroup, stat_name
                            )
                            boot_rows.append([desc, sor[bot], sor[top]])
        with open('csv_files/' + 'BOOT_' + output_filename, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(boot_rows)


def explain():
    """explain distribution"""
    for platform in [SampledRedditThread, SampledStackOverflowPost]:
        print('==={}==='.format(platform.__name__))
        qs = platform.objects.filter(
            has_wiki_link=True, day_of_avg_score__isnull=False)
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
    parser.add_argument(
        '--bootstrap',
        type=int,default=None,
        help='use stats bootstrapping')
    parser.add_argument(
        '--sample_num',
        default=None,
        help='select a sample number')
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
                main(platform, rq, args.frequency, args.bootstrap, args.sample_num)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    from django.db import connection
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
        StackOverflowAnswer
    )
    parse()
