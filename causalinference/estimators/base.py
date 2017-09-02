import causalinference.utils.tools as tools
from ..core import Dict


def estimation_names():
	return ['ate', 'atc', 'att', ]


def standard_err_names():
	return ['ate_se', 'atc_se', 'att_se', ]

class Estimator(Dict):

	"""
	Dictionary-like class containing treatment effect estimates.
	"""

	def __str__(self):

		table_width = 100
		names = estimation_names()
		coefs = [self[name] for name in names if name in self.keys()]
		ses = [self[name] for name in standard_err_names() if name in self.keys()]

		output = '\n'
		output += 'Treatment Effect Estimates: ' + self._method + '\n\n'

		entries1 = ['', 'Est.', 'S.e.', 'z', 'P>|z|',
		           '[95% Conf. int.]']
		entry_types1 = ['string']*6
		col_spans1 = [1]*5 + [2]
		output += tools.add_row(entries1, entry_types1,
		                        col_spans1, table_width)
		output += tools.add_line(table_width)

		entry_types2 = ['string'] + ['float']*6
		col_spans2 = [1]*7
		for (name, coef, se) in zip(names, coefs, ses):
			for i, (coef_val, se_val) in enumerate(zip(coef, se)):
				entries2 = tools.gen_reg_entries(
					'Y{}: {}'.format(i, name.upper()), coef_val, se_val)
				output += tools.add_row(entries2, entry_types2,
										col_spans2, table_width)

		return output

	def as_rows(self):
		names = estimation_names()
		coefs = [self[name] for name in names if name in self.keys()]
		ses = [self[name] for name in standard_err_names() if name in self.keys()]
		r2s = self['r2']

		rows = [('', 'Est.', 'S.e.', 'z', 'P>|z|',
		           '[95% Conf. int.]', 'r2')]
		print(len(coef), len(se), len(r2s))
		for (name, coef, se) in zip(names, coefs, ses):
			for i, (coef_val, se_val, r2_val) in enumerate(zip(coef, se, r2s)):
				row = list(tools.gen_reg_entries(
					'Y{}: {}'.format(i, name.upper()), coef_val, se_val))[1:]
				row.append(r2_val)
				rows.append(row)
		return rows


	

class Estimators(Dict):

	"""
	Dictionary-like class containing treatment effect estimates for each
	estimator used.
	"""

	def __init__(self):

		self._dict = {}


	def __setitem__(self, key, item):

		self._dict[key] = item


	def __str__(self):

		output = ''
		for method in self.keys():
			output += self[method].__str__()

		return output

