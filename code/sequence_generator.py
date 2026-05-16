"""
Sequence generator for piecewise affine maps over Z/p^k Z
"""

import numpy as np

def generate_piecewise_sequence(p, k, hensel_satisfied=True, n_terms=4500, burn_in=300, seed=42):
    """
    Generate piecewise affine sequence over Z/p^k Z
    
    Args:
        p: Prime base
        k: Extension level
        hensel_satisfied: Use Hensel-satisfied matrices if True
        n_terms: Number of terms to generate
        burn_in: Number of initial terms to discard
        seed: Random seed for reproducibility
    
    Returns:
        sequence: Array of output values (first component of state)
    """
    np.random.seed(seed)
    m = p ** k
    
    # Canonical matrices (reduced mod p at runtime)
    if hensel_satisfied:
        A0 = np.array([[1, 1], [3, 1]]) % m
        b0 = np.array([1, 2]) % m
        A1 = np.array([[3, 3], [1, 3]]) % m
        b1 = np.array([2, 1]) % m
    else:
        A0 = np.array([[2, 1], [1, 2]]) % m
        b0 = np.array([3, 4]) % m
        A1 = A0  # Single regime for violated
        b1 = b0
    
    # Initial state
    x = np.array([1, 1], dtype=np.int64)
    
    sequence = []
    for _ in range(burn_in + n_terms):
        # Regime selection based on parity of first component
        regime = x[0] % 2
        
        # Apply piecewise affine map
        if regime == 0:
            x = (A0 @ x + b0) % m
        else:
            x = (A1 @ x + b1) % m
        
        # Record output (first component)
        sequence.append(x[0])
    
    # Remove burn-in
    return np.array(sequence[burn_in:])

def generate_piecewise_sequence_with_states(p, k, hensel_satisfied=True, n_terms=4500, burn_in=300, seed=42):
    """
    Generate piecewise affine sequence WITH full state information
    
    Args:
        p: Prime base
        k: Extension level
        hensel_satisfied: Use Hensel-satisfied matrices if True
        n_terms: Number of terms to generate
        burn_in: Number of initial terms to discard
        seed: Random seed for reproducibility
    
    Returns:
        sequence: Array of output values (first component of state)
        states: List of (x0, x1) state tuples
        regimes: Array of regime selections (0 or 1)
    """
    np.random.seed(seed)
    m = p ** k
    
    # Canonical matrices (reduced mod p at runtime)
    if hensel_satisfied:
        A0 = np.array([[1, 1], [3, 1]]) % m
        b0 = np.array([1, 2]) % m
        A1 = np.array([[3, 3], [1, 3]]) % m
        b1 = np.array([2, 1]) % m
    else:
        A0 = np.array([[2, 1], [1, 2]]) % m
        b0 = np.array([3, 4]) % m
        A1 = A0  # Single regime for violated
        b1 = b0
    
    # Initial state
    x = np.array([1, 1], dtype=np.int64)
    
    sequence = []
    states = []
    regimes = []
    
    for _ in range(burn_in + n_terms):
        # Regime selection based on parity of first component
        regime = x[0] % 2
        
        # Apply piecewise affine map
        if regime == 0:
            x = (A0 @ x + b0) % m
        else:
            x = (A1 @ x + b1) % m
        
        # Record everything
        sequence.append(x[0])
        states.append((x[0], x[1]))
        regimes.append(regime)
    
    # Remove burn-in
    return (np.array(sequence[burn_in:]), 
            states[burn_in:], 
            np.array(regimes[burn_in:]))
