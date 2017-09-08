"""
Main driver script for ML training and testing
Not for prod use

Should be run from Anaconda environment with scipy installed
(Anconda Prompt -> activate sci_basic)

python prediction.py --platform r --treatment has_wiki_link --paired_psm

"""
# pylint: disable=C0103

import os
import argparse
import time
import traceback
import csv
from collections import defaultdict

# ==== END NATIVE IMPORTS
# ==== START LOCAL IMPORTS
from queryset_helpers import (
    batch_qs, list_common_features,
    list_reddit_specific_features, list_stack_specific_features
)
import matplotlib
matplotlib.use('Agg')
# pylint:disable=C0413
import matplotlib.pyplot as plt
import numpy as np
from sklearn import linear_model
from causalinference import CausalModel


def err_handle(msg, out):
    """error handling for this exploratory code"""
    trace = traceback.format_exc()
    print('*** ERR OCCURRED', msg, trace)
    out.append(msg)
    out.append(trace)
    return out


def values_list_to_records(rows, names):
    """
    Converts a Django values_list to a numpy records array
    """
    return np.core.records.fromrecords(rows, names=names)


def get_qs_features_and_outcomes(platform, num_rows=None, filter_kwargs=None, exclude_kwargs=None):
    """Get data from DB for regression and/or causal inference"""
    common_features = list_common_features()
    outcomes = ['score', 'num_comments', ]
    if platform == 'r':
        qs = SampledRedditThread.objects.all()
        features = common_features + list_reddit_specific_features()
    elif platform == 's':
        qs = SampledStackOverflowPost.objects.all()
        features = common_features + list_stack_specific_features()
    if filter_kwargs is not None:
        qs = qs.filter(**filter_kwargs)
    if exclude_kwargs is not None:
        qs = qs.exclude(**exclude_kwargs)
    if num_rows is not None:
        qs = qs.order_by('?')
        qs = qs[:num_rows]
    else:
        qs = qs.order_by('uid')
    return qs, features, outcomes


def extract_vals_and_method_results(qs, field_names):
    """Extract either stored values or method results from a django QS"""
    rows = []
    for _, _, _, batch in batch_qs(qs, batch_size=1000):
        for obj in batch:
            row = []
            for field_name in field_names:
                try:
                    val = getattr(obj, field_name)()
                except TypeError:
                    val = getattr(obj, field_name)
                row.append(val)
            rows.append(row)
    return rows


def causal_inference(
        platform, treatment_name,
        filename_prefix,
        filter_kwargs, exclude_kwargs,
        num_rows=None, quad_psm=False, simple_bin=None, trim_val=0,
        paired_psm=None, iterations=1, sample_num=None):
    """
    Use causalinference module to perform causal inference analysis
    """
    def mark_time(desc):
        """return a tuple of time, description of time"""
        return (time.time(), desc)
    start = time.time()
    summary = {}
    treatment_effects = defaultdict(list)
    goal = 0
    fails = 0
    for iteration in range(iterations):
        if float(iteration) / iterations >= goal:
            print('{}/{}|'.format(iteration, iterations), end='')
            goal += 0.1
        out = []
        times, atts = [], []
        ndifs, big_ndifs_counts = [], []
        times.append(mark_time('function_start'))
        qs, features, outcomes = get_qs_features_and_outcomes(
            platform, num_rows=num_rows, filter_kwargs=filter_kwargs, exclude_kwargs=exclude_kwargs)
        if 'is_top' in filter_kwargs:
            outcomes = ['num_pageviews']
        features.append(treatment_name)
        features.append('uid')
        db_name = connection.settings_dict['NAME']
        filename = '{pre}_Tr_{treatment}_on_{platform}_{subset}_{db}_trim{trim_val}_samples{samples}.txt'.format(**{
            'pre': filename_prefix,
            'treatment': treatment_name,
            'platform': platform,
            'subset': num_rows if num_rows else 'All',
            'db': db_name,
            'trim_val': trim_val,
            'samples': sample_num if sample_num else 0
        })
        field_names = features + outcomes
        rows = qs.values_list(*field_names)

        if iterations > 1:
            samples = []
            for _ in rows:
                rand_index = np.random.randint(0, len(rows) - 1)
                samples.append(rows[rand_index])
            records = values_list_to_records(samples, field_names)
        else:
            records = values_list_to_records(rows, field_names)
        times.append(mark_time('records_loaded'))

        feature_rows = []
        successful_fields = []
        for feature in features:
            feature_row = getattr(records, feature)
            if feature == treatment_name:
                D = feature_row
                continue
            elif feature == 'uid':
                ids = feature_row
                continue
            try:
                has_any_nans = any(np.isnan(feature_row))
            except Exception:
                continue
            if not np.any(feature_row):
                continue
            elif has_any_nans:
                continue
            else:
                if max(feature_row) > 1 or min(feature_row) < 0:
                    if feature in [
                        'user_link_karma',
                        'seconds_since_user_creation',
                        'user_comment_karma',
                        'user_reputation',
                    ]:
                        minval = min(feature_row)
                        if minval <= 0:
                            shifted = np.add(-1 * minval + 1, feature_row)
                        else:
                            shifted = feature_row
                        adjusted_feature = np.log(shifted)
                    else:
                        adjusted_feature = feature_row
                    adjusted_feature = (
                        adjusted_feature - np.mean(adjusted_feature)) / np.std(adjusted_feature)
                    feature_rows.append(adjusted_feature)
                else:
                    feature_rows.append(feature_row)
                successful_fields.append(feature)
        outcome_rows = []
        for outcome in outcomes:
            outcome_row = getattr(records, outcome)
            outcome_rows.append(outcome_row)

        times.append(mark_time('rows_loaded'))
        exclude_from_ps = [
        ]
        skip_fields = [
            'user_is_deleted', 'user_is_mod', 'user_is_suspended',
            'title_includes_question_mark',
        ]

        X = np.transpose(np.array(feature_rows))
        X_c = X[D == 0]
        X_t = X[D == 1]
        to_delete, cols_deleted = [], 0
        for col_num, col in enumerate(X_c.T):
            if not np.any(col):
                to_delete.append(col_num)
        for col_num, col in enumerate(X_t.T):
            if not np.any(col):
                to_delete.append(col_num)
        for col_num in to_delete:
            X = np.delete(X, col_num - cols_deleted, 1)
            successful_fields.remove(successful_fields[col_num - cols_deleted])
            cols_deleted += 1

        dummies = {
            'months':	[
                'jan', 'feb', 'mar', 'apr',
                'may', 'jun', 'jul', 'aug', 'sep',
                'octo', 'nov',
            ],
            'hours': ['zero_to_six', 'six_to_twelve', 'twelve_to_eighteen', ],
            'contexts': ['in_todayilearned',
                         'in_borntoday', 'in_wikipedia', 'in_CelebrityBornToday',
                         'in_The_Donald', ],
            'years': ['year2008', 'year2009', 'year2010',
                      'year2011', 'year2012', 'year2013',
                      'year2014', 'year2015', ],
            'days:': [
                'mon', 'tues', 'wed', 'thurs',
                'fri', 'sat',
            ],
        }
        while True:
            can_break = True
            sums = defaultdict(int)
            total = X.shape[0]
            to_delete, cols_deleted = [], 0

            for col_num in range(X.shape[1]):
                for dummy_category, names in dummies.items():
                    if successful_fields[col_num] in names:
                        col = X.T[col_num]
                        sums[dummy_category] += np.sum(col)

            for dummy_category, names in dummies.items():
                if sums[dummy_category] == 0:
                    continue
                if sums[dummy_category] == total:
                    for col_num in range(X.shape[1]):
                        if successful_fields[col_num] in names:
                            can_break = False
                            to_delete.append(col_num)
                            names.remove(successful_fields[col_num])
                            break
            for col_num in to_delete:
                X = np.delete(X, col_num - cols_deleted, 1)
                successful_fields.remove(
                    successful_fields[col_num - cols_deleted])
                cols_deleted += 1
            if can_break:
                break
        Y = np.transpose(np.array(outcome_rows))
        causal = CausalModel(Y, D, X, ids=ids)
        times.append(mark_time('CausalModel'))
        out.append(str(causal.summary_stats))
        ndifs.append(causal.summary_stats['sum_of_abs_ndiffs'])
        big_ndifs_counts.append(causal.summary_stats['num_large_ndiffs'])
        # causal.est_via_ols()
        # times.append(mark_time('est_via_ols'))
        if not quad_psm:
            causal.est_propensity(successful_fields, exclude_from_ps)
            times.append(mark_time('propensity'))
        else:
            causal.est_propensity_s()
            times.append(mark_time('propensity_s'))
        varname_to_field = {
            "X{}".format(i): field for i, field in enumerate(
                successful_fields) if field not in exclude_from_ps
        }
        outname_to_field = {"Y{}".format(
            i): field for i, field in enumerate(outcomes)}
        for dic in [varname_to_field, outname_to_field]:
            for key, val in dic.items():
                out.append("{}:{}".format(key, val))
        out.append(str(causal.propensity))
        if trim_val == 's':
            causal.trim_s()
        elif trim_val is None:
            causal.trim(True)
        else:
            causal.cutoff = float(trim_val)
            causal.trim()
        times.append(mark_time('trim_{}'.format(causal.cutoff)))
        out.append('TRIM PERFORMED: {}'.format(causal.cutoff))
        out.append(str(causal.summary_stats))
        ndifs.append(causal.summary_stats['sum_of_abs_ndiffs'])
        big_ndifs_counts.append(causal.summary_stats['num_large_ndiffs'])

        if paired_psm:
            psm_est, psm_summary, psm_rows = causal.est_via_psm()
            out.append('PSM PAIR REGRESSION')
            out.append(str(psm_summary))
            out.append(str(psm_est))
            diff_avg = 0
            for row in psm_rows:
                diff_avg += abs(row[1] - row[3])
            diff_avg /= len(psm_rows)
            out.append('Pscore diff average: {}'.format(diff_avg))

            with open('PSM_PAIRS' + filename, 'w') as outfile:
                for psm_row in psm_rows:
                    psm_row = [str(entry) for entry in psm_row]
                    outfile.write(','.join(psm_row))
            atts = psm_est['ols']['att']
        else:
            if simple_bin:
                causal.blocks = int(simple_bin)
                causal.stratify()
                times.append(mark_time('stratify_{}'.format(simple_bin)))
            else:
                try:
                    causal.stratify_s()
                except ValueError as err:
                    fails += 1
                    continue
                times.append(mark_time('stratify_s'))
            out.append(str(causal.strata))
            try:
                causal.est_via_blocking(successful_fields, skip_fields)
                out += causal.estimates['blocking']['coef_rows']
                summary['blocking'] = [[filename]]
                summary['blocking'] += causal.estimates['blocking'].as_rows()
                times.append(mark_time('est_via_blocking'))
                atts = causal.estimates['blocking']['att']
                w_avg_ndiff = 0
                w_num_large_ndiffs = 0
                for stratum in causal.strata:
                    val = stratum.summary_stats['sum_of_abs_ndiffs']
                    count = stratum.raw_data['N']
                    fraction = count / causal.raw_data['N']
                    w_avg_ndiff += fraction * val
                    w_num_large_ndiffs += fraction * \
                        stratum.summary_stats['num_large_ndiffs']
                out.append(
                    'WEIGHTED AVERAGE OF SUM OF ABSOLUTE VALUE OF ALL NDIFs')
                ndifs.append(w_avg_ndiff)
                big_ndifs_counts.append(w_num_large_ndiffs)
                out.append(','.join([str(ndif) for ndif in ndifs]))
                out.append('# of BIG NDIFS')
                out.append(','.join([str(count)
                                     for count in big_ndifs_counts]))

                varname_to_field = {
                    "X{}".format(i): field for i, field in enumerate(
                        successful_fields) if field not in skip_fields
                }
                out.append('VARS USED IN BLOCK REGRESSIONS')
                for dic in [varname_to_field]:
                    for key, val in dic.items():
                        out.append("{}:{}".format(key, val))
            except np.linalg.linalg.LinAlgError as err:
                msg = 'LinAlgError with est_via_blocking: {}'.format(err)
                err_handle(msg, out)
        out.append(str(causal.estimates))
        timing_info = {}
        prev = times[0][0]
        for cur_time, desc in times[1:]:
            timing_info[desc] = cur_time - prev
            prev = cur_time
        for key, val in timing_info.items():
            out.append("{}:{}".format(key, val))
        if iterations == 1:
            with open(filename, 'w') as outfile:
                outfile.write('\n'.join(out))
        else:
            for att_num, att in enumerate(atts):
                treatment_effects[outcomes[att_num]].append(att)
    if iterations > 1:
        boot_rows = [
            ['Bootstrap results for {} iterations of full resampling'.format(
                iterations), str(0.005), str(0.995)]
        ]
        for outcome, att_lst in treatment_effects.items():
            sor = sorted(att_lst)
            n = len(att_lst)
            bot = int(0.005 * n)
            top = int(0.995 * n)
            boot_rows.append([
                outcome, sor[bot], sor[top]
            ])
        boot_rows.append([time.time() - start])
        with open('csv_files/' + 'BOOT_' + filename, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(boot_rows)
        summary = causal_inference(
            platform, filename_prefix,
            treatment_name,
            filter_kwargs, exclude_kwargs,
            num_rows, quad_psm, simple_bin, trim_val,
            paired_psm, iterations=1, sample_num=sample_num)
    return summary


def simple_linear(platform, quality_mode=False):
    """Train a linear regression model and test it!"""
    if quality_mode:
        qs, features, outcomes = get_qs_features_and_outcomes(platform, filter_kwargs={
            'has_wiki_link': True,
            'wiki_content_error': 0,
            'day_of_avg_score__isnull': False,
        })
        features = ['day_of_avg_score']
    else:
        qs, features, outcomes = get_qs_features_and_outcomes(platform)
    for outcome in outcomes:
        field_names = features + [outcome]
        rows = extract_vals_and_method_results(qs, field_names)
        records = values_list_to_records(rows, field_names)
        arr = []
        for feature in features:
            arr.append(getattr(records, feature))
        X = np.array(arr)
        X = np.transpose(X)
        Y = getattr(records, outcome)
        # Split the data into training/testing sets
        test_percent = 10
        test_len = int(X.shape[0] * test_percent / 100)
        X_train = X[:-test_len]
        X_test = X[-test_len:]

        y_train = Y[:-test_len]
        y_test = Y[-test_len:]

        if quality_mode and outcome == 'num_pageviews':
            fig = plt.figure()
            axis = fig.add_subplot(111)
            axis.plot(X_train, y_train)
            axis.set_title('Simple Linear Regression')
            axis.set_xlabel('Quality')
            axis.set_ylabel('Pageviews')
            fig.savefig('output_vs_quality.png')

        # Create linear regression object
        regr = linear_model.LinearRegression()

        # Train the model using the training sets
        regr.fit(X_train, y_train)

        # The coefficients
        # The mean squared error
        y_test_hat = regr.predict(X_test)


def parse():
    """
    Parse args and do the appropriate analysis
    """
    parser = argparse.ArgumentParser(
        description='Train predictive model')
    parser.add_argument(
        '--platform', nargs='?', default=None,
        help='the platform to use. "r" for reddit and "s" for stack overflow')
    parser.add_argument(
        '--rq', nargs='?', default=None, help='the rq to answer')
    parser.add_argument(
        '--num_rows', nargs='?', default=None, help='the number of rows to use.', type=int)
    parser.add_argument(
        '--simple',
        action='store_true',
        help='performs simple linear regression will all covariates')
    parser.add_argument(
        '--quad_psm',
        action='store_true',
        help='to use quad PSM')
    parser.add_argument(
        '--simple_bin', nargs='?', default=None,
        help='add this argument if you want to just simple manual binning (i.e. 2 bins)')
    parser.add_argument(
        '--quality',
        action='store_true',
        help='performs linear regression on quality')
    parser.add_argument(
        '--paired_psm',
        action='store_true',
        help='to do paired psm?')
    parser.add_argument(
        '--trim_val', default=None,
        help='to perform PSM trimming')
    parser.add_argument(
        '--bootstrap',
        type=int, nargs='?', default=None,
        help='use stats bootstrapping')
    parser.add_argument(
        '--sample_num',
        nargs='?', default=None,
        help='select a sample number')
    args = parser.parse_args()
    if args.simple:
        simple_linear(args.platform)
    else:
        if args.rq is None:
            rqs = ['1', '2']
        else:
            rqs = [args.rq]
        if args.bootstrap is None:
            iterations = 1
        else:
            iterations = args.bootstrap
        if args.trim_val is None:
            trim_vals = ['0']
        elif args.trim_val == 'pair':
            trim_vals = [None]
        else:
            trim_vals = args.trim_val.split(',')

        if args.platform is None:
            platforms = ['r', 's', ]
        else:
            platforms = [args.platform]
        for platform in platforms:
            for rq in rqs:
                if rq == '1':
                    treatments = [
                        {
                            'name': 'has_other_link',
                            'filter_kwargs': {},
                            'exclude_kwargs': {'has_wiki_link': True}
                        }, {
                            'name': 'has_wiki_link',
                            'filter_kwargs': {},
                            'exclude_kwargs': {'has_other_link': True}
                        },
                    ]
                elif rq == '1-is_top':
                    treatments = [
                        {
                            'name': 'has_other_link',
                            'filter_kwargs': {'is_top': True},
                            'exclude_kwargs': {'has_wiki_link': True}
                        }, {
                            'name': 'has_wiki_link',
                            'filter_kwargs': {'is_top': True},
                            'exclude_kwargs': {'has_other_link': True}
                        },
                    ]
                elif rq == 'til':
                    treatments = [
                        {
                            'name': 'has_other_link',
                            'filter_kwargs': {'is_top': True},
                            'exclude_kwargs': {'has_wiki_link': True}
                        }, {
                            'name': 'has_wiki_link',
                            'filter_kwargs': {'is_top': True},
                            'exclude_kwargs': {'has_other_link': True}
                        },
                    ]
                elif rq == '2':
                    treatments = [
                        {
                            'pre': 'CI_c_',
                            'name': 'has_wiki_link',
                            'filter_kwargs': {'has_other_link': False},
                            'exclude_kwargs': {'has_wiki_link': True, 'has_c_wiki_link': False},
                        },
                        {
                            'pre': 'CI_bad_',
                            'name': 'has_wiki_link',
                            'filter_kwargs': {'has_other_link': False},
                            'exclude_kwargs': {'has_wiki_link': True, 'has_c_wiki_link': True},
                        },
                    ]
                elif rq == '2-is_top':
                    treatments = [
                        {
                            'pre': 'CI_c_',
                            'name': 'has_wiki_link',
                            'filter_kwargs': {'has_other_link': False, 'is_top': True},
                            'exclude_kwargs': {'has_wiki_link': True, 'has_c_wiki_link': False},
                        },
                        {
                            'pre': 'CI_bad_',
                            'name': 'has_wiki_link',
                            'filter_kwargs': {'has_other_link': False, 'is_top': True},
                            'exclude_kwargs': {'has_wiki_link': True, 'has_c_wiki_link': True},
                        },
                    ]

                summaries = []
                for trim_val in trim_vals:
                    for treatment in treatments:
                        filter_kwargs = treatment['filter_kwargs']
                        exclude_kwargs = treatment['exclude_kwargs']
                        if args.sample_num is None:
                            filter_kwargs['sample_num'] = 0
                        else:
                            filter_kwargs['sample_num__in'] = args.sample_num.split(
                                ',')
                        summary = causal_inference(
                            platform, treatment['name'],
                            treatment.get('pre', 'CI'),
                            filter_kwargs, exclude_kwargs,
                            args.num_rows, args.quad_psm,
                            args.simple_bin, trim_val,
                            args.paired_psm, iterations, args.sample_num)
                        summaries.append(summary)
                    # trim_rows.append(results['trim'])
                with open('SUMMARY_' + platform + '.csv', 'w', newline='') as outfile:
                    writer = csv.writer(outfile)
                    for summary in summaries:
                        for key in summary:
                            writer.writerow([key])
                            writer.writerows(summary[key])

    if args.quality:
        simple_linear(args.platform, True)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from django.db import connection
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
    )
    parse()
