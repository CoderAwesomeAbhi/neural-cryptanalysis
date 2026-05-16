"""
Chain-of-Thought State-Space Experiment
Tests whether explicit state supervision allows networks to bypass the T/L_in barrier
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import matplotlib.pyplot as plt
from pathlib import Path
import json
from tqdm import tqdm

import sys
sys.path.append(str(Path(__file__).parent))
from sequence_generator import generate_piecewise_sequence_with_states

class CoTStatePredictor(nn.Module):
    """
    Chain-of-Thought predictor that outputs intermediate states
    
    Input: s_0, s_1, ..., s_5 (6 observations)
    Output: regime_5, x_6[0], x_6[1], s_6
    """
    def __init__(self, input_size, hidden_size, m):
        super().__init__()
        self.m = m
        
        # Shared encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU()
        )
        
        # Separate heads for each prediction
        self.regime_head = nn.Linear(hidden_size, 2)  # Binary: regime 0 or 1
        self.state_x0_head = nn.Linear(hidden_size, m)  # x[0] ∈ {0, ..., m-1}
        self.state_x1_head = nn.Linear(hidden_size, m)  # x[1] ∈ {0, ..., m-1}
        self.output_head = nn.Linear(hidden_size, m)  # s_6 ∈ {0, ..., m-1}
    
    def forward(self, x):
        features = self.encoder(x)
        
        regime_logits = self.regime_head(features)
        x0_logits = self.state_x0_head(features)
        x1_logits = self.state_x1_head(features)
        output_logits = self.output_head(features)
        
        return regime_logits, x0_logits, x1_logits, output_logits

def create_cot_dataset(sequence, states, regimes, L_in=6):
    """
    Create dataset with state supervision
    
    Args:
        sequence: Output sequence [s_0, s_1, ...]
        states: State sequence [(x0_0, x1_0), (x0_1, x1_1), ...]
        regimes: Regime sequence [r_0, r_1, ...]
        L_in: Input window length
    
    Returns:
        X: Input windows
        y_regime: Target regimes
        y_x0: Target x[0] values
        y_x1: Target x[1] values
        y_output: Target outputs
    """
    X = []
    y_regime = []
    y_x0 = []
    y_x1 = []
    y_output = []
    
    for i in range(len(sequence) - L_in):
        X.append(sequence[i:i+L_in])
        
        # Target is the state and output at position i+L_in
        y_regime.append(regimes[i+L_in])
        y_x0.append(states[i+L_in][0])
        y_x1.append(states[i+L_in][1])
        y_output.append(sequence[i+L_in])
    
    return (np.array(X), np.array(y_regime), 
            np.array(y_x0), np.array(y_x1), np.array(y_output))

def train_cot_model(config, epochs=50):
    """Train Chain-of-Thought model with state supervision"""
    
    print(f"\n{'='*80}")
    print(f"CHAIN-OF-THOUGHT EXPERIMENT: {config['name']}")
    print(f"Training with explicit state supervision")
    print(f"{'='*80}\n")
    
    # Generate sequence WITH state information
    m = config['p'] ** config['k']
    sequence, states, regimes = generate_piecewise_sequence_with_states(
        p=config['p'],
        k=config['k'],
        hensel_satisfied=config['hensel_satisfied'],
        n_terms=4500,
        burn_in=300
    )
    
    # Create CoT dataset
    X, y_regime, y_x0, y_x1, y_output = create_cot_dataset(
        sequence, states, regimes, L_in=6
    )
    
    # Normalize inputs
    X_norm = X / m
    
    # Train/val/test split
    n_train = int(0.8 * len(X))
    n_val = int(0.1 * len(X))
    
    X_train = torch.FloatTensor(X_norm[:n_train])
    regime_train = torch.LongTensor(y_regime[:n_train])
    x0_train = torch.LongTensor(y_x0[:n_train])
    x1_train = torch.LongTensor(y_x1[:n_train])
    output_train = torch.LongTensor(y_output[:n_train])
    
    X_val = torch.FloatTensor(X_norm[n_train:n_train+n_val])
    regime_val = torch.LongTensor(y_regime[n_train:n_train+n_val])
    x0_val = torch.LongTensor(y_x0[n_train:n_train+n_val])
    x1_val = torch.LongTensor(y_x1[n_train:n_train+n_val])
    output_val = torch.LongTensor(y_output[n_train:n_train+n_val])
    
    X_test = torch.FloatTensor(X_norm[n_train+n_val:])
    regime_test = torch.LongTensor(y_regime[n_train+n_val:])
    x0_test = torch.LongTensor(y_x0[n_train+n_val:])
    x1_test = torch.LongTensor(y_x1[n_train+n_val:])
    output_test = torch.LongTensor(y_output[n_train+n_val:])
    
    # Create model
    model = CoTStatePredictor(input_size=6, hidden_size=256, m=m)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    
    # Training loop
    train_loader = DataLoader(
        TensorDataset(X_train, regime_train, x0_train, x1_train, output_train),
        batch_size=256,
        shuffle=True
    )
    
    history = {
        'train_loss': [],
        'val_regime_acc': [],
        'val_state_acc': [],
        'val_output_acc': [],
        'test_output_acc': []
    }
    
    print(f"Period T = {config.get('period', 'unknown')}")
    print(f"T/L_in = {config.get('period', 0) / 6:.1f}")
    print(f"T/N_train = {config.get('period', 0) / n_train:.2f}\n")
    
    for epoch in tqdm(range(epochs), desc="Training"):
        # Training
        model.train()
        epoch_loss = 0.0
        for batch_X, batch_regime, batch_x0, batch_x1, batch_output in train_loader:
            optimizer.zero_grad()
            
            regime_logits, x0_logits, x1_logits, output_logits = model(batch_X)
            
            # Multi-task loss
            loss_regime = criterion(regime_logits, batch_regime)
            loss_x0 = criterion(x0_logits, batch_x0)
            loss_x1 = criterion(x1_logits, batch_x1)
            loss_output = criterion(output_logits, batch_output)
            
            # Weighted combination (output is most important)
            loss = 0.1 * loss_regime + 0.2 * loss_x0 + 0.2 * loss_x1 + 0.5 * loss_output
            
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        
        # Validation
        model.eval()
        with torch.no_grad():
            regime_logits, x0_logits, x1_logits, output_logits = model(X_val)
            
            regime_preds = torch.argmax(regime_logits, dim=1)
            x0_preds = torch.argmax(x0_logits, dim=1)
            x1_preds = torch.argmax(x1_logits, dim=1)
            output_preds = torch.argmax(output_logits, dim=1)
            
            regime_acc = (regime_preds == regime_val).float().mean().item()
            state_acc = ((x0_preds == x0_val) & (x1_preds == x1_val)).float().mean().item()
            output_acc = (output_preds == output_val).float().mean().item()
            
            # Test accuracy
            _, _, _, test_output_logits = model(X_test)
            test_preds = torch.argmax(test_output_logits, dim=1)
            test_acc = (test_preds == output_test).float().mean().item()
            
            history['train_loss'].append(epoch_loss / len(train_loader))
            history['val_regime_acc'].append(regime_acc)
            history['val_state_acc'].append(state_acc)
            history['val_output_acc'].append(output_acc)
            history['test_output_acc'].append(test_acc)
            
            if epoch % 10 == 0:
                print(f"Epoch {epoch:3d}: Loss={epoch_loss/len(train_loader):.4f}, "
                      f"Regime={regime_acc:.1%}, State={state_acc:.1%}, "
                      f"Output={output_acc:.1%}, Test={test_acc:.1%}")
    
    # Final results
    print(f"\n{'='*80}")
    print(f"FINAL RESULTS:")
    print(f"  Regime accuracy: {history['val_regime_acc'][-1]:.1%}")
    print(f"  State accuracy: {history['val_state_acc'][-1]:.1%}")
    print(f"  Output accuracy (val): {history['val_output_acc'][-1]:.1%}")
    print(f"  Output accuracy (test): {history['test_output_acc'][-1]:.1%}")
    print(f"{'='*80}\n")
    
    return {
        'config': config,
        'history': history,
        'final_test_acc': history['test_output_acc'][-1]
    }

def compare_cot_vs_baseline(cot_results, baseline_results, save_path):
    """Compare CoT vs baseline performance"""
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    for idx, (cot_res, base_res) in enumerate(zip(cot_results, baseline_results)):
        ax = axes[idx // 2, idx % 2]
        
        config = cot_res['config']
        epochs = range(len(cot_res['history']['val_output_acc']))
        
        # Plot CoT performance
        ax.plot(epochs, cot_res['history']['val_output_acc'], 
               label='CoT (with state supervision)', linewidth=2, color='blue')
        
        # Plot baseline performance (if available)
        if base_res:
            ax.axhline(base_res['final_acc'], color='red', linestyle='--',
                      label=f'Baseline (no supervision): {base_res["final_acc"]:.1%}')
        
        ax.set_xlabel('Epoch', fontsize=12)
        ax.set_ylabel('Validation Accuracy', fontsize=12)
        ax.set_title(f"{config['name']}\nT={config.get('period', '?')}, T/L_in={config.get('period', 0)/6:.1f}", 
                    fontsize=13, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved CoT comparison to {save_path}")

def main():
    """Run Chain-of-Thought experiments"""
    
    configs = [
        {
            'name': 'Easy (m=25, T=125)',
            'p': 5,
            'k': 2,
            'hensel_satisfied': True,
            'period': 125
        },
        {
            'name': 'Medium (m=49, T=1083)',
            'p': 7,
            'k': 2,
            'hensel_satisfied': True,
            'period': 1083
        },
        {
            'name': 'Hard (m=125, T=7295)',
            'p': 5,
            'k': 3,
            'hensel_satisfied': True,
            'period': 7295
        },
        {
            'name': 'Very Hard (m=121, T=4912)',
            'p': 11,
            'k': 2,
            'hensel_satisfied': True,
            'period': 4912
        }
    ]
    
    # Run CoT experiments
    cot_results = []
    for config in configs:
        results = train_cot_model(config, epochs=50)
        cot_results.append(results)
        
        # Save results
        results_dir = Path(__file__).parent.parent / 'results'
        results_dir.mkdir(exist_ok=True)
        
        with open(results_dir / f"cot_{config['name'].replace(' ', '_')}.json", 'w') as f:
            json_results = {
                'config': config,
                'history': results['history'],
                'final_test_acc': results['final_test_acc']
            }
            json.dump(json_results, f, indent=2)
    
    # Load baseline results for comparison (if they exist)
    baseline_results = [None] * len(configs)  # Placeholder
    
    # Plot comparison
    results_dir = Path(__file__).parent.parent / 'results'
    compare_cot_vs_baseline(cot_results, baseline_results, 
                           results_dir / 'cot_vs_baseline.png')
    
    # Summary
    print("\n" + "="*80)
    print("CHAIN-OF-THOUGHT EXPERIMENT SUMMARY")
    print("="*80)
    for results in cot_results:
        config = results['config']
        print(f"\n{config['name']}:")
        print(f"  Period: {config['period']}")
        print(f"  T/L_in: {config['period']/6:.1f}")
        print(f"  Final test accuracy: {results['final_test_acc']:.1%}")
        
        if results['final_test_acc'] > 0.9:
            print(f"  ✅ CoT BREAKTHROUGH: State supervision enables learning!")
        elif results['final_test_acc'] > 0.5:
            print(f"  ⚠️  PARTIAL SUCCESS: CoT helps but doesn't fully solve it")
        else:
            print(f"  ❌ CoT FAILED: Information-theoretic barrier persists")
    print("="*80)

if __name__ == '__main__':
    main()
