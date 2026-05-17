"""
Simple wrapper class for backward compatibility with scripts that expect
PiecewiseAffineGenerator class interface
"""

import numpy as np


class PiecewiseAffineGenerator:
    """Simple generator class for piecewise affine maps"""
    
    def __init__(self, p, k):
        self.p = p
        self.k = k
        self.m = p ** k
        
        # Default matrices
        self.A0 = np.array([[2, 1], [1, 2]])
        self.b0 = np.array([1, 0])
        self.A1 = np.array([[1, 2], [2, 1]])
        self.b1 = np.array([0, 1])
