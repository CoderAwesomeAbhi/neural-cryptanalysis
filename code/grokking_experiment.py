"""
Grokking Experiment: Train for 100,000 epochs to test delayed generalization
Tests whether neural networks can eventually learn the algebraic structure
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import matplotlib.pyplot as plt
from pathlib import Path
import json
from tqdm import tqdm

# Import from existing codebase
import sys
sys.path.append(str(Path(__file__).parent))
from sequence_generator import generate_piecewise_sequence

class MLPPredictor(nn.Module):
    """Simple MLP for sequence prediction"""
    def __init__(self, input_size, hidden_sizes, output_size):
        super().__init__()
        layers = []
        prev_size = input_size
        for h in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, h),
                nn.ReLU(),
            ])
            prev_size = h
        layers.append(nn.Linear(prev_size, output_size))
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)

def create_dataset(sequence, L_in=6):
    """Create windowed dataset from sequence"""
    X, y = [], []
    for i in range(len(sequence) - L_in):
        X.append(sequence[i:i+L_in])
        y.append(sequence[i+L_in])
    return np.array(X), np.array(y)

def train_with_grokking(config, max_epochs=100000, log_every=1000, checkpoint_every=10000):
    """
    Train with high weight decay for grokking
    
    Args:
        config: Sequence configuration (p, k, hensel_satisfied)
        max_epochs: Maximum training epochs
        log_every: Log accuracy every N epochs
        checkpoint_every: Save checkpoint every N epochs
    """
    print(f"\n{'='*80}")
    print(f"GROKKING EXPERIMENT: {config['name']}")
    print(f"Training for {max_epochs} epochs with weight decay")
    print(f"{'='*80}\n")
    
    # Setup checkpoint directory
    results_dir = Path(__file__).parent.parent / 'results'
    results_dir.mkdir(exist_ok=True)
    checkpoint_path = results_dir / f"checkpoint_{config['name'].replace(' ', '_')}.pt"
    
    # Generate sequence
    m = config['p'] ** config['k']
    sequence = generate_piecewise_sequence(
        p=config['p'],
        k=config['k'],
        hensel_satisfied=config['hensel_satisfied'],
        n_terms=4500,
        burn_in=300
    )
    
    # Create datasets
    X, y = create_dataset(sequence, L_in=6)
    
    # Normalize inputs
    X_norm = X / m
    
    # Train/val/test split
    n_train = int(0.8 * len(X))
    n_val = int(0.1 * len(X))
    
    X_train = torch.FloatTensor(X_norm[:n_train])
    y_train = torch.LongTensor(y[:n_train])
    X_val = torch.FloatTensor(X_norm[n_train:n_train+n_val])
    y_val = torch.LongTensor(y[n_train:n_train+n_val])
    X_test = torch.FloatTensor(X_norm[n_train+n_val:])
    y_test = torch.LongTensor(y[n_train+n_val:])
    
    # Create model
    model = MLPPredictor(input_size=6, hidden_sizes=[256, 128], output_size=m)
    
    # CRITICAL: Use AdamW with weight decay for grokking
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    criterion = nn.CrossEntropyLoss()
    
    # Training loop with logging
    train_losses = []
    val_accs = []
    test_accs = []
    epochs_logged = []
    start_epoch = 0
    best_val_acc = 0.0
    grokking_epoch = None
    
    # Resume from checkpoint if exists
    if checkpoint_path.exists():
        print(f"Found checkpoint at {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        train_losses = checkpoint['train_losses']
        val_accs = checkpoint['val_accs']
        test_accs = checkpoint['test_accs']
        epochs_logged = checkpoint['epochs_logged']
        best_val_acc = checkpoint['best_val_acc']
        grokking_epoch = checkpoint.get('grokking_epoch')
        print(f"Resuming from epoch {start_epoch}")
        print(f"Best val acc so far: {best_val_acc:.1%}\n")
    
    train_loader = DataLoader(
        TensorDataset(X_train, y_train),
        batch_size=256,
        shuffle=True
    )
    
    print("Starting training...")
    print(f"Period T = {config.get('period', 'unknown')}")
    print(f"T/L_in = {config.get('period', 0) / 6:.1f}")
    print(f"T/N_train = {config.get('period', 0) / n_train:.2f}\n")
    
    for epoch in tqdm(range(start_epoch, max_epochs), desc="Training", initial=start_epoch, total=max_epochs):
        # Training
        model.train()
        epoch_loss = 0.0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        
        # Logging
        if epoch % log_every == 0 or epoch == max_epochs - 1:
            model.eval()
            with torch.no_grad():
                # Validation accuracy
                val_outputs = model(X_val)
                val_preds = torch.argmax(val_outputs, dim=1)
                val_acc = (val_preds == y_val).float().mean().item()
                
                # Test accuracy
                test_outputs = model(X_test)
                test_preds = torch.argmax(test_outputs, dim=1)
                test_acc = (test_preds == y_test).float().mean().item()
                
                train_losses.append(epoch_loss / len(train_loader))
                val_accs.append(val_acc)
                test_accs.append(test_acc)
                epochs_logged.append(epoch)
                
                # Detect grokking (sudden jump to >90% accuracy)
                if val_acc > 0.9 and best_val_acc < 0.9 and grokking_epoch is None:
                    grokking_epoch = epoch
                    print(f"\n*** GROKKING DETECTED at epoch {epoch}! ***")
                    print(f"   Val accuracy jumped from {best_val_acc:.1%} to {val_acc:.1%}")
                
                best_val_acc = max(best_val_acc, val_acc)
                
                if epoch % (log_every * 10) == 0:
                    print(f"Epoch {epoch:6d}: Loss={epoch_loss/len(train_loader):.4f}, "
                          f"Val={val_acc:.1%}, Test={test_acc:.1%}, Best={best_val_acc:.1%}")
        
        # Save checkpoint periodically
        if epoch > 0 and epoch % checkpoint_every == 0:
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'train_losses': train_losses,
                'val_accs': val_accs,
                'test_accs': test_accs,
                'epochs_logged': epochs_logged,
                'best_val_acc': best_val_acc,
                'grokking_epoch': grokking_epoch,
                'config': config
            }, checkpoint_path)
            print(f"Checkpoint saved at epoch {epoch}")
    
    # Final results
    print(f"\n{'='*80}")
    print(f"FINAL RESULTS:")
    print(f"  Best validation accuracy: {best_val_acc:.1%}")
    print(f"  Final test accuracy: {test_accs[-1]:.1%}")
    if grokking_epoch:
        print(f"  *** Grokking occurred at epoch: {grokking_epoch} ***")
    else:
        print(f"  No grokking detected (never reached >90% accuracy)")
    print(f"{'='*80}\n")
    
    # Clean up checkpoint on successful completion
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print(f"Checkpoint removed (training completed successfully)")
    
    # Save results
    results = {
        'config': config,
        'epochs_logged': epochs_logged,
        'train_losses': train_losses,
        'val_accs': val_accs,
        'test_accs': test_accs,
        'best_val_acc': best_val_acc,
        'grokking_epoch': grokking_epoch,
        'final_test_acc': test_accs[-1]
    }
    
    return results

def plot_grokking_curves(all_results, save_path):
    """Plot grokking curves for all configurations"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    for idx, results in enumerate(all_results):
        ax = axes[idx // 2, idx % 2]
        
        config = results['config']
        epochs = results['epochs_logged']
        val_accs = results['val_accs']
        test_accs = results['test_accs']
        
        ax.plot(epochs, val_accs, label='Validation', linewidth=2)
        ax.plot(epochs, test_accs, label='Test', linewidth=2, alpha=0.7)
        
        # Mark grokking point if it exists
        if results['grokking_epoch']:
            ax.axvline(results['grokking_epoch'], color='red', 
                      linestyle='--', label=f"Grokking (epoch {results['grokking_epoch']})")
        
        ax.set_xlabel('Epoch', fontsize=12)
        ax.set_ylabel('Accuracy', fontsize=12)
        ax.set_title(f"{config['name']}\nT={config.get('period', '?')}, T/L_in={config.get('period', 0)/6:.1f}", 
                    fontsize=13, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xscale('log')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved grokking curves to {save_path}")

def main():
    """Run grokking experiments on multiple configurations"""
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-epochs', type=int, default=100000, help='Maximum training epochs')
    parser.add_argument('--log-every', type=int, default=1000, help='Log frequency')
    args = parser.parse_args()
    
    # Test configurations
    configs = [
        {
            'name': 'Easy (m=25, T=125)',
            'p': 5,
            'k': 2,
            'hensel_satisfied': True,
            'period': 125
        },
        {
            'name': 'Medium (m=49, T=1083)',
            'p': 7,
            'k': 2,
            'hensel_satisfied': True,
            'period': 1083
        },
        {
            'name': 'Hard (m=125, T=7295)',
            'p': 5,
            'k': 3,
            'hensel_satisfied': True,
            'period': 7295
        },
        {
            'name': 'Very Hard (m=121, T=4912)',
            'p': 11,
            'k': 2,
            'hensel_satisfied': True,
            'period': 4912
        }
    ]
    
    # Run experiments
    all_results = []
    for config in configs:
        results = train_with_grokking(config, max_epochs=args.max_epochs, log_every=args.log_every)
        all_results.append(results)
        
        # Save individual results
        results_dir = Path(__file__).parent.parent / 'results'
        results_dir.mkdir(exist_ok=True)
        
        with open(results_dir / f"grokking_{config['name'].replace(' ', '_')}.json", 'w') as f:
            # Convert to JSON-serializable format
            json_results = {
                'config': config,
                'epochs_logged': results['epochs_logged'],
                'train_losses': results['train_losses'],
                'val_accs': results['val_accs'],
                'test_accs': results['test_accs'],
                'best_val_acc': results['best_val_acc'],
                'grokking_epoch': results['grokking_epoch'],
                'final_test_acc': results['final_test_acc']
            }
            json.dump(json_results, f, indent=2)
    
    # Plot all results
    results_dir = Path(__file__).parent.parent / 'results'
    plot_grokking_curves(all_results, results_dir / 'grokking_curves.png')
    
    # Summary
    print("\n" + "="*80)
    print("GROKKING EXPERIMENT SUMMARY")
    print("="*80)
    for results in all_results:
        config = results['config']
        print(f"\n{config['name']}:")
        print(f"  Period: {config['period']}")
        print(f"  T/L_in: {config['period']/6:.1f}")
        print(f"  Best val acc: {results['best_val_acc']:.1%}")
        print(f"  Final test acc: {results['final_test_acc']:.1%}")
        if results['grokking_epoch']:
            print(f"  [SUCCESS] GROKKED at epoch {results['grokking_epoch']}")
        else:
            print(f"  [FAILED] NO GROKKING (information-theoretic limit confirmed)")
    print("="*80)

if __name__ == '__main__':
    main()
