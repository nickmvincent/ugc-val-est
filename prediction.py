"""
Main driver script for ML training and testing
Not for prod use

Should be run from Anaconda environment with scipy installed
(Anconda Prompt -> activate sci_basic)
"""

# Code source: Jaques Grobler
# License: BSD 3 clause

import os
import argparse
import matplotlib.pyplot as plt
import numpy as np
from sklearn import datasets, linear_model, tree
from queryset_helpers import batch_qs

# Load the diabetes dataset

def values_list_to_records(rows, names):
    """
    Converts a Django values_list to a numpy records array
    """
    return np.core.records.fromrecords(rows, names=names)



def train_and_test(platform):
    """Train a linear regression model and test it!"""
    num_rows = 100000
    
    common_features = [
        # treatment effects
        'has_wiki_link', 'num_wiki_links',
        # contextual information
        'day_of_week', 'day_of_month', 'hour',
    ]
    if platform == 'r':
        qs = SampledRedditThread.objects.all()
        features = common_features + reddit_specific_features()
    elif platform == 's':
        qs = SampledStackOverflowPost.objects.all()
        features = common_features + stack_specific_features()
    qs = qs.order_by('uid')[:num_rows]
    
    outcomes = ['score', 'num_comments', ]
    for outcome in outcomes:
        print('==={}==='.format(outcome))
        field_names = features + [outcome]
        rows = []
        for start, end, total, batch in batch_qs(qs, batch_size=20000):
            print(start, end, total)
            for obj in batch:
                row = []
                for field_name in field_names:
                    try:
                        val = getattr(obj, field_name)()
                    except TypeError:
                        val = getattr(obj, field_name)
                    row.append(val)
                rows.append(row)
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

        # Split the targets into training/testing sets
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
    # parser.add_argument(
    #     '--visualize',
    #     action='store_true',
    #     help='Performs some data visualization')
    args = parser.parse_args()
    train_and_test(args.platform)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
        PostSpecificWikiScores, WikiLink, RevisionScore
    )
    from stats import reddit_specific_features, stack_specific_features
    parse()