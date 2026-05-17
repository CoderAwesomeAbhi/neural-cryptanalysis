"""
Extended grokking study: complete-period vs incomplete-period training.

Implements the review prediction:
- Incomplete regime: N_train < T
- Complete regime:   N_train >= T
and tracks delayed generalization over long training horizons.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from generator import generate_piecewise, get_matrices, verify_trajectory_period


@dataclass
class ExperimentConfig:
    name: str
    p: int
    k: int
    l_in: int
    n_train: int
    n_val: int
    n_test: int
    seed: int


class TokenTransformer(nn.Module):
    def __init__(self, vocab_size: int, l_in: int, d_model: int = 128, nhead: int = 4, layers: int = 2) -> None:
        super().__init__()
        self.token = nn.Embedding(vocab_size, d_model)
        self.pos = nn.Embedding(l_in, d_model)
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=4 * d_model,
            dropout=0.1,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=layers)
        self.head = nn.Linear(d_model, vocab_size)
        self.l_in = l_in

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        bsz, seq_len = x.shape
        pos = torch.arange(seq_len, device=x.device).unsqueeze(0).expand(bsz, -1)
        h = self.token(x) + self.pos(pos)
        h = self.encoder(h)
        return self.head(h[:, -1, :])


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_windows(seq: np.ndarray, l_in: int) -> Tuple[np.ndarray, np.ndarray]:
    x = np.array([seq[i : i + l_in] for i in range(len(seq) - l_in)], dtype=np.int64)
    y = np.array([seq[i + l_in] for i in range(len(seq) - l_in)], dtype=np.int64)
    return x, y


def split_dataset(x: np.ndarray, y: np.ndarray, n_train: int, n_val: int, n_test: int) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    need = n_train + n_val + n_test
    if len(x) < need:
        raise ValueError(f"Need {need} samples, have {len(x)}")
    return {
        "train": (x[:n_train], y[:n_train]),
        "val": (x[n_train : n_train + n_val], y[n_train : n_train + n_val]),
        "test": (x[n_train + n_val : n_train + n_val + n_test], y[n_train + n_val : n_train + n_val + n_test]),
    }


def accuracy(model: nn.Module, x: np.ndarray, y: np.ndarray, device: torch.device, batch_size: int = 256) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for i in range(0, len(x), batch_size):
            xb = torch.from_numpy(x[i : i + batch_size]).to(device)
            yb = torch.from_numpy(y[i : i + batch_size]).to(device)
            pred = model(xb).argmax(dim=1)
            correct += int((pred == yb).sum().item())
            total += len(yb)
    return float(correct / max(total, 1))


def run_experiment(
    cfg: ExperimentConfig,
    epochs: int,
    eval_every: int,
    lr: float,
    weight_decay: float,
    batch_size: int,
    target_acc: float,
) -> Dict[str, object]:
    set_seed(cfg.seed)
    m = cfg.p ** cfg.k
    A_list, b_list = get_matrices("sat")

    # Build enough sequence for all splits.
    n_total_windows = cfg.n_train + cfg.n_val + cfg.n_test
    # generate_piecewise returns length N-burn, so include burn budget explicitly
    n_terms = n_total_windows + cfg.l_in + 450
    seq = np.array(generate_piecewise(m, A_list, b_list, N=n_terms, seed=cfg.seed, burn=300), dtype=np.int64)
    x, y = build_windows(seq, cfg.l_in)
    splits = split_dataset(x, y, cfg.n_train, cfg.n_val, cfg.n_test)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TokenTransformer(vocab_size=m, l_in=cfg.l_in).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = nn.CrossEntropyLoss()

    x_train, y_train = splits["train"]
    ds = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train))
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True)

    history: List[Dict[str, float]] = []
    grok_epoch = None

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            total_loss += float(loss.item())

        if epoch % eval_every == 0 or epoch == 1 or epoch == epochs:
            tr_acc = accuracy(model, *splits["train"], device=device)
            va_acc = accuracy(model, *splits["val"], device=device)
            te_acc = accuracy(model, *splits["test"], device=device)
            history.append(
                {
                    "epoch": float(epoch),
                    "train_loss": total_loss / max(len(loader), 1),
                    "train_acc": tr_acc,
                    "val_acc": va_acc,
                    "test_acc": te_acc,
                }
            )
            if grok_epoch is None and va_acc >= target_acc:
                grok_epoch = epoch
            print(
                f"{cfg.name} | epoch {epoch:5d} | "
                f"loss {history[-1]['train_loss']:.4f} | "
                f"train {tr_acc:.3f} | val {va_acc:.3f} | test {te_acc:.3f}"
            )

    traj_period = verify_trajectory_period(m, A_list, b_list, seed=cfg.seed, burn=300)
    result = {
        "config": cfg.__dict__,
        "modulus": m,
        "trajectory_period": traj_period,
        "repetition_ratio": cfg.n_train / max(traj_period, 1),
        "grokking_epoch": grok_epoch,
        "history": history,
    }
    return result


def make_configs(p: int, k: int, l_in: int, n_val: int, n_test: int, seed: int, complete_factor: float) -> List[ExperimentConfig]:
    m = p ** k
    A_list, b_list = get_matrices("sat")
    t = verify_trajectory_period(m, A_list, b_list, seed=seed, burn=300)
    n_complete = int(np.ceil(complete_factor * t))
    return [
        ExperimentConfig("incomplete", p, k, l_in, 3600, n_val, n_test, seed),
        ExperimentConfig("complete", p, k, l_in, n_complete, n_val, n_test, seed),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extended grokking complete-vs-incomplete study")
    parser.add_argument("--p", type=int, default=5)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--l-in", type=int, default=6)
    parser.add_argument("--epochs", type=int, default=2000)
    parser.add_argument("--eval-every", type=int, default=50)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-2)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--n-val", type=int, default=800)
    parser.add_argument("--n-test", type=int, default=800)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target-acc", type=float, default=0.9)
    parser.add_argument("--complete-factor", type=float, default=1.0, help="N_train = complete_factor * T for complete regime")
    parser.add_argument("--out", default="results/extended_grokking_complete_vs_incomplete.json")
    args = parser.parse_args()

    configs = make_configs(
        p=args.p,
        k=args.k,
        l_in=args.l_in,
        n_val=args.n_val,
        n_test=args.n_test,
        seed=args.seed,
        complete_factor=args.complete_factor,
    )

    all_results = []
    for cfg in configs:
        res = run_experiment(
            cfg=cfg,
            epochs=args.epochs,
            eval_every=args.eval_every,
            lr=args.lr,
            weight_decay=args.weight_decay,
            batch_size=args.batch_size,
            target_acc=args.target_acc,
        )
        all_results.append(res)

    out_path = Path(__file__).resolve().parents[1] / args.out
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
