"""Test neural attack robustness under noisy observations."""
import numpy as np
import torch
import torch.nn as nn
from generator import generate_piecewise, get_matrices
from neural_attack import make_windowed_dataset, train_mlp
import matplotlib.pyplot as plt

def add_noise(sequence, sigma, m):
    """Add Gaussian noise to sequence and wrap modulo m."""
    seq_arr = np.array(sequence, dtype=np.float64)
    noise = np.random.normal(0, sigma, len(seq_arr))
    noisy = seq_arr + noise
    return (np.round(noisy).astype(int) % m).tolist()

def test_noise_robustness():
    """Test MLP performance under different noise levels."""
    m = 125
    L_in = 6
    N_train = 5000
    
    A_list, b_list = get_matrices("sat")
    seq = generate_piecewise(m, A_list, b_list, N=N_train + 1000, burn=100)
    
    noise_levels = [0.0, 0.01, 0.05, 0.1, 0.2, 0.5]
    results = []
    
    print("="*70)
    print("NOISE ROBUSTNESS TEST")
    print("="*70)
    print(f"Modulus: m={m}, Window: L_in={L_in}, Training: N={N_train}")
    print()
    
    for sigma in noise_levels:
        print(f"Testing noise level sigma={sigma}...")
        
        # Add noise
        noisy_seq = add_noise(seq, sigma * m, m)  # Scale by m
        
        # Create dataset and train
        X, y = make_windowed_dataset(noisy_seq, m, L_in)
        result = train_mlp(X, y, m, hidden=(256, 128), epochs=50, seed=42)
        
        acc = result['test_acc']
        
        results.append({'sigma': sigma, 'accuracy': acc})
        print(f"  sigma={sigma:.2f}: Accuracy = {acc*100:.1f}%")
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    sigmas = [r['sigma'] for r in results]
    accs = [r['accuracy']*100 for r in results]
    
    ax.plot(sigmas, accs, 'o-', linewidth=2, markersize=8, color='#1f77b4')
    ax.axhline(y=100/m, color='red', linestyle='--', label=f'Random ({100/m:.1f}%)')
    ax.set_xlabel('Noise Level sigma (relative to m)', fontsize=12)
    ax.set_ylabel('Prediction Accuracy (%)', fontsize=12)
    ax.set_title('Neural Attack Robustness Under Noise', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('noise_robustness.png', dpi=300, bbox_inches='tight')
    print("\n[OK] Saved: noise_robustness.png")
    
    # Save raw data
    import json
    with open('noise_robustness_data.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("[OK] Saved: noise_robustness_data.json")
    
    # Find critical noise level
    critical_idx = next((i for i, r in enumerate(results) if r['accuracy'] < 0.5), len(results))
    if critical_idx < len(results):
        print(f"[OK] Critical noise level: sigma ~= {results[critical_idx]['sigma']}")
    else:
        print(f"[OK] Robust up to sigma = {results[-1]['sigma']}")
    
    return results

if __name__ == "__main__":
    np.random.seed(42)
    torch.manual_seed(42)
    results = test_noise_robustness()
