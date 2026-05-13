"""
STATE-SPACE PHASE PORTRAIT
===========================

Visual proof of entropy difference: Hensel-satisfied fills space (high entropy),
Hensel-violated forms clusters (low entropy).

Author: Abhijay Gangarapu
"""
import numpy as np
import matplotlib.pyplot as plt
from generator import generate_piecewise, get_matrices

def create_phase_portrait():
    """Generate 2D phase portraits comparing Hensel-satisfied vs violated."""
    
    m = 125
    N = 5000
    
    # Generate both sequences
    print("Generating Hensel-satisfied sequence...")
    A_sat, b_sat = get_matrices("sat")
    seq_sat = generate_piecewise(m, A_sat, b_sat, N=N, burn=100)
    
    print("Generating Hensel-violated sequence...")
    A_viol, b_viol = get_matrices("viol")
    seq_viol = generate_piecewise(m, A_viol, b_viol, N=N, burn=100)
    
    # Create 2D projections (consecutive pairs)
    x_sat = seq_sat[:-1]
    y_sat = seq_sat[1:]
    
    x_viol = seq_viol[:-1]
    y_viol = seq_viol[1:]
    
    # Create figure
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Panel 1: Hensel-satisfied
    ax = axes[0]
    ax.scatter(x_sat[:2000], y_sat[:2000], s=1, alpha=0.3, c='#1f77b4')
    ax.set_xlabel('$x_n$', fontsize=14)
    ax.set_ylabel('$x_{n+1}$', fontsize=14)
    ax.set_title('Hensel-Satisfied (δ=0)\nHigh Entropy', fontsize=16, fontweight='bold')
    ax.set_xlim(0, m)
    ax.set_ylim(0, m)
    ax.grid(True, alpha=0.2)
    ax.set_aspect('equal')
    
    # Panel 2: Hensel-violated
    ax = axes[1]
    ax.scatter(x_viol[:2000], y_viol[:2000], s=1, alpha=0.3, c='#ff7f0e')
    ax.set_xlabel('$x_n$', fontsize=14)
    ax.set_ylabel('$x_{n+1}$', fontsize=14)
    ax.set_title('Hensel-Violated (δ≥1)\nLow Entropy', fontsize=16, fontweight='bold')
    ax.set_xlim(0, m)
    ax.set_ylim(0, m)
    ax.grid(True, alpha=0.2)
    ax.set_aspect('equal')
    
    # Panel 3: Overlay comparison
    ax = axes[2]
    ax.scatter(x_sat[:1000], y_sat[:1000], s=2, alpha=0.4, c='#1f77b4', label='Satisfied')
    ax.scatter(x_viol[:1000], y_viol[:1000], s=2, alpha=0.4, c='#ff7f0e', label='Violated')
    ax.set_xlabel('$x_n$', fontsize=14)
    ax.set_ylabel('$x_{n+1}$', fontsize=14)
    ax.set_title('Overlay Comparison', fontsize=16, fontweight='bold')
    ax.set_xlim(0, m)
    ax.set_ylim(0, m)
    ax.grid(True, alpha=0.2)
    ax.legend(fontsize=12)
    ax.set_aspect('equal')
    
    plt.suptitle('State-Space Phase Portrait: Visual Entropy Difference',
                fontsize=18, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    plt.savefig('phase_portrait.png', dpi=300, bbox_inches='tight')
    print("[OK] Saved: phase_portrait.png")
    
    # Compute entropy metrics
    print("\nEntropy Analysis:")
    
    # Bin the 2D space
    bins = 25
    H_sat, _, _ = np.histogram2d(x_sat, y_sat, bins=bins, range=[[0,m],[0,m]])
    H_viol, _, _ = np.histogram2d(x_viol, y_viol, bins=bins, range=[[0,m],[0,m]])
    
    # Normalize
    H_sat = H_sat / H_sat.sum()
    H_viol = H_viol / H_viol.sum()
    
    # Shannon entropy
    def shannon_entropy(p):
        p = p[p > 0]
        return -np.sum(p * np.log2(p))
    
    ent_sat = shannon_entropy(H_sat)
    ent_viol = shannon_entropy(H_viol)
    
    print(f"  Hensel-satisfied entropy: {ent_sat:.2f} bits")
    print(f"  Hensel-violated entropy:  {ent_viol:.2f} bits")
    print(f"  Entropy ratio: {ent_sat/ent_viol:.2f}×")
    
    # Occupied cells
    occupied_sat = np.sum(H_sat > 0)
    occupied_viol = np.sum(H_viol > 0)
    
    print(f"\n  Occupied cells (satisfied):  {occupied_sat}/{bins**2} ({100*occupied_sat/bins**2:.1f}%)")
    print(f"  Occupied cells (violated):   {occupied_viol}/{bins**2} ({100*occupied_viol/bins**2:.1f}%)")
    
    return {
        'entropy_satisfied': float(ent_sat),
        'entropy_violated': float(ent_viol),
        'entropy_ratio': float(ent_sat/ent_viol),
        'occupied_satisfied': int(occupied_sat),
        'occupied_violated': int(occupied_viol)
    }

if __name__ == "__main__":
    results = create_phase_portrait()
    
    import json
    with open('phase_portrait_metrics.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\n[OK] Saved: phase_portrait_metrics.json")
    print("\n[OK] Phase portrait complete!")
