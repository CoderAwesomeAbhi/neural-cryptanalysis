"""
p-adic Positional Encoding for Transformers
Implements the architectural fix proposed in Section 8 of the paper.
"""

import torch
import torch.nn as nn
import numpy as np
from generator import PiecewiseAffineGenerator

class PadicPositionalEncoding(nn.Module):
    """
    p-adic positional encoding that respects p-adic distance.
    
    For positions i and j with v_p(i-j) = ℓ, the encodings are identical
    in the first ℓ dimensions, encoding the p-adic tree structure.
    """
    def __init__(self, d_model, p=5, max_len=5000):
        super().__init__()
        self.d_model = d_model
        self.p = p
        self.max_len = max_len
        
        # Compute p-adic encoding
        pe = torch.zeros(max_len, d_model)
        
        # Number of p-adic levels we can encode
        k_max = int(np.log(max_len) / np.log(p)) + 1
        
        for pos in range(max_len):
            # Extract p-adic digits
            temp = pos
            for i in range(min(k_max, d_model)):
                digit = temp % p
                # Encode digit with sine/cosine for smoothness
                pe[pos, i*2] = np.sin(2 * np.pi * digit / p) if i*2 < d_model else 0
                pe[pos, i*2+1] = np.cos(2 * np.pi * digit / p) if i*2+1 < d_model else 0
                temp //= p
        
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        """
        Args:
            x: Tensor of shape (batch_size, seq_len, d_model)
        Returns:
            x with p-adic positional encoding added
        """
        return x + self.pe[:x.size(1), :]


class HybridPositionalEncoding(nn.Module):
    """
    Hybrid encoding combining standard sinusoidal and p-adic encodings.
    
    PE_hybrid(pos) = α · PE_sin(pos) + (1-α) · PE_p(pos)
    
    where α is a learnable parameter.
    """
    def __init__(self, d_model, p=5, max_len=5000):
        super().__init__()
        self.d_model = d_model
        self.p = p
        
        # Standard sinusoidal encoding
        pe_sin = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe_sin[:, 0::2] = torch.sin(position * div_term)
        pe_sin[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe_sin', pe_sin)
        
        # p-adic encoding
        pe_padic = torch.zeros(max_len, d_model)
        k_max = int(np.log(max_len) / np.log(p)) + 1
        for pos in range(max_len):
            # Extract p-adic digits
            temp = pos
            for i in range(min(k_max, d_model)):
                digit = temp % p
                # Encode digit with sine/cosine
                pe_padic[pos, i*2] = np.sin(2 * np.pi * digit / p) if i*2 < d_model else 0
                pe_padic[pos, i*2+1] = np.cos(2 * np.pi * digit / p) if i*2+1 < d_model else 0
                temp //= p
        self.register_buffer('pe_padic', pe_padic)
        
        # Learnable mixing parameter α
        self.alpha = nn.Parameter(torch.tensor(0.5))
    
    def forward(self, x):
        """
        Args:
            x: Tensor of shape (batch_size, seq_len, d_model)
        Returns:
            x with hybrid positional encoding added
        """
        alpha = torch.sigmoid(self.alpha)  # Constrain to [0, 1]
        pe_hybrid = alpha * self.pe_sin[:x.size(1), :] + (1 - alpha) * self.pe_padic[:x.size(1), :]
        return x + pe_hybrid


class PadicTransformer(nn.Module):
    """
    Transformer with p-adic positional encoding for learning sequences
    over Z/p^k Z with Hensel-satisfied piecewise affine dynamics.
    """
    def __init__(self, vocab_size, d_model=64, nhead=4, num_layers=2, 
                 encoding_type='padic', p=5):
        super().__init__()
        self.d_model = d_model
        self.encoding_type = encoding_type
        
        # Embedding
        self.embedding = nn.Embedding(vocab_size, d_model)
        
        # Positional encoding
        if encoding_type == 'standard':
            # Standard sinusoidal (baseline)
            pe = torch.zeros(5000, d_model)
            position = torch.arange(0, 5000, dtype=torch.float).unsqueeze(1)
            div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
            pe[:, 0::2] = torch.sin(position * div_term)
            pe[:, 1::2] = torch.cos(position * div_term)
            self.register_buffer('pe', pe)
            self.pos_encoder = lambda x: x + self.pe[:x.size(1), :]
        elif encoding_type == 'padic':
            self.pos_encoder = PadicPositionalEncoding(d_model, p=p)
        elif encoding_type == 'hybrid':
            self.pos_encoder = HybridPositionalEncoding(d_model, p=p)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, 
            nhead=nhead,
            dim_feedforward=256,
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Output layer
        self.fc_out = nn.Linear(d_model, vocab_size)
    
    def forward(self, x):
        """
        Args:
            x: Tensor of shape (batch_size, seq_len) with token indices
        Returns:
            logits of shape (batch_size, vocab_size)
        """
        # Embed and add positional encoding
        x = self.embedding(x) * np.sqrt(self.d_model)
        x = self.pos_encoder(x)
        
        # Transformer encoding
        x = self.transformer(x)
        
        # Take last position for next-token prediction
        x = x[:, -1, :]
        
        # Output projection
        return self.fc_out(x)


def train_padic_transformer(p=5, k=3, encoding_type='padic', epochs=100, device='cuda'):
    """
    Train Transformer with p-adic positional encoding on hard sequence.
    
    Args:
        p: Prime base
        k: Extension level
        encoding_type: 'standard', 'padic', or 'hybrid'
        epochs: Number of training epochs
        device: 'cuda' or 'cpu'
    
    Returns:
        model: Trained model
        history: Training history
    """
    m = p ** k
    gen = PiecewiseAffineGenerator(p, k, hensel_satisfied=True)
    
    # Generate training data
    L_in = 32  # Longer context for p-adic structure
    n_train = 3600   # Matches paper setup: T/N_train > 2 (hard regime)
    n_val = 400      # 10% validation split
    
    print(f"Generating sequence with m={m}, T={gen.period}...")
    seq = gen.generate(n_train + n_val + L_in)
    
    # Create datasets
    X_train = torch.zeros(n_train, L_in, dtype=torch.long)
    y_train = torch.zeros(n_train, dtype=torch.long)
    for i in range(n_train):
        X_train[i] = torch.tensor(seq[i:i+L_in])
        y_train[i] = seq[i+L_in]
    
    X_val = torch.zeros(n_val, L_in, dtype=torch.long)
    y_val = torch.zeros(n_val, dtype=torch.long)
    for i in range(n_val):
        X_val[i] = torch.tensor(seq[n_train+i:n_train+i+L_in])
        y_val[i] = seq[n_train+i+L_in]
    
    # Move to device
    X_train, y_train = X_train.to(device), y_train.to(device)
    X_val, y_val = X_val.to(device), y_val.to(device)
    
    # Create model
    model = PadicTransformer(
        vocab_size=m,
        d_model=64,
        nhead=4,
        num_layers=2,
        encoding_type=encoding_type,
        p=p
    ).to(device)
    
    # Training setup
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    history = {'train_loss': [], 'val_loss': [], 'val_acc': []}
    best_acc = 0.0
    
    print(f"\nTraining {encoding_type} Transformer...")
    print(f"Sequence period: {gen.period}, T/L_in = {gen.period/L_in:.1f}")
    
    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0.0
        batch_size = 128
        
        for i in range(0, len(X_train), batch_size):
            batch_X = X_train[i:i+batch_size]
            batch_y = y_train[i:i+batch_size]
            
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        train_loss /= (len(X_train) / batch_size)
        
        # Validation
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val)
            val_loss = criterion(val_outputs, y_val).item()
            val_preds = val_outputs.argmax(dim=1)
            val_acc = (val_preds == y_val).float().mean().item()
        
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)
        
        if val_acc > best_acc:
            best_acc = val_acc
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs}: "
                  f"Train Loss={train_loss:.4f}, "
                  f"Val Loss={val_loss:.4f}, "
                  f"Val Acc={val_acc*100:.1f}%")
    
    print(f"\nBest validation accuracy: {best_acc*100:.1f}%")
    
    return model, history


def compare_encodings(p=5, k=3, epochs=100):
    """
    Compare standard vs p-adic vs hybrid positional encodings.
    
    This is the experiment for Section 8.4 of the paper.
    """
    import matplotlib.pyplot as plt
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")
    
    results = {}
    
    for encoding_type in ['standard', 'padic', 'hybrid']:
        print(f"\n{'='*60}")
        print(f"Testing {encoding_type.upper()} encoding")
        print('='*60)
        
        model, history = train_padic_transformer(
            p=p, k=k, 
            encoding_type=encoding_type,
            epochs=epochs,
            device=device
        )
        
        results[encoding_type] = {
            'model': model,
            'history': history,
            'best_acc': max(history['val_acc'])
        }
    
    # Plot results
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    for encoding_type, data in results.items():
        ax1.plot(data['history']['val_loss'], label=encoding_type)
        ax2.plot(data['history']['val_acc'], label=encoding_type)
    
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Validation Loss')
    ax1.set_title('Validation Loss by Encoding Type')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Validation Accuracy')
    ax2.set_title('Validation Accuracy by Encoding Type')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='50% threshold')
    
    plt.tight_layout()
    import os
    os.makedirs('../results', exist_ok=True)
    plt.savefig('../results/padic_encoding_comparison.png', dpi=300, bbox_inches='tight')
    print(f"\nSaved comparison plot to ../results/padic_encoding_comparison.png")
    
    # Print summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print('='*60)
    for encoding_type, data in results.items():
        print(f"{encoding_type.upper():12s}: Best Acc = {data['best_acc']*100:5.1f}%")
    
    return results


if __name__ == '__main__':
    # Run the comparison experiment
    results = compare_encodings(p=5, k=3, epochs=100)
