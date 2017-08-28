from __future__ import division
import numpy as np

from .base import Estimator
from .ols import calc_cov, calc_ate, calc_ate_se

# TODO

class Weighting(Estimator):

	"""
	Dictionary-like class containing treatment effect estimates.
	"""

	def __init__(self, data):

		self._method = 'Weighting'
		Y, D, X = data['Y'], data['D'], data['X']
		pscore = data['pscore']


		weights = calc_weights(pscore, D)
		self._dict = dict()
		self._dict['ate'] = []
		self._dict['ate_se'] = []
		
		for y in Y.T:
			y_w, Z_w = weigh_data(y, D, X, weights)

			wlscoef = np.linalg.lstsq(Z_w, y_w)[0]
			u_w = y_w - Z_w.dot(wlscoef)
			cov = calc_cov(Z_w, u_w)

			self._dict['ate'].append(calc_ate(wlscoef))
			self._dict['ate_se'].append(calc_ate_se(cov))


def calc_weights(pscore, D):

	N = pscore.shape[0]
	weights = np.empty(N)
	weights[D==0] = 1/(1-pscore[D==0])
	weights[D==1] = 1/pscore[D==1]

	return weights


def weigh_data(Y, D, X, weights):

	N, K = X.shape

	Y_w = weights * Y

	Z_w = np.empty((N,K+2))
	Z_w[:,0] = weights
	Z_w[:,1] = weights * D
	Z_w[:,2:] = weights[:,None] * X

	return (Y_w, Z_w)

