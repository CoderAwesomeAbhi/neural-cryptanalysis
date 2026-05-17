"""
Empirical ergodicity diagnostics (not a formal proof).

Checks:
1. Exact bijectivity on finite state space (measure-preserving proxy).
2. Time-average vs space-average agreement (Birkhoff-style diagnostics).
3. Lagged mixing decay via indicator correlations.
4. Marginal entropy and transition coverage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

from generator import generate_piecewise, get_matrices


State = Tuple[int, int]


def step(x: np.ndarray, m: int, A_list: Sequence[np.ndarray], b_list: Sequence[np.ndarray]) -> np.ndarray:
    r = len(A_list)
    regime = int(x[0]) % r
    return (A_list[regime] @ x + b_list[regime]) % m


def finite_map_table(m: int, A_list: Sequence[np.ndarray], b_list: Sequence[np.ndarray]) -> Dict[State, State]:
    table: Dict[State, State] = {}
    for a in range(m):
        for b in range(m):
            x = np.array([a, b], dtype=np.int64)
            y = step(x, m, A_list, b_list)
            table[(a, b)] = (int(y[0]), int(y[1]))
    return table


def exact_bijectivity_check(m: int, A_list: Sequence[np.ndarray], b_list: Sequence[np.ndarray]) -> bool:
    table = finite_map_table(m, A_list, b_list)
    image = set(table.values())
    return len(image) == m * m


def simulate_states(m: int, A_list: Sequence[np.ndarray], b_list: Sequence[np.ndarray], n_steps: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = rng.integers(0, m, size=2, dtype=np.int64)
    traj = np.empty((n_steps, 2), dtype=np.int64)
    for i in range(n_steps):
        traj[i] = x
        x = step(x, m, A_list, b_list)
    return traj


def space_average_observable(m: int, fn) -> float:
    vals = []
    for a in range(m):
        for b in range(m):
            vals.append(float(fn((a, b))))
    return float(np.mean(vals))


def birkhoff_diagnostics(m: int, A_list: Sequence[np.ndarray], b_list: Sequence[np.ndarray], n_steps: int, n_seeds: int) -> Dict[str, Dict[str, float]]:
    observables = {
        "x0_norm": lambda s: s[0] / (m - 1 if m > 1 else 1),
        "x1_norm": lambda s: s[1] / (m - 1 if m > 1 else 1),
        "halfspace": lambda s: 1.0 if s[0] < (m // 2) else 0.0,
        "diag_band": lambda s: 1.0 if abs(s[0] - s[1]) <= max(1, m // 8) else 0.0,
    }

    out: Dict[str, Dict[str, float]] = {}
    for name, fn in observables.items():
        space_avg = space_average_observable(m, fn)
        time_avgs = []
        for seed in range(n_seeds):
            traj = simulate_states(m, A_list, b_list, n_steps=n_steps, seed=seed + 1000)
            vals = [fn((int(s[0]), int(s[1]))) for s in traj]
            time_avgs.append(float(np.mean(vals)))
        out[name] = {
            "space_avg": space_avg,
            "time_avg_mean": float(np.mean(time_avgs)),
            "time_avg_std": float(np.std(time_avgs)),
            "abs_gap": float(abs(np.mean(time_avgs) - space_avg)),
        }
    return out


def mixing_decay(m: int, A_list: Sequence[np.ndarray], b_list: Sequence[np.ndarray], n_steps: int, lags: Sequence[int], seed: int) -> Dict[int, float]:
    traj = simulate_states(m, A_list, b_list, n_steps=n_steps + max(lags) + 1, seed=seed)
    a = (traj[:, 0] < (m // 2)).astype(np.float64)
    b = (traj[:, 1] < (m // 2)).astype(np.float64)
    a = a - np.mean(a)
    b = b - np.mean(b)
    denom = (np.std(a) * np.std(b)) + 1e-12
    out = {}
    for lag in lags:
        corr = float(np.mean(a[:-lag] * b[lag:]) / denom)
        out[int(lag)] = corr
    return out


def symbolic_quality(m: int, A_list: Sequence[np.ndarray], b_list: Sequence[np.ndarray], n_steps: int, seed: int) -> Dict[str, float]:
    seq = np.array(generate_piecewise(m, A_list, b_list, N=n_steps + 300, burn=300, seed=seed), dtype=np.int64)
    hist = np.bincount(seq, minlength=m).astype(np.float64)
    probs = hist / np.sum(hist)
    entropy = float(-np.sum(np.where(probs > 0, probs * np.log2(probs), 0.0)))
    entropy_norm = entropy / np.log2(m)

    # 2-gram coverage
    grams = set((int(seq[i]), int(seq[i + 1])) for i in range(len(seq) - 1))
    coverage = len(grams) / float(m * m)
    return {"entropy_norm": entropy_norm, "bigram_coverage": coverage}


def run_suite(p: int, k: int, config: str, n_steps: int, n_seeds: int) -> Dict[str, object]:
    m = p ** k
    A_list_int, b_list_int = get_matrices(config)
    A_list = [a % m for a in A_list_int]
    b_list = [b % m for b in b_list_int]

    bijective = exact_bijectivity_check(m, A_list, b_list)
    birkhoff = birkhoff_diagnostics(m, A_list, b_list, n_steps=n_steps, n_seeds=n_seeds)
    mixing = mixing_decay(m, A_list, b_list, n_steps=n_steps, lags=[1, 2, 5, 10, 20, 50, 100], seed=42)
    quality = symbolic_quality(m, A_list, b_list, n_steps=n_steps, seed=42)

    return {
        "p": p,
        "k": k,
        "m": m,
        "config": config,
        "bijective_finite_map": bijective,
        "birkhoff": birkhoff,
        "mixing_correlations": mixing,
        "symbolic_quality": quality,
        "disclaimer": "Empirical diagnostics only; not a formal ergodicity proof.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Empirical ergodicity diagnostics")
    parser.add_argument("--pairs", nargs="+", default=["5:2:sat", "7:2:sat", "5:2:viol"], help="Format p:k:config")
    parser.add_argument("--n-steps", type=int, default=10000)
    parser.add_argument("--n-seeds", type=int, default=20)
    parser.add_argument("--out", default="results/ergodicity_diagnostics.json")
    args = parser.parse_args()

    results: List[Dict[str, object]] = []
    for spec in args.pairs:
        p_str, k_str, cfg = spec.split(":")
        p = int(p_str)
        k = int(k_str)
        res = run_suite(p=p, k=k, config=cfg, n_steps=args.n_steps, n_seeds=args.n_seeds)
        results.append(res)
        print(
            f"p={p}, k={k}, cfg={cfg} | bijective={res['bijective_finite_map']} | "
            f"H/Hmax={res['symbolic_quality']['entropy_norm']:.3f} | "
            f"2gram_cov={res['symbolic_quality']['bigram_coverage']:.3f}"
        )

    out_path = Path(__file__).resolve().parents[1] / args.out
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
