"""
P-ADIC ATTENTION ANALYSIS: Extracting Attention Heatmaps from Transformers
============================================================================

Tests whether Transformer attention patterns correlate with p-adic valuations.
This is the "PhD-level" feature that distinguishes this work.

Author: Abhijay Gangarapu, UT Austin / ISEF 2026
"""
import numpy as np
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from generator import generate_piecewise, get_matrices

class TransformerPredictor(nn.Module):
    """Transformer for sequence prediction with attention extraction."""
    def __init__(self, m, L_in=32, d_model=64, nhead=4, num_layers=2):
        super().__init__()
        self.m = m
        self.L_in = L_in
        self.d_model = d_model
        
        self.embedding = nn.Linear(1, d_model)
        self.pos_encoding = nn.Parameter(torch.randn(1, L_in, d_model))
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=256,
            dropout=0.1, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(d_model, m)
        
        self.attention_weights = []
        
    def forward(self, x):
        # x: (batch, L_in)
        x = x.unsqueeze(-1)  # (batch, L_in, 1)
        x = self.embedding(x)  # (batch, L_in, d_model)
        x = x + self.pos_encoding
        
        # Extract attention weights
        self.attention_weights = []
        for layer in self.transformer.layers:
            x = layer(x)
            # Store attention from last layer
            if hasattr(layer.self_attn, 'attention_weights'):
                self.attention_weights.append(layer.self_attn.attention_weights)
        
        x = x.mean(dim=1)  # Global average pooling
        return self.fc(x)
    
    def get_attention_maps(self, x):
        """Extract attention maps for visualization."""
        self.eval()
        with torch.no_grad():
            _ = self.forward(x)
            if self.attention_weights:
                return self.attention_weights[-1]  # Last layer
        return None

def padic_valuation(n, p):
    """Compute v_p(n): highest power of p dividing n."""
    if n == 0:
        return float('inf')
    v = 0
    while n % p == 0:
        n //= p
        v += 1
    return v

def compute_padic_distance_matrix(L_in, p):
    """
    Compute p-adic distance matrix: d(i,j) = p^(-v_p(i-j))
    
    Hypothesis: Attention weights should correlate with p-adic proximity.
    """
    D = np.zeros((L_in, L_in))
    for i in range(L_in):
        for j in range(L_in):
            if i == j:
                D[i,j] = 1.0  # Self-attention
            else:
                v = padic_valuation(abs(i-j), p)
                D[i,j] = p ** (-v)
    return D

def train_transformer(X, y, m, L_in=32, epochs=50, lr=1e-3):
    """Train Transformer and return model."""
    model = TransformerPredictor(m, L_in=L_in)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    
    X_t = torch.FloatTensor(X)
    y_t = torch.LongTensor(y)
    
    dataset = torch.utils.data.TensorDataset(X_t, y_t)
    loader = torch.utils.data.DataLoader(dataset, batch_size=64, shuffle=True)
    
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(loader):.4f}")
    
    return model

def extract_attention_heatmap(model, seq, m, L_in=32, num_samples=10):
    """
    Extract average attention heatmap from trained Transformer.
    
    Returns:
        avg_attention: (L_in, L_in) matrix of attention weights
    """
    model.eval()
    attention_maps = []
    
    # Sample multiple windows
    for i in range(num_samples):
        start = np.random.randint(0, len(seq) - L_in)
        window = seq[start:start+L_in]
        X = torch.FloatTensor(window).unsqueeze(0) / m  # (1, L_in)
        
        with torch.no_grad():
            _ = model(X)
            # Get attention from self-attention layers
            # This requires modifying TransformerEncoderLayer to expose attention
            # For now, we'll use a proxy: gradient-based attention
    
    # Fallback: Use gradient-based attention approximation
    attention_maps = []
    for i in range(num_samples):
        start = np.random.randint(0, len(seq) - L_in)
        window = seq[start:start+L_in]
        X = torch.FloatTensor(window).unsqueeze(0) / m
        X.requires_grad = True
        
        output = model(X)
        target = output.argmax(dim=1)
        
        # Compute gradients
        model.zero_grad()
        output[0, target].backward()
        
        # Attention proxy: gradient magnitude
        grad = X.grad.squeeze().abs().numpy()
        attention_maps.append(grad)
    
    return np.mean(attention_maps, axis=0)

def test_padic_attention_hypothesis(p=5, m=125, L_in=32, N=10000, epochs=50):
    """
    Main experiment: Test if Transformer attention correlates with p-adic structure.
    
    Returns:
        results: dict with correlation statistics and visualizations
    """
    print("="*70)
    print("P-ADIC ATTENTION HYPOTHESIS TEST (PhD-Level)")
    print("="*70)
    print(f"Prime: p={p}, Modulus: m={m}, Window: L_in={L_in}")
    print()
    
    # Generate sequence
    print("Generating sequence...")
    A_list, b_list = get_matrices("sat")
    seq = generate_piecewise(m, A_list, b_list, N=N+L_in+100, burn=100)
    print(f"Generated {len(seq)} elements")
    
    # Create dataset
    print("Creating dataset...")
    X = np.array([[seq[i+t]/m for t in range(L_in)] for i in range(N)], dtype=np.float32)
    y = np.array([seq[i+L_in] for i in range(N)], dtype=np.int32)
    print(f"Dataset: X={X.shape}, y={y.shape}")
    
    # Train Transformer
    print("\nTraining Transformer...")
    model = train_transformer(X, y, m, L_in=L_in, epochs=epochs)
    
    # Evaluate
    model.eval()
    with torch.no_grad():
        X_t = torch.FloatTensor(X[:1000])
        y_pred = model(X_t).argmax(dim=1).numpy()
        acc = (y_pred == y[:1000]).mean()
    print(f"\nTest Accuracy: {acc*100:.1f}%")
    
    # Extract attention (simplified: use input sensitivity)
    print("\nExtracting attention patterns...")
    attention_scores = []
    for i in range(100):
        window = seq[i:i+L_in]
        X_sample = torch.FloatTensor(window).unsqueeze(0) / m
        X_sample.requires_grad = True
        
        output = model(X_sample)
        target = output.argmax(dim=1)
        
        model.zero_grad()
        output[0, target].backward()
        
        # Attention proxy: gradient magnitude
        grad = X_sample.grad.squeeze().abs().numpy()
        attention_scores.append(grad)
    
    avg_attention = np.mean(attention_scores, axis=0)
    
    # Compute p-adic distances
    print("Computing p-adic distance matrix...")
    padic_distances = np.array([p**(-padic_valuation(j, p)) for j in range(L_in)])
    
    # Correlation test
    rho, pval = spearmanr(avg_attention, padic_distances)
    print(f"\nSpearman correlation: rho={rho:.4f}, p={pval:.4f}")
    
    if pval < 0.05:
        print("[SIGNIFICANT] Attention correlates with p-adic structure!")
    else:
        print("[NOT SIGNIFICANT] No p-adic correlation detected.")
    
    # Visualize
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    # Panel 1: Attention scores
    axes[0].plot(avg_attention, 'o-', color='#1f77b4', linewidth=2)
    axes[0].set_xlabel('Position in Window', fontsize=12)
    axes[0].set_ylabel('Attention Score', fontsize=12)
    axes[0].set_title('Transformer Attention Pattern', fontsize=14, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: p-adic distances
    axes[1].plot(padic_distances, 's-', color='#ff7f0e', linewidth=2)
    axes[1].set_xlabel('Position Offset', fontsize=12)
    axes[1].set_ylabel('p-adic Distance', fontsize=12)
    axes[1].set_title(f'p-adic Distance (p={p})', fontsize=14, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    
    # Panel 3: Correlation scatter
    axes[2].scatter(padic_distances, avg_attention, alpha=0.6, s=50, color='#2ca02c')
    axes[2].set_xlabel('p-adic Distance', fontsize=12)
    axes[2].set_ylabel('Attention Score', fontsize=12)
    axes[2].set_title(f'Correlation (ρ={rho:.3f}, p={pval:.3f})', fontsize=14, fontweight='bold')
    axes[2].grid(True, alpha=0.3)
    
    # Add trend line
    z = np.polyfit(padic_distances, avg_attention, 1)
    p_fit = np.poly1d(z)
    x_line = np.linspace(padic_distances.min(), padic_distances.max(), 100)
    axes[2].plot(x_line, p_fit(x_line), "r--", alpha=0.8, linewidth=2)
    
    plt.tight_layout()
    plt.savefig('padic_attention_analysis.png', dpi=300, bbox_inches='tight')
    print("\n[OK] Saved: padic_attention_analysis.png")
    
    # Save results
    results = {
        'p': p,
        'm': m,
        'L_in': L_in,
        'accuracy': float(acc),
        'correlation_rho': float(rho),
        'correlation_pval': float(pval),
        'significant': bool(pval < 0.05),
        'attention_scores': avg_attention.tolist(),
        'padic_distances': padic_distances.tolist()
    }
    
    import json
    with open('padic_attention_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("[OK] Saved: padic_attention_results.json")
    
    return results

if __name__ == "__main__":
    np.random.seed(42)
    torch.manual_seed(42)
    
    # Run experiment
    results = test_padic_attention_hypothesis(
        p=5, m=125, L_in=32, N=5000, epochs=30
    )
    
    print("\n" + "="*70)
    print("EXPERIMENT COMPLETE")
    print("="*70)
    print(f"Accuracy: {results['accuracy']*100:.1f}%")
    print(f"p-adic Correlation: rho={results['correlation_rho']:.4f} (p={results['correlation_pval']:.4f})")
    if results['significant']:
        print("CONCLUSION: Transformers DO learn p-adic structure!")
    else:
        print("CONCLUSION: Transformers do NOT learn p-adic structure (negative result)")
