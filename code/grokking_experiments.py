#!/usr/bin/env python3
"""
Grokking Experiments - Full Period Coverage
============================================
Train for 10,000 epochs on sequences where N_train = T
to test if networks can "grok" the pattern with enough time.
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt

class MLP(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, output_size)
        )
    
    def forward(self, x):
        return self.net(x)

class SequenceDataset(Dataset):
    def __init__(self, sequence, L_in):
        self.sequence = sequence
        self.L_in = L_in
    
    def __len__(self):
        return len(self.sequence) - self.L_in
    
    def __getitem__(self, idx):
        x = torch.FloatTensor(self.sequence[idx:idx+self.L_in])
        y = torch.LongTensor([self.sequence[idx+self.L_in]])
        return x, y

def generate_periodic_sequence(period, length, vocab_size=10):
    """Generate periodic sequence"""
    base = np.random.randint(0, vocab_size, period)
    full = np.tile(base, (length // period) + 1)
    return full[:length]

def train_with_logging(sequence, L_in=6, epochs=10000, batch_size=32, log_every=100):
    """Train and log accuracy over time"""
    T = len(np.unique(sequence))
    N_train = len(sequence) // 2
    
    train_seq = sequence[:N_train]
    test_seq = sequence[N_train:]
    
    train_dataset = SequenceDataset(train_seq, L_in)
    test_dataset = SequenceDataset(test_seq, L_in)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)
    
    model = MLP(L_in, 256, 10)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    train_accs = []
    test_accs = []
    epochs_logged = []
    
    for epoch in range(epochs):
        # Train
        model.train()
        train_correct = 0
        train_total = 0
        for x, y in train_loader:
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y.squeeze())
            loss.backward()
            optimizer.step()
            
            pred = out.argmax(dim=1)
            train_correct += (pred == y.squeeze()).sum().item()
            train_total += y.size(0)
        
        # Test
        if epoch % log_every == 0 or epoch == epochs - 1:
            model.eval()
            test_correct = 0
            test_total = 0
            with torch.no_grad():
                for x, y in test_loader:
                    out = model(x)
                    pred = out.argmax(dim=1)
                    test_correct += (pred == y.squeeze()).sum().item()
                    test_total += y.size(0)
            
            train_acc = train_correct / train_total if train_total > 0 else 0
            test_acc = test_correct / test_total if test_total > 0 else 0
            
            train_accs.append(train_acc)
            test_accs.append(test_acc)
            epochs_logged.append(epoch)
            
            if epoch % 1000 == 0:
                print(f"Epoch {epoch:>5}: Train={train_acc:.1%}, Test={test_acc:.1%}")
    
    return epochs_logged, train_accs, test_accs

def main():
    print("="*70)
    print("GROKKING EXPERIMENTS - FULL PERIOD COVERAGE")
    print("="*70)
    print()
    
    L_in = 6
    
    # Test configurations with full period coverage (N_train = T)
    configs = [
        ("Easy", 25, 25),      # T=25, N_train=25 (full coverage)
        ("Medium", 50, 50),    # T=50, N_train=50
        ("Hard", 100, 100),    # T=100, N_train=100
        ("Very Hard", 200, 200), # T=200, N_train=200
    ]
    
    results = {}
    
    for name, T, N_train in configs:
        print(f"\n{'='*70}")
        print(f"Configuration: {name}")
        print(f"Period T={T}, N_train={N_train}, T/Lin={T/L_in:.1f}")
        print(f"{'='*70}")
        
        # Generate sequence with exactly T period
        seq = generate_periodic_sequence(T, N_train * 2)
        
        # Train with logging
        epochs, train_accs, test_accs = train_with_logging(
            seq, L_in=L_in, epochs=10000, log_every=100
        )
        
        results[name] = {
            'epochs': epochs,
            'train': train_accs,
            'test': test_accs,
            'T': T,
            'final_test': test_accs[-1]
        }
        
        print(f"\nFinal: Train={train_accs[-1]:.1%}, Test={test_accs[-1]:.1%}")
        
        # Check for grokking (train high, test catches up)
        if train_accs[-1] > 0.9 and test_accs[-1] > 0.7:
            print("✓ GROKKING OBSERVED")
        elif test_accs[-1] < 0.3:
            print("✗ NO GROKKING - Optimization barrier")
        else:
            print("~ PARTIAL - Some generalization")
    
    # Summary
    print("\n" + "="*70)
    print("GROKKING SUMMARY")
    print("="*70)
    print(f"{'Config':>12} {'T':>6} {'T/Lin':>8} {'Final Test':>12} {'Grokked?':>10}")
    print("-"*70)
    
    for name, data in results.items():
        T = data['T']
        ratio = T / L_in
        final = data['final_test']
        grokked = "YES" if final > 0.7 else "NO"
        print(f"{name:>12} {T:>6} {ratio:>8.1f} {final:>12.1%} {grokked:>10}")
    
    print()
    print("="*70)
    print("CONCLUSION")
    print("="*70)
    print()
    print("If grokking occurs (test acc > 70% after 10k epochs):")
    print("  → Barrier is OPTIMIZATION, not information-theoretic")
    print()
    print("If no grokking (test acc < 30% even with full coverage):")
    print("  → Barrier is MECHANISTIC (induction heads can't form)")
    print()
    print("Results show which barrier dominates at each T/Lin ratio.")
    
    # Save results
    with open("grokking_results.txt", "w") as f:
        f.write("Config,T,T_Lin,Final_Test,Grokked\n")
        for name, data in results.items():
            T = data['T']
            ratio = T / L_in
            final = data['final_test']
            grokked = "YES" if final > 0.7 else "NO"
            f.write(f"{name},{T},{ratio:.1f},{final:.4f},{grokked}\n")
    
    print("\nResults saved to grokking_results.txt")

if __name__ == '__main__':
    main()
