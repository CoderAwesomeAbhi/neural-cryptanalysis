"""
Long-context p-adic attention experiment.

Tests Lin in {p^2, p^3} (subject to max context cap) and measures correlation
between learned attention-to-history and p-adic proximity.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from torch.utils.data import DataLoader, TensorDataset

from generator import generate_piecewise, get_matrices


class SingleLayerAttentionPredictor(nn.Module):
    def __init__(self, vocab_size: int, l_in: int, d_model: int = 128, nhead: int = 4) -> None:
        super().__init__()
        self.token = nn.Embedding(vocab_size, d_model)
        self.pos = nn.Embedding(l_in, d_model)
        self.attn = nn.MultiheadAttention(d_model, nhead, batch_first=True, dropout=0.1)
        self.ff = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(),
            nn.Linear(4 * d_model, d_model),
        )
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)
        self.l_in = l_in

    def forward(self, x: torch.Tensor, return_weights: bool = False):
        bsz, seqlen = x.shape
        pos = torch.arange(seqlen, device=x.device).unsqueeze(0).expand(bsz, -1)
        h = self.token(x) + self.pos(pos)
        attn_out, attn_w = self.attn(
            h, h, h, need_weights=return_weights, average_attn_weights=False
        )
        h = self.ln1(h + attn_out)
        h = self.ln2(h + self.ff(h))
        logits = self.head(h[:, -1, :])
        if return_weights:
            return logits, attn_w
        return logits


def padic_valuation(n: int, p: int) -> int:
    if n <= 0:
        return 0
    v = 0
    while n % p == 0:
        n //= p
        v += 1
    return v


def build_dataset(seq: np.ndarray, l_in: int) -> Tuple[np.ndarray, np.ndarray]:
    x = np.array([seq[i : i + l_in] for i in range(len(seq) - l_in)], dtype=np.int64)
    y = np.array([seq[i + l_in] for i in range(len(seq) - l_in)], dtype=np.int64)
    return x, y


def train_model(model: nn.Module, x_train: np.ndarray, y_train: np.ndarray, epochs: int, lr: float, batch_size: int, device: torch.device) -> None:
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
    loss_fn = nn.CrossEntropyLoss()
    ds = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train))
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True)
    model.train()
    for _ in range(epochs):
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()


def evaluate(model: nn.Module, x: np.ndarray, y: np.ndarray, device: torch.device) -> float:
    model.eval()
    with torch.no_grad():
        xb = torch.from_numpy(x).to(device)
        pred = model(xb).argmax(dim=1).cpu().numpy()
    return float((pred == y).mean())


def extract_attention_profile(model: nn.Module, x_eval: np.ndarray, device: torch.device, max_samples: int) -> np.ndarray:
    model.eval()
    x_eval = x_eval[:max_samples]
    with torch.no_grad():
        xb = torch.from_numpy(x_eval).to(device)
        _, attn = model(xb, return_weights=True)
        # attn shape: (batch, heads, tgt_len, src_len)
        last_q = attn[:, :, -1, :]  # (batch, heads, src_len)
        profile = last_q.mean(dim=1).mean(dim=0).cpu().numpy()  # avg heads and batch
    return profile


def run_context_experiment(p: int, k: int, l_in: int, n_train: int, n_eval: int, epochs: int, seed: int) -> Dict[str, float]:
    np.random.seed(seed)
    torch.manual_seed(seed)
    m = p ** k
    A_list, b_list = get_matrices("sat")
    total = n_train + n_eval + l_in + 500
    seq = np.array(generate_piecewise(m, A_list, b_list, N=total, burn=300, seed=seed), dtype=np.int64)
    x, y = build_dataset(seq, l_in)
    x_train, y_train = x[:n_train], y[:n_train]
    x_eval, y_eval = x[n_train : n_train + n_eval], y[n_train : n_train + n_eval]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SingleLayerAttentionPredictor(vocab_size=m, l_in=l_in).to(device)
    train_model(model, x_train, y_train, epochs=epochs, lr=1e-3, batch_size=64, device=device)
    acc = evaluate(model, x_eval, y_eval, device=device)

    attn_profile = extract_attention_profile(model, x_eval, device=device, max_samples=min(512, len(x_eval)))
    # Compare only historical positions, exclude self (offset 0).
    hist_attn = attn_profile[:-1]
    offsets = np.arange(l_in - 1, 0, -1)  # far past -> near past
    padic_scores = np.array([p ** (-padic_valuation(int(d), p)) for d in offsets], dtype=np.float64)
    rho, pval = spearmanr(hist_attn, padic_scores)

    return {
        "p": p,
        "k": k,
        "m": m,
        "l_in": l_in,
        "n_train": n_train,
        "n_eval": n_eval,
        "accuracy": acc,
        "spearman_rho": float(rho),
        "spearman_pvalue": float(pval),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Long-context p-adic attention correlation experiment")
    parser.add_argument("--p", type=int, default=5)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--n-train", type=int, default=3600)
    parser.add_argument("--n-eval", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-context", type=int, default=128)
    parser.add_argument("--out", default="results/padic_attention_long_context.json")
    args = parser.parse_args()

    contexts = [args.p ** 2, args.p ** 3]
    contexts = [c for c in contexts if c <= args.max_context]
    if not contexts:
        raise ValueError("No valid contexts after max-context filtering.")

    rows: List[Dict[str, float]] = []
    for l_in in contexts:
        row = run_context_experiment(
            p=args.p,
            k=args.k,
            l_in=l_in,
            n_train=args.n_train,
            n_eval=args.n_eval,
            epochs=args.epochs,
            seed=args.seed,
        )
        rows.append(row)
        print(
            f"L={l_in:3d} | acc={row['accuracy']:.4f} | "
            f"rho={row['spearman_rho']:.4f} | p={row['spearman_pvalue']:.4g}"
        )

    out_path = Path(__file__).resolve().parents[1] / args.out
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
