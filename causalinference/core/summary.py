from __future__ import division
import numpy as np

import causalinference.utils.tools as tools
from .data import Dict


class Summary(Dict):

	"""
	Dictionary-like class containing summary statistics for input data.

	One of the summary statistics is the normalized difference between
	covariates. Large values indicate that simple linear adjustment methods
	may not be adequate for removing biases that are associated with
	differences in covariates.
	"""

	def __init__(self, data):

		self._dict = dict()

		self._dict['N'], self._dict['K'] = data['N'], data['K']
		self._dict['num_outputs'] = data['num_outputs']
		self._dict['N_c'], self._dict['N_t'] = data['N_c'], data['N_t']
		self._dict['Y_c_mean'] = data['Y_c'].mean(0)
		self._dict['Y_t_mean'] = data['Y_t'].mean(0)
		self._dict['Y_c_sd'] = np.sqrt(data['Y_c'].var(0, ddof=1))
		self._dict['Y_t_sd'] = np.sqrt(data['Y_t'].var(0, ddof=1))
		self._dict['rdiff'] = self['Y_t_mean'] - self['Y_c_mean']
		self._dict['X_c_mean'] = data['X_c'].mean(0)
		self._dict['X_t_mean'] = data['X_t'].mean(0)
		self._dict['X_c_sd'] = np.sqrt(data['X_c'].var(0, ddof=1))
		self._dict['X_t_sd'] = np.sqrt(data['X_t'].var(0, ddof=1))
		self._dict['ndiff'] = calc_ndiff(
			self['X_c_mean'], self['X_t_mean'],
			self['X_c_sd'], self['X_t_sd']
		)
		# might be helpful to assess balance
		self._dict['sum_of_abs_ndiffs'] = sum([
			abs(ndiff) for ndiff in self._dict['ndiff'].T if not np.isnan(ndiff)
		])

		self._dict['num_large_ndiffs'] = len([
			ndiff for ndiff in self._dict['ndiff'] if abs(ndiff) >= 0.25
		])

		self._dict['num_0.1_ndiffs'] = len([
			ndiff for ndiff in self._dict['ndiff'] if abs(ndiff) >= 0.1
		])


	def _summarize_pscore(self, pscore_c, pscore_t):

		"""
		Called by Strata class during initialization.
		"""

		self._dict['p_min'] = min(pscore_c.min(), pscore_t.min())
		self._dict['p_max'] = max(pscore_c.max(), pscore_t.max())
		self._dict['p_c_mean'] = pscore_c.mean()
		self._dict['p_t_mean'] = pscore_t.mean()


	def __str__(self):

		table_width = 80

		N_c, N_t, K = self['N_c'], self['N_t'], self['K']
		Y_c_mean, Y_t_mean = self['Y_c_mean'], self['Y_t_mean']
		Y_c_sd, Y_t_sd = self['Y_c_sd'], self['Y_t_sd']
		X_c_mean, X_t_mean = self['X_c_mean'], self['X_t_mean']
		X_c_sd, X_t_sd = self['X_c_sd'], self['X_t_sd']
		rdiff, ndiff = self['rdiff'], self['ndiff']
		varnames = ['X'+str(i) for i in range(K)]
		outputnames = ['Y'+str(i) for i in range(self['num_outputs'])]
		
		output = '\n'
		output += 'Summary Statistics\n\n'

		entries1 = ['', 'C (N_c='+str(N_c)+')',
		            'T (N_t='+str(N_t)+')', '']
		entry_types1 = ['string']*4
		col_spans1 = [1, 2, 2, 1]
		output += tools.add_row(entries1, entry_types1,
		                        col_spans1, table_width)

		entries2 = ['Variable', 'Mean', 'S.d.',
		            'Mean', 'S.d.', 'rdif']
		entry_types2 = ['string']*6
		col_spans2 = [1]*6
		output += tools.add_row(entries2, entry_types2,
		                        col_spans2, table_width)
		output += tools.add_line(table_width)

		entries3 = ['Y', Y_c_mean, Y_c_sd, Y_t_mean, Y_t_sd, rdiff]
		entry_types3 = ['string'] + ['float']*5
		col_spans3 = [1]*6
		for entries3 in zip(outputnames, Y_c_mean, Y_c_sd,
							Y_t_mean, Y_t_sd, rdiff):
			output += tools.add_row(entries3, entry_types3,
		                        col_spans3, table_width)

		output += '\n'
		output += tools.add_row(entries1, entry_types1,
		                        col_spans1, table_width)

		entries4 = ['Variable', 'Mean', 'S.d.',
		            'Mean', 'S.d.', 'Ndif']
		output += tools.add_row(entries4, entry_types2,
		                        col_spans2, table_width)
		output += tools.add_line(table_width)
		
		entry_types5 = ['string'] + ['float']*5
		col_spans5 = [1]*6
		for entries5 in zip(varnames, X_c_mean, X_c_sd,
		                    X_t_mean, X_t_sd, ndiff):
			output += tools.add_row(entries5, entry_types5,
			                        col_spans5, table_width)

		return output
			

def calc_ndiff(mean_c, mean_t, sd_c, sd_t):

	return (mean_t-mean_c) / np.sqrt((sd_c**2+sd_t**2)/2)

