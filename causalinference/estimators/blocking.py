from __future__ import division
import numpy as np
from collections import defaultdict

from .base import Estimator, estimation_names, standard_err_names
from .. import causal
from ..core import Data




class Blocking(Estimator):

    """
    Dictionary-like class containing treatment effect estimates.
    """

    def __init__(self, strata, adj, feature_names, skip_features):
        # hacky
        self._method = 'Blocking'
        for i, s in enumerate(strata):
            feats = list(feature_names)
            X = s.raw_data['X']
            D = s.raw_data['D']

            if i == 0 or i == len(strata) - 1:
                ids = s.raw_data['ids']
                treat_ids = []
                control_ids = []
                for dval_index, dval in enumerate(D):
                    if dval == 1: #treat
                        treat_ids.append(ids[dval_index])
                    else:
                        control_ids.append(ids[dval_index])
                if i == 0:
                    print('Printing example ids from lowest stratum')
                if i == len(strata) - 1:
                    print('Printing example ids from highest stratum')
                print('treat_ids', treat_ids[:5])
                print('control_ids', control_ids[:5])

            for feature_name in skip_features:
                try:
                    col_num = feats.index(feature_name)
                except ValueError:
                    continue
                X = np.delete(X, col_num, 1)
                feats.remove(feature_name)

            s.raw_data = Data(s.raw_data['Y'], s.raw_data['D'], X, ids=ids)
            try:
                s.est_via_ols(adj, feats)
            except np.linalg.linalg.LinAlgError as err:
                total = X.shape[0]
                to_delete, cols_deleted = [], 0
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
                for col_num in range(X.shape[1]):
                    stdevs = (
                        s.summary_stats['X_c_sd'][col_num],
                        s.summary_stats['X_t_sd'][col_num])
                    if (stdevs[0] == 0 and stdevs[1] == 0):
                        to_delete.append(col_num)
                for col_num in to_delete:
                    print('Deleting col in stratum {} b/c sd=0: Col num: {} and col name: {}'.format(i, col_num, feats[col_num - cols_deleted]))
                    X = np.delete(X, col_num - cols_deleted, 1)
                    feats.remove(feats[col_num - cols_deleted])
                    cols_deleted += 1
                while True:
                    sums = defaultdict(int)
                    can_break = True
                    to_delete, cols_deleted = [], 0

                    for col_num in range(X.shape[1]):
                        for dummy_category, names in dummies.items():
                            if feats[col_num] in names:
                                sums[dummy_category] += np.sum(X.T[col_num])

                    for dummy_category, names in dummies.items():
                        # redundant, total is never equal to 0 anyway
                        # if sums[dummy_category] == 0:
                        #     continue
                        if sums[dummy_category] == total:
                            for col_num in range(X.shape[1]):
                                if feats[col_num] in names:
                                    can_break = False
                                    to_delete.append(col_num)
                                    break
                    for col_num in to_delete:
                        print('Deleting a column b/c redundant dummy var')
                        print('Col num was {} and col name was {}'.format(col_num, feats[col_num - cols_deleted]))
                        X = np.delete(X, col_num - cols_deleted, 1)
                        feats.remove(feats[col_num - cols_deleted])
                        cols_deleted += 1
                        print('So far, {} columns have been deleted'.format(col_num))
                    if can_break:
                        break
                
                strata[i] = causal.CausalModel(
                    s.raw_data['Y'], s.raw_data['D'], X, ids=ids)
                strata[i].est_via_ols(adj, feats)

        Ns = [s.raw_data['N'] for s in strata]
        N_cs = [s.raw_data['N_c'] for s in strata]
        N_ts = [s.raw_data['N_t'] for s in strata]

        ates = np.array([s.estimates['ols']['ate'] for s in strata]).T
        ate_ses = np.array([s.estimates['ols']['ate_se'] for s in strata]).T
        r2s = np.array([s.estimates['ols']['r2'] for s in strata]).T
        name_to_coef_mat = defaultdict(list)
        name_to_coef_lst = [s.estimates['ols']['name_to_coef'] for s in strata]
        for name_to_coef in name_to_coef_lst:
            for name, coefs in name_to_coef.items():
                name_to_coef_mat[name].append(coefs)

        ret = []
        for name, coef_mat in name_to_coef_mat.items():
            mat = np.array(coef_mat).T
            for output_num, vals in enumerate(mat):
                try:
                    row = ','.join([str(name), str(output_num), str(calc_atx(vals, N_ts))])
                    ret.append(row)
                except Exception:
                    pass

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
        for key in estimation_names() + standard_err_names() + ['r2']:
            self._dict[key] = []
        for vals in ates:
            self._dict['ate'].append(calc_atx(vals, Ns))
        for vals in atcs:
            self._dict['atc'].append(calc_atx(vals, N_cs))
        for vals in atts:
            self._dict['att'].append(calc_atx(vals, N_ts))
        
        # this seems wrong
        # however, _dict['r2'] is unused
        for vals in r2s:
            self._dict['r2'].append(vals)
        for errvals in ate_ses:
            self._dict['ate_se'].append(calc_atx_se(errvals, Ns))
        for errvals in atc_ses:
            self._dict['atc_se'].append(calc_atx_se(errvals, N_cs))
        for errvals in att_ses:
            self._dict['att_se'].append(calc_atx_se(errvals, N_ts))
        self._dict['coef_rows'] = ret


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
