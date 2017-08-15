"""
Main driver script for ML training and testing
Not for prod use

Should be run from Anaconda environment with scipy installed
(Anconda Prompt -> activate sci_basic)
"""
# pylint: disable=C0103

import os
import argparse
import time
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

def values_list_to_records(rows, names):
    """
    Converts a Django values_list to a numpy records array
    """
    return np.core.records.fromrecords(rows, names=names)


def get_qs_features_and_outcomes(platform, num_rows=None, filter_kwargs=None):
    """Get data from DB for regression and/or causal inference"""
    common_features = list_common_features()
    common_features.append('has_wiki_link')
    # textual metrics
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


def causal_inference(platform, num_rows=None):
    """
    Use causalinference module to perform causal inference analysis
    Descriptive stats, OLS, PSM
    """
    def mark_time(desc):
        """return a tuple of time, description of time"""
        return (time.time(), desc)

    times = []
    times.append(mark_time('function_start'))
    filename = '{}_{}_causal_results.txt'.format(
        platform,
        num_rows if num_rows else 'All')
    qs, features, outcomes = get_qs_features_and_outcomes(
        platform, num_rows=num_rows)
    outcomes = ['score', ]
    treatment_feature = 'has_wiki_link'
    for outcome in outcomes:
        print('==={}==='.format(outcome))
        field_names = features + [outcome]
        # rows = extract_vals_and_method_results(qs, field_names)
        rows = qs.values_list(*field_names)
        records = values_list_to_records(rows, field_names)
        times.append(mark_time('records_loaded'))
        feature_rows = []
        successful_fields = []
        for feature in features:
            feature_row = getattr(records, feature)
            if feature == treatment_feature:
                D = feature_row
            elif all(x == 0 for x in feature_row):
                print('Feature {} is all zeros - will lead to singular matrix...'.format(feature))
                print('This feature will NOT be included')
            elif any(np.isnan(feature_row)):
                print('Feature {} has a nan value...'.format(feature))
                print('This feature will NOT be included')
            else:
                successful_fields.append(feature)
                feature_rows.append(feature_row)
        times.append(mark_time('feature_rows_loaded'))
        varname_to_field = {}
        out = []
        for i, field in enumerate(successful_fields):
            varname_to_field["X{}".format(i)] = field
        for key, val in varname_to_field.items():
            out.append("{}:{}".format(key, val))
        X = np.array(feature_rows)
        X = np.transpose(X)
        Y = getattr(records, outcome)
        causal = CausalModel(Y, D, X)
        times.append(mark_time('CausalModel'))
        out.append(str(causal.summary_stats))
        causal.est_via_ols()
        times.append(mark_time('est_via_ols'))
        causal.est_propensity_s()
        times.append(mark_time('propensity'))        
        out.append(str(causal.propensity))
        causal.trim_s()
        times.append(mark_time('trim_s'))
        out.append(str(causal.summary_stats))
        causal.stratify_s()
        times.append(mark_time('stratify_s'))
        out.append(str(causal.strata))
        causal.est_via_blocking()
        times.append(mark_time('est_via_blocking'))
        causal.est_via_weighting()
        times.append(mark_time('est_via_weighting'))
        causal.est_via_matching()
        times.append(mark_time('est_via_matching'))
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
        'platform', help='the platform to use. "r" for reddit and "s" for stack overflow')
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
        '--quality',
        action='store_true',
        help='performs linear regression on quality')
    args = parser.parse_args()
    if args.simple:
        simple_linear(args.platform)
    if args.causal:
        causal_inference(args.platform, int(args.num_rows))
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
