"""
Main driver script for ML training and testing
Not for prod use

Should be run from Anaconda environment with scipy installed
(Anconda Prompt -> activate sci_basic)
"""

# Code source: Jaques Grobler
# License: BSD 3 clause

import os
import matplotlib.pyplot as plt
import numpy as np
from sklearn import datasets, linear_model, tree

# Load the diabetes dataset

def values_list_to_records(rows, names):
    """
    Converts a Django values_list to a numpy records array
    """
    return np.core.records.fromrecords(rows, names=names)



def train_and_test():
    """Train a linear regression model and test it!"""
    num_rows = 100000
    qs = SampledRedditThread.objects.filter(has_wiki_link=True, day_of_avg_score__isnull=False)
    qs = qs.order_by('uid')
    # features = ['has_wiki_link', 'day', 'day_of_week', 'title_length', ]
    features = ['day_of_avg_score', ]
    outcome = ['score']
    field_names = features + outcome

    rows = []
    for obj in qs:
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
    print(X)
    Y = records.score
    # Split the data into training/testing sets
    test_percent = 50
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
    print('Coefficients: \n', regr.coef_)
    # The mean squared error
    y_test_hat = regr.predict(X_test)
    lin_msg = "Linear | MSE: {}, R2: {}".format(
        np.mean((y_test_hat - y_test) ** 2),
        regr.score(X_test, y_test)
    )
    print(lin_msg)

    # Plot outputs
    col = X_test[:, 0]
    col = X_test
    plt.scatter(col, y_test, color='black')
    plt.plot(col, y_test_hat, color='blue',
            linewidth=3)
    plt.xticks(())
    plt.yticks(())

    tree_predictor = tree.DecisionTreeRegressor()
    tree_predictor = tree_predictor.fit(X_train, y_train)
    tree_msg = "Tree | MSE: {}, R2: {}".format(
        np.mean((tree_predictor.predict(X_test) - y_test) ** 2),
        tree_predictor.score(X_test, y_test)
    )
    print(tree_msg)
    plt.show()
    

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
        PostSpecificWikiScores, WikiLink, RevisionScore
    )
    train_and_test()
