from __future__ import division
import time
import numpy as np
from itertools import chain
from functools import reduce

from .base import Estimator, estimation_names, standard_err_names
from .. import causal

class Matching(Estimator):

	"""
	Dictionary-like class containing treatment effect estimates. Standard
	errors are only computed when needed.
	"""

	def __init__(self, data, W, m, bias_adj):

		self._method = 'Matching'
		N, N_c, N_t = data['N'], data['N_c'], data['N_t']
		Y_c, Y_t = data['Y_c'], data['Y_t']
		X_c, X_t = data['X_c'], data['X_t']

		self._dict = dict()
		for name in estimation_names() + standard_err_names():
			self._dict[name] = []

		for y_c, y_t in zip(Y_c.T, Y_t.T):
			# get a matching treatment example for EACH control example
			matches_c = [match(X_i, X_t, W, m) for X_i in X_c]
			# get a matching control example for EAHC treatment example
			matches_t = [match(X_i, X_c, W, m) for X_i in X_t]


			# construct a dataset from all the matches so we can look at covariate balance, etc
			# print(
			# 	np.concatenate([y_t, [y_c[idx[0]] for idx in matches_t]]), '\n',
			# 	np.concatenate([X_t, [X_c[idx[0]] for idx in matches_t]]), '\n',
			# 	np.concatenate([[1 for _ in X_t], [0 for _ in matches_t]]), '\n',
			# )
			att_data = causal.CausalModel(
				np.concatenate([y_t, [y_c[idx[0]] for idx in matches_t]]),
				np.concatenate([[1 for _ in X_t], [0 for _ in matches_t]]),
				np.concatenate([X_t, [X_c[idx[0]] for idx in matches_t]]),
			)

			atc_data = causal.CausalModel(
				np.concatenate([y_c, [y_t[idx[0]] for idx in matches_c]]),
				np.concatenate([[0 for _ in X_c], [1 for _ in matches_c]]),
				np.concatenate([X_c, [X_t[idx[0]] for idx in matches_c]]),
			)
			self._dict['att_unique_examples'] = len(set([idx[0] for idx in matches_c])) + len(X_t)
			self._dict['atc_unique_examples'] = len(set([idx[0] for idx in matches_t])) + len(X_c)
			self._dict['att_data'] = att_data
			self._dict['atc_data'] = atc_data
			
			yhat_c = np.array([y_t[idx].mean() for idx in matches_c])
			yhat_t = np.array([y_c[idx].mean() for idx in matches_t])
			ITT_c = yhat_c - y_c
			ITT_t = y_t - yhat_t

			if bias_adj:
				bias_coefs_c = bias_coefs(matches_c, y_t, X_t)
				bias_coefs_t = bias_coefs(matches_t, y_c, X_c)
				bias_c = bias(X_c, X_t, matches_c, bias_coefs_c)
				bias_t = bias(X_t, X_c, matches_t, bias_coefs_t)
				ITT_c = ITT_c - bias_c
				ITT_t = ITT_t + bias_t

			atc = ITT_c.mean()
			att = ITT_t.mean()
			ate = (N_c/N)*atc + (N_t/N)*att
			self._dict['atc'].append(atc)
			self._dict['att'].append(att)
			self._dict['ate'].append(ate)

			scaled_counts_c = scaled_counts(N_c, matches_t)
			scaled_counts_t = scaled_counts(N_t, matches_c)
			vars_c = np.repeat(ITT_c.var(), N_c)  # conservative
			vars_t = np.repeat(ITT_t.var(), N_t)  # conservative
			self._dict['atc_se'].append(calc_atc_se(vars_c, vars_t, scaled_counts_t))
			self._dict['att_se'].append(calc_att_se(vars_c, vars_t, scaled_counts_c))
			self._dict['ate_se'].append(
				calc_ate_se(vars_c, vars_t, scaled_counts_c, scaled_counts_t)
			)


def norm(X_i, X_m, W):

	dX = X_m - X_i
	if W.ndim == 1:
		return (dX**2 * W).sum(1)
	else:
		return (dX.dot(W)*dX).sum(1)


def smallestm(d, m):

	# Finds indices of the smallest m numbers in an array. Tied values are
	# included as well, so number of returned indices can be greater than m.

	# partition around (m+1)th order stat
	par_idx = np.argpartition(d, m)

	if d[par_idx[:m]].max() < d[par_idx[m]]:  # m < (m+1)th
		return par_idx[:m]
	elif d[par_idx[m]] < d[par_idx[m+1:]].min():  # m+1 < (m+2)th
		return par_idx[:m+1]
	else:  # mth = (m+1)th = (m+2)th, so increment and recurse
		return smallestm(d, m+2)


def match(X_i, X_m, W, m):
	d = norm(X_i, X_m, W)
	return smallestm(d, m)


def bias_coefs(matches, Y_m, X_m):

	# Computes OLS coefficient in bias correction regression. Constructs
	# data for regression by including (possibly multiple times) every
	# observation that has appeared in the matched sample.

	flat_idx = reduce(lambda x,y: np.concatenate((x,y)), matches)
	N, K = len(flat_idx), X_m.shape[1]

	Y = Y_m[flat_idx]
	X = np.empty((N, K+1))
	X[:, 0] = 1  # intercept term
	X[:, 1:] = X_m[flat_idx]

	return np.linalg.lstsq(X, Y)[0][1:]  # don't need intercept coef


def bias(X, X_m, matches, coefs):

	# Computes bias correction term, which is approximated by the dot
	# product of the matching discrepancy (i.e., X-X_matched) and the
	# coefficients from the bias correction regression.

	X_m_mean = [X_m[idx].mean(0) for idx in matches]
	bias_list = [(X_j-X_i).dot(coefs) for X_i,X_j in zip(X, X_m_mean)]

	return np.array(bias_list)


def scaled_counts(N, matches):

	# Counts the number of times each subject has appeared as a match. In
	# the case of multiple matches, each subject only gets partial credit.

	s_counts = np.zeros(N)

	for matches_i in matches:
		scale = 1 / len(matches_i)
		for match in matches_i:
			s_counts[match] += scale

	return s_counts


def calc_atx_var(vars_c, vars_t, weights_c, weights_t):

	N_c, N_t = len(vars_c), len(vars_t)
	summands_c = weights_c**2 * vars_c
	summands_t = weights_t**2 * vars_t

	return summands_t.sum()/N_t**2 + summands_c.sum()/N_c**2
	

def calc_atc_se(vars_c, vars_t, scaled_counts_t):

	N_c, N_t = len(vars_c), len(vars_t)
	weights_c = np.ones(N_c)
	weights_t = (N_t/N_c) * scaled_counts_t

	var = calc_atx_var(vars_c, vars_t, weights_c, weights_t)

	return np.sqrt(var)


def calc_att_se(vars_c, vars_t, scaled_counts_c):

	N_c, N_t = len(vars_c), len(vars_t)
	weights_c = (N_c/N_t) * scaled_counts_c
	weights_t = np.ones(N_t)

	var = calc_atx_var(vars_c, vars_t, weights_c, weights_t)

	return np.sqrt(var)


def calc_ate_se(vars_c, vars_t, scaled_counts_c, scaled_counts_t):

	N_c, N_t = len(vars_c), len(vars_t)
	N = N_c + N_t
	weights_c = (N_c/N)*(1+scaled_counts_c)
	weights_t = (N_t/N)*(1+scaled_counts_t)
	
	var = calc_atx_var(vars_c, vars_t, weights_c, weights_t)

	return np.sqrt(var)

