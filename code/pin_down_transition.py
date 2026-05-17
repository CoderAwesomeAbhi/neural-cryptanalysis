#!/usr/bin/env python3
"""
Pin Down Phase Transition - 50+ Configurations
==============================================
Generate sequences with periods spanning T/Lin = 20 to 180
to precisely locate the critical threshold.
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# Simple MLP for fast testing
class SimpleMLP(nn.Module):
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
    """Generate periodic sequence with given period"""
    base = np.random.randint(0, vocab_size, period)
    full = np.tile(base, (length // period) + 1)
    return full[:length]

def train_and_test(sequence, L_in=6, epochs=500, batch_size=32):
    """Train MLP and return test accuracy"""
    T = len(np.unique(sequence))  # Approximate period
    N_train = len(sequence) // 2
    
    train_seq = sequence[:N_train]
    test_seq = sequence[N_train:]
    
    train_dataset = SequenceDataset(train_seq, L_in)
    test_dataset = SequenceDataset(test_seq, L_in)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)
    
    model = SimpleMLP(L_in, 128, 10)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # Train
    model.train()
    for epoch in range(epochs):
        for x, y in train_loader:
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y.squeeze())
            loss.backward()
            optimizer.step()
    
    # Test
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for x, y in test_loader:
            out = model(x)
            pred = out.argmax(dim=1)
            correct += (pred == y.squeeze()).sum().item()
            total += y.size(0)
    
    return correct / total if total > 0 else 0.0

def main():
    print("="*70)
    print("PINNING DOWN PHASE TRANSITION - 50+ CONFIGURATIONS")
    print("="*70)
    print()
    
    L_in = 6
    N_train = 3600
    
    # Generate 50+ periods spanning the transition range
    periods = [
        # Below transition (should succeed)
        20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100,
        # Transition zone (critical range)
        110, 120, 130, 140, 150, 160, 170, 180, 190, 200,
        220, 240, 260, 280, 300, 320, 340, 360, 380, 400,
        # Above transition (should fail)
        450, 500, 550, 600, 650, 700, 750, 800, 850, 900,
        950, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1800, 2000
    ]
    
    print(f"Testing {len(periods)} configurations")
    print(f"L_in = {L_in}, N_train = {N_train}")
    print()
    print(f"{'Period':>8} {'T/Lin':>8} {'Accuracy':>10} {'Status':>10}")
    print("-"*70)
    
    results = []
    for T in periods:
        ratio = T / L_in
        seq = generate_periodic_sequence(T, N_train * 2)
        acc = train_and_test(seq, L_in=L_in, epochs=300)
        
        status = "LEARN" if acc > 0.8 else "FAIL" if acc < 0.3 else "TRANSITION"
        results.append((T, ratio, acc, status))
        
        print(f"{T:>8} {ratio:>8.1f} {acc:>10.1%} {status:>10}")
    
    # Find transition point
    print()
    print("="*70)
    print("TRANSITION ANALYSIS")
    print("="*70)
    
    learn_configs = [r for r in results if r[3] == "LEARN"]
    fail_configs = [r for r in results if r[3] == "FAIL"]
    
    if learn_configs and fail_configs:
        max_learn = max(learn_configs, key=lambda x: x[0])
        min_fail = min(fail_configs, key=lambda x: x[0])
        
        print(f"Last successful: T={max_learn[0]}, T/Lin={max_learn[1]:.1f}, acc={max_learn[2]:.1%}")
        print(f"First failure: T={min_fail[0]}, T/Lin={min_fail[1]:.1f}, acc={min_fail[2]:.1%}")
        print()
        print(f"CRITICAL THRESHOLD: T/Lin in ({max_learn[1]:.1f}, {min_fail[1]:.1f})")
        print(f"Range width: {min_fail[1] - max_learn[1]:.1f}")
    
    # Save results
    with open("transition_results.txt", "w") as f:
        f.write("Period,T_Lin,Accuracy,Status\n")
        for T, ratio, acc, status in results:
            f.write(f"{T},{ratio:.1f},{acc:.4f},{status}\n")
    
    print()
    print("Results saved to transition_results.txt")

if __name__ == '__main__':
    main()
