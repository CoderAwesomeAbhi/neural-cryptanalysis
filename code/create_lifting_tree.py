"""
HENSEL LIFTING TREE VISUALIZATION
==================================

Visual diagram showing how periods grow under ring extension p -> p² -> p³.
This is the "Aha!" moment for understanding super-linear growth.

Author: Abhijay Gangarapu
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

def create_lifting_tree():
    """Create publication-quality lifting tree diagram."""
    
    # Data from prime_sweep_data.json
    primes = [5, 7, 11, 13]
    periods = {
        5: {1: 25, 2: 212, 3: 1800},
        7: {1: 27, 2: 1008, 3: 57960},
        11: {1: 98, 2: 12034, 3: 14801},
        13: {1: 74, 2: 20475, 3: 1938536}
    }
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    for idx, p in enumerate(primes):
        ax = axes[idx]
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        
        # Title
        ax.text(5, 9.5, f'Prime p = {p}', ha='center', fontsize=18, fontweight='bold')
        
        # Level k=1 (mod p)
        T1 = periods[p][1]
        box1 = FancyBboxPatch((3.5, 7), 3, 1, boxstyle="round,pad=0.1", 
                              edgecolor='#1f77b4', facecolor='#aec7e8', linewidth=3)
        ax.add_patch(box1)
        ax.text(5, 7.5, f'$\\mathbb{{Z}}/{p}\\mathbb{{Z}}$\n$T({p}) = {T1}$', 
                ha='center', va='center', fontsize=14, fontweight='bold')
        
        # Arrow 1
        arrow1 = FancyArrowPatch((5, 7), (5, 5.5), arrowstyle='->', 
                                mutation_scale=30, linewidth=3, color='black')
        ax.add_patch(arrow1)
        
        # Growth ratio 1
        ratio1 = periods[p][2] / periods[p][1]
        ax.text(6.5, 6.2, f'×{ratio1:.1f}', fontsize=12, color='red', fontweight='bold')
        
        # Level k=2 (mod p²)
        T2 = periods[p][2]
        box2 = FancyBboxPatch((3, 4.5), 4, 1, boxstyle="round,pad=0.1",
                              edgecolor='#ff7f0e', facecolor='#ffbb78', linewidth=3)
        ax.add_patch(box2)
        ax.text(5, 5, f'$\\mathbb{{Z}}/{p}^2\\mathbb{{Z}}$\n$T({p}^2) = {T2:,}$',
                ha='center', va='center', fontsize=14, fontweight='bold')
        
        # Arrow 2
        arrow2 = FancyArrowPatch((5, 4.5), (5, 3), arrowstyle='->',
                                mutation_scale=30, linewidth=3, color='black')
        ax.add_patch(arrow2)
        
        # Growth ratio 2
        ratio2 = periods[p][3] / periods[p][2]
        ax.text(6.5, 3.7, f'×{ratio2:.1f}', fontsize=12, color='red', fontweight='bold')
        
        # Level k=3 (mod p³)
        T3 = periods[p][3]
        box3 = FancyBboxPatch((2.5, 1.5), 5, 1, boxstyle="round,pad=0.1",
                              edgecolor='#2ca02c', facecolor='#98df8a', linewidth=3)
        ax.add_patch(box3)
        ax.text(5, 2, f'$\\mathbb{{Z}}/{p}^3\\mathbb{{Z}}$\n$T({p}^3) = {T3:,}$',
                ha='center', va='center', fontsize=14, fontweight='bold')
        
        # Super-linear indicator
        if ratio1 > p and ratio2 > p:
            ax.text(5, 0.5, '[OK] SUPER-LINEAR GROWTH', ha='center', fontsize=12,
                   color='green', fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
        
        # Theoretical bound
        ax.text(5, 0, f'Linear bound: ×{p}', ha='center', fontsize=10,
               style='italic', color='gray')
    
    plt.suptitle('Hensel Lifting Tree: Period Growth Under Ring Extension',
                fontsize=20, fontweight='bold', y=0.98)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig('lifting_tree.png', dpi=300, bbox_inches='tight')
    print("[OK] Saved: lifting_tree.png")
    
    # Create summary table
    fig2, ax = plt.subplots(figsize=(12, 6))
    ax.axis('tight')
    ax.axis('off')
    
    # Table data
    table_data = []
    table_data.append(['Prime p', 'T(p)', 'T(p²)', 'T(p³)', 'Ratio 1->2', 'Ratio 2->3'])
    for p in primes:
        T1, T2, T3 = periods[p][1], periods[p][2], periods[p][3]
        r1 = T2/T1
        r2 = T3/T2
        table_data.append([
            f'{p}',
            f'{T1:,}',
            f'{T2:,}',
            f'{T3:,}',
            f'{r1:.1f}× (>{p})',
            f'{r2:.1f}× (>{p})'
        ])
    
    table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                    colWidths=[0.1, 0.15, 0.15, 0.2, 0.2, 0.2])
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 2.5)
    
    # Style header row
    for i in range(6):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Style data rows
    for i in range(1, 5):
        for j in range(6):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#E7E6E6')
    
    plt.title('Period Growth Summary: All Primes', fontsize=16, fontweight='bold', pad=20)
    plt.savefig('lifting_tree_table.png', dpi=300, bbox_inches='tight')
    print("[OK] Saved: lifting_tree_table.png")

if __name__ == "__main__":
    create_lifting_tree()
    print("\n[OK] Lifting tree visualizations complete!")
