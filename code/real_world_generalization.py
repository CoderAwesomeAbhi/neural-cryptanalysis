"""
Real-world cipher generalization benchmark.

Runs the same neural next-bit predictor on:
1. Trivium keystream bits
2. ChaCha20 keystream bits
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

import numpy as np

from trivium_attack import Trivium, run_attack, set_seed


class ChaCha20:
    """Minimal ChaCha20 keystream generator (RFC 8439 style core)."""

    def __init__(self, key: bytes, nonce: bytes, counter: int = 1) -> None:
        if len(key) != 32:
            raise ValueError("ChaCha20 key must be 32 bytes.")
        if len(nonce) != 12:
            raise ValueError("ChaCha20 nonce must be 12 bytes.")
        self.key = key
        self.nonce = nonce
        self.counter = counter

    @staticmethod
    def _rotl32(x: int, n: int) -> int:
        return ((x << n) & 0xFFFFFFFF) | (x >> (32 - n))

    def _quarter_round(self, st: List[int], a: int, b: int, c: int, d: int) -> None:
        st[a] = (st[a] + st[b]) & 0xFFFFFFFF
        st[d] ^= st[a]
        st[d] = self._rotl32(st[d], 16)
        st[c] = (st[c] + st[d]) & 0xFFFFFFFF
        st[b] ^= st[c]
        st[b] = self._rotl32(st[b], 12)
        st[a] = (st[a] + st[b]) & 0xFFFFFFFF
        st[d] ^= st[a]
        st[d] = self._rotl32(st[d], 8)
        st[c] = (st[c] + st[d]) & 0xFFFFFFFF
        st[b] ^= st[c]
        st[b] = self._rotl32(st[b], 7)

    def _block(self) -> bytes:
        constants = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574]
        key_words = [int.from_bytes(self.key[4 * i : 4 * (i + 1)], "little") for i in range(8)]
        nonce_words = [int.from_bytes(self.nonce[4 * i : 4 * (i + 1)], "little") for i in range(3)]
        state = constants + key_words + [self.counter] + nonce_words
        working = state.copy()

        for _ in range(10):
            self._quarter_round(working, 0, 4, 8, 12)
            self._quarter_round(working, 1, 5, 9, 13)
            self._quarter_round(working, 2, 6, 10, 14)
            self._quarter_round(working, 3, 7, 11, 15)
            self._quarter_round(working, 0, 5, 10, 15)
            self._quarter_round(working, 1, 6, 11, 12)
            self._quarter_round(working, 2, 7, 8, 13)
            self._quarter_round(working, 3, 4, 9, 14)

        out = [((working[i] + state[i]) & 0xFFFFFFFF) for i in range(16)]
        self.counter = (self.counter + 1) & 0xFFFFFFFF
        return b"".join(w.to_bytes(4, "little") for w in out)

    def generate_bytes(self, n_bytes: int) -> bytes:
        out = bytearray()
        while len(out) < n_bytes:
            out.extend(self._block())
        return bytes(out[:n_bytes])

    def generate_bits(self, n_bits: int) -> List[int]:
        n_bytes = (n_bits + 7) // 8
        ks = self.generate_bytes(n_bytes)
        bits: List[int] = []
        for b in ks:
            for i in range(8):
                bits.append((b >> i) & 1)
                if len(bits) >= n_bits:
                    return bits
        return bits


def main() -> None:
    parser = argparse.ArgumentParser(description="Neural generalization to real stream ciphers")
    parser.add_argument("--n-bits", type=int, default=15000)
    parser.add_argument("--n-train", type=int, default=3600)
    parser.add_argument("--n-test", type=int, default=1000)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--contexts", type=int, nargs="+", default=[6, 24, 64])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="results/real_world_generalization.json")
    args = parser.parse_args()

    set_seed(args.seed)
    results = {"seed": args.seed, "ciphers": {}}

    # Trivium
    trivium_key = np.random.randint(0, 2, size=80).tolist()
    trivium_iv = np.random.randint(0, 2, size=80).tolist()
    trivium_bits = Trivium(trivium_key, trivium_iv).generate(args.n_bits)
    trivium_rows = []
    for l_in in args.contexts:
        row = run_attack(
            bits=trivium_bits,
            l_in=l_in,
            n_train=args.n_train,
            n_test=args.n_test,
            epochs=args.epochs,
            seed=args.seed,
        ).__dict__
        trivium_rows.append(row)
        print(f"Trivium | L={l_in:3d} | acc={row['accuracy']:.4f} | adv={row['advantage']:+.4f}")
    results["ciphers"]["trivium"] = trivium_rows

    # ChaCha20
    chacha_key = bytes(np.random.randint(0, 256, size=32).tolist())
    chacha_nonce = bytes(np.random.randint(0, 256, size=12).tolist())
    chacha_bits = ChaCha20(chacha_key, chacha_nonce).generate_bits(args.n_bits)
    chacha_rows = []
    for l_in in args.contexts:
        row = run_attack(
            bits=chacha_bits,
            l_in=l_in,
            n_train=args.n_train,
            n_test=args.n_test,
            epochs=args.epochs,
            seed=args.seed,
        ).__dict__
        chacha_rows.append(row)
        print(f"ChaCha20 | L={l_in:3d} | acc={row['accuracy']:.4f} | adv={row['advantage']:+.4f}")
    results["ciphers"]["chacha20"] = chacha_rows

    out_path = Path(__file__).resolve().parents[1] / args.out
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
