"""
Main driver script for ML training and testing
Not for prod use

Should be run from Anaconda environment with scipy installed
(Anconda Prompt -> activate sci_basic)

python prediction.py --platform r --treatment has_wiki_link --causal --simple_psm --paired_psm

"""
# pylint: disable=C0103

import os
import argparse
import time
import traceback

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
    print(msg)
    out.append(msg)
    trace = traceback.format_exc()
    print(trace)
    out.append(trace)
    return out


def values_list_to_records(rows, names):
    """
    Converts a Django values_list to a numpy records array
    """
    return np.core.records.fromrecords(rows, names=names)


def get_qs_features_and_outcomes(platform, num_rows=None, filter_kwargs=None):
    """Get data from DB for regression and/or causal inference"""
    common_features = list_common_features()
    outcomes = ['score', 'num_comments', ]
    if platform == 'r':
        qs = SampledRedditThread.objects.all()
        features = common_features + list_reddit_specific_features()
    elif platform == 's':
        qs = SampledStackOverflowPost.objects.all()
        features = common_features + list_stack_specific_features()
        outcomes += ['num_pageviews', ]
    if filter_kwargs is not None:
        qs = qs.filter(**filter_kwargs)
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
        platform, treatment_feature,
        num_rows=None, simple_psm=False, simple_bin=None, trim_val=None,
        paired_psm=None):
    """
    Use causalinference module to perform causal inference analysis
    """
    def mark_time(desc):
        """return a tuple of time, description of time"""
        return (time.time(), desc)

    times = []
    times.append(mark_time('function_start'))
    
    if treatment_feature == 'has_good_wiki_link':
        filter_kwargs = {'has_wiki_link': True, 'day_of_avg_score__isnull': False}
    else:
        filter_kwargs = None
    qs, features, outcomes = get_qs_features_and_outcomes(
        platform, num_rows=num_rows, filter_kwargs=filter_kwargs)
    features.append(treatment_feature)

    filename = 'causal_treatment_{}_platform_{}_subset_{}.txt'.format(
        treatment_feature, platform,
        num_rows if num_rows else 'All')
    print('==={}==='.format(outcomes))
    field_names = features + outcomes
    rows = qs.values_list(*field_names)
    records = values_list_to_records(rows, field_names)
    times.append(mark_time('records_loaded'))

    feature_rows = []
    successful_fields = []
    for feature in features + ['uid']:
        print(feature)
        feature_row = getattr(records, feature)
        if feature == treatment_feature:
            D = feature_row
        if feature == 'uid':
            ids = feature_row
        elif all(x == 0 for x in feature_row):
            print(
                'Feature {} is all zeros - will lead to singular matrix'.format(feature))
        elif any(np.isnan(feature_row)):
            print('Feature {} has a nan value...'.format(feature))
        else:
            successful_fields.append(feature)
            feature_rows.append(feature_row)
    outcome_rows = []
    for outcome in outcomes:
        outcome_row = getattr(records, outcome)
        outcome_rows.append(outcome_row)

    times.append(mark_time('rows_loaded'))
    varname_to_field = {"X{}".format(i):field for i, field in enumerate(successful_fields)}
    outname_to_field = {"Y{}".format(i):field for i, field in enumerate(outcomes)}
    out = []
    
    for dic in [varname_to_field, outname_to_field]:
        for key, val in dic.items():
            out.append("{}:{}".format(key, val))

        
    X = np.transpose(np.array(feature_rows))
    Y = np.transpose(np.array(outcome_rows))

    causal = CausalModel(Y, D, X, ids=ids)
    times.append(mark_time('CausalModel'))
    out.append(str(causal.summary_stats))
    print(causal.summary_stats)
    causal.est_via_ols()
    times.append(mark_time('est_via_ols'))
    print(causal.estimates)
    if simple_psm:
        causal.est_propensity()
        times.append(mark_time('propensity'))
    else:
        causal.est_propensity_s()
        times.append(mark_time('propensity_s'))
    out.append(str(causal.propensity))
    print(causal.propensity)
    if trim_val:
        if trim_val == 'auto':
            causal.trim_s()
            times.append(mark_time('trim_s'))
            out.append('TRIM PERFORMED')
            out.append(str(causal.summary_stats))
        else:
            try:
                causal.cutoff = float(trim_val)
                causal.trim()
                times.append(mark_time('trim_{}'.format(trim_val)))
                out.append(str(causal.summary_stats))
            except:
                pass
    else:
        print('Skipping trim value as per request')
    if paired_psm:
        psm_est, psm_rows = causal.est_via_psm()
        print(str(psm_est))
        out.append(str(psm_est))

        with open('PSM_PAIRS' + filename, 'w') as outfile:
            outfile.write('\n'.join(psm_rows))
    else:
        if simple_bin:
            causal.blocks = int(simple_bin)
            causal.stratify()
            times.append(mark_time('stratify_{}'.format(simple_bin)))
        else:
            causal.stratify_s()
            times.append(mark_time('stratify_s'))
        out.append(str(causal.strata))
        print(causal.strata)
        try:
            causal.est_via_blocking()
            times.append(mark_time('est_via_blocking'))
        except np.linalg.linalg.LinAlgError as err:
            msg = 'LinAlgError with est_via_blocking: {}'.format(err)
            err_handle(msg, out)
    try:
        causal.est_via_matching()
        times.append(mark_time('est_via_matching'))
    except np.linalg.linalg.LinAlgError as err:
        msg = 'LinAlgError with est_via_weighting: {}'.format(err)
        err_handle(msg, out)
    out.append(str(causal.estimates))
    timing_info = {}
    prev = times[0][0]
    for cur_time, desc in times[1:]:
        timing_info[desc] = cur_time - prev
        prev = cur_time
    for key, val in timing_info.items():
        out.append("{}:{}".format(key, val))
    with open(filename, 'w') as outfile:
        outfile.write('\n'.join(out))


def simple_linear(platform, quality_mode=False):
    """Train a linear regression model and test it!"""
    if quality_mode:
        qs, features, outcomes = get_qs_features_and_outcomes(platform, filter_kwargs={
            'has_wiki_link': True,
            'wiki_content_analyzed': True,
            'wiki_content_error': 0,
            'day_of_avg_score__isnull': False,
        })
        features = ['day_of_avg_score']
    else:
        qs, features, outcomes = get_qs_features_and_outcomes(platform)
    for outcome in outcomes:
        print('==={}==='.format(outcome))
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
        for index, coeff in enumerate(regr.coef_):
            print("{}:{}, ".format(features[index], coeff), end='')
        print('')
        # The mean squared error
        y_test_hat = regr.predict(X_test)
        lin_msg = "Linear | MSE: {}, R2: {}".format(
            np.mean((y_test_hat - y_test) ** 2),
            regr.score(X_test, y_test)
        )
        print(lin_msg)


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
        '--treatment', nargs='?', default=None, help='the treatment feature to use')
    parser.add_argument(
        '--num_rows', nargs='?', default=None, help='the number of rows to use.', type=int)
    parser.add_argument(
        '--simple',
        action='store_true',
        help='performs simple linear regression will all covariates')
    parser.add_argument(
        '--causal',
        action='store_true',
        help='performs causal analysis')
    parser.add_argument(
        '--simple_psm',
        action='store_true',
        help='to use simple PSM')
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
        '--trim_val',
        action='store_true',
        help='to perform PSM trimming')
    args = parser.parse_args()
    if args.simple:
        simple_linear(args.platform)
    if args.causal:
        if args.treatment is None:
            treatments = ['has_wiki_link', 'has_good_wiki_link']
        else:
            treatments = [args.treatment]
        if args.platform is None:
            platforms = ['r', 's']
        else:
            platforms = [args.platform]
        for platform in platforms:
            for treatment in treatments:
                causal_inference(
                    platform, treatment,
                    args.num_rows, args.simple_psm,
                    args.simple_bin, args.trim_val,
                    args.paired_psm)
        else:
            causal_inference(
                args.platform, args.treatment,
                args.num_rows, args.simple_psm,
                args.simple_bin, args.trim_val,
                args.paired_psm)
    if args.quality:
        simple_linear(args.platform, True)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
    )
    parse()
