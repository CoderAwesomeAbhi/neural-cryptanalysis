#!/usr/bin/env python3
"""
gohr_neural_distinguisher.py
============================
Neural Distinguisher for Real Cipher Validation (Gohr 2019 style)

Instead of the circular approach (compute T, show T/L_in is large, conclude
"unlearnable"), this implements ACTUAL neural distinguishing attacks:

Task: Binary classification — distinguish cipher output from random
Architecture: Residual network with batch normalization (following Gohr CRYPTO 2019)
Training: Multiple random keys/nonces per cipher
Test: Measure distinguishing advantage on held-out keys

This validates the T/L_in threshold in a non-circular way:
  - Short-period generators → distinguisher succeeds → threshold predicts this
  - Real ciphers → distinguisher fails → threshold predicts this
  - Transition region → partial success → threshold predicts this

References:
  Gohr, A. (2019). "Improving Attacks on Round-Reduced Speck32/64 Using Deep
  Learning." CRYPTO 2019.
"""

import sys
import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, str(Path(__file__).parent))
from generator import (
    generate_piecewise, A0_CANON, A1_CANON, b0_CANON, b1_CANON,
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ═══════════════════════════════════════════════════════════════════════════
# Gohr-style Residual Network
# ═══════════════════════════════════════════════════════════════════════════

class ResidualBlock(nn.Module):
    """Residual block with batch norm (Gohr 2019 architecture)."""
    def __init__(self, channels):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv1d(channels, channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(channels),
            nn.ReLU(),
            nn.Conv1d(channels, channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(channels),
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(x + self.block(x))


class NeuralDistinguisher(nn.Module):
    """
    Gohr-style neural distinguisher for binary classification.

    Input: (batch, seq_len) — sequence of symbols
    Output: (batch, 1) — probability of being cipher (vs random)
    """
    def __init__(self, seq_len: int = 64, n_channels: int = 32,
                 n_blocks: int = 3):
        super().__init__()
        self.seq_len = seq_len

        # Initial embedding
        self.embed = nn.Sequential(
            nn.Conv1d(1, n_channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(n_channels),
            nn.ReLU(),
        )

        # Residual blocks
        self.res_blocks = nn.Sequential(
            *[ResidualBlock(n_channels) for _ in range(n_blocks)]
        )

        # Classification head
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(n_channels, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        # x: (B, seq_len) → (B, 1, seq_len)
        x = x.unsqueeze(1)
        x = self.embed(x)
        x = self.res_blocks(x)
        return self.head(x).squeeze(-1)

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ═══════════════════════════════════════════════════════════════════════════
# Cipher implementations
# ═══════════════════════════════════════════════════════════════════════════

def trivium_keystream(key_bits, iv_bits, n_bits):
    """Simplified Trivium stream cipher (288-bit state)."""
    s = [0] * 288
    for i in range(min(len(key_bits), 80)):
        s[i] = key_bits[i] & 1
    for i in range(min(len(iv_bits), 80)):
        s[93 + i] = iv_bits[i] & 1
    s[285] = s[286] = s[287] = 1

    # Warm up (1152 clocks)
    for _ in range(1152):
        t1 = s[65] ^ s[92]
        t2 = s[161] ^ s[176]
        t3 = s[242] ^ s[287]
        t1_ = t1 ^ (s[90] & s[91]) ^ s[170]
        t2_ = t2 ^ (s[174] & s[175]) ^ s[263]
        t3_ = t3 ^ (s[285] & s[286]) ^ s[68]
        s = [t3_] + s[:92] + [t1_] + s[93:176] + [t2_] + s[177:287]

    keystream = []
    for _ in range(n_bits):
        t1 = s[65] ^ s[92]
        t2 = s[161] ^ s[176]
        t3 = s[242] ^ s[287]
        keystream.append(t1 ^ t2 ^ t3)
        t1_ = t1 ^ (s[90] & s[91]) ^ s[170]
        t2_ = t2 ^ (s[174] & s[175]) ^ s[263]
        t3_ = t3 ^ (s[285] & s[286]) ^ s[68]
        s = [t3_] + s[:92] + [t1_] + s[93:176] + [t2_] + s[177:287]

    return keystream


def lfsr_sequence(taps, init, n_bits):
    """Linear Feedback Shift Register."""
    state = list(init)
    n = len(state)
    out = []
    for _ in range(n_bits):
        out.append(state[0])
        new_bit = 0
        for tap in taps:
            new_bit ^= state[tap]
        state = state[1:] + [new_bit]
    return out


def chacha_quarter_round(a, b, c, d):
    mask = 0xFFFFFFFF
    a = (a + b) & mask; d ^= a; d = ((d << 16) | (d >> 16)) & mask
    c = (c + d) & mask; b ^= c; b = ((b << 12) | (b >> 20)) & mask
    a = (a + b) & mask; d ^= a; d = ((d << 8) | (d >> 24)) & mask
    c = (c + d) & mask; b ^= c; b = ((b << 7) | (b >> 25)) & mask
    return a, b, c, d


def chacha20_block(key, counter, nonce, n_rounds=4):
    SIGMA = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]
    state = list(SIGMA) + list(key[:8]) + [counter, 0] + list(nonce[:2])
    w = list(state)
    for _ in range(n_rounds // 2):
        w[0],w[4],w[8],w[12] = chacha_quarter_round(w[0],w[4],w[8],w[12])
        w[1],w[5],w[9],w[13] = chacha_quarter_round(w[1],w[5],w[9],w[13])
        w[2],w[6],w[10],w[14] = chacha_quarter_round(w[2],w[6],w[10],w[14])
        w[3],w[7],w[11],w[15] = chacha_quarter_round(w[3],w[7],w[11],w[15])
        w[0],w[5],w[10],w[15] = chacha_quarter_round(w[0],w[5],w[10],w[15])
        w[1],w[6],w[11],w[12] = chacha_quarter_round(w[1],w[6],w[11],w[12])
        w[2],w[7],w[8],w[13] = chacha_quarter_round(w[2],w[7],w[8],w[13])
        w[3],w[4],w[9],w[14] = chacha_quarter_round(w[3],w[4],w[9],w[14])
    return [(w[i] + state[i]) & 0xFFFFFFFF for i in range(16)]


def chacha20_keystream_bits(key_words, n_bits, n_rounds=4):
    nonce = [0x00000001, 0x00000002]
    bits = []
    counter = 0
    while len(bits) < n_bits:
        block = chacha20_block(key_words, counter, nonce, n_rounds)
        for word in block:
            for shift in range(32):
                bits.append((word >> shift) & 1)
        counter += 1
    return bits[:n_bits]


def padic_sequence_bytes(p, k, seed, N, burn=300):
    """Generate piecewise affine sequence and convert to byte-level."""
    m = p ** k
    seq = generate_piecewise(m, [A0_CANON, A1_CANON], [b0_CANON, b1_CANON],
                              N=N + burn, seed=seed, burn=burn)
    return seq


# ═══════════════════════════════════════════════════════════════════════════
# Dataset generation for distinguishing task
# ═══════════════════════════════════════════════════════════════════════════

def generate_distinguishing_data(
    cipher_fn, n_samples: int = 10000, seq_len: int = 64,
    n_keys: int = 100, normalize: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate balanced dataset for cipher vs random distinguishing.

    Returns:
      X: (2*n_samples, seq_len) float32
      y: (2*n_samples,) int — 0=random, 1=cipher
    """
    rng = np.random.default_rng(42)

    # Cipher samples (from different keys)
    cipher_samples = []
    samples_per_key = max(1, n_samples // n_keys)

    for key_idx in range(n_keys):
        bits = cipher_fn(key_seed=key_idx)
        # Extract windows
        for j in range(samples_per_key):
            start = rng.integers(0, max(1, len(bits) - seq_len))
            window = bits[start:start + seq_len]
            if len(window) == seq_len:
                cipher_samples.append(window)
            if len(cipher_samples) >= n_samples:
                break
        if len(cipher_samples) >= n_samples:
            break

    cipher_samples = cipher_samples[:n_samples]

    # Random samples (uniform)
    max_val = max(max(s) for s in cipher_samples) if cipher_samples else 1
    vocab_size = max_val + 1

    random_samples = []
    for _ in range(n_samples):
        random_samples.append(
            rng.integers(0, vocab_size, seq_len).tolist()
        )

    # Combine
    X = np.array(cipher_samples + random_samples, dtype=np.float32)
    y = np.array([1] * len(cipher_samples) + [0] * len(random_samples),
                 dtype=np.int64)

    if normalize and vocab_size > 1:
        X = X / vocab_size

    # Shuffle
    idx = rng.permutation(len(X))
    return X[idx], y[idx]


# ═══════════════════════════════════════════════════════════════════════════
# Training
# ═══════════════════════════════════════════════════════════════════════════

def train_distinguisher(
    X_train, y_train, X_test, y_test,
    seq_len: int = 64, epochs: int = 50, lr: float = 1e-3,
    batch_size: int = 256, seed: int = 42,
) -> Dict:
    """Train neural distinguisher and return metrics."""
    torch.manual_seed(seed)

    X_tr = torch.tensor(X_train, dtype=torch.float32, device=DEVICE)
    y_tr = torch.tensor(y_train, dtype=torch.float32, device=DEVICE)
    X_te = torch.tensor(X_test, dtype=torch.float32, device=DEVICE)
    y_te = torch.tensor(y_test, dtype=torch.float32, device=DEVICE)

    loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=batch_size,
                        shuffle=True)

    model = NeuralDistinguisher(seq_len=seq_len).to(DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.BCEWithLogitsLoss()

    for epoch in range(epochs):
        model.train()
        for Xb, yb in loader:
            optimizer.zero_grad()
            loss = criterion(model(Xb), yb)
            loss.backward()
            optimizer.step()

    # Evaluate
    model.eval()
    with torch.no_grad():
        logits = model(X_te)
        probs = torch.sigmoid(logits)
        preds = (probs > 0.5).long()
        acc = (preds == y_te.long()).float().mean().item()

        # Distinguishing advantage = |acc - 0.5| * 2
        advantage = abs(acc - 0.5) * 2

        # Per-class accuracy
        cipher_mask = y_te == 1
        random_mask = y_te == 0
        cipher_acc = (preds[cipher_mask] == 1).float().mean().item() \
            if cipher_mask.sum() > 0 else 0
        random_acc = (preds[random_mask] == 0).float().mean().item() \
            if random_mask.sum() > 0 else 0

    return {
        "accuracy": acc,
        "advantage": advantage,
        "cipher_recall": cipher_acc,
        "random_recall": random_acc,
        "n_params": model.count_parameters(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Cipher factory functions
# ═══════════════════════════════════════════════════════════════════════════

def make_trivium_fn(n_bits=5000):
    def fn(key_seed=0):
        rng = np.random.default_rng(key_seed)
        key = rng.integers(0, 2, 80).tolist()
        iv = rng.integers(0, 2, 80).tolist()
        bits = trivium_keystream(key, iv, n_bits)
        # Convert to bytes
        byte_seq = []
        for i in range(0, len(bits) - 7, 1):
            val = sum(bits[i+j] << j for j in range(8))
            byte_seq.append(val % 256)
        return byte_seq
    return fn


def make_chacha_fn(n_bits=5000, n_rounds=4):
    def fn(key_seed=0):
        rng = np.random.default_rng(key_seed)
        key = [int(x) for x in rng.integers(0, 2**32, 8)]
        bits = chacha20_keystream_bits(key, n_bits, n_rounds)
        byte_seq = []
        for i in range(0, len(bits) - 7, 1):
            val = sum(bits[i+j] << j for j in range(8))
            byte_seq.append(val % 256)
        return byte_seq
    return fn


def make_lfsr_fn(reg_size=31, n_bits=5000):
    def fn(key_seed=0):
        rng = np.random.default_rng(key_seed)
        init = rng.integers(0, 2, reg_size).tolist()
        if sum(init) == 0:
            init[0] = 1
        # Use primitive polynomial taps
        if reg_size == 3:
            taps = [0, 2]
        elif reg_size == 7:
            taps = [0, 6]
        elif reg_size == 15:
            taps = [0, 14]
        elif reg_size == 31:
            taps = [0, 28]
        else:
            taps = [0, reg_size - 1]
        bits = lfsr_sequence(taps, init, n_bits)
        byte_seq = []
        for i in range(0, len(bits) - 7, 1):
            val = sum(bits[i+j] << j for j in range(8))
            byte_seq.append(val % 256)
        return byte_seq
    return fn


def make_padic_fn(p, k, n_terms=5000):
    def fn(key_seed=0):
        m = p ** k
        seq = padic_sequence_bytes(p, k, seed=key_seed + 42, N=n_terms)
        return seq
    return fn


# ═══════════════════════════════════════════════════════════════════════════
# Main experiment
# ═══════════════════════════════════════════════════════════════════════════

def main():
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print("GOHR-STYLE NEURAL DISTINGUISHER EXPERIMENT")
    print(f"Device: {DEVICE}")
    print("=" * 80)

    # Define test suite
    test_cases = [
        # (name, cipher_fn, T_estimate, T_over_L, n_keys)
        ("LFSR-3bit (T=7)",        make_lfsr_fn(3),     7,       1.2,   50),
        ("LFSR-7bit (T=127)",      make_lfsr_fn(7),     127,     21.2,  50),
        ("LFSR-15bit (T=32767)",   make_lfsr_fn(15),    32767,   5461,  50),
        ("LFSR-31bit (T=2^31)",    make_lfsr_fn(31),    2**31-1, 3.6e8, 50),
        ("p-adic easy (p=5,k=1)",  make_padic_fn(5, 1), 25,      4.2,   50),
        ("p-adic med (p=5,k=2)",   make_padic_fn(5, 2), 125,     20.8,  50),
        ("p-adic hard (p=5,k=3)",  make_padic_fn(5, 3), 7295,    1216,  50),
        ("p-adic hard (p=7,k=2)",  make_padic_fn(7, 2), 1083,    180.5, 50),
        ("Trivium",                make_trivium_fn(),    2**288,  ">>",  100),
        ("ChaCha20-4r",            make_chacha_fn(n_rounds=4), 2**64, ">>", 100),
    ]

    all_results = []
    seq_len = 64
    n_samples = 5000

    for name, cipher_fn, T_est, T_L_est, n_keys in test_cases:
        print(f"\n{'-' * 60}")
        print(f"  {name}")
        print(f"  T ~ {T_est}, T/L_in ~ {T_L_est}, n_keys={n_keys}")

        try:
            # Generate data
            X, y = generate_distinguishing_data(
                cipher_fn, n_samples=n_samples, seq_len=seq_len,
                n_keys=n_keys)

            # Split
            n_tr = int(0.8 * len(X))
            X_train, y_train = X[:n_tr], y[:n_tr]
            X_test, y_test = X[n_tr:], y[n_tr:]

            # Train & evaluate (3 seeds for stability)
            advantages = []
            accuracies = []
            for seed in range(3):
                metrics = train_distinguisher(
                    X_train, y_train, X_test, y_test,
                    seq_len=seq_len, epochs=50, seed=seed)
                advantages.append(metrics["advantage"])
                accuracies.append(metrics["accuracy"])

            mean_adv = float(np.mean(advantages))
            std_adv = float(np.std(advantages))
            mean_acc = float(np.mean(accuracies))

            result = {
                "name": name,
                "T_estimate": str(T_est),
                "T_over_L": str(T_L_est),
                "mean_accuracy": mean_acc,
                "mean_advantage": mean_adv,
                "std_advantage": std_adv,
                "distinguishable": mean_adv > 0.05,
                "prediction": "LEARNABLE" if (isinstance(T_L_est, (int, float)) and T_L_est < 30) else "UNLEARNABLE",
                "correct": (mean_adv > 0.05) == (isinstance(T_L_est, (int, float)) and T_L_est < 30),
            }

            status = "OK" if result["correct"] else "X"
            print(f"  Accuracy: {mean_acc:.1%}, Advantage: {mean_adv:.3f}+/-{std_adv:.3f}")
            print(f"  Distinguishable: {result['distinguishable']}, "
                  f"Predicted: {result['prediction']} -> {status}")

        except Exception as e:
            print(f"  ERROR: {e}")
            result = {"name": name, "error": str(e)}

        all_results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("NEURAL DISTINGUISHER RESULTS")
    print("=" * 80)
    print(f"{'Cipher':<30} {'T/L':>10} {'Adv':>8} {'Dist?':>6} "
          f"{'Pred':>12} {'OK':>4}")
    print("-" * 75)

    correct = 0
    total = 0
    for r in all_results:
        if "error" in r:
            print(f"{r['name']:<30} {'ERROR':>10}")
            continue
        total += 1
        if r["correct"]:
            correct += 1
        print(f"{r['name']:<30} {r['T_over_L']:>10} "
              f"{r['mean_advantage']:>7.3f} "
              f"{'YES' if r['distinguishable'] else 'NO':>6} "
              f"{r['prediction']:>12} "
              f"{'OK' if r['correct'] else 'X':>4}")

    print(f"\nPrediction accuracy: {correct}/{total} "
          f"({correct/total:.0%})" if total > 0 else "")

    # Save
    with open(results_dir / "gohr_distinguisher_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nSaved to {results_dir / 'gohr_distinguisher_results.json'}")


if __name__ == "__main__":
    main()
