"""
Chain-of-Thought with Autoregressive Scratchpads
Tests whether explicit state tracking enables learning long-period sequences
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))
from generator import A0_CANON, A1_CANON, b0_CANON, b1_CANON

# Set random seeds for reproducibility
torch.manual_seed(42)
np.random.seed(42)


class CoTDataset(Dataset):
    """
    Dataset that includes explicit state transitions
    Format: (s_t, x_t) -> (s_{t+1}, x_{t+1})
    """
    def __init__(self, sequence, states, vocab_size):
        self.sequence = sequence
        self.states = states
        self.vocab_size = vocab_size
        
    def __len__(self):
        return len(self.sequence) - 1
    
    def __getitem__(self, idx):
        # Input: current state + current output
        s_t = self.states[idx]
        x_t = self.sequence[idx]
        
        # Target: next state + next output
        s_next = self.states[idx + 1]
        x_next = self.sequence[idx + 1]
        
        return (
            torch.LongTensor(s_t),
            torch.LongTensor([x_t]),
            torch.LongTensor(s_next),
            torch.LongTensor([x_next])
        )


class CoTTransformer(nn.Module):
    """
    Transformer that autoregressively generates:
    (s_t, x_t) -> predict s_{t+1} -> predict x_{t+1}
    """
    def __init__(self, vocab_size, state_dim=2, d_model=128, nhead=4, num_layers=2):
        super().__init__()
        
        self.vocab_size = vocab_size
        self.state_dim = state_dim
        self.d_model = d_model
        
        # Embeddings
        self.state_embed = nn.Linear(state_dim, d_model)
        self.output_embed = nn.Embedding(vocab_size, d_model)
        
        # Transformer
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=4*d_model,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Prediction heads
        self.state_head = nn.Linear(d_model, state_dim * vocab_size)  # Predict each state component
        self.output_head = nn.Linear(d_model, vocab_size)
        
    def forward(self, state, output):
        """
        state: (batch, state_dim)
        output: (batch, 1)
        """
        # Embed inputs
        state_emb = self.state_embed(state.float())  # (batch, d_model)
        output_emb = self.output_embed(output.squeeze(1))  # (batch, d_model)
        
        # Concatenate as sequence: [state, output]
        x = torch.stack([state_emb, output_emb], dim=1)  # (batch, 2, d_model)
        
        # Transform
        h = self.transformer(x)  # (batch, 2, d_model)
        
        # Predict next state from position 0
        state_logits = self.state_head(h[:, 0, :])  # (batch, state_dim * vocab_size)
        state_logits = state_logits.view(-1, self.state_dim, self.vocab_size)
        
        # Predict next output from position 1
        output_logits = self.output_head(h[:, 1, :])  # (batch, vocab_size)
        
        return state_logits, output_logits


def train_cot_model(config, max_epochs=100):
    """
    Train CoT model with explicit state tracking
    """
    print(f"\n{'='*80}")
    print(f"CHAIN-OF-THOUGHT EXPERIMENT: {config['name']}")
    print(f"Testing explicit state tracking for long-period sequences")
    print(f"{'='*80}\n")
    
    m = config['p'] ** config['k']
    
    # Use canonical matrices
    A0 = A0_CANON
    b0 = b0_CANON
    A1 = A1_CANON
    b1 = b1_CANON
    
    # Generate with state tracking
    n_terms = 4500
    states = []
    outputs = []
    
    state = np.array([1, 1])  # Initial state
    for _ in range(n_terms):
        states.append(state.copy())
        output = state[0] % m
        outputs.append(output)
        
        # Update state
        regime = 0 if state[0] < m // 2 else 1
        if regime == 0:
            state = (A0 @ state + b0) % m
        else:
            state = (A1 @ state + b1) % m
    
    # Create dataset
    dataset = CoTDataset(outputs, states, m)
    
    # Split
    n_train = int(0.8 * len(dataset))
    n_val = int(0.1 * len(dataset))
    
    train_dataset = torch.utils.data.Subset(dataset, range(n_train))
    val_dataset = torch.utils.data.Subset(dataset, range(n_train, n_train + n_val))
    test_dataset = torch.utils.data.Subset(dataset, range(n_train + n_val, len(dataset)))
    
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64)
    test_loader = DataLoader(test_dataset, batch_size=64)
    
    # Create model
    model = CoTTransformer(vocab_size=m, state_dim=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # Training loop
    print(f"Training CoT model...")
    print(f"Period T = {config['period']}")
    print(f"T/L_in = {config['period'] / 2:.1f}")  # Effective L_in = 2 (state + output)
    print()
    
    best_val_acc = 0.0
    
    for epoch in range(max_epochs):
        # Train
        model.train()
        total_loss = 0
        
        for s_t, x_t, s_next, x_next in train_loader:
            optimizer.zero_grad()
            
            state_logits, output_logits = model(s_t, x_t)
            
            # Loss for state prediction
            state_loss = sum([
                nn.functional.cross_entropy(
                    state_logits[:, i, :],
                    s_next[:, i]
                ) for i in range(2)
            ])
            
            # Loss for output prediction
            output_loss = nn.functional.cross_entropy(output_logits, x_next.squeeze(1))
            
            loss = state_loss + output_loss
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        # Validate
        if (epoch + 1) % 10 == 0:
            model.eval()
            correct_output = 0
            correct_state = 0
            total = 0
            
            with torch.no_grad():
                for s_t, x_t, s_next, x_next in val_loader:
                    state_logits, output_logits = model(s_t, x_t)
                    
                    # Check output prediction
                    output_preds = torch.argmax(output_logits, dim=1)
                    correct_output += (output_preds == x_next.squeeze(1)).sum().item()
                    
                    # Check state prediction
                    state_preds = torch.argmax(state_logits, dim=2)
                    correct_state += (state_preds == s_next).all(dim=1).sum().item()
                    
                    total += s_t.size(0)
            
            output_acc = correct_output / total
            state_acc = correct_state / total
            
            best_val_acc = max(best_val_acc, output_acc)
            
            print(f"Epoch {epoch+1:3d}: Loss={total_loss/len(train_loader):.4f}, "
                  f"Output Acc={output_acc:.1%}, State Acc={state_acc:.1%}")
    
    # Test
    model.eval()
    correct_output = 0
    correct_state = 0
    total = 0
    
    with torch.no_grad():
        for s_t, x_t, s_next, x_next in test_loader:
            state_logits, output_logits = model(s_t, x_t)
            
            output_preds = torch.argmax(output_logits, dim=1)
            correct_output += (output_preds == x_next.squeeze(1)).sum().item()
            
            state_preds = torch.argmax(state_logits, dim=2)
            correct_state += (state_preds == s_next).all(dim=1).sum().item()
            
            total += s_t.size(0)
    
    test_output_acc = correct_output / total
    test_state_acc = correct_state / total
    
    print(f"\n{'='*80}")
    print(f"FINAL RESULTS:")
    print(f"  Output prediction accuracy: {test_output_acc:.1%}")
    print(f"  State prediction accuracy: {test_state_acc:.1%}")
    print(f"  Best validation accuracy: {best_val_acc:.1%}")
    
    if test_output_acc > 0.9:
        print(f"  ✓ CoT ENABLES LEARNING!")
    else:
        print(f"  ✗ CoT does not overcome information-theoretic barrier")
    print(f"{'='*80}\n")
    
    return test_output_acc, test_state_acc


def main():
    """Run CoT experiments"""
    
    configs = [
        {
            'name': 'Medium (m=49, T=1083)',
            'p': 7,
            'k': 2,
            'period': 1083
        },
        {
            'name': 'Hard (m=125, T=7295)',
            'p': 5,
            'k': 3,
            'period': 7295
        }
    ]
    
    results = []
    for config in configs:
        output_acc, state_acc = train_cot_model(config, max_epochs=100)
        results.append({
            'config': config['name'],
            'output_acc': output_acc,
            'state_acc': state_acc
        })
    
    # Summary
    print("\n" + "="*80)
    print("CHAIN-OF-THOUGHT SUMMARY")
    print("="*80)
    for r in results:
        print(f"{r['config']}:")
        print(f"  Output: {r['output_acc']:.1%}, State: {r['state_acc']:.1%}")
    print("="*80)


if __name__ == '__main__':
    main()
