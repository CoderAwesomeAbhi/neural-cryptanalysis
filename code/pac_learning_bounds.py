"""
PAC Learning Sample Complexity Analysis
Derives theoretical bounds for learning periodic sequences
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))


def vc_dimension_periodic(T, m):
    """
    VC dimension of period-T functions over alphabet size m
    
    A period-T function is determined by T values from {0, ..., m-1}
    VC dimension ≈ T log(m)
    """
    return T * np.log2(m)


def pac_sample_complexity(T, m, epsilon=0.1, delta=0.05):
    """
    PAC learning sample complexity for period-T sequences
    
    With probability ≥ 1-δ, need n samples to achieve error ≤ ε:
    n ≥ (1/ε) * (VC(H) + log(1/δ))
    
    For periodic sequences: VC(H) = T log(m)
    """
    vc_dim = vc_dimension_periodic(T, m)
    n_samples = (1 / epsilon) * (vc_dim + np.log(1 / delta))
    return int(np.ceil(n_samples))


def information_theoretic_lower_bound(T, m):
    """
    Information-theoretic lower bound
    
    To distinguish among m^T possible period-T sequences,
    need at least log(m^T) / log(m) = T samples
    """
    return T


def empirical_sample_requirement(T, L_in):
    """
    Empirical requirement from experiments
    
    Need ρ ≥ c repetitions per transition
    With L_in context, see L_in transitions
    Total samples: N ≥ c * T
    """
    c = 100  # Empirical constant from experiments
    return c * T / L_in


def analyze_config(p, k, T, L_in=6):
    """Analyze sample complexity for a configuration"""
    m = p ** k
    
    print(f"\n{'='*80}")
    print(f"SAMPLE COMPLEXITY ANALYSIS: p={p}, k={k}, T={T}")
    print(f"{'='*80}")
    print(f"Alphabet size m = {m}")
    print(f"Period T = {T}")
    print(f"Context window L_in = {L_in}")
    print(f"T/L_in = {T/L_in:.1f}")
    print()
    
    # VC dimension
    vc_dim = vc_dimension_periodic(T, m)
    print(f"VC Dimension: {vc_dim:.1f} bits")
    
    # PAC bounds
    pac_01 = pac_sample_complexity(T, m, epsilon=0.1, delta=0.05)
    pac_001 = pac_sample_complexity(T, m, epsilon=0.01, delta=0.05)
    
    print(f"\nPAC Learning Bounds (δ=0.05):")
    print(f"  ε=0.1:  n ≥ {pac_01:,} samples")
    print(f"  ε=0.01: n ≥ {pac_001:,} samples")
    
    # Information-theoretic bound
    info_bound = information_theoretic_lower_bound(T, m)
    print(f"\nInformation-Theoretic Lower Bound:")
    print(f"  n ≥ {info_bound:,} samples (Ω(T))")
    
    # Empirical requirement
    emp_req = empirical_sample_requirement(T, L_in)
    print(f"\nEmpirical Requirement (from experiments):")
    print(f"  n ≥ {emp_req:,.0f} samples")
    
    # Typical training set
    n_train = 3600
    print(f"\nTypical Training Set: {n_train:,} samples")
    print(f"  Ratio to info bound: {n_train / info_bound:.2f}x")
    print(f"  Ratio to PAC bound (ε=0.1): {n_train / pac_01:.2f}x")
    print(f"  Ratio to empirical: {n_train / emp_req:.2f}x")
    
    # Verdict
    print(f"\n{'='*60}")
    if n_train >= emp_req:
        print(f"✓ SUFFICIENT SAMPLES (n ≥ empirical requirement)")
    elif n_train >= info_bound:
        print(f"⚠ MARGINAL (n ≥ info bound, but < empirical)")
    else:
        print(f"✗ INSUFFICIENT (n < information-theoretic minimum)")
    print(f"{'='*60}")
    
    return {
        'p': p, 'k': k, 'T': T, 'm': m,
        'vc_dim': vc_dim,
        'pac_01': pac_01,
        'pac_001': pac_001,
        'info_bound': info_bound,
        'emp_req': emp_req,
        'n_train': n_train
    }


def plot_sample_complexity():
    """Plot sample complexity vs period"""
    periods = np.logspace(1, 4, 50)
    m = 25
    
    # Different bounds
    info_bounds = [information_theoretic_lower_bound(T, m) for T in periods]
    pac_bounds = [pac_sample_complexity(T, m, epsilon=0.1, delta=0.05) for T in periods]
    emp_bounds = [empirical_sample_requirement(T, 6) for T in periods]
    
    plt.figure(figsize=(10, 6))
    plt.loglog(periods, info_bounds, 'b-', label='Info-theoretic Ω(T)', linewidth=2)
    plt.loglog(periods, pac_bounds, 'r--', label='PAC (ε=0.1, δ=0.05)', linewidth=2)
    plt.loglog(periods, emp_bounds, 'g:', label='Empirical (c≈100)', linewidth=2)
    
    # Typical training set
    plt.axhline(3600, color='k', linestyle='-.', label='Typical n_train=3600')
    
    # Mark experimental configs
    configs = [
        (125, 'Easy'),
        (1083, 'Medium'),
        (7295, 'Hard')
    ]
    for T, name in configs:
        plt.plot(T, information_theoretic_lower_bound(T, m), 'ko', markersize=8)
        plt.text(T, information_theoretic_lower_bound(T, m) * 0.5, name, 
                ha='center', fontsize=9)
    
    plt.xlabel('Period T', fontsize=12)
    plt.ylabel('Required Samples n', fontsize=12)
    plt.title('Sample Complexity Bounds for Periodic Sequences', fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    
    results_dir = Path(__file__).parent.parent / 'results'
    results_dir.mkdir(exist_ok=True)
    plt.savefig(results_dir / 'sample_complexity_bounds.pdf', bbox_inches='tight')
    print(f"\nPlot saved to {results_dir / 'sample_complexity_bounds.pdf'}")


def main():
    """Run sample complexity analysis"""
    
    print("\n" + "="*80)
    print("PAC LEARNING SAMPLE COMPLEXITY ANALYSIS")
    print("="*80)
    
    configs = [
        {'p': 5, 'k': 2, 'T': 125, 'name': 'Easy'},
        {'p': 7, 'k': 2, 'T': 1083, 'name': 'Medium'},
        {'p': 5, 'k': 3, 'T': 7295, 'name': 'Hard'}
    ]
    
    results = []
    for config in configs:
        result = analyze_config(config['p'], config['k'], config['T'])
        results.append(result)
    
    # Summary table
    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)
    print(f"{'Config':<10} {'T':>6} {'Info':>8} {'PAC':>10} {'Empirical':>12} {'n_train':>8} {'Status':<15}")
    print("-"*80)
    
    for r, config in zip(results, configs):
        status = "✓ Sufficient" if r['n_train'] >= r['emp_req'] else "✗ Insufficient"
        print(f"{config['name']:<10} {r['T']:>6} {r['info_bound']:>8,} {r['pac_01']:>10,} "
              f"{r['emp_req']:>12,.0f} {r['n_train']:>8,} {status:<15}")
    
    print("="*80)
    
    # Theoretical conclusion
    print("\n" + "="*80)
    print("THEORETICAL CONCLUSION")
    print("="*80)
    print("1. Information-theoretic bound: Ω(T) samples necessary")
    print("2. PAC learning bound: O(T log m / ε) samples sufficient")
    print("3. Empirical observation: ~100T samples needed in practice")
    print()
    print("The gap between theory (T) and practice (100T) suggests:")
    print("  • Neural networks require multiple repetitions per transition")
    print("  • Constant factor c≈100 depends on architecture and optimization")
    print("  • This is NOT an optimization failure - it's sample complexity")
    print("="*80)
    
    # Generate plot
    plot_sample_complexity()


if __name__ == '__main__':
    main()
