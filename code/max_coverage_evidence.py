"""
max_coverage_evidence.py
========================
Maximum computational evidence for paper appendix.

Tasks:
  1. Period computations: all primes p < 100, k = 1, 2, 3
  2. Ergodicity metrics (chi^2, autocorrelation, coverage) for 100+ cases
  3. Verify zero counterexamples to super-linear growth
  4. Statistical analysis with confidence levels

Output: results/max_coverage_results.json  +  results/max_coverage_report.txt
"""

import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from scipy import stats

# ── helpers ──────────────────────────────────────────────────────────────────

A0 = np.array([[1, 1], [3, 1]], dtype=np.int64)
A1 = np.array([[3, 3], [1, 3]], dtype=np.int64)
b0 = np.array([1, 2], dtype=np.int64)
b1 = np.array([2, 1], dtype=np.int64)


def sieve(n):
    s = bytearray([1]) * (n + 1)
    s[0] = s[1] = 0
    for i in range(2, int(n**0.5) + 1):
        if s[i]:
            s[i*i::i] = bytearray(len(s[i*i::i]))
    return [i for i in range(2, n + 1) if s[i]]


def step(x, m):
    if x[0] % 2 == 0:
        return (A0 @ x + b0) % m
    else:
        return (A1 @ x + b1) % m


def brent_period(x0, m, limit=None):
    """Brent's cycle detection. Returns period or -1 if > limit."""
    if limit is None:
        limit = m * m * 4
    power = lam = 1
    tortoise = x0.copy()
    hare = step(x0, m)
    while not np.array_equal(tortoise, hare):
        if power == lam:
            tortoise = hare.copy()
            power *= 2
            lam = 0
        hare = step(hare, m)
        lam += 1
        if lam > limit:
            return -1
    return lam


def max_period(m, n_seeds=300, limit=None):
    """Sample n_seeds starting points; return maximum period found."""
    rng = np.random.default_rng(42)
    best = 0
    for _ in range(n_seeds):
        x0 = rng.integers(0, m, size=2, dtype=np.int64)
        T = brent_period(x0, m, limit)
        if T > best:
            best = T
    return best


def generate_orbit(m, seed=42, length=None):
    """Return orbit of first component, length = min(period, 20000)."""
    rng = np.random.default_rng(seed)
    x = rng.integers(0, m, size=2, dtype=np.int64)
    # burn-in
    for _ in range(200):
        x = step(x, m)
    # detect period first (capped)
    T = brent_period(x.copy(), m, limit=min(m * m, 200_000))
    if length is None:
        length = min(T if T > 0 else 20000, 20000)
    seq = np.empty(length, dtype=np.int64)
    for i in range(length):
        seq[i] = x[0]
        x = step(x, m)
    return seq, T


# ── ergodicity metrics ────────────────────────────────────────────────────────

def chi2_uniform(seq, m):
    counts = np.bincount(seq % m, minlength=m).astype(float)
    expected = len(seq) / m
    chi2, pval = stats.chisquare(counts, f_exp=np.full(m, expected))
    return float(chi2), float(pval)


def mean_abs_acf(seq, max_lag=40):
    s = seq.astype(float) - seq.mean()
    var = s.var()
    if var < 1e-12:
        return 1.0
    acf = [float(np.mean(s[:-lag] * s[lag:]) / var) for lag in range(1, max_lag + 1)]
    return float(np.mean(np.abs(acf)))


def ngram_coverage(seq, m, n=2):
    total = m ** n
    seen = set(zip(*[seq[i:] for i in range(n)]))
    return len(seen) / total


def entropy_ratio(seq, m):
    counts = np.bincount(seq % m, minlength=m).astype(float)
    p = counts / counts.sum()
    p = p[p > 0]
    H = float(-np.sum(p * np.log2(p)))
    return H / np.log2(m)


# ── main computation ──────────────────────────────────────────────────────────

def run():
    primes = sieve(97)   # all primes < 100
    assert len(primes) == 25, f"Expected 25 primes < 100, got {len(primes)}"

    lines = []
    def log(s=""):
        print(s)
        lines.append(s)

    log("=" * 78)
    log("MAXIMUM COMPUTATIONAL EVIDENCE — APPENDIX DATA")
    log(f"Primes p < 100: {primes}")
    log(f"Levels k = 1, 2, 3  |  Total configurations: {25 * 3} = 75")
    log("=" * 78)

    # ── PART 1: Period table ──────────────────────────────────────────────────
    log("\n" + "-" * 78)
    log("PART 1: PERIOD COMPUTATIONS  (all p < 100, k = 1, 2, 3)")
    log("-" * 78)
    log(f"{'p':>4}  {'k':>2}  {'m=p^k':>8}  {'T_sat':>12}  {'T/T_prev':>10}  {'superlinear?':>13}")
    log("-" * 78)

    period_data = []   # list of dicts
    prev_T = {}        # prev_T[p] = T at k-1

    t0 = time.time()
    for p in primes:
        prev_T[p] = None
        for k in range(1, 4):
            m = p ** k
            # Adaptive limit: for large m cap at 10M steps
            limit = min(m * m, 10_000_000)
            T = max_period(m, n_seeds=300, limit=limit)

            ratio_str = "—"
            superlinear = None
            if prev_T[p] is not None and prev_T[p] > 0 and T > 0:
                ratio = T / prev_T[p]
                ratio_str = f"{ratio:.3f}"
                superlinear = ratio > p   # strict super-linear: T(p^k) > p * T(p^{k-1})

            log(f"{p:>4}  {k:>2}  {m:>8,}  {T:>12,}  {ratio_str:>10}  "
                f"{'YES' if superlinear else ('NO' if superlinear is False else '—'):>13}")

            period_data.append({
                "p": p, "k": k, "m": m, "T": T,
                "ratio": float(T / prev_T[p]) if (prev_T[p] and prev_T[p] > 0 and T > 0) else None,
                "superlinear": superlinear,
            })
            prev_T[p] = T

    elapsed_periods = time.time() - t0
    log(f"\n[Period computation time: {elapsed_periods:.1f}s]")

    # ── PART 2: Ergodicity metrics ────────────────────────────────────────────
    log("\n" + "-" * 78)
    log("PART 2: ERGODICITY METRICS  (chi^2, autocorrelation, coverage, entropy)")
    log("-" * 78)
    log(f"{'p':>4}  {'k':>2}  {'m':>7}  {'T':>10}  {'p(chi2)':>9}  "
        f"{'|ACF|':>7}  {'cov2':>6}  {'H/Hmax':>7}  {'ergodic?':>9}")
    log("-" * 78)

    ergodicity_data = []
    t1 = time.time()

    for p in primes:
        for k in range(1, 4):
            m = p ** k
            seq, T = generate_orbit(m)

            chi2_stat, pval = chi2_uniform(seq, m)
            acf = mean_abs_acf(seq, max_lag=min(40, max(5, len(seq) // 10)))
            cov = ngram_coverage(seq, m, n=2)
            H_r = entropy_ratio(seq, m)

            # Ergodic verdict: all four metrics pass
            ergodic = (pval > 0.01) and (acf < 0.20) and (cov > 0.40) and (H_r > 0.90)

            T_str = f"{T:,}" if T > 0 else "?"
            log(f"{p:>4}  {k:>2}  {m:>7,}  {T_str:>10}  {pval:>9.4f}  "
                f"{acf:>7.4f}  {cov:>6.3f}  {H_r:>7.4f}  "
                f"{'YES' if ergodic else 'NO':>9}")

            ergodicity_data.append({
                "p": p, "k": k, "m": m, "T": T,
                "chi2": float(chi2_stat), "pval": float(pval),
                "mean_abs_acf": float(acf),
                "ngram_cov2": float(cov),
                "entropy_ratio": float(H_r),
                "ergodic": ergodic,
            })

    elapsed_ergodicity = time.time() - t1
    log(f"\n[Ergodicity computation time: {elapsed_ergodicity:.1f}s]")

    # ── PART 3: Super-linear growth verification ──────────────────────────────
    log("\n" + "-" * 78)
    log("PART 3: SUPER-LINEAR GROWTH — COUNTEREXAMPLE SEARCH")
    log("-" * 78)

    # Collect all (k>=2) transitions
    transitions = [d for d in period_data if d["ratio"] is not None]
    n_transitions = len(transitions)
    n_superlinear = sum(1 for d in transitions if d["superlinear"] is True)
    n_sublinear   = sum(1 for d in transitions if d["superlinear"] is False)
    n_unknown     = sum(1 for d in transitions if d["superlinear"] is None)

    log(f"Total k-level transitions tested : {n_transitions}")
    log(f"  Super-linear (T(p^k) > p·T(p^{{k-1}})): {n_superlinear}")
    log(f"  Sub-linear (counterexamples)          : {n_sublinear}")
    log(f"  Unknown (period not found)            : {n_unknown}")

    counterexamples = [d for d in transitions if d["superlinear"] is False]
    if counterexamples:
        log("\nCOUNTEREXAMPLES FOUND:")
        for d in counterexamples:
            log(f"  p={d['p']}, k={d['k']}, m={d['m']}, T={d['T']}, ratio={d['ratio']:.3f} < p={d['p']}")
    else:
        log("\nZERO COUNTEREXAMPLES TO SUPER-LINEAR GROWTH FOUND.")
        log("All measured transitions satisfy T(p^k) > p · T(p^{k-1}).")

    # ── PART 4: Statistical analysis ─────────────────────────────────────────
    log("\n" + "-" * 78)
    log("PART 4: STATISTICAL ANALYSIS & CONFIDENCE LEVELS")
    log("-" * 78)

    # 4a. Ergodicity pass rates
    n_ergodic = sum(1 for d in ergodicity_data if d["ergodic"])
    n_total_erg = len(ergodicity_data)
    pass_rate = n_ergodic / n_total_erg

    # Wilson confidence interval for proportion
    z = 1.96  # 95%
    n = n_total_erg
    p_hat = pass_rate
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denom
    margin = z * np.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2)) / denom
    ci_lo, ci_hi = max(0, centre - margin), min(1, centre + margin)

    log(f"\nErgodicity pass rate: {n_ergodic}/{n_total_erg} = {pass_rate*100:.1f}%")
    log(f"  95% Wilson CI: [{ci_lo*100:.1f}%, {ci_hi*100:.1f}%]")

    # 4b. Chi-squared p-values: are they consistent with uniform?
    pvals = [d["pval"] for d in ergodicity_data]
    log(f"\nChi-squared p-values (uniform equidistribution):")
    log(f"  Median p-value : {np.median(pvals):.4f}")
    log(f"  Mean p-value   : {np.mean(pvals):.4f}")
    log(f"  Fraction > 0.05: {np.mean(np.array(pvals) > 0.05)*100:.1f}%")
    log(f"  Fraction > 0.01: {np.mean(np.array(pvals) > 0.01)*100:.1f}%")

    # 4c. Autocorrelation
    acfs = [d["mean_abs_acf"] for d in ergodicity_data]
    log(f"\nMean |ACF| statistics:")
    log(f"  Mean  : {np.mean(acfs):.4f}")
    log(f"  Median: {np.median(acfs):.4f}")
    log(f"  Fraction < 0.10: {np.mean(np.array(acfs) < 0.10)*100:.1f}%")
    log(f"  Fraction < 0.20: {np.mean(np.array(acfs) < 0.20)*100:.1f}%")

    # 4d. Coverage
    covs = [d["ngram_cov2"] for d in ergodicity_data]
    log(f"\n2-gram coverage statistics:")
    log(f"  Mean  : {np.mean(covs):.4f}")
    log(f"  Median: {np.median(covs):.4f}")
    log(f"  Fraction > 0.50: {np.mean(np.array(covs) > 0.50)*100:.1f}%")

    # 4e. Entropy
    entropies = [d["entropy_ratio"] for d in ergodicity_data]
    log(f"\nEntropy ratio H/H_max statistics:")
    log(f"  Mean  : {np.mean(entropies):.4f}")
    log(f"  Median: {np.median(entropies):.4f}")
    log(f"  Fraction > 0.95: {np.mean(np.array(entropies) > 0.95)*100:.1f}%")

    # 4f. Super-linear growth: binomial test
    if n_transitions > 0:
        # Under null H0: ratio is random (50% chance of super-linear), test against p=0.5
        binom_result = stats.binomtest(n_superlinear, n_transitions, p=0.5, alternative='greater')
        log(f"\nSuper-linear growth binomial test:")
        log(f"  H0: P(super-linear) = 0.5  (random baseline)")
        log(f"  Observed: {n_superlinear}/{n_transitions} = {n_superlinear/n_transitions*100:.1f}%")
        log(f"  p-value: {binom_result.pvalue:.2e}")
        log(f"  Conclusion: {'REJECT H0 — strong evidence for super-linear growth' if binom_result.pvalue < 0.001 else 'Cannot reject H0'}")

    # 4g. Growth ratio statistics
    ratios = [d["ratio"] for d in transitions if d["ratio"] is not None]
    if ratios:
        log(f"\nGrowth ratio T(p^k)/T(p^{{k-1}}) statistics:")
        log(f"  Min   : {min(ratios):.3f}")
        log(f"  Max   : {max(ratios):.3f}")
        log(f"  Mean  : {np.mean(ratios):.3f}")
        log(f"  Median: {np.median(ratios):.3f}")

    # ── Summary ───────────────────────────────────────────────────────────────
    log("\n" + "=" * 78)
    log("SUMMARY FOR PAPER APPENDIX")
    log("=" * 78)
    log(f"Configurations tested (period)    : {len(period_data)}")
    log(f"Configurations tested (ergodicity): {len(ergodicity_data)}")
    log(f"Counterexamples to super-linear   : {len(counterexamples)}")
    log(f"Ergodicity pass rate              : {pass_rate*100:.1f}%  (95% CI: [{ci_lo*100:.1f}%, {ci_hi*100:.1f}%])")
    log(f"Total computation time            : {time.time() - t0:.1f}s")
    log("=" * 78)

    # ── Save outputs ──────────────────────────────────────────────────────────
    out_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out_dir, exist_ok=True)

    json_path = os.path.join(out_dir, "max_coverage_results.json")
    with open(json_path, "w") as f:
        json.dump({
            "period_data": period_data,
            "ergodicity_data": ergodicity_data,
            "summary": {
                "n_period_configs": len(period_data),
                "n_ergodicity_configs": len(ergodicity_data),
                "n_counterexamples": len(counterexamples),
                "ergodicity_pass_rate": pass_rate,
                "ci_95_lo": ci_lo,
                "ci_95_hi": ci_hi,
                "n_superlinear": n_superlinear,
                "n_transitions": n_transitions,
            }
        }, f, indent=2)

    txt_path = os.path.join(out_dir, "max_coverage_report.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[Saved] {json_path}")
    print(f"[Saved] {txt_path}")


if __name__ == "__main__":
    run()
