"""
Neural threshold derivation from coverage bounds + empirical gradient constant.

This script implements:
1. A provable transition-coverage accuracy upper bound.
2. A fitted gradient-memorization constant c_grad from observed accuracies.
3. Operational threshold estimates T_crit = N_train / c_grad.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np


DATA_POINTS: List[Dict[str, float]] = [
    # name, alphabet m, period T, context L, train N, observed acc
    {"name": "PW-3R m=35", "m": 35, "T": 10, "L": 6, "N": 3600, "acc": 1.000},
    {"name": "Linear m=5", "m": 5, "T": 25, "L": 6, "N": 3600, "acc": 1.000},
    {"name": "H-viol m=25", "m": 25, "T": 30, "L": 6, "N": 3600, "acc": 1.000},
    {"name": "H-sat m=25", "m": 25, "T": 125, "L": 6, "N": 3600, "acc": 1.000},
    {"name": "H-sat m=49", "m": 49, "T": 1083, "L": 6, "N": 3600, "acc": 0.163},
    {"name": "H-sat m=121", "m": 121, "T": 4912, "L": 6, "N": 3600, "acc": 0.073},
    {"name": "H-sat m=125", "m": 125, "T": 7295, "L": 6, "N": 3600, "acc": 0.026},
    {"name": "H-sat m=169", "m": 169, "T": 20475, "L": 6, "N": 3600, "acc": 0.022},
]


def coverage_upper_bound(n_train: float, period: float, m: float) -> float:
    """Provable transition-coverage upper bound."""
    coverage = min(1.0, n_train / period)
    return (1.0 / m) + (1.0 - 1.0 / m) * coverage


def gradient_memorization_model(rho: np.ndarray, m: np.ndarray, c_grad: float) -> np.ndarray:
    """
    Empirical model:
    Acc(rho) = 1/m + (1 - 1/m) * (1 - exp(-rho / c_grad)).
    """
    return (1.0 / m) + (1.0 - 1.0 / m) * (1.0 - np.exp(-rho / c_grad))


def fit_c_grad(points: List[Dict[str, float]]) -> float:
    """Grid-search fit for c_grad minimizing MSE."""
    rho = np.array([p["N"] / p["T"] for p in points], dtype=np.float64)
    m = np.array([p["m"] for p in points], dtype=np.float64)
    y = np.array([p["acc"] for p in points], dtype=np.float64)

    grid = np.linspace(0.25, 80.0, 4000)
    losses = []
    for c in grid:
        pred = gradient_memorization_model(rho, m, c)
        losses.append(float(np.mean((pred - y) ** 2)))
    best_idx = int(np.argmin(losses))
    return float(grid[best_idx])


def derive_threshold(c_grad: float, n_train: int, l_in: int) -> Dict[str, float]:
    t_crit = n_train / c_grad
    return {
        "c_grad": c_grad,
        "t_crit": t_crit,
        "t_over_l_crit": t_crit / l_in,
    }


def build_report(points: List[Dict[str, float]], c_grad: float) -> Dict[str, object]:
    rows = []
    for p in points:
        rho = p["N"] / p["T"]
        cov = coverage_upper_bound(p["N"], p["T"], p["m"])
        pred = float(gradient_memorization_model(np.array([rho]), np.array([p["m"]]), c_grad)[0])
        rows.append(
            {
                "name": p["name"],
                "m": p["m"],
                "T": p["T"],
                "L": p["L"],
                "N": p["N"],
                "rho": rho,
                "observed_acc": p["acc"],
                "coverage_upper_bound": cov,
                "fitted_model_acc": pred,
            }
        )

    thresholds = derive_threshold(c_grad=c_grad, n_train=3600, l_in=6)
    return {
        "model": "coverage_bound + empirical_gradient_constant",
        "notes": "c_grad is fitted from data, not a theorem.",
        "thresholds_baseline": thresholds,
        "rows": rows,
    }


def save_plot(points: List[Dict[str, float]], c_grad: float, out_file: Path) -> None:
    rho = np.array([p["N"] / p["T"] for p in points], dtype=np.float64)
    m = np.array([p["m"] for p in points], dtype=np.float64)
    y = np.array([p["acc"] for p in points], dtype=np.float64)
    cov = np.array([coverage_upper_bound(p["N"], p["T"], p["m"]) for p in points], dtype=np.float64)

    xs = np.linspace(0.01, max(40.0, float(np.max(rho)) * 1.1), 1000)
    m_ref = 125.0
    ys = gradient_memorization_model(xs, np.full_like(xs, m_ref), c_grad)

    plt.figure(figsize=(9, 6))
    plt.scatter(rho, y, label="Observed accuracy", c="#1f77b4", s=60)
    plt.scatter(rho, cov, label="Coverage upper bound", c="#ff7f0e", marker="x", s=70)
    plt.plot(xs, ys, label=f"Fitted model (m={int(m_ref)}, c_grad={c_grad:.2f})", c="#2ca02c", linewidth=2)
    plt.xscale("log")
    plt.ylim(0.0, 1.05)
    plt.xlabel("Repetition ratio rho = N_train / T")
    plt.ylabel("Accuracy")
    plt.title("Neural threshold: coverage bound and fitted gradient constant")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_file, dpi=200)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive neural threshold constants")
    parser.add_argument("--out-json", default="results/neural_threshold_derivation.json")
    parser.add_argument("--out-plot", default="results/neural_threshold_derivation.png")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_json = root / args.out_json
    out_plot = root / args.out_plot
    out_json.parent.mkdir(exist_ok=True)
    out_plot.parent.mkdir(exist_ok=True)

    c_grad = fit_c_grad(DATA_POINTS)
    report = build_report(DATA_POINTS, c_grad)

    with out_json.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    save_plot(DATA_POINTS, c_grad, out_plot)

    th = report["thresholds_baseline"]
    print(f"Fitted c_grad: {th['c_grad']:.3f}")
    print(f"Baseline T_crit (N=3600): {th['t_crit']:.2f}")
    print(f"Baseline (T/L)_crit (L=6): {th['t_over_l_crit']:.2f}")
    print(f"Saved: {out_json}")
    print(f"Saved: {out_plot}")


if __name__ == "__main__":
    main()
