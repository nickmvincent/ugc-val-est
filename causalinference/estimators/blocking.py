from __future__ import division
import numpy as np
from collections import defaultdict

from .base import Estimator, estimation_names, standard_err_names
from .. import causal




class Blocking(Estimator):

    """
    Dictionary-like class containing treatment effect estimates.
    """

    def __init__(self, strata, adj, feature_names):

        self._method = 'Blocking'

        for i, s in enumerate(strata):
            try:
                s.est_via_ols(adj)
            except np.linalg.linalg.LinAlgError as err:
                print('Error in strata {}'.format(i))
                X = s.raw_data['X']
                to_delete = []
                dummies = {
                    'months':	[
                        'jan', 'feb', 'mar', 'apr',
                        'may', 'jun', 'jul', 'aug', 'sep',
                        'octo', 'nov',
                    ],
                    'hours': ['zero_to_six', 'six_to_twelve', 'twelve_to_eighteen', ],
                    'contexts': ['in_todayilearned',
                                'in_borntoday', 'in_wikipedia', 'in_CelebrityBornToday', 'in_The_Donald', ],
                    'years': ['year2008', 'year2009', 'year2010',
                            'year2011', 'year2012', 'year2013',
                            'year2014', 'year2015', ],
                    'days:': [
                        'mon', 'tues', 'wed', 'thurs',
                        'fri', 'sat',
                    ],
                }
                for col_num, ndiff_val in enumerate(s.summary_stats['ndiff']):
                    means = (
                        s.summary_stats['X_c_mean'][col_num],
                        s.summary_stats['X_t_mean'][col_num])
                    stdevs = (
                        s.summary_stats['X_c_sd'][col_num],
                        s.summary_stats['X_t_sd'][col_num])
                    if (means[0] == 0 and stdevs[0] == 0 or
                            means[1] == 0 and stdevs[1] == 0):
                        print(
                            'ALL ZEROS - need to remove column number {}'.format(col_num))
                        to_delete.append(col_num)
                        # make sure to remove the corresponding column from the dummies object
                        for dummy, names in dummies.items():
                            if feature_names[col_num] in names:
                                names.remove(feature_names[col_num])
                cols_deleted = 0
                for col_num in to_delete:
                    X = np.delete(X, col_num - cols_deleted, 1)
                    cols_deleted += 1
                
                while True:
                    sums = defaultdict(int)
                    total = X.shape[0]

                    for col_num in range(X.shape[1]):
                        for dummy_category, names in dummies.items():
                            if feature_names[col_num] in names:
                                col = X.T[col_num]
                                sums[dummy_category] += np.sum(col)
                    can_break = True
                    to_delete = []

                    for dummy_category, names in dummies.items():
                        if sums[dummy_category] == 0:
                            continue
                        if sums[dummy_category] == total:
                            print('Found a dependent dummy var')
                            for col_num in range(len(X.T)):
                                if feature_names[col_num] in names:
                                    print('it was {}'.format(feature_names[col_num]))                                
                                    print('so it will be deleted')
                                    can_break = False
                                    to_delete.append(col_num)
                                    names.remove(feature_names[col_num])
                                    break
                    for col_num in to_delete:
                        X = np.delete(X, col_num - cols_deleted, 1)
                        cols_deleted += 1
                    if can_break:
                        break
                
                strata[i] = causal.CausalModel(
                    s.raw_data['Y'], s.raw_data['D'], X)
                strata[i].est_via_ols(adj)

        Ns = [s.raw_data['N'] for s in strata]
        N_cs = [s.raw_data['N_c'] for s in strata]
        N_ts = [s.raw_data['N_t'] for s in strata]


        ates = np.array([s.estimates['ols']['ate'] for s in strata]).T
        ate_ses = np.array([s.estimates['ols']['ate_se'] for s in strata]).T
        if adj <= 1:
            atcs, atts = ates, ates
            atc_ses, att_ses = ate_ses, ate_ses
        else:
            atcs = np.array([s.estimates['ols']['atc'] for s in strata]).T
            atts = np.array([s.estimates['ols']['att'] for s in strata]).T
            atc_ses = np.array([s.estimates['ols']['atc_se']
                                for s in strata]).T
            att_ses = np.array([s.estimates['ols']['att_se']
                                for s in strata]).T

        self._dict = dict()
        for key in estimation_names() + standard_err_names():
            self._dict[key] = []
        for vals in ates:
            self._dict['ate'].append(calc_atx(vals, Ns))
        for vals in atcs:
            self._dict['atc'].append(calc_atx(vals, N_cs))
        for vals in atts:
            self._dict['att'].append(calc_atx(vals, N_ts))
        for errvals in ate_ses:
            self._dict['ate_se'].append(calc_atx_se(errvals, Ns))
        for errvals in atc_ses:
            self._dict['atc_se'].append(calc_atx_se(errvals, N_cs))
        for errvals in att_ses:
            self._dict['att_se'].append(calc_atx_se(errvals, N_ts))


def calc_atx(atxs, Ns):
    """Calculate average treatment effect for a given set of
    treatment effects computed for a set of strat.
    Uses Ns to weight.
    """

    N = sum(Ns)

    return np.sum(np.array(atxs) * np.array(Ns)) / N


def calc_atx_se(atx_ses, Ns):

    N = sum(Ns)
    var = np.sum(np.array(atx_ses)**2 * np.array(Ns)**2) / N**2

    return np.sqrt(var)
