"""
core.py — Shared generator, period computation, and configuration definitions.
All experiments import from here for reproducibility.
"""

import numpy as np
from itertools import islice

# ─────────────────────────────────────────────────────────────
# Canonical matrices (same for all primes, reduced mod p)
# ─────────────────────────────────────────────────────────────
A0_BASE = np.array([[1, 1], [3, 1]], dtype=np.int64)
A1_BASE = np.array([[3, 3], [1, 3]], dtype=np.int64)
b0_BASE = np.array([1, 2], dtype=np.int64)
b1_BASE = np.array([2, 1], dtype=np.int64)

A0_VIOL_BASE = np.array([[2, 1], [1, 2]], dtype=np.int64)
b0_VIOL_BASE = np.array([3, 4], dtype=np.int64)

CONFIGS = {
    # (p, k, sat/viol)
    "p5k1sat":  dict(p=5,  k=1, m=5,   sat=True),
    "p5k2sat":  dict(p=5,  k=2, m=25,  sat=True),
    "p5k3sat":  dict(p=5,  k=3, m=125, sat=True),
    "p5k2viol": dict(p=5,  k=2, m=25,  sat=False),
    "p7k1sat":  dict(p=7,  k=1, m=7,   sat=True),
    "p7k2sat":  dict(p=7,  k=2, m=49,  sat=True),
    "p7k3sat":  dict(p=7,  k=3, m=343, sat=True),
    "p7k2viol": dict(p=7,  k=2, m=49,  sat=False),
}


def make_matrices(m: int, sat: bool):
    A0 = A0_BASE % m
    A1 = A1_BASE % m
    b0 = b0_BASE % m
    b1 = b1_BASE % m
    if not sat:
        A0 = A0_VIOL_BASE % m
        b0 = b0_VIOL_BASE % m
    return A0, A1, b0, b1


def piecewise_step(x: np.ndarray, m: int, A0, A1, b0, b1) -> np.ndarray:
    if x[0] % 2 == 0:
        return (A0 @ x + b0) % m
    else:
        return (A1 @ x + b1) % m


def generate_sequence(m: int, sat: bool, N: int = 10000,
                       burn: int = 300, seed: int = 42) -> np.ndarray:
    """Return first-component sequence of length N after burn-in."""
    np.random.seed(seed)
    x = np.array([seed % m, (seed + 1) % m], dtype=np.int64)
    A0, A1, b0, b1 = make_matrices(m, sat)
    for _ in range(burn):
        x = piecewise_step(x, m, A0, A1, b0, b1)
    seq = np.empty(N, dtype=np.int64)
    for i in range(N):
        seq[i] = x[0]
        x = piecewise_step(x, m, A0, A1, b0, b1)
    return seq


def find_trajectory_period(seq: np.ndarray, max_T: int = 50000) -> int:
    """Find minimal period T of a sequence by brute-force match."""
    n = len(seq)
    for T in range(1, min(max_T, n // 2)):
        if np.all(seq[:30] == seq[T:T + 30]):
            # Verify over longer span
            L = min(n - T, 200)
            if np.all(seq[:L] == seq[T:T + L]):
                return T
    return -1  # not found


def compute_hensel_index(m: int, sat: bool) -> int:
    """Return min Hensel index over regime matrices (0 = satisfied)."""
    A0, A1, _, _ = make_matrices(m, sat)
    p = None
    # Find p from m
    for pp in range(2, 20):
        mm = pp
        for _ in range(10):
            if mm == m:
                p = pp
                break
            mm *= pp
        if p is not None:
            break
    if p is None:
        return -1
    d0 = int(np.round(np.linalg.det(A0.astype(float) - np.eye(2)))) % m
    d1 = int(np.round(np.linalg.det(A1.astype(float) - np.eye(2)))) % m
    idx0 = 0 if d0 % p != 0 else 1
    idx1 = 0 if d1 % p != 0 else 1
    return max(idx0, idx1)
