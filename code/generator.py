"""
generator.py
============
Piecewise Affine Recurrence Generator over Z/mZ.

Implements the state-transition map:

    x_{n+1} = A_{phi(x_n)} * x_n + b_{phi(x_n)}   (mod m)

where phi(x) = x[0] mod r  (first-component parity switching function).

Cross-prime design: all canonical matrix entries are small integers (<= 4),
so the same matrices are used at every prime p in {5, 7, 11, 13} and reduced
to Z/p^kZ at runtime.  This isolates the role of the Hensel condition from
prime-specific arithmetic effects.

Canonical matrices (Section 2.3 of the paper):
----------------------------------------------
Hensel-satisfied (δ(Aᵢ) = 0 for all regimes):
  A0 = [[1,1],[3,1]], b0 = [1,2]     det(A0-I) mod p = -3 mod p
  A1 = [[3,3],[1,3]], b1 = [2,1]     det(A1-I) mod p = 1

Hensel-violated (δ(A0_viol) >= 1):
  A0_viol = [[2,1],[1,2]], b0_viol = [3,4]    det(A0_viol-I) = 0 always

Author: Research pipeline for
  "Period Growth and Neural Predictability in Piecewise Affine Systems
   over Residue Rings" — Abhijay Gangarapu, UT Austin / ISEF
"""

import numpy as np
from math import gcd
from typing import List, Tuple, Dict, Optional
import itertools


# --- canonical matrix definitions -------------------------------------------

# Hensel-satisfied two-regime configuration
# det(A0_CANON - I) = det([[0,1],[3,0]]) = -3     ≠ 0 mod p for p in {5,7,11,13}
# det(A1_CANON - I) = det([[2,3],[1,2]]) =  1     ≠ 0 mod p for all p
A0_CANON = np.array([[1, 1], [3, 1]], dtype=np.int64)
b0_CANON = np.array([1, 2],           dtype=np.int64)
A1_CANON = np.array([[3, 3], [1, 3]], dtype=np.int64)
b1_CANON = np.array([2, 1],           dtype=np.int64)

# Hensel-violated variant for comparison
# det(A0_VIOL - I) = det([[1,1],[1,1]]) = 0       ≡ 0 mod any prime
A0_VIOL  = np.array([[2, 1], [1, 2]], dtype=np.int64)
b0_VIOL  = np.array([3, 4],           dtype=np.int64)

# Three-regime extension (used for PW-3R composite m=35 experiment)
# det(A2_3R) = det([[3,4],[2,3]]) = 9-8 = 1       ≠ 0 mod any prime
A2_3R    = np.array([[3, 4], [2, 3]], dtype=np.int64)
b2_3R    = np.array([1, 1],           dtype=np.int64)

# Primes used in all cross-prime experiments (Section 5 of the paper)
PRIMES: List[int] = [5, 7, 11, 13]

# State dimension throughout all experiments
STATE_DIM: int = 2


# --- arithmetic helpers ------------------------------------------------------

def prime_factorization(n: int) -> List[Tuple[int, int]]:
    """
    Return prime factorization of n as list of (prime, exponent) pairs.
    
    Example: prime_factorization(125) = [(5, 3)]
             prime_factorization(35) = [(5, 1), (7, 1)]
    """
    if n <= 1:
        return []
    factors = []
    d = 2
    while d * d <= n:
        exp = 0
        while n % d == 0:
            n //= d
            exp += 1
        if exp > 0:
            factors.append((d, exp))
        d += 1
    if n > 1:
        factors.append((n, 1))
    return factors


def is_prime_power(m: int) -> Optional[Tuple[int, int]]:
    """
    Check if m = p^k for some prime p and k >= 1.
    
    Returns (p, k) if m is a prime power, None otherwise.
    """
    factors = prime_factorization(m)
    if len(factors) == 1:
        return factors[0]
    return None


def det2x2_mod(A: np.ndarray, m: int) -> int:
    """Determinant of a 2×2 integer matrix modulo m."""
    return int(int(A[0, 0]) * int(A[1, 1]) - int(A[0, 1]) * int(A[1, 0])) % m


def is_invertible_mod(A: np.ndarray, m: int) -> bool:
    """True iff det(A) is coprime to m, i.e. A in GL_d(Z/mZ)."""
    return gcd(det2x2_mod(A, m), m) == 1


def hensel_index(A: np.ndarray, p: int) -> int:
    """
    Compute δ(A) = ν_p(det(A - I)), the p-adic valuation of det(A - I).

    Returns 0  if det(A-I) ≢ 0 (mod p)   [Hensel-satisfied]
    Returns k>=1 if p^k | det(A-I) but p^{k+1} ∤ det(A-I)
    Returns infinity  (represented as 999) if det(A-I) = 0 (practically impossible
              for our matrices away from trivial cases)
    """
    I2 = np.eye(2, dtype=np.int64)
    val = int(det2x2_mod((A - I2).astype(np.int64), p))
    if val != 0:
        return 0
    # Compute actual p-adic valuation of the integer det(A-I)
    raw = int((A[0, 0] - 1) * (A[1, 1] - 1) - A[0, 1] * A[1, 0])
    if raw == 0:
        return 999  # Exactly zero (not a prime-adic question)
    k = 0
    while raw % p == 0:
        raw //= p
        k += 1
    return k


def hensel_satisfied(A: np.ndarray, p: int) -> bool:
    """True iff δ(A) = 0 (Definition 2.2 of the paper)."""
    return hensel_index(A, p) == 0


def hensel_condition(A: np.ndarray, p: int) -> bool:
    """
    Backward-compatible alias used by verification scripts.
    Equivalent to hensel_satisfied(A, p).
    """
    return hensel_satisfied(A, p)


# --- cross-prime matrix accessor ---------------------------------------------

def get_matrices(config: str = "sat") -> Tuple[List[np.ndarray], List[np.ndarray]]:
    """
    Return (A_list, b_list) for 'sat' (Hensel-satisfied) or 'viol' (violated).
    The integer matrices are reduced mod m inside generate_piecewise at runtime,
    so this function returns the canonical integer matrices unchanged.
    """
    if config == "sat":
        return [A0_CANON, A1_CANON], [b0_CANON, b1_CANON]
    elif config == "viol":
        return [A0_VIOL, A1_CANON], [b0_VIOL, b1_CANON]
    elif config == "3r":
        return [A0_CANON, A1_CANON, A2_3R], [b0_CANON, b1_CANON, b2_3R]
    else:
        raise ValueError(f"Unknown config '{config}'. Use 'sat', 'viol', or '3r'.")


def verify_hensel_table() -> Dict:
    """
    Compute the Hensel index table (Table 1 of the paper) for all four primes.

    Returns a dict: {p: {'det_A0': int, 'delta_A0': int,
                          'det_A1': int, 'delta_A1': int,
                          'det_Av': int, 'delta_Av': int}} for p in PRIMES.
    """
    I2 = np.eye(2, dtype=np.int64)
    result = {}
    for p in PRIMES:
        result[p] = {
            "det_A0":   det2x2_mod(A0_CANON - I2, p),
            "delta_A0": hensel_index(A0_CANON, p),
            "det_A1":   det2x2_mod(A1_CANON - I2, p),
            "delta_A1": hensel_index(A1_CANON, p),
            "det_Av":   det2x2_mod(A0_VIOL  - I2, p),
            "delta_Av": hensel_index(A0_VIOL, p),
        }
    return result


# --- sequence generation -----------------------------------------------------

def generate_piecewise(
    m: int,
    A_list: List[np.ndarray],
    b_list: List[np.ndarray],
    N: int = 12000,
    d: int = STATE_DIM,
    seed: int = 42,
    burn: int = 300,
) -> List[int]:
    """
    Generate N terms of the piecewise affine recurrence over Z/mZ.

    State update:  x_{n+1} = A_{phi(x)} * x + b_{phi(x)}  mod m
    Switching fn:  phi(x) = x[0] mod r    (first-component parity)
    Output:        s_n = x_n[0]           (first component)

    Parameters
    ----------
    m     : modulus (any positive integer; need not be prime or prime power)
    A_list: list of r transition matrices; each must lie in GL_d(Z/mZ)
    b_list: list of r shift vectors in (Z/mZ)^d
    N     : total iterations (before discarding burn-in)
    d     : state dimension (must match matrix sizes)
    seed  : RNG seed for initial state x_0 (reproducible across all experiments)
    burn  : number of initial terms discarded to eliminate transient effects

    Returns
    -------
    List[int] of length N - burn, each in {0, ..., m-1}.
    """
    if m <= 1:
        raise ValueError(f"m must be >= 2, got {m}")
    if N <= 0:
        raise ValueError(f"N must be > 0, got {N}")
    if burn < 0:
        raise ValueError(f"burn must be >= 0, got {burn}")
    if burn >= N:
        raise ValueError(f"burn ({burn}) must be smaller than N ({N})")

    r = len(A_list)
    if r == 0:
        raise ValueError("A_list must not be empty")
    if len(b_list) != r:
        raise ValueError("A_list and b_list must have the same length")

    for i, (A, b) in enumerate(zip(A_list, b_list)):
        if A.shape != (d, d):
            raise ValueError(f"A_list[{i}] has shape {A.shape}, expected {(d, d)}")
        if b.shape != (d,):
            raise ValueError(f"b_list[{i}] has shape {b.shape}, expected {(d,)}")
    for i, A in enumerate(A_list):
        if not is_invertible_mod(A, m):
            raise ValueError(f"A_list[{i}] is not invertible mod {m} "
                             f"(det = {det2x2_mod(A, m)}, gcd with m = {gcd(det2x2_mod(A, m), m)})")

    # Reduce matrices and vectors to Z/mZ once at setup time
    A_mods = [(A % m).astype(np.int64) for A in A_list]
    b_mods = [(b % m).astype(np.int64) for b in b_list]

    rng = np.random.default_rng(seed)
    x   = rng.integers(0, m, d).astype(np.int64)

    seq: List[int] = []
    for _ in range(N):
        seq.append(int(x[0]))
        phi = int(x[0]) % r
        x   = (A_mods[phi] @ x + b_mods[phi]) % m

    return seq[burn:]


def generate_linear(
    m: int,
    A: np.ndarray,
    b: np.ndarray,
    N: int = 12000,
    d: int = STATE_DIM,
    seed: int = 42,
    burn: int = 300,
) -> List[int]:
    """
    Generate N terms of the purely linear recurrence x_{n+1} = A*x + b mod m.
    This is the r=1 special case of generate_piecewise.
    """
    return generate_piecewise(m, [A], [b], N=N, d=d, seed=seed, burn=burn)


# --- period computation -------------------------------------------------------

def _apply_map(
    x: Tuple[int, ...],
    A_mods: List[np.ndarray],
    b_mods: List[np.ndarray],
    m: int,
) -> Tuple[int, ...]:
    """Single map application for tuple-based cycle detection."""
    r   = len(A_mods)
    phi = x[0] % r
    xv  = np.array(x, dtype=np.int64)
    xn  = (A_mods[phi] @ xv + b_mods[phi]) % m
    return tuple(int(v) for v in xn)


def compute_period_single(
    m: int,
    A_list: List[np.ndarray],
    b_list: List[np.ndarray],
    x0: Tuple[int, ...],
    method: str = "auto",
) -> int:
    """
    Compute the cycle length of the orbit starting at x0.

    Methods:
      'hash'   : Hash-based detection (O(T) space, O(T) time)
      'floyd'  : Floyd's cycle detection (O(1) space, O(T) time)
      'brent'  : Brent's algorithm (O(1) space, faster than Floyd)
      'auto'   : Choose based on m^d (hash for small, Brent for large)

    Returns the cycle length, or -1 if not found within reasonable limit.
    """
    A_mods = [(A % m).astype(np.int64) for A in A_list]
    b_mods = [(b % m).astype(np.int64) for b in b_list]

    d = len(x0)
    state_space_size = m ** d

    # Auto-select method based on state space size
    if method == "auto":
        method = "hash" if state_space_size <= 10_000 else "brent"

    if method == "hash":
        seen: Dict[Tuple, int] = {}
        x = x0
        limit = min(state_space_size + 10, 10_000_000)
        for step in range(limit):
            if x in seen:
                return step - seen[x]
            seen[x] = step
            x = _apply_map(x, A_mods, b_mods, m)
        return -1

    elif method == "floyd":
        # Floyd's tortoise and hare
        tortoise = x0
        hare = x0
        
        # Phase 1: Find collision point
        while True:
            tortoise = _apply_map(tortoise, A_mods, b_mods, m)
            hare = _apply_map(hare, A_mods, b_mods, m)
            hare = _apply_map(hare, A_mods, b_mods, m)
            if tortoise == hare:
                break
        
        # Phase 2: Find cycle length
        mu = 0
        tortoise = x0
        while tortoise != hare:
            tortoise = _apply_map(tortoise, A_mods, b_mods, m)
            hare = _apply_map(hare, A_mods, b_mods, m)
            mu += 1
        
        # Phase 3: Find period
        lam = 1
        hare = _apply_map(tortoise, A_mods, b_mods, m)
        while tortoise != hare:
            hare = _apply_map(hare, A_mods, b_mods, m)
            lam += 1
        
        return lam

    elif method == "brent":
        # Brent's algorithm (faster than Floyd)
        power = lam = 1
        tortoise = x0
        hare = _apply_map(x0, A_mods, b_mods, m)
        
        # Find period
        while tortoise != hare:
            if power == lam:
                tortoise = hare
                power *= 2
                lam = 0
            hare = _apply_map(hare, A_mods, b_mods, m)
            lam += 1
        
        return lam

    else:
        raise ValueError(f"Unknown method '{method}'. Use 'hash', 'floyd', 'brent', or 'auto'.")


def compute_max_period(
    m: int,
    A_list: List[np.ndarray],
    b_list: List[np.ndarray],
    n_starts: int = 500,
    seed: int = 42,
    exhaustive_threshold: int = 2500,
) -> int:
    """
    Compute the maximum cycle length (state-space maximum period) over all
    starting states (exhaustive for small m^d, random sampling otherwise).

    For m^d <= exhaustive_threshold: enumerates all m^d starting states.
    Otherwise: samples n_starts random starting states.

    Parameters
    ----------
    m                   : modulus
    A_list, b_list      : regime matrices and offsets
    n_starts            : number of random starting states when not exhaustive
    seed                : RNG seed for reproducible sampling
    exhaustive_threshold: m^d threshold below which all states are enumerated

    Returns
    -------
    Maximum cycle length found.
    """
    if m <= 1:
        raise ValueError(f"m must be >= 2, got {m}")
    if not A_list or not b_list:
        raise ValueError("A_list and b_list must not be empty")
    if len(A_list) != len(b_list):
        raise ValueError("A_list and b_list must have the same length")

    d = len(b_list[0])
    if any(len(b) != d for b in b_list):
        raise ValueError("All vectors in b_list must have the same dimension")
    if any(A.shape != (d, d) for A in A_list):
        raise ValueError("All matrices in A_list must have shape (d, d)")

    if m ** d <= exhaustive_threshold:
        starts = list(itertools.product(range(m), repeat=d))
    else:
        rng = np.random.default_rng(seed)
        sampled = {
            tuple(int(v) for v in rng.integers(0, m, d).tolist())
            for _ in range(max(n_starts, 1))
        }
        starts = list(sampled)

    max_T = 0
    for x0 in starts:
        T = compute_period_single(m, A_list, b_list, x0)
        if T > max_T:
            max_T = T
    return max_T


def verify_trajectory_period(
    m: int,
    A_list: List[np.ndarray],
    b_list: List[np.ndarray],
    seed: int = 42,
    burn: int = 300,
    N_verify: int = 80_000,
    check_len: int = 30,
) -> int:
    """
    Verify the trajectory period for the specific starting state produced by
    the given seed, as used in neural experiments.

    Methodology (Appendix B of the paper):
      1. Generate N_verify terms with burn=0 from the given seed.
      2. Find the smallest T >= 1 such that
             s[burn + i] = s[burn + i + T]   for all i in {0, ..., check_len-1}.
         This is the period of the orbit that the neural model actually sees.

    Note: The trajectory period can be smaller than the state-space maximum
    period if seed places the initial state in a non-maximal orbit.
    (Example: p=5, m=25, sat — state-space max = 212, trajectory period = 125.)

    Returns
    -------
    Trajectory period T, or -1 if not found within N_verify/2 steps.
    """
    full_seq = generate_piecewise(m, A_list, b_list, N=N_verify, seed=seed, burn=0)
    s = full_seq  # length N_verify

    max_T = (len(s) - burn) // 2
    for T in range(1, max_T):
        if all(s[burn + i] == s[burn + i + T] for i in range(min(check_len, len(s) - burn - T))):
            return T
    return -1


def compute_cross_prime_periods(
    primes: List[int] = None,
    k_max: int = 3,
    config: str = "sat",
    n_starts: int = 500,
    seed: int = 42,
) -> Dict[int, Dict[int, int]]:
    """
    Compute maximum periods for multiple primes and extension levels.
    
    This is the core function for generating Table 2 (cross-prime period table).
    
    Parameters
    ----------
    primes   : list of primes to test (default: [5, 7, 11, 13])
    k_max    : maximum extension level (default: 3)
    config   : 'sat' or 'viol' (Hensel-satisfied or violated)
    n_starts : number of random starting states for large state spaces
    seed     : RNG seed for reproducibility
    
    Returns
    -------
    Nested dict: {p: {k: T(p^k)}} for each prime p and level k in 1..k_max
    """
    if primes is None:
        primes = PRIMES
    
    A_list, b_list = get_matrices(config)
    results = {}
    
    for p in primes:
        results[p] = {}
        for k in range(1, k_max + 1):
            m = p ** k
            
            # Skip if state space is too large
            if m ** STATE_DIM > 5_000_000:
                results[p][k] = -1  # Mark as not computed
                continue
            
            T = compute_max_period(m, A_list, b_list, n_starts=n_starts, seed=seed)
            results[p][k] = T
            
            print(f"  p={p:2d}, k={k}, m={m:5d}: T = {T:8d}")
    
    return results


class PiecewiseAffineGenerator:
    """
    Convenience wrapper around canonical piecewise-affine configurations.

    This class is used by analysis scripts that need a compact object-style API.
    It delegates all core math to the module-level generator/period functions.
    """

    def __init__(
        self,
        p: int,
        k: int,
        hensel_satisfied: bool = True,
        seed: int = 42,
        n_starts: int = 500,
    ) -> None:
        if p <= 1:
            raise ValueError(f"p must be > 1, got {p}")
        if k <= 0:
            raise ValueError(f"k must be >= 1, got {k}")

        self.p = int(p)
        self.k = int(k)
        self.m = self.p ** self.k
        self.seed = int(seed)
        self.hensel_satisfied = bool(hensel_satisfied)
        self.config = "sat" if self.hensel_satisfied else "viol"
        self.A_list, self.b_list = get_matrices(self.config)
        self.period = compute_max_period(
            self.m,
            self.A_list,
            self.b_list,
            n_starts=n_starts,
            seed=self.seed,
        )

    def generate(self, N: int, burn: int = 0, seed: Optional[int] = None) -> List[int]:
        """
        Generate a first-component output sequence from the configured map.
        """
        return generate_piecewise(
            self.m,
            self.A_list,
            self.b_list,
            N=N,
            seed=self.seed if seed is None else int(seed),
            burn=burn,
        )

# --- self-test ----------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 65)
    print("generator.py — Self-Test")
    print("=" * 65)

    I2 = np.eye(2, dtype=np.int64)
    p  = 5

    # -- Hensel condition verification -----------------------------------------
    print("\n[ Hensel Index Table (all four primes) ]")
    table = verify_hensel_table()
    header = f"  {'p':>3}  {'det(A0-I)':>10}  δ(A0)  {'det(A1-I)':>10}  δ(A1)  {'det(Av-I)':>10}  δ(Av)"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for prime, row in table.items():
        print(f"  {prime:>3}  {row['det_A0']:>10}    {row['delta_A0']}  "
              f"{row['det_A1']:>10}    {row['delta_A1']}  "
              f"{row['det_Av']:>10}  {'>='+str(row['delta_Av']) if row['delta_Av']>0 else '0':>5}")

    # Expected values (from Table 1 of the paper):
    expected = {5: (2, 0, 1, 0, 0), 7: (4, 0, 1, 0, 0),
                11: (8, 0, 1, 0, 0), 13: (10, 0, 1, 0, 0)}
    for prime, row in table.items():
        exp = expected[prime]
        assert row["det_A0"]  == exp[0], f"det(A0-I) mod {prime} mismatch"
        assert row["delta_A0"] == exp[1]
        assert row["det_A1"]  == exp[2]
        assert row["delta_A1"] == exp[3]
        assert row["det_Av"]  == exp[4]
    print("  [OK] All Hensel index values match Table 1 of the paper.")

    # -- Period growth under ring extension (p=5) ------------------------------
    print("\n[ Period Growth: p=5, Hensel-sat vs Hensel-viol ]")
    A_sat,  b_sat  = get_matrices("sat")
    A_viol, b_viol = get_matrices("viol")

    expected_sat  = {1: 25, 2: 212, 3: 7295}
    expected_viol = {1: 3,  2: 30,  3: 469}

    print(f"  {'k':>3}  {'m':>5}  {'T_sat':>8}  {'T_viol':>8}  {'sat/viol':>9}")
    print("  " + "-" * 40)
    for k in [1, 2, 3]:
        m   = p ** k
        T_s = compute_max_period(m, A_sat,  b_sat)
        T_v = compute_max_period(m, A_viol, b_viol)
        assert T_s == expected_sat[k],  f"T_sat(p^{k}) mismatch: got {T_s}"
        assert T_v == expected_viol[k], f"T_viol(p^{k}) mismatch: got {T_v}"
        print(f"  {k:>3}  {m:>5}  {T_s:>8}  {T_v:>8}  {T_s/T_v:>9.2f}×")

    # -- Trajectory period for seed=42 -----------------------------------------
    print("\n[ Trajectory Period Verification: seed=42, burn=300 ]")
    traj_tests = [
        ("sat m=5",   5,   A_sat,  b_sat,  25),
        ("sat m=25",  25,  A_sat,  b_sat,  125),   # ≠ state-space max (212)
        ("sat m=125", 125, A_sat,  b_sat,  7295),
        ("viol m=25", 25,  A_viol, b_viol, 30),
    ]
    for label, m, As, bs, exp_T in traj_tests:
        T = verify_trajectory_period(m, As, bs)
        mark = "[OK]" if T == exp_T else f"[X] (got {T})"
        print(f"  {label:<14} traj T = {T:>6}  (expected {exp_T:>6})  {mark}")

    # -- Sample sequence --------------------------------------------------------
    seq = generate_piecewise(p, A_sat, b_sat, N=320, burn=0)
    print(f"\n[ First 20 terms from sat config, m=5 ]")
    print(f"  {seq[:20]}")
    print("\nAll generator self-tests passed.")
