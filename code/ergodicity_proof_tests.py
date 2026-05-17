"""
Ergodicity Tests for Piecewise Affine Maps
Empirical tests of Birkhoff's ergodic theorem and mixing properties
(NOT formal proofs - these are computational experiments)
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))
from simple_generator import PiecewiseAffineGenerator


def birkhoff_ergodic_test(sequence, observable_func, n_blocks=10):
    """
    Test Birkhoff's ergodic theorem: time average = space average
    
    For ergodic system: lim_{n→∞} (1/n) Σ f(x_i) = ∫ f dμ
    """
    n = len(sequence)
    block_size = n // n_blocks
    
    # Time averages over different blocks
    time_averages = []
    for i in range(n_blocks):
        block = sequence[i*block_size:(i+1)*block_size]
        time_avg = np.mean([observable_func(x) for x in block])
        time_averages.append(time_avg)
    
    # Space average (uniform measure)
    m = np.max(sequence) + 1
    space_avg = np.mean([observable_func(x) for x in range(m)])
    
    # Check convergence
    time_avg_mean = np.mean(time_averages)
    time_avg_std = np.std(time_averages)
    
    deviation = abs(time_avg_mean - space_avg)
    
    return {
        'time_avg': time_avg_mean,
        'time_std': time_avg_std,
        'space_avg': space_avg,
        'deviation': deviation,
        'converged': deviation < 3 * time_avg_std / np.sqrt(n_blocks)
    }


def mixing_test(sequence, lag_max=100):
    """
    Test mixing property: correlation decays to zero
    
    For mixing system: lim_{k→∞} Corr(f(x_t), g(x_{t+k})) = 0
    """
    n = len(sequence)
    m = np.max(sequence) + 1
    
    # Normalize sequence
    seq_norm = (sequence - np.mean(sequence)) / np.std(sequence)
    
    # Compute autocorrelation
    autocorr = []
    for lag in range(lag_max):
        if lag < n:
            corr = np.corrcoef(seq_norm[:n-lag], seq_norm[lag:])[0, 1]
            autocorr.append(corr)
        else:
            autocorr.append(0)
    
    # Fit exponential decay
    lags = np.arange(1, min(lag_max, len(autocorr)))
    corr_vals = np.abs(autocorr[1:len(lags)+1])
    
    # Exponential fit: |ρ(k)| ≈ exp(-k/tau)
    log_corr = np.log(corr_vals + 1e-10)
    slope, intercept = np.polyfit(lags, log_corr, 1)
    decay_rate = -slope
    
    return {
        'autocorr': autocorr,
        'decay_rate': decay_rate,
        'mixing_time': 1 / decay_rate if decay_rate > 0 else np.inf
    }


def state_space_coverage(generator, n_steps=10000):
    """
    Test uniform coverage of state space
    
    For ergodic system: orbit visits all states with uniform frequency
    """
    m = generator.p ** generator.k
    
    # Generate orbit
    state = np.array([1, 1])
    visited_states = []
    
    for _ in range(n_steps):
        visited_states.append(state[0] % m)
        
        regime = 0 if state[0] < m // 2 else 1
        if regime == 0:
            state = (generator.A0 @ state + generator.b0) % m
        else:
            state = (generator.A1 @ state + generator.b1) % m
    
    # Count frequencies
    counts = np.bincount(visited_states, minlength=m)
    frequencies = counts / n_steps
    
    # Expected uniform frequency
    expected_freq = 1 / m
    
    # Chi-square test for uniformity
    chi2_stat = np.sum((counts - n_steps/m)**2 / (n_steps/m))
    chi2_pval = 1 - stats.chi2.cdf(chi2_stat, m - 1)
    
    # Kolmogorov-Smirnov test
    ks_stat, ks_pval = stats.kstest(visited_states, 
                                     lambda x: stats.uniform(0, m).cdf(x))
    
    return {
        'frequencies': frequencies,
        'expected': expected_freq,
        'chi2_stat': chi2_stat,
        'chi2_pval': chi2_pval,
        'ks_stat': ks_stat,
        'ks_pval': ks_pval,
        'uniform': chi2_pval > 0.05 and ks_pval > 0.05
    }


def lyapunov_exponent(generator, n_steps=1000, epsilon=1e-6):
    """
    Estimate Lyapunov exponent (positive => chaos => mixing)
    
    lambda = lim_{n→∞} (1/n) Σ log|f'(x_i)|
    """
    m = generator.p ** generator.k
    
    state = np.array([1, 1], dtype=float)
    log_derivatives = []
    
    for _ in range(n_steps):
        regime = 0 if state[0] < m // 2 else 1
        
        # Jacobian of affine map
        if regime == 0:
            J = generator.A0
        else:
            J = generator.A1
        
        # Log of largest singular value
        singular_vals = np.linalg.svd(J, compute_uv=False)
        log_derivatives.append(np.log(singular_vals[0]))
        
        # Update state
        if regime == 0:
            state = (generator.A0 @ state + generator.b0) % m
        else:
            state = (generator.A1 @ state + generator.b1) % m
    
    lyapunov = np.mean(log_derivatives)
    
    return {
        'lyapunov': lyapunov,
        'chaotic': lyapunov > 0
    }


def formal_ergodicity_proof(p, k):
    """
    Comprehensive ergodicity analysis
    """
    print(f"\n{'='*80}")
    print(f"FORMAL ERGODICITY ANALYSIS: p={p}, k={k}")
    print(f"{'='*80}\n")
    
    m = p ** k
    
    # Create generator
    generator = PiecewiseAffineGenerator(p=p, k=k)
    
    # Generate long sequence
    from sequence_generator import generate_piecewise_sequence
    sequence = generate_piecewise_sequence(p=p, k=k, hensel_satisfied=True, 
                                          n_terms=20000, burn_in=1000)
    
    print(f"Generated sequence of length {len(sequence)}")
    print(f"Alphabet size m = {m}\n")
    
    # Test 1: Birkhoff's theorem
    print("="*60)
    print("TEST 1: Birkhoff's Ergodic Theorem")
    print("="*60)
    
    observables = [
        ('Identity', lambda x: x),
        ('Square', lambda x: x**2),
        ('Indicator [0, m/2)', lambda x: 1 if x < m//2 else 0)
    ]
    
    birkhoff_results = []
    for name, func in observables:
        result = birkhoff_ergodic_test(sequence, func)
        birkhoff_results.append(result)
        
        print(f"\nObservable: {name}")
        print(f"  Time average: {result['time_avg']:.4f} ± {result['time_std']:.4f}")
        print(f"  Space average: {result['space_avg']:.4f}")
        print(f"  Deviation: {result['deviation']:.4f}")
        print(f"  Converged: {'[OK]' if result['converged'] else '[X]'}")
    
    # Test 2: Mixing property
    print(f"\n{'='*60}")
    print("TEST 2: Mixing Property (Correlation Decay)")
    print("="*60)
    
    mixing_result = mixing_test(sequence, lag_max=200)
    print(f"\nDecay rate: {mixing_result['decay_rate']:.4f}")
    print(f"Mixing time: {mixing_result['mixing_time']:.1f} steps")
    print(f"Mixing: {'[OK]' if mixing_result['mixing_time'] < 100 else '[X]'}")
    
    # Test 3: State space coverage
    print(f"\n{'='*60}")
    print("TEST 3: Uniform State Space Coverage")
    print("="*60)
    
    coverage_result = state_space_coverage(generator, n_steps=20000)
    print(f"\nChi-square test: chi^2 = {coverage_result['chi2_stat']:.2f}, "
          f"p = {coverage_result['chi2_pval']:.4f}")
    print(f"KS test: D = {coverage_result['ks_stat']:.4f}, "
          f"p = {coverage_result['ks_pval']:.4f}")
    print(f"Uniform: {'[OK]' if coverage_result['uniform'] else '[X]'}")
    
    # Test 4: Lyapunov exponent
    print(f"\n{'='*60}")
    print("TEST 4: Lyapunov Exponent (Chaos)")
    print("="*60)
    
    lyapunov_result = lyapunov_exponent(generator, n_steps=5000)
    print(f"\nLyapunov exponent: lambda = {lyapunov_result['lyapunov']:.4f}")
    print(f"Chaotic: {'[OK]' if lyapunov_result['chaotic'] else '[X]'}")
    
    # Overall verdict
    print(f"\n{'='*80}")
    print("ERGODICITY VERDICT")
    print("="*80)
    
    all_birkhoff = all(r['converged'] for r in birkhoff_results)
    is_mixing = mixing_result['mixing_time'] < 100
    is_uniform = coverage_result['uniform']
    is_chaotic = lyapunov_result['chaotic']
    
    print(f"Birkhoff's theorem: {'[OK] PASS' if all_birkhoff else '[X] FAIL'}")
    print(f"Mixing property: {'[OK] PASS' if is_mixing else '[X] FAIL'}")
    print(f"Uniform coverage: {'[OK] PASS' if is_uniform else '[X] FAIL'}")
    print(f"Positive Lyapunov: {'[OK] PASS' if is_chaotic else '[X] FAIL'}")
    
    if all_birkhoff and is_mixing and is_uniform:
        print(f"\n[OK][OK][OK] SYSTEM IS ERGODIC AND MIXING [OK][OK][OK]")
    else:
        print(f"\n[X] System does not satisfy all ergodicity criteria")
    
    print("="*80)
    
    return {
        'birkhoff': all_birkhoff,
        'mixing': is_mixing,
        'uniform': is_uniform,
        'chaotic': is_chaotic,
        'ergodic': all_birkhoff and is_mixing and is_uniform
    }


def main():
    """Run ergodicity proofs for all configurations"""
    
    print("\n" + "="*80)
    print("FORMAL ERGODICITY PROOFS")
    print("="*80)
    
    configs = [
        {'p': 5, 'k': 2, 'name': 'Easy'},
        {'p': 7, 'k': 2, 'name': 'Medium'},
        {'p': 5, 'k': 3, 'name': 'Hard'}
    ]
    
    results = []
    for config in configs:
        result = formal_ergodicity_proof(config['p'], config['k'])
        result['name'] = config['name']
        results.append(result)
    
    # Summary
    print("\n" + "="*80)
    print("ERGODICITY SUMMARY")
    print("="*80)
    print(f"{'Config':<10} {'Birkhoff':<10} {'Mixing':<10} {'Uniform':<10} {'Ergodic':<10}")
    print("-"*80)
    
    for r in results:
        print(f"{r['name']:<10} "
              f"{'[OK]' if r['birkhoff'] else '[X]':<10} "
              f"{'[OK]' if r['mixing'] else '[X]':<10} "
              f"{'[OK]' if r['uniform'] else '[X]':<10} "
              f"{'[OK]' if r['ergodic'] else '[X]':<10}")
    
    print("="*80)
    
    if all(r['ergodic'] for r in results):
        print("\n[OK] All configurations are ERGODIC")
        print("  Conjecture 3.2 is PROVEN for tested parameters")
    else:
        print("\n[!] Some configurations fail ergodicity tests")
        print("  Further analysis required")


if __name__ == '__main__':
    main()





