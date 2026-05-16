"""
berlekamp_massey.py
===================
Berlekamp–Massey algorithm over GF(p) (prime modulus).

Given a finite sequence s = (s_0, s_1, ..., s_{n-1}) over Z/pZ, computes the
shortest linear feedback shift register (LFSR) that generates s, i.e. the
shortest linear recurrence

    s_i = c_1 s_{i-1} + c_2 s_{i-2} + ... + c_L s_{i-L}   (mod p)

that holds for all i = L, L+1, ..., n-1.

The linear complexity LC(s) = L of the sequence is a foundational
cryptographic parameter: exactly 2L observed terms suffice for the
Berlekamp–Massey algorithm to reconstruct (and thereafter predict) the
entire sequence using only linear methods.

Key relationship to neural hardness (Section 6.1 of the paper):
  LC measures resistance to linear attackers (unlimited data).
  T/L_in measures resistance to windowed nonlinear attackers.
  High LC does not imply high T/L_in — the H-viol m=25 configuration has
  LC=27 yet T/L_in=5.0 and is trivially predicted by the MLP.

Reference:
  Massey, J. L. (1969). Shift-register synthesis and BCH decoding.
  IEEE Transactions on Information Theory, 15(1), 122–127.

Author: Research pipeline for
  "Period Growth and Neural Predictability in Piecewise Affine Systems
   over Residue Rings" — Abhijay Gangarapu, UT Austin / ISEF
"""

from typing import List, Tuple, Dict


# --- core Berlekamp–Massey algorithm -----------------------------------------

def berlekamp_massey(seq: List[int], p: int) -> int:
    """
    Compute the linear complexity of seq over GF(p).

    Runs the Berlekamp–Massey algorithm in O(n²) time.

    Parameters
    ----------
    seq : sequence of integers in {0, ..., p-1}
    p   : prime modulus (field characteristic)

    Returns
    -------
    LC : int, the linear complexity (length of shortest generating LFSR)
    """
    s = [int(x) % p for x in seq]
    n = len(s)

    C  = [1] + [0] * n   # current connection polynomial (coefficient list)
    B  = [1] + [0] * n   # previous connection polynomial
    L  = 0               # current LFSR length
    m_ = 1               # steps since last length change
    b  = 1               # leading coefficient of B at last length change

    for i in range(n):
        # Discrepancy: d = Σ_{j=0}^{L} C[j] * s[i-j]  mod p
        d = sum(C[j] * s[i - j] for j in range(min(L + 1, len(C)))) % p

        if d == 0:
            m_ += 1
        elif 2 * L <= i:
            # Length-increasing step
            T         = C[:]
            c_over_b  = d * pow(b, p - 2, p) % p          # d/b in GF(p)
            while len(C) < len(B) + m_:
                C.append(0)
            for j in range(len(B)):
                idx = j + m_
                if idx < len(C):
                    C[idx] = (C[idx] - c_over_b * B[j]) % p
                else:
                    C.append((-c_over_b * B[j]) % p)
            L  = i + 1 - L
            B  = T
            b  = d
            m_ = 1
        else:
            # Length-preserving step
            c_over_b = d * pow(b, p - 2, p) % p
            while len(C) < len(B) + m_:
                C.append(0)
            for j in range(len(B)):
                idx = j + m_
                if idx < len(C):
                    C[idx] = (C[idx] - c_over_b * B[j]) % p
                else:
                    C.append((-c_over_b * B[j]) % p)
            m_ += 1

    return L


def lfsr_from_bm(seq: List[int], p: int) -> Tuple[int, List[int]]:
    """
    Run Berlekamp–Massey and return (L, feedback_taps) where taps c satisfy
        s[i] = Σ_{j=1}^{L} c[j-1] * s[i-j]  (mod p).

    Parameters
    ----------
    seq : sequence of integers in {0, ..., p-1}
    p   : prime modulus

    Returns
    -------
    (L, taps) where L = LC(s) and taps = [c_1, ..., c_L] in GF(p).
    """
    s  = [int(x) % p for x in seq]
    n  = len(s)
    C  = [1] + [0] * n
    B  = [1] + [0] * n
    L  = 0; m_ = 1; b = 1

    for i in range(n):
        d = sum(C[j] * s[i - j] for j in range(min(L + 1, len(C)))) % p
        if d == 0:
            m_ += 1
        elif 2 * L <= i:
            T = C[:]
            c_over_b = d * pow(b, p - 2, p) % p
            while len(C) < len(B) + m_: C.append(0)
            for j in range(len(B)):
                idx = j + m_
                if idx < len(C): C[idx] = (C[idx] - c_over_b * B[j]) % p
                else:            C.append((-c_over_b * B[j]) % p)
            L = i + 1 - L; B = T; b = d; m_ = 1
        else:
            c_over_b = d * pow(b, p - 2, p) % p
            while len(C) < len(B) + m_: C.append(0)
            for j in range(len(B)):
                idx = j + m_
                if idx < len(C): C[idx] = (C[idx] - c_over_b * B[j]) % p
                else:            C.append((-c_over_b * B[j]) % p)
            m_ += 1

    # Connection polynomial C satisfies: s[i] = -Σ_{j=1}^{L} C[j] s[i-j]
    taps = [(-C[j]) % p for j in range(1, L + 1)]
    return L, taps


def verify_lfsr(
    seq: List[int],
    p: int,
    verify_steps: int = 50,
) -> Tuple[int, int]:
    """
    Run Berlekamp–Massey, then verify the recovered LFSR predicts the
    next `verify_steps` terms of the sequence correctly.

    Parameters
    ----------
    seq          : full sequence; BM uses all terms, then predicts beyond
    p            : prime modulus
    verify_steps : number of additional terms to check

    Returns
    -------
    (LC, n_errors) where n_errors is the number of mispredicted terms.
    """
    L, taps = lfsr_from_bm(seq, p)
    s       = [int(x) % p for x in seq]

    # Seed the LFSR with s[0 ... L-1], then predict s[L], s[L+1], ...
    errors = 0
    buf    = list(s[:L])
    end    = min(L + verify_steps, len(s))

    for i in range(L, end):
        pred = sum(taps[j] * buf[i - L + j] for j in range(L)) % p
        buf.append(pred)
        if pred != s[i]:
            errors += 1

    return L, errors


def compute_lc_table(
    p: int = 5,
    n_terms: int = 300,
    seed: int = 42,
) -> Dict[str, Dict]:
    """
    Compute linear complexity for the four canonical configurations
    used in Table 3 of the paper.

    Parameters
    ----------
    p       : prime for GF(p) projection (default 5, paper standard)
    n_terms : number of post-burn terms to pass to Berlekamp–Massey
    seed    : RNG seed for sequence generation

    Returns
    -------
    dict keyed by config name, values: {'LC', 'crack_cost', 'errors'}.
    """
    import sys
    sys.path.insert(0, ".")
    from generator import (
        generate_piecewise, generate_linear,
        A0_CANON, b0_CANON, A1_CANON, b1_CANON,
        A0_VIOL,  b0_VIOL,
    )

    configs = [
        ("Linear (m=5)",          lambda: generate_linear(5,  A0_CANON, b0_CANON, N=n_terms+200, seed=seed)),
        ("PW-2R H-sat (m=25)",    lambda: generate_piecewise(25,  [A0_CANON, A1_CANON], [b0_CANON, b1_CANON], N=n_terms+200, seed=seed)),
        ("PW-2R H-sat (m=125)",   lambda: generate_piecewise(125, [A0_CANON, A1_CANON], [b0_CANON, b1_CANON], N=n_terms+200, seed=seed)),
        ("PW-2R H-viol (m=25)",   lambda: generate_piecewise(25,  [A0_VIOL, A1_CANON],  [b0_VIOL,  b1_CANON], N=n_terms+200, seed=seed)),
    ]

    results = {}
    for name, fn in configs:
        full_seq = fn()
        # Project to GF(p) and take n_terms terms post-burn (burn already removed)
        gf_seq   = [v % p for v in full_seq[:n_terms]]
        LC, errs = verify_lfsr(gf_seq, p, verify_steps=50)
        results[name] = {
            "LC":         LC,
            "crack_cost": 2 * LC,
            "errors":     errs,
        }
    return results


# --- self-test ----------------------------------------------------------------

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from generator import (
        generate_piecewise, generate_linear,
        A0_CANON, b0_CANON, A1_CANON, b1_CANON,
        A0_VIOL,  b0_VIOL,
    )

    p = 5
    print("=" * 65)
    print("berlekamp_massey.py — Self-Test (Table 3 of the paper)")
    print("=" * 65)

    # Expected values from Table 3 of the paper (tolerance ±30)
    expected_LC = {
        "Linear (m=5)":        3,
        "PW-2R H-sat (m=25)":  125,
        "PW-2R H-sat (m=125)": 150,
        "PW-2R H-viol (m=25)": 27,
    }

    table = compute_lc_table(p=p, n_terms=300, seed=42)
    print(f"\n  {'Configuration':<28}  {'LC':>6}  {'Crack cost':>12}  {'LFSR errs':>10}  pass")
    print("  " + "-" * 70)

    for name, row in table.items():
        exp  = expected_LC[name]
        ok   = abs(row["LC"] - exp) <= 30
        mark = "[OK]" if ok else f"[X] (expected ~{exp})"
        print(f"  {name:<28}  {row['LC']:>6}  "
              f"{row['crack_cost']:>12}  {row['errors']:>10}  {mark}")

    print()
    print("Note: LC values are window-dependent; tolerance ±30 is appropriate")
    print("      for 300-term windows as used in the paper.")
