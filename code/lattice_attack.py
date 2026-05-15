"""
LLL Lattice Attack on Piecewise Affine Generator
Quantitative analysis of lattice-based cryptanalysis resistance.
"""

import numpy as np
from generator import PiecewiseAffineGenerator
import json

def lll_reduce(basis):
    """
    Lenstra-Lenstra-Lovász (LLL) lattice basis reduction.
    
    Args:
        basis: n x n matrix where rows are basis vectors
    
    Returns:
        reduced_basis: LLL-reduced basis
        transform: Unimodular transformation matrix
    """
    n = basis.shape[0]
    basis = basis.astype(float)
    
    # Gram-Schmidt orthogonalization
    def gram_schmidt(B):
        n = B.shape[0]
        B_star = np.zeros_like(B, dtype=float)
        mu = np.zeros((n, n), dtype=float)
        
        for i in range(n):
            B_star[i] = B[i].copy()
            for j in range(i):
                mu[i, j] = np.dot(B[i], B_star[j]) / np.dot(B_star[j], B_star[j])
                B_star[i] -= mu[i, j] * B_star[j]
        
        return B_star, mu
    
    # LLL algorithm
    delta = 0.75  # Lovász condition parameter
    k = 1
    transform = np.eye(n, dtype=int)
    
    max_iterations = 1000
    iteration = 0
    
    while k < n and iteration < max_iterations:
        iteration += 1
        
        # Gram-Schmidt
        B_star, mu = gram_schmidt(basis)
        
        # Size reduction
        for j in range(k-1, -1, -1):
            if abs(mu[k, j]) > 0.5:
                q = round(mu[k, j])
                basis[k] -= q * basis[j]
                transform[k] -= q * transform[j]
        
        # Recompute after size reduction
        B_star, mu = gram_schmidt(basis)
        
        # Lovász condition
        if np.dot(B_star[k], B_star[k]) >= (delta - mu[k, k-1]**2) * np.dot(B_star[k-1], B_star[k-1]):
            k += 1
        else:
            # Swap basis[k] and basis[k-1]
            basis[[k, k-1]] = basis[[k-1, k]]
            transform[[k, k-1]] = transform[[k-1, k]]
            k = max(k-1, 1)
    
    return basis, transform


def construct_lattice_basis(sequence, n_terms=100, m=125):
    """
    Construct lattice basis from observed sequence terms.
    
    For a linear recurrence x_{n+d} = sum(a_i * x_{n+i}) mod m,
    the lattice attack tries to find the shortest vector that
    reveals the recurrence coefficients.
    
    Args:
        sequence: Observed sequence terms
        n_terms: Number of terms to use
        m: Modulus
    
    Returns:
        basis: Lattice basis matrix
    """
    d = 2  # Dimension of state space
    
    # Construct Hankel matrix
    # Each row: [x_i, x_{i+1}, ..., x_{i+d}]
    n_rows = n_terms - d
    H = np.zeros((n_rows, d+1), dtype=int)
    
    for i in range(n_rows):
        H[i] = sequence[i:i+d+1]
    
    # Construct lattice basis
    # The idea: if x_{i+d} = sum(a_j * x_{i+j}) mod m,
    # then the vector [a_0, a_1, ..., a_{d-1}, -1, 0, ..., 0]
    # is in the lattice
    
    n = d + 1 + n_rows
    basis = np.zeros((n, n), dtype=int)
    
    # First d+1 rows: identity scaled by m
    for i in range(d+1):
        basis[i, i] = m
    
    # Remaining rows: Hankel matrix
    for i in range(n_rows):
        basis[d+1+i, :d+1] = H[i]
        basis[d+1+i, d+1+i] = 1
    
    return basis


def lattice_attack(p=5, k=2, n_terms=100, verbose=True):
    """
    Perform LLL lattice attack on piecewise affine generator.
    
    Args:
        p: Prime base
        k: Extension level
        n_terms: Number of sequence terms to observe
        verbose: Print detailed results
    
    Returns:
        results: Dictionary with attack results
    """
    m = p ** k
    gen = PiecewiseAffineGenerator(p, k, hensel_satisfied=True)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"LLL Lattice Attack: p={p}, k={k}, m={m}")
        print('='*60)
        print(f"Sequence period: T = {gen.period}")
        print(f"Hensel satisfied: {gen.hensel_satisfied}")
    
    # Generate sequence
    seq = gen.generate(n_terms + 100)
    
    # Construct lattice basis
    basis = construct_lattice_basis(seq, n_terms=n_terms, m=m)
    
    if verbose:
        print(f"\nLattice dimension: {basis.shape[0]} x {basis.shape[1]}")
        print(f"Basis determinant: {abs(np.linalg.det(basis)):.2e}")
    
    # Apply LLL reduction
    reduced_basis, transform = lll_reduce(basis)
    
    # Find shortest vector
    norms = [np.linalg.norm(reduced_basis[i]) for i in range(reduced_basis.shape[0])]
    shortest_idx = np.argmin(norms)
    shortest_vector = reduced_basis[shortest_idx]
    shortest_norm = norms[shortest_idx]
    
    if verbose:
        print(f"\nShortest vector norm: {shortest_norm:.2f}")
        print(f"Shortest vector (first 10 components): {shortest_vector[:10]}")
    
    # Check if attack succeeded
    # For a successful attack, the shortest vector should reveal
    # the linear recurrence coefficients
    
    # Extract potential coefficients (first d components)
    d = 2
    potential_coeffs = shortest_vector[:d]
    
    # Test if these coefficients predict the sequence
    errors = 0
    for i in range(n_terms - d - 1):
        predicted = sum(potential_coeffs[j] * seq[i+j] for j in range(d)) % m
        actual = seq[i+d]
        if predicted != actual:
            errors += 1
    
    success_rate = 1 - errors / (n_terms - d - 1)
    
    if verbose:
        print(f"\nAttack success rate: {success_rate*100:.1f}%")
        print(f"Prediction errors: {errors}/{n_terms-d-1}")
        
        if success_rate < 0.1:
            print("\n✅ ATTACK FAILED: Lattice attack cannot recover recurrence")
            print("   Resistance: HIGH")
        elif success_rate < 0.5:
            print("\n⚠️  ATTACK PARTIALLY SUCCESSFUL")
            print("   Resistance: MEDIUM")
        else:
            print("\n❌ ATTACK SUCCESSFUL: Recurrence recovered")
            print("   Resistance: LOW")
    
    results = {
        'p': p,
        'k': k,
        'm': m,
        'period': gen.period,
        'n_terms': n_terms,
        'lattice_dim': basis.shape[0],
        'shortest_norm': float(shortest_norm),
        'success_rate': float(success_rate),
        'errors': int(errors),
        'resistance': 'HIGH' if success_rate < 0.1 else ('MEDIUM' if success_rate < 0.5 else 'LOW')
    }
    
    return results


def comprehensive_lattice_analysis():
    """
    Comprehensive lattice attack analysis across multiple configurations.
    
    This provides quantitative resistance metrics for Section 4.4 of the paper.
    """
    configurations = [
        (5, 1),   # m = 5
        (5, 2),   # m = 25
        (5, 3),   # m = 125
        (7, 2),   # m = 49
        (11, 2),  # m = 121
        (13, 2),  # m = 169
    ]
    
    results = []
    
    print("\n" + "="*80)
    print("COMPREHENSIVE LLL LATTICE ATTACK ANALYSIS")
    print("="*80)
    
    for p, k in configurations:
        result = lattice_attack(p, k, n_terms=200, verbose=True)
        results.append(result)
        print()
    
    # Save results
    with open('../results/lattice_attack_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary table
    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)
    print(f"{'Config':<12} {'m':<6} {'Period':<10} {'Shortest Norm':<15} {'Success Rate':<15} {'Resistance':<12}")
    print("-"*80)
    
    for r in results:
        config = f"p={r['p']}, k={r['k']}"
        print(f"{config:<12} {r['m']:<6} {r['period']:<10} {r['shortest_norm']:<15.2f} {r['success_rate']*100:<14.1f}% {r['resistance']:<12}")
    
    print("\n✅ Results saved to ../results/lattice_attack_results.json")
    
    return results


def higher_dimensional_analysis():
    """
    Test Hensel satisfaction for higher-dimensional matrices (d > 2).
    
    This addresses the scalability question for Section 4.5.
    """
    print("\n" + "="*80)
    print("HIGHER-DIMENSIONAL HENSEL ANALYSIS")
    print("="*80)
    
    p = 5
    k = 2
    m = p ** k
    
    results = []
    
    for d in [2, 3, 4, 5]:
        print(f"\nDimension d = {d}")
        print("-" * 40)
        
        # Generate random invertible matrix mod m
        np.random.seed(42 + d)
        
        # Ensure invertibility by starting with identity and adding random
        A = np.eye(d, dtype=int)
        for _ in range(d):
            i, j = np.random.randint(0, d, 2)
            if i != j:
                A[i, j] = np.random.randint(1, p)
        
        # Compute Hensel index
        det_A = int(np.round(np.linalg.det(A))) % m
        det_A_minus_I = int(np.round(np.linalg.det(A - np.eye(d)))) % m
        
        # p-adic valuation
        def v_p(n, p):
            if n % p != 0:
                return 0
            count = 0
            while n % p == 0:
                n //= p
                count += 1
            return count
        
        delta = v_p(det_A_minus_I, p)
        hensel_satisfied = (delta == 0)
        
        print(f"det(A) mod {m} = {det_A}")
        print(f"det(A-I) mod {m} = {det_A_minus_I}")
        print(f"δ = v_{p}(det(A-I)) = {delta}")
        print(f"Hensel satisfied: {hensel_satisfied}")
        
        results.append({
            'd': d,
            'det_A': det_A,
            'det_A_minus_I': det_A_minus_I,
            'delta': delta,
            'hensel_satisfied': hensel_satisfied
        })
    
    # Save results
    with open('../results/higher_dimensional_hensel.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to ../results/higher_dimensional_hensel.json")
    
    return results


if __name__ == '__main__':
    # Run comprehensive lattice attack analysis
    lattice_results = comprehensive_lattice_analysis()
    
    # Run higher-dimensional analysis
    higher_dim_results = higher_dimensional_analysis()
    
    print("\n" + "="*80)
    print("ALL ANALYSES COMPLETE")
    print("="*80)
    print("\nGenerated files:")
    print("  - ../results/lattice_attack_results.json")
    print("  - ../results/higher_dimensional_hensel.json")
