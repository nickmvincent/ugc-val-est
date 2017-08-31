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
				X = s.raw_data['X']
				to_delete = []
				for col_num, ndiff_val in enumerate(s.summary_stats['ndiff']):
					if np.isnan(ndiff_val):
						to_delete.append(col_num)
					else:
						mean_tup = (s.summary_stats['X_c_mean'][col_num],
						s.summary_stats['X_t_mean'])
						if mean_tup[0] == 0 or mean_tup[1] == 0:
							stdev_tup = (
								s.summary_stats['X_c_sd'],
								s.summary_stats['X_t_sd']
							)
							if (mean_tup[0] == 0 and stdev_tup[0] == 0 or
								mean_tup[1] == 0 and stdev_tup[1] == 0):
								print('Ran into a problem column in strata {}'.format(i))
								print('Need to remove column number {}'.format(col_num))
								to_delete.append(col_num)
				cols_deleted = 0
				for col_num in to_delete:
					X = np.delete(X, col_num - cols_deleted, 1)
					cols_deleted += 1
				strata[i] = causal.CausalModel(s.raw_data['Y'], s.raw_data['D'], X)
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
			atc_ses = np.array([s.estimates['ols']['atc_se'] for s in strata]).T
			att_ses = np.array([s.estimates['ols']['att_se'] for s in strata]).T

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

