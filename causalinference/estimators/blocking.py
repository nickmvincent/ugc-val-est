from __future__ import division
import numpy as np

from .base import Estimator, estimation_names, standard_err_names
from .. import causal

class Blocking(Estimator):

	"""
	Dictionary-like class containing treatment effect estimates.
	"""

	def __init__(self, strata, adj):
	
		self._method = 'Blocking'

		for i, s in enumerate(strata):
			try:
				s.est_via_ols(adj)
			except np.linalg.linalg.LinAlgError as err:
				# if there is a variable that is uniform for a stratum
				# this will cause ndiff to be calculated as nan (zero std)
				print('Entering singular matrix fixing code')
				print(s.summary_stats)
				X = s.raw_data['X']
				to_delete = []
				for col_num, ndiff_val in enumerate(s.summary_stats['ndiff']):
					if np.isnan(ndiff_val):
						to_delete.append(col_num)
				cols_deleted = 0
				for col_num in to_delete:
					X = np.delete(X, col_num - cols_deleted, 1)
					cols_deleted += 1
				strata[i] = causal.CausalModel(s.raw_data['Y'], s.raw_data['D'], X)
				print('New causal model created!')
				print(strata[i].summary_stats)
				strata[i].est_via_ols(adj)
				print(strata[i].estimates)

		Ns = [s.raw_data['N'] for s in strata]
		N_cs = [s.raw_data['N_c'] for s in strata]
		N_ts = [s.raw_data['N_t'] for s in strata]

		ates = [s.estimates['ols']['ate'] for s in strata]
		ate_ses = [s.estimates['ols']['ate_se'] for s in strata]
		if adj <= 1:
			atcs, atts = ates, ates
			atc_ses, att_ses = ate_ses, ate_ses
		else:
			atcs = [s.estimates['ols']['atc'] for s in strata]
			atts = [s.estimates['ols']['att'] for s in strata]
			atc_ses = [s.estimates['ols']['atc_se'] for s in strata]
			att_ses = [s.estimates['ols']['att_se'] for s in strata]

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

