import numpy as np


class Dict(object):

	"""
	Dictionary-mimicking class.
	"""

	def __getitem__(self, key):

		return self._dict[key]


	def __iter__(self):

		return iter(self._dict)

	
	def __repr__(self):

		return self._dict.__repr__()


	def keys(self):

		return self._dict.keys()

	
	def iteritems(self):

		return self._dict.iteritems()


	def get(self, key, default=None):
	
		return self._dict.get(key, default)


class Data(Dict):

	"""
	Dictionary-like class containing basic data.
	"""

	def __init__(self, outcome, treatment, covariates):
		"""
		This is where matrix dimensionality N X K is explictly defined
		ie.
		     K=3
		     
		     ***
		     ***
		N=5  ***
		     ***
		     ***
		"""
		Y, D, X = preprocess(outcome, treatment, covariates)
		self._dict = dict()
		self._dict['Y'] = Y
		self._dict['D'] = D
		self._dict['X'] = X
		self._dict['N'], self._dict['K'] = X.shape
		self._dict['num_outputs'] = Y.shape[1]
		self._dict['controls'] = (D==0)
		self._dict['treated'] = (D==1)
		self._dict['Y_c'] = Y[self._dict['controls']]
		self._dict['Y_t'] = Y[self._dict['treated']]
		self._dict['X_c'] = X[self._dict['controls']]
		self._dict['X_t'] = X[self._dict['treated']]
		self._dict['N_t'] = D.sum()
		self._dict['N_c'] = self._dict['N'] - self._dict['N_t']
		if self._dict['K']+1 > self._dict['N_c']:
			print(self._dict['K'], self._dict['N_c'])
			raise ValueError('Too few control units: N_c < K+1')
		if self._dict['K']+1 > self._dict['N_t']:
			print(self._dict['K'], self._dict['N_t'])
			raise ValueError('Too few treated units: N_t < K+1')


def preprocess(Y, D, X):
	"""Verfies shape of Y, D, X
	
	D is the treatment vector (Boolean vector)
	It is a column vector with shape N, 1 (N rows, 1 column)
	i.e.
	0
	1
	0
	1
	1

	X is the intput vector (numeric)
	It is a matrix with shape N, K
	"""
	if Y.shape[0] == D.shape[0] == X.shape[0]:
		N = Y.shape[0]
	else:
		raise IndexError('Input data have different number of rows')

	if D.shape != (N, ):
		D.shape = (N, )
	if D.dtype != 'int':
		D = D.astype(int)
	# reshape X and Y matrices in case they have only a single index
	# this gives them two indices (so they are seen as matrix not vector)
	if X.shape == (N, ):
		X.shape = (N, 1)
	if Y.shape == (N, ):
		Y.shape = (N, 1)

	return (Y, D, X)

