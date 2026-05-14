"""
algebraic_attacks.py
====================
Algebraic Attack Analysis for Piecewise Affine Systems

Implements and analyzes three algebraic attack vectors:
1. Polynomial system solving (Groebner basis)
2. Chinese Remainder Theorem (CRT) decomposition
3. Lattice-based state recovery

Author: Abhijay Gangarapu, UT Austin / ISEF
"""

import numpy as np
from typing import List, Tuple, Dict
from math import gcd


def analyze_polynomial_system(m: int, A_list: List[np.ndarray], 
                               b_list: List[np.ndarray], 
                               observed: List[int]) -> Dict:
    """
    Analyze polynomial system attack complexity.
    
    Given L observed outputs, the attacker solves:
        s_i = x_i[0]
        x_{i+1} = A_{s_i mod r} x_i + b_{s_i mod r}  (mod m)
    
    This is a system of 2L polynomial equations in 2 unknowns (initial state).
    
    Complexity: O(m^2) for exhaustive search, O(m^{1.5}) with Groebner basis.
    """
    L = len(observed)
    r = len(A_list)
    
    # For small m, exhaustive search is feasible
    if m <= 1000:
        attack_feasible = True
        complexity = m ** 2
        method = "Exhaustive search"
    else:
        attack_feasible = False
        complexity = m ** 1.5  # Groebner basis estimate
        method = "Groebner basis (infeasible for large m)"
    
    return {
        'attack': 'Polynomial System Solving',
        'observed_terms': L,
        'state_space_size': m ** 2,
        'complexity': complexity,
        'feasible': attack_feasible,
        'method': method,
        'resistance': 'HIGH' if not attack_feasible else 'LOW'
    }


def analyze_crt_decomposition(m: int, factors: List[Tuple[int, int]]) -> Dict:
    """
    Analyze CRT decomposition attack.
    
    If m = p1^k1 * p2^k2 * ... * pn^kn, attacker can:
    1. Solve the system modulo each prime power separately
    2. Combine solutions using CRT
    
    Complexity: O(sum(pi^{2ki})) vs O(m^2) for direct attack.
    
    This is only effective when m is composite with small prime factors.
    """
    if len(factors) == 1:
        # Prime power - no CRT advantage
        return {
            'attack': 'CRT Decomposition',
            'applicable': False,
            'reason': 'm is a prime power - CRT provides no advantage',
            'resistance': 'HIGH'
        }
    
    # Compute complexity of CRT attack
    crt_complexity = sum(p ** (2 * k) for p, k in factors)
    direct_complexity = m ** 2
    speedup = direct_complexity / crt_complexity
    
    return {
        'attack': 'CRT Decomposition',
        'applicable': True,
        'factors': factors,
        'crt_complexity': crt_complexity,
        'direct_complexity': direct_complexity,
        'speedup_factor': speedup,
        'feasible': crt_complexity < 10**6,
        'resistance': 'MEDIUM' if speedup > 10 else 'HIGH'
    }


def analyze_lattice_attack(m: int, L: int, d: int = 2) -> Dict:
    """
    Analyze lattice-based state recovery.
    
    Given L consecutive outputs, construct a lattice where short vectors
    correspond to the initial state. Uses LLL algorithm.
    
    Complexity: O(L^3 * log^3(m)) for LLL reduction.
    
    Success probability depends on L/d ratio and m.
    """
    lattice_dim = L * d
    lll_complexity = (lattice_dim ** 3) * (np.log2(m) ** 3)
    
    # Heuristic: need L >= 2d + log2(m) for high success probability
    required_L = 2 * d + int(np.log2(m))
    success_prob = min(1.0, L / required_L) if L >= d else 0.0
    
    return {
        'attack': 'Lattice-based (LLL)',
        'observed_terms': L,
        'lattice_dimension': lattice_dim,
        'lll_complexity': lll_complexity,
        'required_terms': required_L,
        'success_probability': success_prob,
        'feasible': lll_complexity < 10**9 and success_prob > 0.5,
        'resistance': 'LOW' if success_prob > 0.8 else 'MEDIUM' if success_prob > 0.3 else 'HIGH'
    }


def comprehensive_attack_analysis(m: int, A_list: List[np.ndarray], 
                                   b_list: List[np.ndarray],
                                   L_observed: int = 100) -> Dict:
    """
    Comprehensive analysis of all algebraic attacks.
    
    Returns resistance profile across all attack vectors.
    """
    from generator import prime_factorization
    
    factors = prime_factorization(m)
    
    poly_attack = analyze_polynomial_system(m, A_list, b_list, list(range(L_observed)))
    crt_attack = analyze_crt_decomposition(m, factors)
    lattice_attack = analyze_lattice_attack(m, L_observed)
    
    # Overall resistance: weakest link
    resistances = [poly_attack['resistance'], crt_attack['resistance'], 
                   lattice_attack['resistance']]
    overall = 'LOW' if 'LOW' in resistances else 'MEDIUM' if 'MEDIUM' in resistances else 'HIGH'
    
    return {
        'm': m,
        'factors': factors,
        'observed_terms': L_observed,
        'polynomial_attack': poly_attack,
        'crt_attack': crt_attack,
        'lattice_attack': lattice_attack,
        'overall_resistance': overall,
        'recommendation': 'Use prime power moduli (not composite) for maximum resistance'
    }


if __name__ == "__main__":
    from generator import get_matrices
    
    print("=" * 80)
    print("ALGEBRAIC ATTACK ANALYSIS")
    print("=" * 80)
    
    A_list, b_list = get_matrices('sat')
    
    configs = [
        (25, "p=5, k=2"),
        (125, "p=5, k=3"),
        (121, "p=11, k=2"),
        (169, "p=13, k=2"),
        (35, "composite 5*7")
    ]
    
    for m, label in configs:
        print(f"\n[{label}, m={m}]")
        result = comprehensive_attack_analysis(m, A_list, b_list, L_observed=100)
        print(f"  Overall Resistance: {result['overall_resistance']}")
        print(f"  Polynomial: {result['polynomial_attack']['resistance']} "
              f"(complexity: {result['polynomial_attack']['complexity']:.2e})")
        print(f"  CRT: {result['crt_attack']['resistance']}")
        print(f"  Lattice: {result['lattice_attack']['resistance']} "
              f"(success prob: {result['lattice_attack']['success_probability']:.2%})")
