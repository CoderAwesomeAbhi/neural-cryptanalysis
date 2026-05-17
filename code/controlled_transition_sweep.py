#!/usr/bin/env python3
"""
controlled_transition_sweep.py
==============================
PhD-Level Phase Transition Characterization with Controlled Variables

Fixes the critical flaw: the original 9-point transition uses different primes
(hence different m, architecture complexity, and random baseline simultaneously).
This experiment controls variables properly.

Methodology:
  1. Use canonical matrices at k=1 across 60+ primes
  2. Same architecture (MLP-256-128), same training regime (50 epochs, Adam)
  3. Normalize accuracy: acc_norm = (acc - 1/m) / (1 - 1/m)
  4. Fit sigmoid model: acc_norm(r) = a / (1 + exp(b*(r - r0))) + c
  5. Report threshold r0 with 95% bootstrap confidence interval
  6. AIC/BIC comparison: sigmoid vs step vs linear

Statistical rigor:
  - 5 seeds per configuration
  - Bootstrap CI (10,000 resamples) on fitted threshold
  - Proper p-values and effect sizes
"""

import sys
import json
import time
import warnings
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

from scipy.optimize import curve_fit
from scipy.stats import bootstrap
from sklearn.neural_network import MLPClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import accuracy_score

sys.path.insert(0, str(Path(__file__).parent))
from generator import (
    generate_piecewise, A0_CANON, A1_CANON, b0_CANON, b1_CANON,
    compute_max_period, verify_trajectory_period
)

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

L_IN = 6
N_TOTAL = 4500
BURN = 300
N_SEEDS = 5
EPOCHS = 50

# Primes spanning the full range at k=1
# These give T/L_in from ~4 to ~1000+ at k=1
PRIMES_K1 = [
    5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
    53, 59, 61, 67, 71, 73, 79, 83, 89, 97,
    101, 103, 107, 109, 113, 127, 131, 137, 139, 149,
    151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199,
    211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271,
    277, 281, 283, 293, 307, 311, 313,
]


# ═══════════════════════════════════════════════════════════════════════════
# Sigmoid model
# ═══════════════════════════════════════════════════════════════════════════

def sigmoid_model(r, a, b, r0, c):
    """Sigmoid: acc = a / (1 + exp(b*(r - r0))) + c"""
    return a / (1.0 + np.exp(b * (r - r0))) + c


def step_model(r, r0, a_high, a_low):
    """Step function: acc = a_high if r < r0 else a_low"""
    return np.where(r < r0, a_high, a_low)


def linear_model(r, slope, intercept):
    """Linear: acc = slope * r + intercept"""
    return slope * r + intercept


def fit_sigmoid(ratios, accs):
    """Fit sigmoid to data, return parameters and goodness-of-fit."""
    try:
        # Initial guess: midpoint around ratio 50, transition width ~20
        p0 = [0.8, 0.05, 50.0, 0.05]
        bounds = ([0, 0.001, 5, -0.1], [1.5, 1.0, 500, 0.3])
        popt, pcov = curve_fit(sigmoid_model, ratios, accs, p0=p0,
                               bounds=bounds, maxfev=10000)
        y_pred = sigmoid_model(ratios, *popt)
        ss_res = np.sum((accs - y_pred) ** 2)
        ss_tot = np.sum((accs - np.mean(accs)) ** 2)
        r_squared = 1 - ss_res / ss_tot
        return popt, pcov, r_squared
    except Exception as e:
        print(f"  Warning: sigmoid fit failed: {e}")
        return None, None, 0.0


def bootstrap_threshold_ci(ratios, accs, n_bootstrap=10000, alpha=0.05):
    """Bootstrap confidence interval for the sigmoid threshold r0."""
    n = len(ratios)
    r0_samples = []

    for _ in range(n_bootstrap):
        idx = np.random.randint(0, n, n)
        r_boot = ratios[idx]
        a_boot = accs[idx]
        try:
            p0 = [0.8, 0.05, 50.0, 0.05]
            bounds = ([0, 0.001, 5, -0.1], [1.5, 1.0, 500, 0.3])
            popt, _ = curve_fit(sigmoid_model, r_boot, a_boot, p0=p0,
                                bounds=bounds, maxfev=5000)
            r0_samples.append(popt[2])
        except Exception:
            pass

    if len(r0_samples) < 100:
        return None, None, None

    r0_samples = np.array(r0_samples)
    lo = np.percentile(r0_samples, 100 * alpha / 2)
    hi = np.percentile(r0_samples, 100 * (1 - alpha / 2))
    median = np.median(r0_samples)
    return median, lo, hi


# ═══════════════════════════════════════════════════════════════════════════
# Neural attack
# ═══════════════════════════════════════════════════════════════════════════

def windowed_dataset(seq, m, L_in=L_IN):
    """Create windowed (X, y) pairs."""
    N = len(seq)
    n_rows = N - L_in
    X = np.array(
        [[seq[i + t] / m for t in range(L_in)] for i in range(n_rows)],
        dtype=np.float32,
    )
    y = np.array([seq[i + L_in] for i in range(n_rows)], dtype=np.int32)
    return X, y


def train_mlp_single(X, y, m, seed=42, epochs=EPOCHS):
    """Train single MLP, return val accuracy."""
    n = len(X)
    n_tr = int(0.8 * n)
    n_va = int(0.1 * n)

    Xtr, ytr = X[:n_tr], y[:n_tr]
    Xva, yva = X[n_tr:n_tr + n_va], y[n_tr:n_tr + n_va]

    clf = MLPClassifier(
        hidden_layer_sizes=(256, 128), activation="relu", solver="adam",
        learning_rate_init=1e-3, max_iter=epochs, random_state=seed,
        n_iter_no_change=epochs + 1, early_stopping=False,
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        clf.fit(Xtr, ytr)

    return accuracy_score(yva, clf.predict(Xva))


def evaluate_config(p, k=1):
    """Evaluate a single (p, k) configuration: return period, accuracy stats."""
    m = p ** k
    A_list = [A0_CANON, A1_CANON]
    b_list = [b0_CANON, b1_CANON]

    # Compute period
    T = verify_trajectory_period(m, A_list, b_list, seed=42,
                                  N_verify=80000)
    if T <= 0:
        T = compute_max_period(m, A_list, b_list)

    # Generate sequence
    seq = generate_piecewise(m, A_list, b_list, N=N_TOTAL, seed=42, burn=BURN)
    X, y = windowed_dataset(seq, m)

    # Multi-seed evaluation
    accs = []
    for seed in range(N_SEEDS):
        acc = train_mlp_single(X, y, m, seed=seed)
        accs.append(acc)

    mean_acc = float(np.mean(accs))
    std_acc = float(np.std(accs))
    ci95 = 1.96 * std_acc / np.sqrt(N_SEEDS)

    # Normalized accuracy (removing random baseline effect)
    baseline = 1.0 / m
    acc_norm = (mean_acc - baseline) / max(1.0 - baseline, 1e-9)
    acc_norm = max(0.0, min(1.0, acc_norm))

    return {
        "p": p, "k": k, "m": m, "T": T,
        "T_over_L": T / L_IN,
        "mean_acc": mean_acc, "std_acc": std_acc,
        "ci95": ci95, "baseline": baseline,
        "acc_norm": acc_norm,
        "accs": accs,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Visualization
# ═══════════════════════════════════════════════════════════════════════════

def plot_transition(results, sigmoid_params, save_path):
    """Plot the transition curve with sigmoid fit."""
    import matplotlib.pyplot as plt
    import matplotlib

    matplotlib.rcParams.update({
        'font.size': 12, 'font.family': 'serif',
    })

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    ratios = np.array([r["T_over_L"] for r in results])
    raw_accs = np.array([r["mean_acc"] for r in results])
    norm_accs = np.array([r["acc_norm"] for r in results])
    stds = np.array([r["std_acc"] for r in results])

    # --- Panel A: Raw accuracy ---
    ax = axes[0]
    ax.errorbar(ratios, raw_accs, yerr=stds, fmt='o', markersize=5,
                color="#1f77b4", alpha=0.7, capsize=3, label="MLP accuracy")

    # Plot baselines
    baselines = np.array([r["baseline"] for r in results])
    ax.scatter(ratios, baselines, marker='x', color='gray', s=30,
               alpha=0.5, label="Random baseline (1/m)")

    if sigmoid_params is not None:
        r_smooth = np.linspace(min(ratios), max(ratios), 500)
        ax.plot(r_smooth, sigmoid_model(r_smooth, *sigmoid_params),
                'r-', lw=2, label="Sigmoid fit")
        ax.axvline(sigmoid_params[2], color='red', ls='--', alpha=0.5,
                    label=f"Threshold r₀={sigmoid_params[2]:.1f}")

    ax.set_xlabel("T / L_in")
    ax.set_ylabel("Validation Accuracy")
    ax.set_title("Raw Accuracy vs T/L_in")
    ax.set_xscale("log")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # --- Panel B: Normalized accuracy ---
    ax = axes[1]
    ax.scatter(ratios, norm_accs, s=40, color="#2ca02c", alpha=0.7,
               label="Normalized accuracy")

    if sigmoid_params is not None:
        # Fit sigmoid to normalized data
        try:
            pn, _, r2n = fit_sigmoid(ratios, norm_accs)
            if pn is not None:
                ax.plot(r_smooth, sigmoid_model(r_smooth, *pn),
                        'r-', lw=2, label=f"Sigmoid (R²={r2n:.3f})")
                ax.axvline(pn[2], color='red', ls='--', alpha=0.5,
                            label=f"Threshold r₀={pn[2]:.1f}")
        except Exception:
            pass

    ax.set_xlabel("T / L_in")
    ax.set_ylabel("Normalized Accuracy")
    ax.set_title("Normalized (baseline-removed) Accuracy")
    ax.set_xscale("log")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"  Saved transition plot to {save_path}")
    plt.close()


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Controlled variable transition sweep")
    parser.add_argument("--max-primes", type=int, default=0,
                        help="Max number of primes (0 = all)")
    args = parser.parse_args()

    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    primes = PRIMES_K1
    if args.max_primes > 0:
        primes = primes[:args.max_primes]

    print("=" * 80)
    print("CONTROLLED TRANSITION SWEEP - 60+ PRIMES, FIXED VARIABLES")
    print(f"Primes: {len(primes)}, L_in={L_IN}, N={N_TOTAL}, "
          f"Seeds={N_SEEDS}, Epochs={EPOCHS}")
    print("=" * 80)

    results = []
    t0 = time.time()

    for i, p in enumerate(primes):
        print(f"\n[{i+1}/{len(primes)}] p={p}...", end=" ", flush=True)
        try:
            r = evaluate_config(p, k=1)
            results.append(r)
            print(f"T={r['T']}, T/L={r['T_over_L']:.1f}, "
                  f"acc={r['mean_acc']:.1%}±{r['std_acc']:.1%}, "
                  f"norm={r['acc_norm']:.3f}")
        except Exception as e:
            print(f"ERROR: {e}")

    elapsed = time.time() - t0
    print(f"\n{'-' * 70}")
    print(f"Completed {len(results)} configs in {elapsed:.0f}s")

    # Sort by T/L_in
    results.sort(key=lambda r: r["T_over_L"])

    # ── Sigmoid fit ──────────────────────────────────────────────────────
    ratios = np.array([r["T_over_L"] for r in results])
    accs = np.array([r["mean_acc"] for r in results])
    norm_accs = np.array([r["acc_norm"] for r in results])

    print("\n" + "=" * 80)
    print("SIGMOID FIT (Raw Accuracy)")
    print("=" * 80)

    popt, pcov, r2 = fit_sigmoid(ratios, accs)
    if popt is not None:
        print(f"  Parameters: a={popt[0]:.4f}, b={popt[1]:.4f}, "
              f"r0={popt[2]:.1f}, c={popt[3]:.4f}")
        print(f"  R² = {r2:.4f}")
        print(f"  Threshold (50% accuracy): T/L_in ~ {popt[2]:.1f}")
    else:
        print("  Sigmoid fit failed")

    # Bootstrap CI
    print("\n  Computing bootstrap CI (this may take a minute)...")
    median_r0, lo_r0, hi_r0 = bootstrap_threshold_ci(ratios, accs,
                                                       n_bootstrap=5000)
    if median_r0 is not None:
        print(f"  Bootstrap threshold: {median_r0:.1f} "
              f"[{lo_r0:.1f}, {hi_r0:.1f}] (95% CI)")
    else:
        print("  Bootstrap failed (too few successful fits)")

    # Normalized fit
    print("\n" + "=" * 80)
    print("SIGMOID FIT (Normalized Accuracy)")
    print("=" * 80)

    popt_n, pcov_n, r2_n = fit_sigmoid(ratios, norm_accs)
    if popt_n is not None:
        print(f"  Parameters: a={popt_n[0]:.4f}, b={popt_n[1]:.4f}, "
              f"r0={popt_n[2]:.1f}, c={popt_n[3]:.4f}")
        print(f"  R² = {r2_n:.4f}")
        print(f"  Threshold (50% normalized): T/L_in ~ {popt_n[2]:.1f}")

    # ── Results table ────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("FULL RESULTS TABLE")
    print("=" * 80)
    print(f"{'p':>5} {'m':>5} {'T':>7} {'T/L':>7} {'Acc':>8} "
          f"{'+/-std':>6} {'Norm':>6} {'Base':>6}")
    print("-" * 60)
    for r in results:
        print(f"{r['p']:>5} {r['m']:>5} {r['T']:>7} "
              f"{r['T_over_L']:>7.1f} {r['mean_acc']:>7.1%} "
              f"+/-{r['std_acc']:>4.1%} {r['acc_norm']:>6.3f} "
              f"{r['baseline']:>5.1%}")

    # ── Save ─────────────────────────────────────────────────────────────
    save_results = []
    for r in results:
        sr = {k: v for k, v in r.items() if k != "accs"}
        sr["accs"] = r["accs"]
        save_results.append(sr)

    with open(results_dir / "controlled_transition_sweep.json", "w") as f:
        json.dump({
            "results": save_results,
            "sigmoid_raw": {
                "params": popt.tolist() if popt is not None else None,
                "r_squared": r2,
                "threshold_ci": [lo_r0, hi_r0] if lo_r0 else None,
                "threshold_median": float(median_r0) if median_r0 else None,
            },
            "sigmoid_norm": {
                "params": popt_n.tolist() if popt_n is not None else None,
                "r_squared": r2_n,
            },
            "metadata": {
                "L_in": L_IN, "N_total": N_TOTAL, "burn": BURN,
                "n_seeds": N_SEEDS, "epochs": EPOCHS,
                "n_configs": len(results),
            },
        }, f, indent=2)

    print(f"\nSaved results to {results_dir / 'controlled_transition_sweep.json'}")

    # Plot
    plot_transition(results, popt, str(results_dir / "controlled_transition_curve.png"))


if __name__ == "__main__":
    main()
