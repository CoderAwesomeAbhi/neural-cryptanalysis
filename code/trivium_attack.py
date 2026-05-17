"""
Trivium neural predictability benchmark.

Implements a standard Trivium bit generator and evaluates a next-bit neural
predictor under finite context windows.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class Trivium:
    """
    Trivium stream cipher (80-bit key, 80-bit IV, 288-bit state).
    """

    def __init__(self, key_bits: Sequence[int], iv_bits: Sequence[int]) -> None:
        if len(key_bits) != 80 or len(iv_bits) != 80:
            raise ValueError("Trivium requires 80-bit key and 80-bit IV.")
        self.s = [0] * 288
        # Register 1: key in s[0:80], then zeros to s[92].
        for i in range(80):
            self.s[i] = int(key_bits[i]) & 1
        # Register 2: iv in s[93:173], then zeros to s[176].
        for i in range(80):
            self.s[93 + i] = int(iv_bits[i]) & 1
        # Register 3: zeros and trailing 111.
        self.s[285] = 1
        self.s[286] = 1
        self.s[287] = 1

        for _ in range(4 * 288):
            self._step(discard_output=True)

    def _step(self, discard_output: bool = False) -> int:
        s = self.s
        t1 = s[65] ^ s[92]
        t2 = s[161] ^ s[176]
        t3 = s[242] ^ s[287]
        z = t1 ^ t2 ^ t3
        t1 = t1 ^ (s[90] & s[91]) ^ s[170]
        t2 = t2 ^ (s[174] & s[175]) ^ s[263]
        t3 = t3 ^ (s[285] & s[286]) ^ s[68]

        new_s = [0] * 288
        # Register 1 length 93: inject t3.
        new_s[0] = t3
        new_s[1:93] = s[0:92]
        # Register 2 length 84: inject t1.
        new_s[93] = t1
        new_s[94:177] = s[93:176]
        # Register 3 length 111: inject t2.
        new_s[177] = t2
        new_s[178:288] = s[177:287]

        self.s = new_s
        return 0 if discard_output else z

    def generate(self, n_bits: int) -> List[int]:
        return [self._step(discard_output=False) for _ in range(n_bits)]


class BitMLP(nn.Module):
    def __init__(self, l_in: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(l_in, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass
class AttackResult:
    l_in: int
    n_train: int
    n_test: int
    accuracy: float
    baseline: float
    advantage: float


def build_dataset(bits: Sequence[int], l_in: int) -> tuple[np.ndarray, np.ndarray]:
    bits_np = np.asarray(bits, dtype=np.int64)
    x = np.array([bits_np[i : i + l_in] for i in range(len(bits_np) - l_in)], dtype=np.float32)
    y = np.array([bits_np[i + l_in] for i in range(len(bits_np) - l_in)], dtype=np.int64)
    return x, y


def run_attack(bits: Sequence[int], l_in: int, n_train: int, n_test: int, epochs: int, seed: int) -> AttackResult:
    set_seed(seed)
    x, y = build_dataset(bits, l_in)
    if len(x) < n_train + n_test:
        raise ValueError("Not enough data for requested train/test split.")

    x_train = torch.from_numpy(x[:n_train])
    y_train = torch.from_numpy(y[:n_train])
    x_test = torch.from_numpy(x[n_train : n_train + n_test])
    y_test = torch.from_numpy(y[n_train : n_train + n_test])

    y_test_np = y_test.numpy()
    baseline = float(max(np.mean(y_test_np == 0), np.mean(y_test_np == 1)))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = BitMLP(l_in=l_in).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()

    loader = DataLoader(TensorDataset(x_train, y_train), batch_size=128, shuffle=True)

    for _ in range(epochs):
        model.train()
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        pred = model(x_test.to(device)).argmax(dim=1).cpu().numpy()
    acc = float((pred == y_test_np).mean())
    return AttackResult(l_in=l_in, n_train=n_train, n_test=n_test, accuracy=acc, baseline=baseline, advantage=acc - baseline)


def main() -> None:
    parser = argparse.ArgumentParser(description="Neural predictability benchmark on Trivium keystream.")
    parser.add_argument("--n-bits", type=int, default=12000)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--n-train", type=int, default=3600)
    parser.add_argument("--n-test", type=int, default=1000)
    parser.add_argument("--contexts", type=int, nargs="+", default=[6, 24, 64])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="results/trivium_neural_attack.json")
    args = parser.parse_args()

    set_seed(args.seed)
    key = np.random.randint(0, 2, size=80).tolist()
    iv = np.random.randint(0, 2, size=80).tolist()
    bits = Trivium(key, iv).generate(args.n_bits)

    results = []
    for l_in in args.contexts:
        res = run_attack(
            bits=bits,
            l_in=l_in,
            n_train=args.n_train,
            n_test=args.n_test,
            epochs=args.epochs,
            seed=args.seed,
        )
        print(
            f"L={res.l_in:3d} | acc={res.accuracy:.4f} | baseline={res.baseline:.4f} | "
            f"adv={res.advantage:+.4f}"
        )
        results.append(res.__dict__)

    payload = {
        "seed": args.seed,
        "n_bits": args.n_bits,
        "epochs": args.epochs,
        "results": results,
    }
    out_path = Path(__file__).resolve().parents[1] / args.out
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
