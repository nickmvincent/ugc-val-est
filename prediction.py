"""
Main driver script for ML training and testing
Not for prod use

Should be run from Anaconda environment with scipy installed
(Anconda Prompt -> activate sci_basic)
"""
# pylint: disable=C0103

import os
import argparse
import matplotlib.pyplot as plt
import numpy as np
from sklearn import linear_model, tree
from queryset_helpers import batch_qs
from causalinference import CausalModel

# Load the diabetes dataset


def values_list_to_records(rows, names):
    """
    Converts a Django values_list to a numpy records array
    """
    return np.core.records.fromrecords(rows, names=names)


def get_data(platform, num_rows=None):
    """Get data from DB for regression and/or causal inference"""
    common_features = [
        # treatment effects
        'has_wiki_link', # 'day_of_avg_score',
        # contextual information
        'day_of_week', 'day_of_month', 'hour',
        'body_length', # TODO: 'body_num_links',
    ]
    if platform == 'r':
        qs = SampledRedditThread.objects.all()
        features = common_features + reddit_specific_features()
    elif platform == 's':
        qs = SampledStackOverflowPost.objects.all()
        features = common_features + stack_specific_features()
    qs = qs.order_by('uid')
    if num_rows is not None:
        qs = qs[:num_rows]
    outcomes = ['score', 'num_comments', ]
    return qs, features, outcomes


def extract_vals_and_method_results(qs, field_names):
    """Extract either stored values or method results from a django QS"""
    rows = []
    for start, end, total, batch in batch_qs(qs, batch_size=1000):
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


def causal_inference(platform):
    qs, features, outcomes = get_data(platform, 100000)
    outcomes = ['score', ]
    treatment_feature = 'has_wiki_link'
    for outcome in outcomes:
        print('==={}==='.format(outcome))
        field_names = features + [outcome]
        # rows = extract_vals_and_method_results(qs, field_names)
        rows = qs.values_list(*field_names)
        records = values_list_to_records(rows, field_names)
        feature_rows = []
        successful_fields = []
        for feature in features:
            feature_row = getattr(records, feature)
            if feature == treatment_feature:
                D = feature_row
            elif any(np.isnan(feature_row)):
                print('possible error - there is a None in feature {}'.format(feature))
                print('This feature will NOT be included')
            else:
                successful_fields.append(feature)
                feature_rows.append(feature_row)
        print(successful_fields)
        X = np.array(feature_rows)
        X = np.transpose(X)
        Y = getattr(records, outcome)
        causal = CausalModel(Y, D, X)
        print(causal.summary_stats)
        causal.est_via_ols()
        print(causal.estimates)
        causal.est_propensity_s()
        print(causal.propensity)
        causal.trim_s()
        print(causal.summary_stats)
        causal.stratify_s()
        print(causal.strata)
        causal.est_via_blocking()
        print(causal.estimates)
        causal.est_via_weighting()
        print(causal.estimates)
        causal.est_via_matching()
        print(causal.estimates)
        


def simple_linear(platform):
    """Train a linear regression model and test it!"""
    qs, features, outcomes = get_data(platform)
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
        test_percent = 30
        test_len = int(X.shape[0] * test_percent / 100)
        X_train = X[:-test_len]
        X_test = X[-test_len:]

        y_train = Y[:-test_len]
        y_test = Y[-test_len:]

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
    plt.show()


def parse():
    """
    Parse args and do the appropriate analysis
    """
    parser = argparse.ArgumentParser(
        description='Train predictive model')
    parser.add_argument(
        'platform', help='the platform to use. "r" for reddit and "s" for stack overflow')
    parser.add_argument(
        '--causal',
        action='store_true',
        help='Use causal inference?')
    args = parser.parse_args()
    if args.causal:
        causal_inference(args.platform)
    else:
        simple_linear(args.platform)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
    )
    from stats import reddit_specific_features, stack_specific_features
    parse()
