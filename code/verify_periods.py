"""Verify all period claims in Table 2 of the paper."""
import numpy as np
from generator import compute_max_period
import json

# Canonical matrices from paper
A0 = np.array([[1,1],[3,1]])
A1 = np.array([[3,3],[1,3]])
b0 = np.array([1,2])
b1 = np.array([2,1])

# Violated matrices
A0_viol = np.array([[2,1],[1,2]])
b0_viol = np.array([3,4])

# Paper claims from Table 2
paper_claims = {
    # p=5
    (5, 1, True): 25,
    (5, 2, True): 212,
    (5, 3, True): 7295,
    (5, 1, False): 3,
    (5, 2, False): 30,
    (5, 3, False): 469,
    
    # p=7
    (7, 1, True): 29,
    (7, 2, True): 1083,
    (7, 3, True): 62250,
    (7, 1, False): 9,
    (7, 2, False): 46,
    (7, 3, False): 522,
    
    # p=11
    (11, 1, True): 40,
    (11, 2, True): 4912,
    (11, 3, True): 14801,
    (11, 1, False): 25,
    (11, 2, False): 282,
    
    # p=13
    (13, 1, True): 74,
    (13, 2, True): 20475,
    (13, 3, True): 1938536,
    (13, 1, False): 6,
    (13, 2, False): 151,
}

def verify_period(p, k, sat, paper_value):
    """Verify a single period claim."""
    m = p ** k
    
    # Select matrices
    if sat:
        A0_mod = A0 % p
        A1_mod = A1 % p
        b0_mod = b0 % p
        b1_mod = b1 % p
    else:
        A0_mod = A0_viol % p
        A1_mod = A1 % p  # A1 is same for both
        b0_mod = b0_viol % p
        b1_mod = b1 % p
    
    # Compute period
    A_list = [A0_mod, A1_mod]
    b_list = [b0_mod, b1_mod]
    
    if m * m <= 2500:
        # Exhaustive for small m
        n_starts = m * m
    else:
        # Sampling for large m
        n_starts = 1000
    
    computed = compute_max_period(m, A_list, b_list, n_starts=n_starts, seed=42)
    
    match = "OK" if computed == paper_value else "FAIL"
    status = "PASS" if computed == paper_value else "FAIL"
    
    return {
        'p': p,
        'k': k,
        'm': m,
        'sat': sat,
        'paper': paper_value,
        'computed': computed,
        'match': match,
        'status': status
    }

print("=" * 80)
print("VERIFYING ALL PERIOD CLAIMS IN TABLE 2")
print("=" * 80)
print()

results = []
failures = []

for (p, k, sat), paper_value in sorted(paper_claims.items()):
    result = verify_period(p, k, sat, paper_value)
    results.append(result)
    
    sat_str = "sat" if sat else "viol"
    print(f"p={p:2d}, k={k}, {sat_str:4s}: Paper={paper_value:7d}, Computed={result['computed']:7d} {result['match']}")
    
    if result['status'] == 'FAIL':
        failures.append(result)

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total claims: {len(results)}")
print(f"Verified: {len([r for r in results if r['status'] == 'PASS'])}")
print(f"Failed: {len(failures)}")

if failures:
    print()
    print("FAILURES:")
    for f in failures:
        sat_str = "sat" if f['sat'] else "viol"
        print(f"  p={f['p']}, k={f['k']}, {sat_str}: Paper={f['paper']}, Computed={f['computed']}")
        print(f"    Difference: {abs(f['paper'] - f['computed'])} ({abs(f['paper'] - f['computed'])/f['paper']*100:.1f}%)")

# Save results
with open('../results/period_verification.json', 'w') as f:
    json.dump(results, f, indent=2)

print()
print(f"Results saved to results/period_verification.json")
