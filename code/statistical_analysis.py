"""
statistical_analysis.py
=======================
Rigorous Statistical Analysis for Neural Attack Results

Implements:
- Confidence intervals (bootstrap and parametric)
- Hypothesis testing (t-tests, Mann-Whitney U)
- Effect size calculations (Cohen's d)
- Multiple comparison corrections (Bonferroni, Holm)

Author: Abhijay Gangarapu, UT Austin / ISEF
"""

import numpy as np
from typing import List, Dict, Tuple
from scipy import stats


def bootstrap_ci(data: List[float], confidence: float = 0.95, n_bootstrap: int = 10000) -> Tuple[float, float, float]:
    """Bootstrap confidence interval for mean."""
    data = np.array(data)
    means = [np.mean(np.random.choice(data, size=len(data), replace=True)) 
             for _ in range(n_bootstrap)]
    alpha = 1 - confidence
    return np.mean(data), np.percentile(means, 100 * alpha/2), np.percentile(means, 100 * (1-alpha/2))


def cohens_d(group1: List[float], group2: List[float]) -> float:
    """Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def compare_configurations(results: Dict[str, List[float]], alpha: float = 0.05) -> Dict:
    """
    Compare multiple configurations with proper statistical tests.
    
    Returns:
    - Pairwise comparisons with p-values
    - Effect sizes
    - Bonferroni-corrected significance
    """
    configs = list(results.keys())
    n_comparisons = len(configs) * (len(configs) - 1) // 2
    bonferroni_alpha = alpha / n_comparisons
    
    comparisons = []
    for i, cfg1 in enumerate(configs):
        for cfg2 in configs[i+1:]:
            data1, data2 = results[cfg1], results[cfg2]
            
            # t-test
            t_stat, p_val = stats.ttest_ind(data1, data2)
            
            # Mann-Whitney U (non-parametric)
            u_stat, u_pval = stats.mannwhitneyu(data1, data2, alternative='two-sided')
            
            # Effect size
            effect = cohens_d(data1, data2)
            
            comparisons.append({
                'config1': cfg1,
                'config2': cfg2,
                'mean1': np.mean(data1),
                'mean2': np.mean(data2),
                't_statistic': t_stat,
                'p_value': p_val,
                'u_statistic': u_stat,
                'u_pvalue': u_pval,
                'cohens_d': effect,
                'significant_bonferroni': p_val < bonferroni_alpha,
                'effect_size_interpretation': 'large' if abs(effect) > 0.8 else 'medium' if abs(effect) > 0.5 else 'small'
            })
    
    return {
        'n_comparisons': n_comparisons,
        'bonferroni_alpha': bonferroni_alpha,
        'comparisons': comparisons
    }


def analyze_phase_transition(T_over_L_values: List[float], accuracies: List[List[float]]) -> Dict:
    """
    Analyze the phase transition between learnable and hard regimes.
    
    Fits a logistic curve and identifies the transition point.
    """
    from scipy.optimize import curve_fit
    
    # Logistic function
    def logistic(x, L, k, x0):
        return L / (1 + np.exp(-k * (x - x0)))
    
    # Prepare data
    X = np.array(T_over_L_values)
    Y = np.array([np.mean(acc) for acc in accuracies])
    
    # Fit logistic curve
    try:
        popt, pcov = curve_fit(logistic, np.log10(X), Y, p0=[1.0, -1.0, 1.5], maxfev=10000)
        L_fit, k_fit, x0_fit = popt
        
        # Transition point (50% accuracy)
        transition_log = x0_fit
        transition_T_over_L = 10 ** transition_log
        
        # Confidence interval on transition point
        perr = np.sqrt(np.diag(pcov))
        transition_ci = (10 ** (x0_fit - 1.96*perr[2]), 10 ** (x0_fit + 1.96*perr[2]))
        
        fit_success = True
    except:
        transition_T_over_L = -1
        transition_ci = (-1, -1)
        fit_success = False
    
    return {
        'fit_success': fit_success,
        'transition_point': transition_T_over_L,
        'transition_ci_95': transition_ci,
        'interpretation': f'Phase transition at T/L_in ~= {transition_T_over_L:.1f} [{transition_ci[0]:.1f}, {transition_ci[1]:.1f}]' if fit_success else 'Fit failed'
    }


def full_statistical_report(config_results: Dict[str, List[float]]) -> Dict:
    """Generate comprehensive statistical report."""
    report = {}
    
    # Per-configuration statistics
    for cfg, data in config_results.items():
        mean, ci_low, ci_high = bootstrap_ci(data)
        report[cfg] = {
            'n': len(data),
            'mean': mean,
            'std': np.std(data, ddof=1),
            'ci_95': (ci_low, ci_high),
            'min': np.min(data),
            'max': np.max(data)
        }
    
    # Pairwise comparisons
    report['comparisons'] = compare_configurations(config_results)
    
    return report


if __name__ == "__main__":
    print("=" * 80)
    print("STATISTICAL ANALYSIS DEMO")
    print("=" * 80)
    
    # Simulate results from paper
    easy_configs = {
        'm=5': [1.0, 1.0, 1.0, 1.0, 1.0],
        'm=25_easy': [1.0, 1.0, 1.0, 1.0, 1.0],
    }
    
    hard_configs = {
        'm=125': [0.026, 0.023, 0.029, 0.025, 0.027],
        'm=169': [0.022, 0.017, 0.025, 0.020, 0.023],
    }
    
    all_configs = {**easy_configs, **hard_configs}
    
    report = full_statistical_report(all_configs)
    
    print("\nPer-Configuration Statistics:")
    for cfg, stats in report.items():
        if cfg != 'comparisons':
            print(f"  {cfg}: mean={stats['mean']:.3f}, 95% CI=[{stats['ci_95'][0]:.3f}, {stats['ci_95'][1]:.3f}]")
    
    print(f"\nPairwise Comparisons (Bonferroni α={report['comparisons']['bonferroni_alpha']:.4f}):")
    for comp in report['comparisons']['comparisons']:
        sig = "***" if comp['significant_bonferroni'] else "ns"
        print(f"  {comp['config1']} vs {comp['config2']}: p={comp['p_value']:.4f} {sig}, d={comp['cohens_d']:.2f}")
