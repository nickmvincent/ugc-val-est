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

def values_list_to_records(vals, names):
    """
    Converts a Django values_list to a numpy records array
    """
    return np.core.records.fromrecords(vals, names=names)



def train_and_test():
    """Train a linear regression model and test it!"""
    qs = SampledStackOverflowPost.objects.all().prefetch_related('post_specific_wiki_links__day_of')
    field_names = ('user_reputation', 'score', )
    vals = qs.values_list(*field_names)
    records = values_list_to_records(vals, field_names)
    print(records.dtype.names)
    X = records.user_reputation
    print(X.shape)
    X = X.reshape(-1, 1)
    print(X.shape)
    Y = records.score
    # Split the data into training/testing sets
    test_percent = 50
    test_len = int(X.shape[0] * test_percent / 100)
    print(test_len)
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
    lin_msg = "Linear | MSE: {}, Var Score: {}".format(
        np.mean((regr.predict(X_test) - y_test) ** 2),
        regr.score(X_test, y_test)
    )
    print(lin_msg)

    # Plot outputs
    # plt.scatter(X_test, y_test, color='black')
    # plt.plot(X_test, regr.predict(X_test), color='blue',
    #         linewidth=3)
    # plt.xticks(())
    # plt.yticks(())
    # plt.show()

    tree_predictor = tree.DecisionTreeRegressor()
    tree_predictor = tree_predictor.fit(X_train, y_train)
    tree_msg = "Tree | MSE: {}, VarScore: {}".format(
        np.mean((tree_predictor.predict(X_test) - y_test) ** 2),
        tree_predictor.score(X_test, y_test)
    )
    print(tree_msg)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
        PostSpecificWikiLink, WikiLink, RevisionScore
    )
    train_and_test()
