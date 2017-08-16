import numpy as np
from scipy.stats import norm, logistic

from os import path
lalonde_file = path.join(path.dirname(__file__), 'lalonde_data.txt')
vignette_file = path.join(path.dirname(__file__), 'vignette_data.txt')


def convert_to_formatting(entry_types):

	for entry_type in entry_types:
		if entry_type == 'string':
			yield 's'
		elif entry_type == 'float':
			yield '.3f'
		elif entry_type == 'integer':
			yield '.0f'


def add_row(entries, entry_types, col_spans, width):

	#Convert an array of string or numeric entries into a string with
	#even formatting and spacing.

	vis_cols = len(col_spans)
	invis_cols = sum(col_spans)

	char_per_col = width // invis_cols
	first_col_padding = width % invis_cols

	char_spans = [char_per_col * col_span for col_span in col_spans]
	char_spans[0] += first_col_padding
	formatting = convert_to_formatting(entry_types)
	line = ['%'+str(s)+f for (s,f) in zip(char_spans,formatting)]

	return (''.join(line) % tuple(entries)) + '\n'


def add_line(width):

	return '-'*width + '\n'


def gen_reg_entries(varname, coef, se):

	z = coef / se
	p = 2*(1 - norm.cdf(np.abs(z)))
	lw = coef - 1.96*se
	up = coef + 1.96*se

	return (varname, coef, se, z, p, lw, up)


def random_data(N=5000, K=3, unobservables=False, **kwargs):

	"""
	Function that generates data according to one of two simple models that
	satisfies the unconfoundedness assumption.

	The covariates and error terms are generated according to
		X ~ N(mu, Sigma), epsilon ~ N(0, Gamma).

	The counterfactual outcomes are generated by
		Y0 = X*beta + epsilon_0,
		Y1 = delta + X*(beta+theta) + epsilon_1.

	Selection is done according to the following propensity score function:
		P(D=1|X) = Lambda(X*beta).

	Here Lambda is the standard logistic CDF.

	Parameters
	----------
	N: int
		Number of units to draw. Defaults to 5000.
	K: int
		Number of covariates. Defaults to 3.
	unobservables: bool
		Returns potential outcomes and true propensity score
		in addition to observed outcome and covariates if True.
		Defaults to False.
	mu, Sigma, Gamma, beta, delta, theta: NumPy ndarrays, optional
		Parameter values appearing in data generating process.

	Returns
	-------
	tuple
		A tuple in the form of (Y, D, X) or (Y, D, X, Y0, Y1) of
		observed outcomes, treatment indicators, covariate matrix,
		and potential outomces.
	"""

	mu = kwargs.get('mu', np.zeros(K))
	beta = kwargs.get('beta', np.ones(K))
	theta = kwargs.get('theta', np.ones(K))
	delta = kwargs.get('delta', 3)
	Sigma = kwargs.get('Sigma', np.identity(K))
	Gamma = kwargs.get('Gamma', np.identity(2))

	X = np.random.multivariate_normal(mean=mu, cov=Sigma, size=N)
	Xbeta = X.dot(beta)
	pscore = logistic.cdf(Xbeta)
	D = np.array([np.random.binomial(1, p, size=1) for p in pscore]).flatten()

	epsilon = np.random.multivariate_normal(mean=np.zeros(2), cov=Gamma, size=N)
	Y0 = Xbeta + epsilon[:,0]
	Y1 = delta + X.dot(beta+theta) + epsilon[:,1]
	Y = (1-D)*Y0 + D*Y1

	if unobservables:
		return Y, D, X, Y0, Y1, pscore
	else:
		return Y, D, X


def read_tsv(filepath):

	data = np.loadtxt(filepath, delimiter='\t', skiprows=1)
	Y = data[:,0]
	D = data[:,1]
	X = data[:,2:]

	return Y, D, X


def vignette_data():

	return read_tsv(vignette_file)


def lalonde_data():

	return read_tsv(lalonde_file)

