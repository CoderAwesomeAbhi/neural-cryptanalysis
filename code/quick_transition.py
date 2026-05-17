#!/usr/bin/env python3
"""Quick transition test - 10 key configurations"""
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

class MLP(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size), nn.ReLU(),
            nn.Linear(hidden_size, output_size)
        )
    def forward(self, x): return self.net(x)

class SeqDataset(Dataset):
    def __init__(self, seq, L): self.seq, self.L = seq, L
    def __len__(self): return len(self.seq) - self.L
    def __getitem__(self, i): return torch.FloatTensor(self.seq[i:i+self.L]), torch.LongTensor([self.seq[i+self.L]])

def test_period(T, L_in=6, epochs=200):
    seq = np.tile(np.random.randint(0, 10, T), 10)
    train, test = seq[:len(seq)//2], seq[len(seq)//2:]
    train_dl = DataLoader(SeqDataset(train, L_in), 32, True)
    test_dl = DataLoader(SeqDataset(test, L_in), 32)
    
    model = MLP(L_in, 64, 10)
    opt = torch.optim.Adam(model.parameters(), 0.001)
    crit = nn.CrossEntropyLoss()
    
    for _ in range(epochs):
        for x, y in train_dl:
            opt.zero_grad()
            crit(model(x), y.squeeze()).backward()
            opt.step()
    
    model.eval()
    correct = sum((model(x).argmax(1) == y.squeeze()).sum().item() for x, y in test_dl)
    total = sum(y.size(0) for _, y in test_dl)
    return correct / total if total > 0 else 0

print("="*60)
print("QUICK TRANSITION TEST - 10 KEY CONFIGURATIONS")
print("="*60)
periods = [20, 30, 50, 80, 100, 150, 200, 300, 500, 1000]
print(f"{'T':>6} {'T/Lin':>8} {'Acc':>8} {'Status':>10}")
print("-"*60)

results = []
for T in periods:
    acc = test_period(T)
    status = "LEARN" if acc > 0.7 else "FAIL" if acc < 0.3 else "TRANS"
    results.append((T, T/6, acc, status))
    print(f"{T:>6} {T/6:>8.1f} {acc:>8.1%} {status:>10}")

learn = [r for r in results if r[3] == "LEARN"]
fail = [r for r in results if r[3] == "FAIL"]
if learn and fail:
    print(f"\nTransition: T/Lin in ({max(learn, key=lambda x:x[0])[1]:.1f}, {min(fail, key=lambda x:x[0])[1]:.1f})")
