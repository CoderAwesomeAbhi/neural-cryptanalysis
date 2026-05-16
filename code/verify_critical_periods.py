"""Quick verification of critical period claims from Table 2."""
import numpy as np
import sys
sys.path.append('.')
from generator import compute_max_period

# Canonical matrices
A0 = np.array([[1,1],[3,1]])
A1 = np.array([[3,3],[1,3]])
b0 = np.array([1,2])
b1 = np.array([2,1])

# Critical claims to verify
critical_claims = [
    (5, 2, 25, 212, "p5k2sat - used throughout paper"),
    (5, 3, 125, 7295, "p5k3sat - main hard sequence"),
    (7, 2, 49, 1083, "p7k2sat - neural attack table"),
]

print("=" * 70)
print("CRITICAL PERIOD VERIFICATION")
print("=" * 70)
print()

all_pass = True

for p, k, m, expected, description in critical_claims:
    A0_mod = A0 % p
    A1_mod = A1 % p
    b0_mod = b0 % p
    b1_mod = b1 % p
    
    A_list = [A0_mod, A1_mod]
    b_list = [b0_mod, b1_mod]
    
    # Use exhaustive search for small m, sampling for large
    n_starts = m * m if m * m <= 2500 else 1000
    
    computed = compute_max_period(m, A_list, b_list, n_starts=n_starts, seed=42)
    
    match = computed == expected
    status = "PASS" if match else "FAIL"
    symbol = "OK" if match else "FAIL"
    
    print(f"{description}")
    print(f"  p={p}, k={k}, m={m}")
    print(f"  Paper: {expected:,}")
    print(f"  Computed: {computed:,}")
    print(f"  Status: {status} {symbol}")
    print()
    
    if not match:
        all_pass = False
        print(f"  ERROR: Mismatch! Difference: {abs(computed - expected):,}")
        print()

print("=" * 70)
if all_pass:
    print("ALL CRITICAL CLAIMS VERIFIED")
    print("Status: PASS")
else:
    print("VERIFICATION FAILED")
    print("Status: FAIL")
print("=" * 70)
