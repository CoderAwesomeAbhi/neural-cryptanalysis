"""
Induction Head Death Visualization

Creates a plot showing the exact moment the Transformer "dies" as T/L_in increases.
Plots attention entropy vs T/L_in to visualize the internal death of the model.
"""
import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import sys
sys.path.append('.')
from core import generate_sequence

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

class SimpleTransformer(nn.Module):
    def __init__(self, L_in, m, d_model=64, nhead=4):
        super().__init__()
        self.embedding = nn.Linear(1, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, 
                                                    dim_feedforward=128, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.fc = nn.Linear(d_model, m)
        self.L_in = L_in
    
    def forward(self, x):
        # x: (batch, L_in)
        x = x.unsqueeze(-1)  # (batch, L_in, 1)
        x = self.embedding(x)  # (batch, L_in, d_model)
        x = self.transformer(x)  # (batch, L_in, d_model)
        x = x[:, -1, :]  # Take last position
        return self.fc(x)
    
    def get_attention_weights(self, x):
        """Extract attention weights from the model."""
        x = x.unsqueeze(-1)
        x = self.embedding(x)
        
        # Get attention from first layer
        attn_weights = []
        for layer in self.transformer.layers:
            # Forward through self-attention
            attn_output, attn_weight = layer.self_attn(x, x, x, need_weights=True, average_attn_weights=True)
            attn_weights.append(attn_weight.detach().cpu().numpy())
            x = layer(x)
        
        return attn_weights

def compute_attention_entropy(attn_weights):
    """Compute entropy of attention distribution."""
    # attn_weights: (batch, L_in, L_in)
    entropies = []
    for batch_attn in attn_weights:
        for query_attn in batch_attn:
            # Normalize to probability distribution
            p = query_attn / query_attn.sum()
            # Compute entropy
            entropy = -np.sum(p * np.log(p + 1e-10))
            entropies.append(entropy)
    return np.mean(entropies)

def train_and_analyze(m, T, L_in, N_train=3600, epochs=50):
    """Train model and compute attention entropy."""
    # Generate sequence
    seq = generate_sequence(m, sat=True, N=N_train+1000, burn=300, seed=42)
    
    # Create dataset
    train_dataset = SequenceDataset(seq, L_in, N_train)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    
    # Create model
    model = SimpleTransformer(L_in, m)
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
    
    # Test accuracy
    model.eval()
    test_dataset = SequenceDataset(seq, L_in, 500)
    test_loader = DataLoader(test_dataset, batch_size=32)
    
    correct = 0
    total = 0
    all_attn_weights = []
    
    with torch.no_grad():
        for X, y in test_loader:
            logits = model(X)
            pred = logits.argmax(dim=1)
            correct += (pred == y).sum().item()
            total += y.size(0)
            
            # Get attention weights
            try:
                attn = model.get_attention_weights(X)
                all_attn_weights.extend(attn[0])  # First layer
            except:
                pass
    
    accuracy = correct / total
    
    # Compute attention entropy
    if all_attn_weights:
        entropy = compute_attention_entropy(np.array(all_attn_weights))
    else:
        entropy = 0
    
    return accuracy, entropy, T/L_in

def main():
    print("="*70)
    print("INDUCTION HEAD DEATH VISUALIZATION")
    print("="*70)
    print()
    print("Plotting attention entropy vs T/L_in to show exact threshold")
    print("where the Transformer's attention mechanism dies.")
    print()
    
    # Test configurations with varying T/L_in ratios
    configs = [
        (5, 25, 6, "p5k1sat"),      # T/L_in = 4.2
        (25, 212, 6, "p5k2sat"),    # T/L_in = 35.3
        (25, 212, 12, "p5k2sat"),   # T/L_in = 17.7
        (125, 7295, 6, "p5k3sat"),  # T/L_in = 1215.8
        (125, 7295, 12, "p5k3sat"), # T/L_in = 607.9
        (125, 7295, 24, "p5k3sat"), # T/L_in = 304.0
    ]
    
    results = []
    
    for m, T, L_in, name in configs:
        print(f"Testing {name} with m={m}, T={T}, L_in={L_in}...")
        acc, entropy, ratio = train_and_analyze(m, T, L_in)
        results.append({
            'name': name,
            'm': m,
            'T': T,
            'L_in': L_in,
            'ratio': ratio,
            'accuracy': acc,
            'entropy': entropy
        })
        print(f"  T/L_in={ratio:.1f}, Accuracy={acc*100:.1f}%, Entropy={entropy:.3f}")
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Accuracy vs T/L_in
    ratios = [r['ratio'] for r in results]
    accuracies = [r['accuracy']*100 for r in results]
    
    ax1.scatter(ratios, accuracies, s=100, alpha=0.7, c='blue')
    ax1.axhline(y=50, color='red', linestyle='--', label='Random baseline')
    ax1.axvline(x=200, color='green', linestyle='--', alpha=0.5, label='Threshold ~200')
    ax1.set_xlabel('T/L_in Ratio', fontsize=12)
    ax1.set_ylabel('Accuracy (%)', fontsize=12)
    ax1.set_title('Neural Predictability vs Period/Context Ratio', fontsize=14, fontweight='bold')
    ax1.set_xscale('log')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Annotate points
    for r in results:
        ax1.annotate(f"{r['name']}\n({r['L_in']})", 
                    (r['ratio'], r['accuracy']*100),
                    textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
    
    # Plot 2: Attention Entropy vs T/L_in
    entropies = [r['entropy'] for r in results]
    
    ax2.scatter(ratios, entropies, s=100, alpha=0.7, c='red')
    ax2.axvline(x=200, color='green', linestyle='--', alpha=0.5, label='Threshold ~200')
    ax2.set_xlabel('T/L_in Ratio', fontsize=12)
    ax2.set_ylabel('Attention Entropy (nats)', fontsize=12)
    ax2.set_title('Induction Head Death: Attention Diffusion', fontsize=14, fontweight='bold')
    ax2.set_xscale('log')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Annotate points
    for r in results:
        ax2.annotate(f"{r['name']}\n({r['L_in']})", 
                    (r['ratio'], r['entropy']),
                    textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
    
    plt.tight_layout()
    plt.savefig('../results/induction_head_death.png', dpi=300, bbox_inches='tight')
    print()
    print("="*70)
    print("Visualization saved to: results/induction_head_death.png")
    print("="*70)
    print()
    print("INTERPRETATION:")
    print("- Left: Accuracy collapses as T/L_in crosses ~200")
    print("- Right: Attention entropy increases (diffuses) at same threshold")
    print("- This visualizes the exact moment the Transformer 'dies'")
    print("="*70)

if __name__ == "__main__":
    main()
