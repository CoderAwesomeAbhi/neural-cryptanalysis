"""
Ablation study: Test if T/L_in threshold holds across different scales.

This addresses Reviewer 2's criticism that the "21" constant is an artifact
of specific hyperparameters. We test:
1. Different context lengths: L_in in {6, 12, 24, 48}
2. Different training sizes: N_train in {1800, 3600, 7200}
3. Different model capacities: hidden in {64, 128, 256}

Hypothesis: The threshold T/L_in ~ 20-25 should hold across scales.
"""
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import sys
sys.path.append('.')
from core import generate_sequence
from generator import compute_max_period

class SequenceDataset(Dataset):
    def __init__(self, sequence, L_in, N):
        self.sequence = sequence
        self.L_in = L_in
        self.N = N
    
    def __len__(self):
        return self.N
    
    def __getitem__(self, idx):
        start = idx % (len(self.sequence) - self.L_in - 1)
        X = torch.tensor(self.sequence[start:start+self.L_in], dtype=torch.float32)
        y = self.sequence[start + self.L_in]
        return X, y


class SimpleMLP(nn.Module):
    def __init__(self, L_in, hidden=128, m=5):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(L_in, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, m)
        )
    
    def forward(self, x):
        return self.net(x)


def train_and_test(sequence, m, L_in, N_train, hidden, epochs=50):
    """Train and test neural network."""
    # Create datasets
    train_dataset = SequenceDataset(sequence, L_in, N_train)
    test_dataset = SequenceDataset(sequence, L_in, 1000)
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=32)
    
    # Create model
    model = SimpleMLP(L_in, hidden, m)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    
    # Train
    model.train()
    for epoch in range(epochs):
        for X, y in train_loader:
            optimizer.zero_grad()
            logits = model(X)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
    
    # Test
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for X, y in test_loader:
            logits = model(X)
            pred = logits.argmax(dim=1)
            correct += (pred == y).sum().item()
            total += y.size(0)
    
    return correct / total


def main():
    print("="*70)
    print("ABLATION STUDY: T/L_in Threshold Across Scales")
    print("="*70)
    print()
    print("Testing whether T/L_in ~ 20-25 threshold holds across:")
    print("  - Different context lengths (L_in)")
    print("  - Different training sizes (N_train)")
    print("  - Different model capacities (hidden)")
    print()
    
    # Generate sequences with different periods
    A0 = np.array([[1,1],[3,1]])
    A1 = np.array([[3,3],[1,3]])
    b0 = np.array([1,2])
    b1 = np.array([2,1])
    
    configs = [
        (5, 1, 25, "p5k1sat"),    # T=25 (easy)
        (5, 2, 212, "p5k2sat"),   # T=212 (medium)
        (5, 3, 7295, "p5k3sat"),  # T=7295 (hard)
    ]
    
    # Ablation parameters
    L_in_values = [6, 12, 24]
    N_train_values = [1800, 3600, 7200]
    hidden_values = [64, 128, 256]
    
    results = []
    
    print("Generating sequences...")
    sequences = {}
    for p, k, T, name in configs:
        m = p ** k
        # Use sat=True for Hensel-satisfied sequences
        seq = generate_sequence(m, sat=True, N=15000, burn=300, seed=42)
        sequences[name] = (seq, m, T)
        print(f"  {name}: m={m}, T={T}")
    
    print()
    print("="*70)
    print("Running ablation study...")
    print("="*70)
    
    # Baseline: original setup
    print("\nBASELINE (L_in=6, N_train=3600, hidden=128):")
    print("-"*70)
    for name, (seq, m, T) in sequences.items():
        acc = train_and_test(seq, m, L_in=6, N_train=3600, hidden=128)
        ratio = T / 6
        results.append({
            'config': name,
            'T': T,
            'L_in': 6,
            'N_train': 3600,
            'hidden': 128,
            'T/L_in': ratio,
            'accuracy': acc
        })
        print(f"  {name:12s}: T={T:5d}, T/L_in={ratio:6.1f}, acc={acc*100:5.1f}%")
    
    # Ablation 1: Vary L_in
    print("\nABLATION 1: Vary context length (L_in)")
    print("-"*70)
    for L_in in L_in_values:
        if L_in == 6:
            continue  # Already done in baseline
        print(f"\nL_in={L_in}, N_train=3600, hidden=128:")
        for name, (seq, m, T) in sequences.items():
            acc = train_and_test(seq, m, L_in=L_in, N_train=3600, hidden=128)
            ratio = T / L_in
            results.append({
                'config': name,
                'T': T,
                'L_in': L_in,
                'N_train': 3600,
                'hidden': 128,
                'T/L_in': ratio,
                'accuracy': acc
            })
            print(f"  {name:12s}: T={T:5d}, T/L_in={ratio:6.1f}, acc={acc*100:5.1f}%")
    
    # Ablation 2: Vary N_train
    print("\nABLATION 2: Vary training size (N_train)")
    print("-"*70)
    for N_train in N_train_values:
        if N_train == 3600:
            continue  # Already done in baseline
        print(f"\nL_in=6, N_train={N_train}, hidden=128:")
        for name, (seq, m, T) in sequences.items():
            acc = train_and_test(seq, m, L_in=6, N_train=N_train, hidden=128)
            ratio = T / 6
            results.append({
                'config': name,
                'T': T,
                'L_in': 6,
                'N_train': N_train,
                'hidden': 128,
                'T/L_in': ratio,
                'accuracy': acc
            })
            print(f"  {name:12s}: T={T:5d}, T/L_in={ratio:6.1f}, acc={acc*100:5.1f}%")
    
    # Ablation 3: Vary hidden
    print("\nABLATION 3: Vary model capacity (hidden)")
    print("-"*70)
    for hidden in hidden_values:
        if hidden == 128:
            continue  # Already done in baseline
        print(f"\nL_in=6, N_train=3600, hidden={hidden}:")
        for name, (seq, m, T) in sequences.items():
            acc = train_and_test(seq, m, L_in=6, N_train=3600, hidden=hidden)
            ratio = T / 6
            results.append({
                'config': name,
                'T': T,
                'L_in': 6,
                'N_train': 3600,
                'hidden': hidden,
                'T/L_in': ratio,
                'accuracy': acc
            })
            print(f"  {name:12s}: T={T:5d}, T/L_in={ratio:6.1f}, acc={acc*100:5.1f}%")
    
    # Analysis
    print("\n" + "="*70)
    print("ANALYSIS: Does threshold hold across scales?")
    print("="*70)
    
    # Find threshold for each configuration
    print("\nThreshold analysis (where accuracy drops below 80%):")
    print("-"*70)
    
    for L_in in [6, 12, 24]:
        for N_train in [1800, 3600, 7200]:
            for hidden in [64, 128, 256]:
                subset = [r for r in results if r['L_in'] == L_in and 
                         r['N_train'] == N_train and r['hidden'] == hidden]
                if not subset:
                    continue
                
                # Find where accuracy drops
                threshold_ratio = None
                for r in sorted(subset, key=lambda x: x['T/L_in']):
                    if r['accuracy'] < 0.8:
                        threshold_ratio = r['T/L_in']
                        break
                
                if threshold_ratio:
                    print(f"L_in={L_in:2d}, N_train={N_train:4d}, hidden={hidden:3d}: "
                          f"threshold T/L_in ~ {threshold_ratio:.1f}")
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("If threshold varies significantly across configurations,")
    print("then the '21' constant is an artifact of hyperparameters.")
    print("If threshold remains ~20-25 across scales, then it's more fundamental.")
    print("="*70)


if __name__ == "__main__":
    main()
