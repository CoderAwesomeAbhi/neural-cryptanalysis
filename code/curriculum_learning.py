"""
Curriculum Learning for Adversarial Training
Gradually increase sequence difficulty to test if transfer learning enables
breaking the T/L_in threshold
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))
from sequence_generator import generate_piecewise_sequence


def create_dataset(sequence, L_in=6):
    """Create windowed dataset"""
    X, y = [], []
    for i in range(len(sequence) - L_in):
        X.append(sequence[i:i+L_in])
        y.append(sequence[i+L_in])
    return np.array(X), np.array(y)


def train_on_config(model, config, epochs=50, L_in=6):
    """Train model on a specific configuration"""
    m = config['p'] ** config['k']
    
    # Generate sequence
    sequence = generate_piecewise_sequence(
        p=config['p'],
        k=config['k'],
        hensel_satisfied=True,
        n_terms=4500,
        burn_in=300
    )
    
    # Create dataset
    X, y = create_dataset(sequence, L_in)
    X_norm = X / m
    
    # Split
    n_train = int(0.8 * len(X))
    n_val = int(0.1 * len(X))
    
    X_train = torch.FloatTensor(X_norm[:n_train])
    y_train = torch.LongTensor(y[:n_train])
    X_val = torch.FloatTensor(X_norm[n_train:n_train+n_val])
    y_val = torch.LongTensor(y[n_train:n_train+n_val])
    
    # Update output layer if needed
    if model.network[-1].out_features != m:
        model.network[-1] = nn.Linear(model.network[-1].in_features, m)
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    
    train_loader = DataLoader(
        TensorDataset(X_train, y_train),
        batch_size=64,
        shuffle=True
    )
    
    best_val_acc = 0.0
    
    for epoch in range(epochs):
        model.train()
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
        
        # Validate
        if (epoch + 1) % 10 == 0:
            model.eval()
            with torch.no_grad():
                val_outputs = model(X_val)
                val_preds = torch.argmax(val_outputs, dim=1)
                val_acc = (val_preds == y_val).float().mean().item()
            
            best_val_acc = max(best_val_acc, val_acc)
            print(f"  Epoch {epoch+1:3d}: Val Acc = {val_acc:.1%}")
    
    return best_val_acc


class MLPPredictor(nn.Module):
    """MLP for sequence prediction"""
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


def curriculum_learning_experiment():
    """
    Curriculum: Easy -> Medium -> Hard
    Test if gradual exposure enables transfer learning
    """
    print(f"\n{'='*80}")
    print(f"CURRICULUM LEARNING EXPERIMENT")
    print(f"Progressive training: T=125 → T=1083 → T=7295")
    print(f"{'='*80}\n")
    
    curriculum = [
        {
            'name': 'Easy (m=25, T=125)',
            'p': 5,
            'k': 2,
            'period': 125,
            'epochs': 50
        },
        {
            'name': 'Medium (m=49, T=1083)',
            'p': 7,
            'k': 2,
            'period': 1083,
            'epochs': 100
        },
        {
            'name': 'Hard (m=125, T=7295)',
            'p': 5,
            'k': 3,
            'period': 7295,
            'epochs': 150
        }
    ]
    
    # Initialize model
    model = MLPPredictor(input_size=6, hidden_sizes=[256, 128], output_size=25)
    
    results = []
    
    for stage, config in enumerate(curriculum, 1):
        print(f"\n{'='*60}")
        print(f"STAGE {stage}: {config['name']}")
        print(f"Period T = {config['period']}, T/L_in = {config['period']/6:.1f}")
        print(f"{'='*60}")
        
        val_acc = train_on_config(model, config, epochs=config['epochs'])
        
        results.append({
            'stage': stage,
            'config': config['name'],
            'period': config['period'],
            'val_acc': val_acc
        })
        
        print(f"\nStage {stage} complete: Best Val Acc = {val_acc:.1%}")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"CURRICULUM LEARNING SUMMARY")
    print(f"{'='*80}")
    for r in results:
        print(f"Stage {r['stage']} ({r['config']}): {r['val_acc']:.1%}")
    
    # Check if curriculum helped
    final_acc = results[-1]['val_acc']
    if final_acc > 0.5:
        print(f"\n✓ CURRICULUM LEARNING ENABLES TRANSFER!")
        print(f"  Final accuracy {final_acc:.1%} >> random baseline")
    else:
        print(f"\n✗ Curriculum learning does not overcome barrier")
        print(f"  Final accuracy {final_acc:.1%} ≈ random baseline")
    print(f"{'='*80}\n")
    
    return results


def main():
    """Run curriculum learning experiments"""
    results = curriculum_learning_experiment()
    
    # Save results
    results_dir = Path(__file__).parent.parent / 'results'
    results_dir.mkdir(exist_ok=True)
    
    import json
    with open(results_dir / 'curriculum_learning.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {results_dir / 'curriculum_learning.json'}")


if __name__ == '__main__':
    main()
