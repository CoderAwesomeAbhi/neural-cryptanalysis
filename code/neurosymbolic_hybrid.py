"""
Neurosymbolic Hybrid Architecture
Combines neural pattern recognition with symbolic p-adic reasoning
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))
from generator import A0_CANON, A1_CANON, b0_CANON, b1_CANON

# Set random seed for reproducibility
torch.manual_seed(42)
np.random.seed(42)


class SymbolicPAdicModule(nn.Module):
    """
    Differentiable module for exact modular arithmetic
    Learns affine transformations: x -> (Ax + b) mod m
    """
    def __init__(self, m, state_dim=2):
        super().__init__()
        self.m = m
        self.state_dim = state_dim
        
        # Learnable parameters (initialized near identity)
        self.A = nn.Parameter(torch.eye(state_dim) + 0.1 * torch.randn(state_dim, state_dim))
        self.b = nn.Parameter(torch.zeros(state_dim))
        
    def forward(self, state):
        """
        state: (batch, state_dim) - integer states
        Returns: (batch, state_dim) - transformed states mod m (as float for gradient flow)
        """
        # Affine transformation
        transformed = torch.matmul(state.float(), self.A.t()) + self.b
        
        # Modular reduction (keep as float for gradient flow)
        output = torch.fmod(transformed, self.m)
        output = torch.where(output < 0, output + self.m, output)
        
        return output  # Return float, not .long()


class RegimeClassifier(nn.Module):
    """Neural network that learns regime selection φ(x)"""
    def __init__(self, m, hidden_size=64):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(2, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 2)  # Binary regime
        )
        
    def forward(self, state):
        """
        state: (batch, 2)
        Returns: (batch, 2) logits for regime 0 or 1
        """
        return self.network(state.float())


class NeurosymbolicHybrid(nn.Module):
    """
    Hybrid architecture:
    1. Neural network classifies regime φ(x)
    2. Symbolic module applies exact affine transformation
    """
    def __init__(self, m):
        super().__init__()
        self.m = m
        
        # Neural component
        self.regime_classifier = RegimeClassifier(m)
        
        # Symbolic components (one per regime)
        self.symbolic_0 = SymbolicPAdicModule(m)
        self.symbolic_1 = SymbolicPAdicModule(m)
        
    def forward(self, state):
        """
        state: (batch, 2)
        Returns: next_state (batch, 2) as float, regime_logits (batch, 2)
        """
        # Classify regime
        regime_logits = self.regime_classifier(state)
        regime_probs = torch.softmax(regime_logits, dim=1)
        
        # Apply both symbolic transformations (returns float)
        next_state_0 = self.symbolic_0(state)
        next_state_1 = self.symbolic_1(state)
        
        # Weighted combination (differentiable)
        next_state = (
            regime_probs[:, 0:1] * next_state_0 +
            regime_probs[:, 1:2] * next_state_1
        )
        
        return next_state, regime_logits


def train_neurosymbolic(config, max_epochs=100):
    """Train neurosymbolic hybrid model"""
    print(f"\n{'='*80}")
    print(f"NEUROSYMBOLIC HYBRID: {config['name']}")
    print(f"Neural regime selection + Symbolic p-adic arithmetic")
    print(f"{'='*80}\n")
    
    m = config['p'] ** config['k']
    
    # Use canonical matrices from generator.py
    A0 = A0_CANON
    b0 = b0_CANON
    A1 = A1_CANON
    b1 = b1_CANON
    
    n_terms = 4500
    states = []
    regimes = []
    
    state = np.array([1, 1])
    for _ in range(n_terms):
        states.append(state.copy())
        regime = state[0] % 2  # Use parity for consistency
        regimes.append(regime)
        
        if regime == 0:
            state = (A0 @ state + b0) % m
        else:
            state = (A1 @ state + b1) % m
    
    # Create dataset: (state_t, regime_t) -> state_{t+1}
    X_state = torch.LongTensor(states[:-1])
    y_state = torch.LongTensor(states[1:])
    y_regime = torch.LongTensor(regimes[:-1])
    
    # Split
    n_train = int(0.8 * len(X_state))
    n_val = int(0.1 * len(X_state))
    
    X_train = X_state[:n_train]
    y_state_train = y_state[:n_train]
    y_regime_train = y_regime[:n_train]
    
    X_val = X_state[n_train:n_train+n_val]
    y_state_val = y_state[n_train:n_train+n_val]
    y_regime_val = y_regime[n_train:n_train+n_val]
    
    # Model
    model = NeurosymbolicHybrid(m)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    train_loader = DataLoader(
        TensorDataset(X_train, y_state_train, y_regime_train),
        batch_size=64,
        shuffle=True
    )
    
    print(f"Training neurosymbolic model...")
    print(f"Period T = {config['period']}")
    print(f"T/L_in = {config['period'] / 2:.1f}\n")
    
    best_val_acc = 0.0
    
    for epoch in range(max_epochs):
        model.train()
        total_loss = 0
        
        for batch_state, batch_next, batch_regime in train_loader:
            optimizer.zero_grad()
            
            pred_next, regime_logits = model(batch_state)
            
            # State prediction loss: use MSE since pred_next is continuous float
            # (cross-entropy would require logits over m classes per component)
            state_loss = nn.functional.mse_loss(pred_next, batch_next.float())
            
            # Regime classification loss
            regime_loss = nn.functional.cross_entropy(regime_logits, batch_regime)
            
            loss = state_loss + regime_loss
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        # Validate
        if (epoch + 1) % 10 == 0:
            model.eval()
            with torch.no_grad():
                pred_next, regime_logits = model(X_val)
                
                # State accuracy (exact match after rounding)
                pred_next_rounded = pred_next.round().long()
                state_correct = (pred_next_rounded == y_state_val).all(dim=1).sum().item()
                state_acc = state_correct / len(X_val)
                
                # Regime accuracy
                regime_preds = torch.argmax(regime_logits, dim=1)
                regime_acc = (regime_preds == y_regime_val).float().mean().item()
                
                best_val_acc = max(best_val_acc, state_acc)
                
                print(f"Epoch {epoch+1:3d}: Loss={total_loss/len(train_loader):.4f}, "
                      f"State Acc={state_acc:.1%}, Regime Acc={regime_acc:.1%}")
    
    # Final test
    X_test = X_state[n_train+n_val:]
    y_state_test = y_state[n_train+n_val:]
    y_regime_test = y_regime[n_train+n_val:]
    
    model.eval()
    with torch.no_grad():
        pred_next, regime_logits = model(X_test)
        
        pred_next_rounded = pred_next.round().long()
        state_correct = (pred_next_rounded == y_state_test).all(dim=1).sum().item()
        test_state_acc = state_correct / len(X_test)
        
        regime_preds = torch.argmax(regime_logits, dim=1)
        test_regime_acc = (regime_preds == y_regime_test).float().mean().item()
    
    print(f"\n{'='*80}")
    print(f"FINAL RESULTS:")
    print(f"  State prediction accuracy: {test_state_acc:.1%}")
    print(f"  Regime classification accuracy: {test_regime_acc:.1%}")
    print(f"  Best validation accuracy: {best_val_acc:.1%}")
    
    if test_state_acc > 0.9:
        print(f"  ✓ NEUROSYMBOLIC HYBRID SUCCEEDS!")
    else:
        print(f"  ✗ Hybrid does not overcome barrier")
    print(f"{'='*80}\n")
    
    return test_state_acc, test_regime_acc


def main():
    """Run neurosymbolic experiments"""
    configs = [
        {
            'name': 'Medium (m=49, T=1083)',
            'p': 7,
            'k': 2,
            'period': 1083
        },
        {
            'name': 'Hard (m=125, T=7295)',
            'p': 5,
            'k': 3,
            'period': 7295
        }
    ]
    
    results = []
    for config in configs:
        state_acc, regime_acc = train_neurosymbolic(config, max_epochs=100)
        results.append({
            'config': config['name'],
            'state_acc': state_acc,
            'regime_acc': regime_acc
        })
    
    print("\n" + "="*80)
    print("NEUROSYMBOLIC HYBRID SUMMARY")
    print("="*80)
    for r in results:
        print(f"{r['config']}:")
        print(f"  State: {r['state_acc']:.1%}, Regime: {r['regime_acc']:.1%}")
    print("="*80)


if __name__ == '__main__':
    main()
