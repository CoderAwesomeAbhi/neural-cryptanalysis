#!/usr/bin/env python3
"""Quick grokking test - 3 configurations"""
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

class MLP(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size), nn.ReLU(),
            nn.Linear(hidden_size, hidden_size), nn.ReLU(),
            nn.Linear(hidden_size, output_size)
        )
    def forward(self, x): return self.net(x)

class SeqDataset(Dataset):
    def __init__(self, seq, L): self.seq, self.L = seq, L
    def __len__(self): return len(self.seq) - self.L
    def __getitem__(self, i): return torch.FloatTensor(self.seq[i:i+self.L]), torch.LongTensor([self.seq[i+self.L]])

def grok_test(T, L_in=6, epochs=2000):
    seq = np.tile(np.random.randint(0, 10, T), 4)
    train, test = seq[:len(seq)//2], seq[len(seq)//2:]
    train_dl = DataLoader(SeqDataset(train, L_in), 32, True)
    test_dl = DataLoader(SeqDataset(test, L_in), 32)
    
    model = MLP(L_in, 128, 10)
    opt = torch.optim.Adam(model.parameters(), 0.001)
    crit = nn.CrossEntropyLoss()
    
    accs = []
    for ep in range(epochs):
        for x, y in train_dl:
            opt.zero_grad()
            crit(model(x), y.squeeze()).backward()
            opt.step()
        
        if ep % 500 == 0 or ep == epochs-1:
            model.eval()
            correct = sum((model(x).argmax(1) == y.squeeze()).sum().item() for x, y in test_dl)
            total = sum(y.size(0) for _, y in test_dl)
            acc = correct / total if total > 0 else 0
            accs.append((ep, acc))
            print(f"  Epoch {ep:>4}: {acc:.1%}")
            model.train()
    
    return accs

print("="*60)
print("QUICK GROKKING TEST - FULL PERIOD COVERAGE")
print("="*60)

configs = [("Easy", 25), ("Medium", 50), ("Hard", 100)]
for name, T in configs:
    print(f"\n{name}: T={T}, T/Lin={T/6:.1f}")
    print("-"*60)
    accs = grok_test(T)
    final = accs[-1][1]
    grokked = "YES" if final > 0.7 else "NO"
    print(f"Final: {final:.1%} - Grokked: {grokked}")

print("\n" + "="*60)
print("If grokking occurs -> Optimization barrier")
print("If no grokking -> Mechanistic barrier (induction heads)")
