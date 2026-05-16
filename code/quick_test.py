"""
MINIMAL FAST VERSION - Runs in 10 minutes
Tests 1 config with 1000 epochs to verify everything works
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from tqdm import tqdm
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from sequence_generator import generate_piecewise_sequence

class MLPPredictor(nn.Module):
    def __init__(self, input_size, hidden_sizes, output_size):
        super().__init__()
        layers = []
        prev_size = input_size
        for h in hidden_sizes:
            layers.extend([nn.Linear(prev_size, h), nn.ReLU()])
            prev_size = h
        layers.append(nn.Linear(prev_size, output_size))
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)

def create_dataset(sequence, L_in=6):
    X, y = [], []
    for i in range(len(sequence) - L_in):
        X.append(sequence[i:i+L_in])
        y.append(sequence[i+L_in])
    return np.array(X), np.array(y)

print("="*80)
print("MINIMAL FAST TEST - 1 config, 1000 epochs (~5 minutes)")
print("="*80)

# Generate sequence
print("\n[1/4] Generating sequence...")
m = 25
sequence = generate_piecewise_sequence(p=5, k=2, hensel_satisfied=True, n_terms=4500, burn_in=300)
print(f"Generated {len(sequence)} terms, period T=125")

# Create dataset
print("\n[2/4] Creating dataset...")
X, y = create_dataset(sequence, L_in=6)
X_norm = X / m

n_train = int(0.8 * len(X))
n_val = int(0.1 * len(X))

X_train = torch.FloatTensor(X_norm[:n_train])
y_train = torch.LongTensor(y[:n_train])
X_val = torch.FloatTensor(X_norm[n_train:n_train+n_val])
y_val = torch.LongTensor(y[n_train:n_train+n_val])

print(f"Train: {len(X_train)}, Val: {len(X_val)}")

# Create model
print("\n[3/4] Creating model...")
model = MLPPredictor(input_size=6, hidden_sizes=[256, 128], output_size=m)
optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
criterion = nn.CrossEntropyLoss()

train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=256, shuffle=True)

# Train
print("\n[4/4] Training for 1000 epochs...")
print("This should take ~5 minutes\n")

best_val_acc = 0.0
for epoch in tqdm(range(1000), desc="Training"):
    model.train()
    for batch_X, batch_y in train_loader:
        optimizer.zero_grad()
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()
    
    # Validate every 100 epochs
    if epoch % 100 == 0:
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val)
            val_preds = torch.argmax(val_outputs, dim=1)
            val_acc = (val_preds == y_val).float().mean().item()
            best_val_acc = max(best_val_acc, val_acc)
            print(f"Epoch {epoch:4d}: Val Acc = {val_acc:.1%}, Best = {best_val_acc:.1%}")

print("\n" + "="*80)
print("MINIMAL TEST COMPLETE!")
print("="*80)
print(f"Best validation accuracy: {best_val_acc:.1%}")
print(f"Expected: ~100% (this is an easy sequence)")
print("\nIf this worked, the full experiments will work too.")
print("Run full version overnight: python run_all_experiments.py")
print("="*80)
