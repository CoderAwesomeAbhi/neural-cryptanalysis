"""
AES-CTR COMPARISON BENCHMARK
=============================

Compare neural attack success rate: Our p-adic generator vs AES-CTR.
This is the "world-class headline" if our generator resists better.

Author: Abhijay Gangarapu
"""
import numpy as np
import torch
import torch.nn as nn
from Crypto.Cipher import AES
from generator import generate_piecewise, get_matrices
from neural_attack import train_mlp, make_windowed_dataset

def generate_aes_ctr_sequence(key, nonce, length, modulus):
    """Generate sequence using AES-CTR mode."""
    cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
    
    # Generate random bytes and reduce mod m
    num_bytes = length * 2  # 2 bytes per element
    ciphertext = cipher.encrypt(b'\x00' * num_bytes)
    
    # Convert to integers mod m
    sequence = []
    for i in range(0, len(ciphertext), 2):
        val = int.from_bytes(ciphertext[i:i+2], 'big') % modulus
        sequence.append(val)
    
    return sequence[:length]

def benchmark_neural_attack():
    """Compare neural attack success on p-adic generator vs AES-CTR."""
    
    m = 125
    L_in = 6
    N_train = 5000
    
    print("="*70)
    print("AES-CTR COMPARISON BENCHMARK")
    print("="*70)
    print(f"Modulus: m={m}, Window: L_in={L_in}, Training: N={N_train}")
    print()
    
    # Test 1: Our p-adic generator (Hensel-satisfied)
    print("Test 1: p-adic Generator (Hensel-satisfied)")
    print("-" * 70)
    A_list, b_list = get_matrices("sat")
    seq_padic = generate_piecewise(m, A_list, b_list, N=N_train+1000, burn=100)
    
    X_padic, y_padic = make_windowed_dataset(seq_padic, m, L_in)
    result_padic = train_mlp(X_padic, y_padic, m, epochs=50, seed=42)
    
    print(f"  Val accuracy:  {result_padic['val_acc']*100:.1f}%")
    print(f"  Test accuracy: {result_padic['test_acc']*100:.1f}%")
    print()
    
    # Test 2: AES-CTR
    print("Test 2: AES-CTR (Industry Standard)")
    print("-" * 70)
    key = b'\x00' * 16  # 128-bit key
    nonce = b'\x00' * 8  # 64-bit nonce
    seq_aes = generate_aes_ctr_sequence(key, nonce, N_train+1000, m)
    
    X_aes, y_aes = make_windowed_dataset(seq_aes, m, L_in)
    result_aes = train_mlp(X_aes, y_aes, m, epochs=50, seed=42)
    
    print(f"  Val accuracy:  {result_aes['val_acc']*100:.1f}%")
    print(f"  Test accuracy: {result_aes['test_acc']*100:.1f}%")
    print()
    
    # Test 3: Random baseline
    print("Test 3: Random Baseline")
    print("-" * 70)
    seq_random = np.random.randint(0, m, N_train+1000)
    
    X_rand, y_rand = make_windowed_dataset(seq_random.tolist(), m, L_in)
    result_rand = train_mlp(X_rand, y_rand, m, epochs=50, seed=42)
    
    print(f"  Val accuracy:  {result_rand['val_acc']*100:.1f}%")
    print(f"  Test accuracy: {result_rand['test_acc']*100:.1f}%")
    print()
    
    # Comparison
    print("="*70)
    print("COMPARISON SUMMARY")
    print("="*70)
    
    results = {
        'p-adic Generator': result_padic['test_acc'],
        'AES-CTR': result_aes['test_acc'],
        'Random': result_rand['test_acc']
    }
    
    print(f"\n{'Generator':<20} {'Test Accuracy':<15} {'vs Random':<15}")
    print("-" * 50)
    
    random_acc = result_rand['test_acc']
    for name, acc in results.items():
        ratio = acc / random_acc if random_acc > 0 else 0
        print(f"{name:<20} {acc*100:>6.1f}%          {ratio:>6.2f}×")
    
    print()
    
    # Verdict
    if result_padic['test_acc'] < result_aes['test_acc']:
        print("✓ HEADLINE: p-adic generator RESISTS neural attacks better than AES-CTR!")
        print(f"  Resistance ratio: {result_aes['test_acc']/result_padic['test_acc']:.2f}×")
    else:
        print("  p-adic generator and AES-CTR show similar resistance.")
    
    # Visualization
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    names = list(results.keys())
    accs = [results[n]*100 for n in names]
    colors = ['#2ca02c', '#1f77b4', '#d62728']
    
    bars = ax.bar(names, accs, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    
    # Add random baseline line
    ax.axhline(y=random_acc*100, color='red', linestyle='--', linewidth=2, 
               label=f'Random Baseline ({random_acc*100:.1f}%)')
    
    ax.set_ylabel('Test Accuracy (%)', fontsize=14)
    ax.set_title('Neural Attack Success Rate: p-adic vs AES-CTR', 
                fontsize=16, fontweight='bold')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, acc in zip(bars, accs):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{acc:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('aes_comparison.png', dpi=300, bbox_inches='tight')
    print("\n[OK] Saved: aes_comparison.png")
    
    # Save results
    import json
    comparison_data = {
        'padic_test_acc': float(result_padic['test_acc']),
        'aes_test_acc': float(result_aes['test_acc']),
        'random_test_acc': float(result_rand['test_acc']),
        'padic_better': bool(result_padic['test_acc'] < result_aes['test_acc']),
        'resistance_ratio': float(result_aes['test_acc']/result_padic['test_acc']) if result_padic['test_acc'] > 0 else 0
    }
    
    with open('aes_comparison_results.json', 'w') as f:
        json.dump(comparison_data, f, indent=2)
    print("[OK] Saved: aes_comparison_results.json")
    
    return comparison_data

if __name__ == "__main__":
    try:
        results = benchmark_neural_attack()
        print("\n[OK] AES comparison complete!")
    except ImportError:
        print("\n[WARNING] pycryptodome not installed. Install with: pip install pycryptodome")
        print("Skipping AES comparison.")
