#!/usr/bin/env python3
"""
grokking_full_coverage.py
=========================
PhD-Level Grokking Experiment: Does the Network Discover the Algebraic Rule?

This experiment answers the most important open question in the paper:
Given FULL period coverage (N_train = T), can neural networks learn the
piecewise affine rule, or do they merely memorize the lookup table?

Methodology:
  1. Full coverage: N_train >= T (every transition seen at least once)
  2. New starting points for test: different seeds/states than training
  3. 10,000+ epochs with AdamW (weight decay = 0.01) for grokking
  4. Track train/val/test accuracy per epoch
  5. Test set uses DIFFERENT initial states to test generalization

Key distinction from prior grokking_experiment.py:
  - Old: test set drawn from SAME trajectory (measures memorization)
  - New: test set drawn from DIFFERENT trajectories (measures rule learning)

Expected results:
  - T <= 100: Networks should grokk (learn the algebraic rule)
  - T > 1000: Even full coverage may not suffice → mechanistic barrier

References:
  - Power et al. (2022) "Grokking: Generalization beyond overfitting"
  - Gohr (2019) neural cryptanalysis methodology
"""

import sys
import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from generator import (
    generate_piecewise,
    A0_CANON, A1_CANON, b0_CANON, b1_CANON,
    compute_max_period,
    verify_trajectory_period,
)

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

L_IN = 6
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

CONFIGS = [
    # (name, p, k, expected_period)
    ("T=25 (p=5,k=1)",    5,  1,  25),
    ("T=29 (p=7,k=1)",    7,  1,  29),
    ("T=40 (p=11,k=1)",   11, 1,  40),
    ("T=74 (p=13,k=1)",   13, 1,  74),
    ("T=125 (p=5,k=2)",   5,  2,  125),
    ("T=281 (p=17,k=1)",  17, 1,  281),
    ("T=1083 (p=7,k=2)",  7,  2,  1083),
    ("T=7295 (p=5,k=3)",  5,  3,  7295),
]


# ═══════════════════════════════════════════════════════════════════════════
# Model
# ═══════════════════════════════════════════════════════════════════════════

class GrokkingMLP(nn.Module):
    """MLP with proper initialization for grokking experiments."""

    def __init__(self, input_size: int, hidden_sizes: Tuple[int, ...],
                 output_size: int, dropout: float = 0.0):
        super().__init__()
        layers = []
        prev = input_size
        for h in hidden_sizes:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            prev = h
        layers.append(nn.Linear(prev, output_size))
        self.net = nn.Sequential(*layers)

        # Kaiming initialization
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x):
        return self.net(x)

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ═══════════════════════════════════════════════════════════════════════════
# Dataset construction
# ═══════════════════════════════════════════════════════════════════════════

def make_windowed_dataset(seq: List[int], m: int, L_in: int = L_IN
                          ) -> Tuple[np.ndarray, np.ndarray]:
    """Convert sequence to windowed (X, y) pairs."""
    N = len(seq)
    n_rows = N - L_in
    X = np.array(
        [[seq[i + t] / m for t in range(L_in)] for i in range(n_rows)],
        dtype=np.float32,
    )
    y = np.array([seq[i + L_in] for i in range(n_rows)], dtype=np.int64)
    return X, y


def generate_full_coverage_data(
    p: int, k: int, seed_train: int = 42, seed_test: int = 137,
    coverage_factor: float = 3.0, test_coverage: float = 2.0,
) -> Dict:
    """
    Generate training and test data with full period coverage.

    Training: coverage_factor * T terms from seed_train
    Test: test_coverage * T terms from seed_test (DIFFERENT starting point)

    This ensures:
      - Training sees every transition at least coverage_factor times
      - Test uses a different trajectory segment for true generalization
    """
    m = p ** k
    A_list = [A0_CANON, A1_CANON]
    b_list = [b0_CANON, b1_CANON]

    # Compute the trajectory period for the training seed
    T_train = verify_trajectory_period(m, A_list, b_list, seed=seed_train)
    if T_train <= 0:
        T_train = compute_max_period(m, A_list, b_list)

    # Generate training data: enough to cover full period multiple times
    N_train = max(int(coverage_factor * T_train) + 500, 2000)
    seq_train = generate_piecewise(m, A_list, b_list, N=N_train + 300,
                                    seed=seed_train, burn=300)

    # Generate test data from DIFFERENT seed (different starting state)
    N_test = max(int(test_coverage * T_train) + 300, 1000)
    seq_test = generate_piecewise(m, A_list, b_list, N=N_test + 300,
                                   seed=seed_test, burn=300)

    X_train, y_train = make_windowed_dataset(seq_train, m)
    X_test, y_test = make_windowed_dataset(seq_test, m)

    # Also create a val split from the TRAINING trajectory
    # (to monitor memorization vs generalization)
    n_tr = int(0.85 * len(X_train))
    X_val, y_val = X_train[n_tr:], y_train[n_tr:]
    X_train, y_train = X_train[:n_tr], y_train[:n_tr]

    return {
        "m": m, "p": p, "k": k, "T": T_train,
        "X_train": X_train, "y_train": y_train,
        "X_val": X_val, "y_val": y_val,
        "X_test": X_test, "y_test": y_test,
        "N_train": len(X_train), "N_test": len(X_test),
        "coverage": len(X_train) / max(T_train, 1),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Training loop with grokking detection
# ═══════════════════════════════════════════════════════════════════════════

def train_grokking(
    data: Dict,
    max_epochs: int = 10000,
    lr: float = 1e-3,
    weight_decay: float = 0.01,
    batch_size: int = 256,
    log_every: int = 100,
    hidden: Tuple[int, ...] = (256, 128),
    seed: int = 42,
) -> Dict:
    """
    Train with AdamW + weight decay for grokking detection.

    Returns detailed training history including:
      - Per-epoch train loss, val accuracy, test accuracy
      - Grokking epoch (when test acc first exceeds 90%)
      - Whether memorization or generalization occurred
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    m = data["m"]
    T = data["T"]

    # Create tensors
    X_tr = torch.tensor(data["X_train"], dtype=torch.float32, device=DEVICE)
    y_tr = torch.tensor(data["y_train"], dtype=torch.long, device=DEVICE)
    X_va = torch.tensor(data["X_val"], dtype=torch.float32, device=DEVICE)
    y_va = torch.tensor(data["y_val"], dtype=torch.long, device=DEVICE)
    X_te = torch.tensor(data["X_test"], dtype=torch.float32, device=DEVICE)
    y_te = torch.tensor(data["y_test"], dtype=torch.long, device=DEVICE)

    loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=batch_size,
                        shuffle=True, drop_last=False)

    model = GrokkingMLP(L_IN, hidden, m).to(DEVICE)
    optimizer = optim.AdamW(model.parameters(), lr=lr,
                            weight_decay=weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs)
    criterion = nn.CrossEntropyLoss()

    # History tracking
    history = {
        "epochs": [], "train_loss": [], "train_acc": [],
        "val_acc": [], "test_acc": [],
    }
    best_test_acc = 0.0
    grokking_epoch = None
    memorization_epoch = None

    t0 = time.time()

    for epoch in range(max_epochs):
        # --- Training step ---
        model.train()
        total_loss = 0.0
        correct_train = 0
        total_train = 0

        for Xb, yb in loader:
            optimizer.zero_grad()
            logits = model(Xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(Xb)
            correct_train += (logits.argmax(1) == yb).sum().item()
            total_train += len(Xb)

        scheduler.step()

        # --- Logging ---
        if epoch % log_every == 0 or epoch == max_epochs - 1:
            model.eval()
            with torch.no_grad():
                train_acc = correct_train / max(total_train, 1)
                val_acc = (model(X_va).argmax(1) == y_va).float().mean().item()
                test_acc = (model(X_te).argmax(1) == y_te).float().mean().item()

            history["epochs"].append(epoch)
            history["train_loss"].append(total_loss / max(total_train, 1))
            history["train_acc"].append(train_acc)
            history["val_acc"].append(val_acc)
            history["test_acc"].append(test_acc)

            if test_acc > best_test_acc:
                best_test_acc = test_acc

            # Detect memorization (train acc > 95%)
            if memorization_epoch is None and train_acc > 0.95:
                memorization_epoch = epoch

            # Detect grokking (test acc on NEW trajectories > 90%)
            if grokking_epoch is None and test_acc > 0.90:
                grokking_epoch = epoch

            if epoch % (log_every * 10) == 0:
                elapsed = time.time() - t0
                print(f"  Epoch {epoch:6d}: loss={total_loss/total_train:.4f} "
                      f"train={train_acc:.1%} val={val_acc:.1%} "
                      f"test={test_acc:.1%} [{elapsed:.0f}s]")

        # Early stopping if grokking achieved and stable
        if (grokking_epoch is not None and
                epoch > grokking_epoch + 500 and
                best_test_acc > 0.95):
            print(f"  Early stop: grokking achieved and stable at epoch {epoch}")
            break

    elapsed = time.time() - t0

    return {
        "history": history,
        "best_test_acc": best_test_acc,
        "grokking_epoch": grokking_epoch,
        "memorization_epoch": memorization_epoch,
        "final_train_acc": history["train_acc"][-1],
        "final_val_acc": history["val_acc"][-1],
        "final_test_acc": history["test_acc"][-1],
        "total_epochs": len(history["epochs"]) * log_every,
        "elapsed_seconds": elapsed,
        "n_params": GrokkingMLP(L_IN, hidden, m).count_parameters(),
        "T": T, "m": m, "coverage": data["coverage"],
    }


# ═══════════════════════════════════════════════════════════════════════════
# Visualization
# ═══════════════════════════════════════════════════════════════════════════

def plot_grokking_results(all_results: List[Dict], save_path: str):
    """Plot grokking curves for all configurations."""
    import matplotlib.pyplot as plt
    import matplotlib

    matplotlib.rcParams.update({
        'font.size': 11, 'axes.titlesize': 13, 'axes.labelsize': 12,
        'font.family': 'serif',
    })

    n = len(all_results)
    cols = min(3, n)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 5 * rows))
    if n == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    for idx, res in enumerate(all_results):
        ax = axes[idx]
        h = res["history"]
        epochs = h["epochs"]

        ax.plot(epochs, h["train_acc"], label="Train", lw=2, color="#1f77b4")
        ax.plot(epochs, h["val_acc"], label="Val (same traj)", lw=2,
                color="#ff7f0e", ls="--")
        ax.plot(epochs, h["test_acc"], label="Test (new traj)", lw=2.5,
                color="#2ca02c")

        ax.axhline(1.0 / res["m"], color="gray", ls=":", alpha=0.5,
                    label=f"Random (1/{res['m']})")

        if res["grokking_epoch"] is not None:
            ax.axvline(res["grokking_epoch"], color="red", ls="--", alpha=0.7,
                        label=f"Grokk @ {res['grokking_epoch']}")
        if res["memorization_epoch"] is not None:
            ax.axvline(res["memorization_epoch"], color="purple", ls=":",
                        alpha=0.5, label=f"Memo @ {res['memorization_epoch']}")

        ax.set_xlabel("Epoch")
        ax.set_ylabel("Accuracy")
        ax.set_title(f"T={res['T']}, T/L={res['T']/L_IN:.1f}, "
                     f"cov={res['coverage']:.1f}x")
        ax.set_xscale("symlog", linthresh=100)
        ax.set_ylim(-0.02, 1.05)
        ax.legend(fontsize=8, loc="lower right")
        ax.grid(True, alpha=0.3)

    for idx in range(n, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"  Saved grokking plot to {save_path}")
    plt.close()


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Full-coverage grokking experiment")
    parser.add_argument("--max-epochs", type=int, default=10000)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--coverage", type=float, default=3.0,
                        help="Training coverage factor (multiples of T)")
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--configs", type=str, default="all",
                        help="Comma-separated config indices or 'all'")
    args = parser.parse_args()

    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    # Select configs
    if args.configs == "all":
        selected = CONFIGS
    else:
        indices = [int(x) for x in args.configs.split(",")]
        selected = [CONFIGS[i] for i in indices]

    print("=" * 80)
    print("FULL-COVERAGE GROKKING EXPERIMENT")
    print(f"Device: {DEVICE}")
    print(f"Max epochs: {args.max_epochs}, Coverage: {args.coverage}x")
    print(f"Weight decay: {args.weight_decay}")
    print("=" * 80)

    all_results = []

    for name, p, k, expected_T in selected:
        print(f"\n{'-' * 70}")
        print(f"Config: {name}")
        print(f"  p={p}, k={k}, m={p**k}, expected T={expected_T}")

        # Generate data with full coverage
        data = generate_full_coverage_data(
            p, k, coverage_factor=args.coverage)
        print(f"  Actual T={data['T']}, N_train={data['N_train']}, "
              f"N_test={data['N_test']}")
        print(f"  Coverage: {data['coverage']:.1f}x, "
              f"T/L_in={data['T']/L_IN:.1f}")

        # Train
        result = train_grokking(
            data, max_epochs=args.max_epochs, log_every=args.log_every,
            weight_decay=args.weight_decay,
        )
        result["name"] = name
        result["p"] = p
        result["k"] = k

        # Summary
        print(f"\n  RESULT: {name}")
        print(f"    Best test acc (new traj): {result['best_test_acc']:.1%}")
        print(f"    Final train/val/test: {result['final_train_acc']:.1%} / "
              f"{result['final_val_acc']:.1%} / {result['final_test_acc']:.1%}")
        if result["grokking_epoch"] is not None:
            print(f"    OK GROKKING at epoch {result['grokking_epoch']}")
        else:
            print(f"    X NO GROKKING (test never exceeded 90%)")
        if result["memorization_epoch"] is not None:
            print(f"    Memorization at epoch {result['memorization_epoch']}")

        all_results.append(result)

        # Save individual result
        save_data = {k: v for k, v in result.items()
                     if k != "history" or True}
        with open(results_dir / f"grokking_fullcov_{name.replace(' ', '_')}.json",
                  "w") as f:
            json.dump(save_data, f, indent=2, default=str)

    # Plot
    plot_grokking_results(all_results, str(results_dir / "grokking_full_coverage.png"))

    # Summary table
    print("\n" + "=" * 80)
    print("GROKKING EXPERIMENT SUMMARY")
    print("=" * 80)
    print(f"{'Config':<25} {'T':>6} {'T/L':>6} {'Cov':>5} "
          f"{'Train':>7} {'Test':>7} {'Grokk':>8} {'Memo':>8}")
    print("-" * 80)
    for r in all_results:
        grokk = str(r["grokking_epoch"]) if r["grokking_epoch"] else "—"
        memo = str(r["memorization_epoch"]) if r["memorization_epoch"] else "—"
        print(f"{r['name']:<25} {r['T']:>6} {r['T']/L_IN:>6.1f} "
              f"{r['coverage']:>5.1f} {r['final_train_acc']:>6.1%} "
              f"{r['final_test_acc']:>6.1%} {grokk:>8} {memo:>8}")

    print("\nKEY FINDING:")
    grokked = [r for r in all_results if r["grokking_epoch"] is not None]
    failed = [r for r in all_results if r["grokking_epoch"] is None]
    if grokked:
        print(f"  GROKKED ({len(grokked)}): "
              + ", ".join(r["name"] for r in grokked))
    if failed:
        print(f"  FAILED ({len(failed)}): "
              + ", ".join(r["name"] for r in failed))
    print("=" * 80)


if __name__ == "__main__":
    main()
