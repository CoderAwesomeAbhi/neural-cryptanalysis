"""
Generate NIST-compliant sequence with period > 1,000,000
Uses p=13, k=3 configuration where T >> 1M bits
"""

import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from generator import A0_CANON, A1_CANON, b0_CANON, b1_CANON, compute_max_period

def generate_long_sequence_for_nist(p=13, k=3, n_bits=1_000_000):
    """Generate sequence with period > n_bits for NIST testing"""
    
    m = p ** k
    print(f"\n{'='*80}")
    print(f"GENERATING NIST-COMPLIANT SEQUENCE")
    print(f"{'='*80}")
    print(f"Configuration: p={p}, k={k}, m={m}")
    
    # Compute actual period
    A_list = [A0_CANON, A1_CANON]
    b_list = [b0_CANON, b1_CANON]
    T = compute_max_period(m, A_list, b_list, n_starts=1000)
    print(f"Maximum period T = {T:,}")
    
    # Each state yields log2(m) bits
    bits_per_state = int(np.log2(m))
    period_in_bits = T * bits_per_state
    
    print(f"Bits per state: {bits_per_state}")
    print(f"Period in bits: {period_in_bits:,}")
    print(f"Target bits: {n_bits:,}")
    print(f"Repetitions in {n_bits:,} bits: {n_bits / period_in_bits:.2f}")
    
    if period_in_bits < n_bits:
        print(f"\n[WARNING] Period {period_in_bits:,} < {n_bits:,} bits")
        print(f"Sequence will repeat {n_bits/period_in_bits:.1f} times")
        print(f"NIST tests WILL FAIL due to periodicity detection")
        return None
    
    print(f"\n[OK] Period {period_in_bits:,} > {n_bits:,} bits")
    print(f"NIST tests should pass (no repetition in sample)")
    
    # Generate sequence
    print(f"\nGenerating {n_bits:,} bits...")
    
    state = np.array([1, 1], dtype=np.int64)
    bits = []
    
    n_states = (n_bits + bits_per_state - 1) // bits_per_state
    
    for i in range(n_states):
        if i % 10000 == 0:
            print(f"  Progress: {i:,}/{n_states:,} states ({len(bits):,} bits)")
        
        # Extract bits from state
        for component in state:
            val = int(component)
            for _ in range(bits_per_state // 2):
                bits.append(val & 1)
                val >>= 1
                if len(bits) >= n_bits:
                    break
            if len(bits) >= n_bits:
                break
        
        if len(bits) >= n_bits:
            break
        
        # Advance state
        regime = state[0] % 2
        if regime == 0:
            state = (A0_CANON @ state + b0_CANON) % m
        else:
            state = (A1_CANON @ state + b1_CANON) % m
    
    bits = bits[:n_bits]
    
    # Save to file
    output_file = Path(__file__).parent / f"nist_sequence_p{p}_k{k}.txt"
    with open(output_file, 'w') as f:
        f.write(''.join(map(str, bits)))
    
    print(f"\n[SUCCESS] Generated {len(bits):,} bits")
    print(f"Saved to: {output_file}")
    
    # Basic statistics
    ones = sum(bits)
    zeros = len(bits) - ones
    print(f"\nStatistics:")
    print(f"  Ones:  {ones:,} ({ones/len(bits)*100:.2f}%)")
    print(f"  Zeros: {zeros:,} ({zeros/len(bits)*100:.2f}%)")
    print(f"  Balance: {abs(ones-zeros)/len(bits)*100:.2f}% deviation from 50/50")
    
    return bits, output_file


if __name__ == "__main__":
    # Try p=13, k=3 first
    bits, filepath = generate_long_sequence_for_nist(p=13, k=3, n_bits=1_000_000)
    
    if bits is None:
        print("\n[CRITICAL] Need larger configuration!")
        print("Trying p=13, k=4...")
        bits, filepath = generate_long_sequence_for_nist(p=13, k=4, n_bits=1_000_000)
    
    if bits:
        print(f"\n{'='*80}")
        print("READY FOR NIST TESTING")
        print(f"{'='*80}")
        print(f"Run NIST Statistical Test Suite on: {filepath}")
        print(f"Expected: 14-15/15 tests pass (no periodicity detected)")
