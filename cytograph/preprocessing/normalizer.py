import numpy as np

import loompy

from .utils import div0


class Normalizer:
	"""
	Normalize and optionally standardize and batch-correct a dataset, dealing properly 
	with edge cases such as division by zero.
	"""
	def __init__(self, standardize: bool = False, layer: str = "") -> None:
		self.standardize = standardize
		self.sd = None  # type: np.ndarray
		self.mu = None  # type: np.ndarray
		self.totals = None  # type: np.ndarray
		self.level = 0
		self.layer = layer

	def fit(self, ds: loompy.LoomConnection) -> None:
		self.sd = np.zeros(ds.shape[0])
		self.mu = np.zeros(ds.shape[0])
		self.totals = np.zeros(ds.shape[1])

		for _, selection, view in ds.scan(axis=0):
			vals = view[self.layer][:, :].astype("float")
			self.totals += np.sum(vals, axis=0)
		self.level = np.median(self.totals)

		for _, selection, view in ds.scan(axis=0):
			vals = view[self.layer][:, :].astype("float")
			# Rescale to the median total UMI count, plus 1 (to avoid log of zero), then log transform
			vals = np.log2(div0(vals, self.totals) * self.level + 1)
			self.mu[selection] = np.mean(vals, axis=1)
			self.sd[selection] = np.std(vals, axis=1)

	def transform(self, vals: np.ndarray, cells: np.ndarray = None) -> np.ndarray:
		"""
		Normalize a matrix using the previously calculated aggregate statistics

		Args:
			vals (ndarray):		Matrix of shape (n_genes, n_cells)
			cells (ndarray):	Optional indices of the cells that are represented in vals

		Returns:
			vals_adjusted (ndarray):	The normalized values
		"""
		# Adjust total count per cell to the desired overall level
		if cells is None:
			cells = slice(None)
		vals = vals.astype("float")
		vals = np.log2(div0(vals, self.totals[cells]) * self.level + 1)

		# Subtract mean per gene
		vals = vals - self.mu[:, None]
		if self.standardize:
			# Scale to unit standard deviation per gene
			vals = div0(vals.T, self.sd).T
		return vals

	def fit_transform(self, ds: loompy.LoomConnection, vals: np.ndarray, cells: np.ndarray = None) -> np.ndarray:
		self.fit(ds)
		return self.transform(vals, cells)
