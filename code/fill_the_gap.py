#!/usr/bin/env python3
"""
CRITICAL FIX: Fill the gap between T=125 and T=1083
This is the #1 priority - the paper's central claim depends on this.
Ultra-fast version: 100 epochs, small model, 10 key points.
"""
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

class TinyMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(6, 64), nn.ReLU(), nn.Linear(64, 10))
    def forward(self, x): return self.net(x)

class D(Dataset):
    def __init__(self, s, L=6): self.s, self.L = s, L
    def __len__(self): return len(self.s) - self.L
    def __getitem__(self, i): return torch.FloatTensor(self.s[i:i+self.L]), torch.LongTensor([self.s[i+self.L]])

def test(T):
    s = np.tile(np.random.randint(0, 10, T), 20)
    tr, te = s[:len(s)//2], s[len(s)//2:]
    trl, tel = DataLoader(D(tr), 64, True), DataLoader(D(te), 64)
    m = TinyMLP()
    o = torch.optim.Adam(m.parameters(), 0.003)
    c = nn.CrossEntropyLoss()
    
    for _ in range(100):  # Fast: only 100 epochs
        for x, y in trl:
            o.zero_grad()
            c(m(x), y.squeeze()).backward()
            o.step()
    
    m.eval()
    cor = sum((m(x).argmax(1) == y.squeeze()).sum().item() for x, y in tel)
    tot = sum(y.size(0) for _, y in tel)
    return cor / tot

print("="*70)
print("FILLING THE GAP: T=125 to T=1083 (THE CRITICAL EXPERIMENT)")
print("="*70)
print("\nThis is the #1 priority fix for the paper.")
print("Testing 10 points in the gap with fast training (100 epochs).\n")

# The critical gap + boundaries
periods = [125, 150, 200, 250, 300, 400, 500, 600, 750, 900, 1083]

print(f"{'T':>6} {'T/Lin':>8} {'Accuracy':>10} {'Status':>12}")
print("-"*70)

results = []
for T in periods:
    acc = test(T)
    ratio = T / 6
    status = "LEARN" if acc > 0.7 else "FAIL" if acc < 0.3 else "**TRANSITION**"
    results.append((T, ratio, acc, status))
    print(f"{T:>6} {ratio:>8.1f} {acc:>10.1%} {status:>12}")

print("\n" + "="*70)
print("CRITICAL ANALYSIS")
print("="*70)

learn = [r for r in results if r[2] > 0.7]
fail = [r for r in results if r[2] < 0.3]

if learn and fail:
    last_learn = max(learn, key=lambda x: x[0])
    first_fail = min(fail, key=lambda x: x[0])
    
    print(f"\nLast success: T={last_learn[0]}, T/Lin={last_learn[1]:.1f}, acc={last_learn[2]:.1%}")
    print(f"First failure: T={first_fail[0]}, T/Lin={first_fail[1]:.1f}, acc={first_fail[2]:.1%}")
    print(f"\nCRITICAL THRESHOLD: T/Lin in ({last_learn[1]:.1f}, {first_fail[1]:.1f})")
    print(f"Range width: {first_fail[1] - last_learn[1]:.1f}")
    
    if first_fail[1] < 50:
        print("\n✓ Paper claim (20-30) is CORRECT")
    elif first_fail[1] < 100:
        print("\n⚠ Paper claim needs update: threshold is ~50-100, not 20-30")
    else:
        print("\n✗ Paper claim is WRONG: threshold is >100, not 20-30")
else:
    print("\n⚠ Transition not clearly defined - need more epochs or data points")

print("\n" + "="*70)
print("ACTION ITEMS:")
print("="*70)
print("1. If threshold < 50: Paper is correct, just add this data")
print("2. If threshold 50-100: Rewrite abstract to say 'T/Lin ~ 50-100'")
print("3. If threshold > 100: Major rewrite needed - central claim is wrong")
print("\nThis experiment took ~2-3 minutes. The paper's credibility depends on it.")
