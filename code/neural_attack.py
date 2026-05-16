"""
neural_attack.py
================
Neural Cryptanalysis Experiments: MLP and Transformer.

Trains sequence-prediction models on windowed sequences from the piecewise
affine recurrence generator and evaluates next-term prediction accuracy.

Experimental setup (Section 4 of the paper):
  Input:    L_in = 6 consecutive residue values, normalized to [0, 1]
  Target:   next residue value (classification over Z/mZ)
  MLP:      MLPClassifier(256, 128), ReLU, Adam lr=0.001, 50 epochs
  Transformer: 2-layer encoder, d_model=64, 4 heads, ff_dim=128, 50 epochs
  Split:    80% train / 10% val / 10% test

Key finding (Section 6.1 of the paper):
  The ratio T/L_in is the operationally relevant hardness parameter:
    T/L_in <= 21  ->  both models achieve 100% accuracy
    T/L_in >= 181 ->  both models collapse to <= 17% accuracy (near-random)

Author: Research pipeline for
  "Period Growth and Neural Predictability in Piecewise Affine Systems
   over Residue Rings" — Abhijay Gangarapu, UT Austin / ISEF
"""

import sys
import warnings
import numpy as np
from typing import List, Tuple, Dict, Optional

# -- scikit-learn MLP ----------------------------------------------------------
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score

# -- PyTorch Transformer -------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[neural_attack] Warning: PyTorch not found. Transformer experiments disabled.")

L_IN: int = 6   # Default input window length
L_IN_SWEEP: List[int] = [6, 16, 32, 64, 128, 256]  # For threshold experiments


# ════════════════════════════════════════════════════════════════════════════
# Dataset construction
# ════════════════════════════════════════════════════════════════════════════

def make_windowed_dataset(
    seq: List[int],
    m: int,
    L_in: int = L_IN,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert a 1-D integer sequence into windowed (X, y) pairs.

        X[i] = (seq[i]/m, seq[i+1]/m, ..., seq[i+L_in-1]/m) in [0,1]^{L_in}
        y[i] = seq[i + L_in]  in {0, ..., m-1}

    Parameters
    ----------
    seq  : list of integers in {0, ..., m-1}
    m    : modulus (used for normalization to [0,1])
    L_in : input window length

    Returns
    -------
    X : float32 array of shape (N-L_in, L_in)
    y : int32   array of shape (N-L_in,)
    """
    if m <= 1:
        raise ValueError(f"m must be >= 2, got {m}")
    if L_in <= 0:
        raise ValueError(f"L_in must be > 0, got {L_in}")
    N = len(seq)
    if N <= L_in:
        raise ValueError(f"Sequence too short ({N}) for L_in={L_in}")
    if any((int(v) < 0 or int(v) >= m) for v in seq):
        raise ValueError("All sequence values must lie in {0, ..., m-1}")

    n_rows = N - L_in
    X = np.array(
        [[seq[i + t] / m for t in range(L_in)] for i in range(n_rows)],
        dtype=np.float32,
    )
    y = np.array([seq[i + L_in] for i in range(n_rows)], dtype=np.int32)
    return X, y


def train_val_test_split(
    X: np.ndarray,
    y: np.ndarray,
    train_frac: float = 0.8,
    val_frac:   float = 0.1,
) -> Tuple[np.ndarray, ...]:
    """Deterministic (non-shuffled) 80/10/10 split."""
    N  = len(X)
    t1 = int(train_frac * N)
    t2 = int((train_frac + val_frac) * N)
    return X[:t1], y[:t1], X[t1:t2], y[t1:t2], X[t2:], y[t2:]


# ════════════════════════════════════════════════════════════════════════════
# MLP (scikit-learn)
# ════════════════════════════════════════════════════════════════════════════

def train_mlp(
    X:      np.ndarray,
    y:      np.ndarray,
    m:      int,
    epochs: int = 50,
    seed:   int = 42,
    hidden: Tuple[int, ...] = (256, 128),
    lr:     float = 1e-3,
) -> Dict:
    """
    Train an MLP-(256,128) classifier and return accuracy metrics.

    Parameters
    ----------
    X, y   : windowed dataset (from make_windowed_dataset)
    m      : number of output classes
    epochs : training iterations (early stopping disabled)
    seed   : random seed
    hidden : hidden layer sizes
    lr     : Adam learning rate

    Returns
    -------
    dict with 'val_acc', 'test_acc', 'n_train', 'n_val', 'n_test'.
    """
    if m <= 1:
        raise ValueError(f"m must be >= 2, got {m}")
    if epochs <= 0:
        raise ValueError(f"epochs must be > 0, got {epochs}")
    if len(X) != len(y):
        raise ValueError(f"X and y length mismatch: {len(X)} != {len(y)}")

    np.random.seed(seed)
    Xtr, ytr, Xva, yva, Xte, yte = train_val_test_split(X, y)

    clf = MLPClassifier(
        hidden_layer_sizes=hidden,
        activation="relu",
        solver="adam",
        learning_rate_init=lr,
        max_iter=epochs,
        random_state=seed,
        warm_start=False,
        n_iter_no_change=epochs + 1,   # disable early stopping
        early_stopping=False,
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        clf.fit(Xtr, ytr)

    return {
        "val_acc":         accuracy_score(yva, clf.predict(Xva)),
        "test_acc":        accuracy_score(yte, clf.predict(Xte)),
        "n_train":         len(Xtr),
        "n_val":           len(Xva),
        "n_test":          len(Xte),
        "random_baseline": 1.0 / m,
    }


def evaluate_mlp_over_seeds(
    X:       np.ndarray,
    y:       np.ndarray,
    m:       int,
    n_seeds: int = 5,
    epochs:  int = 50,
    **kwargs,
) -> Dict:
    """
    Evaluate MLP over multiple random seeds; return mean ± std of val_acc.
    """
    if n_seeds <= 0:
        raise ValueError(f"n_seeds must be > 0, got {n_seeds}")
    if epochs <= 0:
        raise ValueError(f"epochs must be > 0, got {epochs}")

    accs = [
        train_mlp(X, y, m, epochs=epochs, seed=seed, **kwargs)["val_acc"]
        for seed in range(n_seeds)
    ]
    mean = float(np.mean(accs))
    std = float(np.std(accs))
    ci95 = 1.96 * std / np.sqrt(n_seeds)
    return {
        "mean": mean,
        "std":  std,
        "min":  float(np.min(accs)),
        "max":  float(np.max(accs)),
        "ci95": float(ci95),
        "random_baseline": 1.0 / m,
        "n_seeds": n_seeds,
    }


def evaluate_over_seeds(
    X: np.ndarray,
    y: np.ndarray,
    m: int,
    n_seeds: int = 5,
    epochs: int = 50,
    **kwargs,
) -> Dict:
    """
    Compatibility wrapper used by verify_all.py.
    Returns the same aggregate values with explicit key names.
    """
    stats = evaluate_mlp_over_seeds(X, y, m, n_seeds=n_seeds, epochs=epochs, **kwargs)
    return {
        "mean_val_acc": stats["mean"],
        "std_val_acc": stats["std"],
        "min_val_acc": stats["min"],
        "max_val_acc": stats["max"],
        "val_ci95": stats["ci95"],
        "random_baseline": stats["random_baseline"],
        "n_seeds": stats["n_seeds"],
    }


# ════════════════════════════════════════════════════════════════════════════
# PyTorch Transformer
# ════════════════════════════════════════════════════════════════════════════

if TORCH_AVAILABLE:

    class AttentionCapturingLayer(nn.TransformerEncoderLayer):
        """
        TransformerEncoderLayer subclass that captures attention weights
        on every forward pass by calling self_attn with need_weights=True.

        This is necessary because the standard TransformerEncoderLayer sets
        need_weights=False internally (for efficiency), which prevents
        attention extraction via normal hooks.
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.last_attn_weights: Optional["torch.Tensor"] = None

        def forward(
            self,
            src:                 "torch.Tensor",
            src_mask:            Optional["torch.Tensor"] = None,
            src_key_padding_mask: Optional["torch.Tensor"] = None,
            **kwargs,
        ) -> "torch.Tensor":
            """
            Override forward to capture attention weights.
            src shape: (B, L, d_model) when batch_first=True.
            """
            # batch_first=True: src is (B, L, d_model)
            # MultiheadAttention also has batch_first=True inside, so we pass
            # src directly (no transpose needed).
            try:
                src2, attn = self.self_attn(
                    src, src, src,
                    attn_mask=src_mask,
                    key_padding_mask=src_key_padding_mask,
                    need_weights=True,
                    average_attn_weights=True,  # PyTorch >= 1.13
                )
            except TypeError:
                # Fallback for PyTorch < 1.13
                src2, attn = self.self_attn(
                    src, src, src,
                    attn_mask=src_mask,
                    key_padding_mask=src_key_padding_mask,
                    need_weights=True,
                )

            self.last_attn_weights = attn.detach().cpu()  # (B, L, L)

            # Standard residual connections and layer normalisation
            src = self.norm1(src + self.dropout1(src2))
            src2 = self.linear2(self.dropout(self.activation(self.linear1(src))))
            src = self.norm2(src + self.dropout2(src2))
            return src


    class SeqTransformer(nn.Module):
        """
        Two-layer Transformer encoder for next-term prediction over Z/mZ.

        Architecture (Appendix D of the paper):
          embed:   Linear(1 -> d_model)
          pos_enc: Embedding(L_in, d_model)  [learned positional encoding]
          encoder: 2 × AttentionCapturingLayer(d_model, nhead, ff_dim, dropout=0)
          head:    Linear(d_model × L_in -> m)

        Input:  (B, L_in) float tensor of normalised residues in [0,1]
        Output: (B, m) logits over Z/mZ
        """

        def __init__(
            self,
            m:        int,
            L_in:     int = L_IN,
            d_model:  int = 64,
            nhead:    int = 4,
            ff_dim:   int = 128,
            n_layers: int = 2,
            dropout:  float = 0.0,
        ):
            super().__init__()
            self.m       = m
            self.L_in    = L_in
            self.d_model = d_model

            self.embed   = nn.Linear(1, d_model)
            self.pos_enc = nn.Embedding(L_in, d_model)

            self.encoder = nn.ModuleList([
                AttentionCapturingLayer(
                    d_model=d_model,
                    nhead=nhead,
                    dim_feedforward=ff_dim,
                    dropout=dropout,
                    batch_first=True,
                )
                for _ in range(n_layers)
            ])

            self.head = nn.Linear(d_model * L_in, m)

        def _embed(self, x: "torch.Tensor") -> "torch.Tensor":
            """
            Embed a batch of input windows.
            x:      (B, L_in) normalised floats
            return: (B, L_in, d_model)
            """
            x   = x.unsqueeze(-1)                           # (B, L_in, 1)
            x   = self.embed(x)                             # (B, L_in, d_model)
            pos = torch.arange(self.L_in, device=x.device)  # (L_in,)
            x   = x + self.pos_enc(pos)                     # (B, L_in, d_model)
            return x

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            """
            x:      (B, L_in)  normalised residue windows
            return: (B, m)     logits
            """
            h = self._embed(x)                  # (B, L_in, d_model)
            for layer in self.encoder:
                h = layer(h)                    # (B, L_in, d_model)
            h = h.flatten(1)                    # (B, L_in × d_model)
            return self.head(h)                 # (B, m)

        def get_attention_maps(
            self,
            x: "torch.Tensor",
        ) -> List["torch.Tensor"]:
            """
            Extract layer-by-layer attention weight matrices for a batch.

            Parameters
            ----------
            x : (B, L_in) input tensor

            Returns
            -------
            List of tensors, one per encoder layer, each shape (B, L_in, L_in).
            Entries are head-averaged attention weights.
            """
            self.eval()
            with torch.no_grad():
                h = self._embed(x)
                maps = []
                for layer in self.encoder:
                    h = layer(h)
                    if layer.last_attn_weights is not None:
                        maps.append(layer.last_attn_weights)  # (B, L_in, L_in)
            return maps

        def count_parameters(self) -> int:
            return sum(p.numel() for p in self.parameters() if p.requires_grad)


    class SeqLSTM(nn.Module):
        """LSTM for next-term prediction over Z/mZ."""
        
        def __init__(self, m: int, L_in: int = L_IN, hidden_size: int = 128, num_layers: int = 2):
            super().__init__()
            self.m, self.L_in = m, L_in
            self.lstm = nn.LSTM(1, hidden_size, num_layers, batch_first=True)
            self.fc = nn.Sequential(nn.Linear(hidden_size, 64), nn.ReLU(), nn.Linear(64, m))
        
        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            return self.fc(self.lstm(x.unsqueeze(-1))[0][:, -1, :])
        
        def count_parameters(self) -> int:
            return sum(p.numel() for p in self.parameters() if p.requires_grad)


    def train_lstm(X: np.ndarray, y: np.ndarray, m: int, epochs: int = 50, 
                   lr: float = 1e-3, batch_size: int = 256, seed: int = 42, 
                   device: str = "cpu") -> Tuple["SeqLSTM", Dict]:
        """Train LSTM."""
        torch.manual_seed(seed)
        Xtr, ytr, Xva, yva, Xte, yte = train_val_test_split(X, y)
        
        def to_t(X, y): return torch.tensor(X, dtype=torch.float32, device=device), torch.tensor(y, dtype=torch.long, device=device)
        Xtr_t, ytr_t = to_t(Xtr, ytr)
        Xva_t, yva_t = to_t(Xva, yva)
        Xte_t, yte_t = to_t(Xte, yte)
        
        model = SeqLSTM(m=m).to(device)
        optimizer = optim.Adam(model.parameters(), lr=lr)
        criterion = nn.CrossEntropyLoss()
        
        for _ in range(epochs):
            model.train()
            for Xb, yb in DataLoader(TensorDataset(Xtr_t, ytr_t), batch_size=batch_size, shuffle=True):
                optimizer.zero_grad()
                criterion(model(Xb), yb).backward()
                optimizer.step()
        
        model.eval()
        with torch.no_grad():
            val_acc = (model(Xva_t).argmax(1) == yva_t).float().mean().item()
            test_acc = (model(Xte_t).argmax(1) == yte_t).float().mean().item()
        
        return model, {"val_acc": val_acc, "test_acc": test_acc, "n_params": model.count_parameters(), "random_baseline": 1.0/m}


    def train_transformer(
        X:         np.ndarray,
        y:         np.ndarray,
        m:         int,
        epochs:    int = 50,
        lr:        float = 1e-3,
        batch_size: int = 256,
        seed:      int = 42,
        device:    str = "cpu",
        verbose:   bool = False,
    ) -> Tuple["SeqTransformer", Dict]:
        """
        Train a SeqTransformer and return (model, metrics).

        Parameters
        ----------
        X, y       : windowed dataset
        m          : number of output classes (modulus)
        epochs     : training epochs
        lr         : Adam learning rate
        batch_size : mini-batch size
        seed       : RNG seed for weight initialisation
        device     : 'cpu' or 'cuda'
        verbose    : print epoch-level loss

        Returns
        -------
        (trained model, metrics dict with val_acc, test_acc, ...)
        """
        torch.manual_seed(seed)
        Xtr, ytr, Xva, yva, Xte, yte = train_val_test_split(X, y)

        def to_tensors(Xa, ya):
            return (
                torch.tensor(Xa, dtype=torch.float32, device=device),
                torch.tensor(ya, dtype=torch.long,    device=device),
            )

        Xtr_t, ytr_t = to_tensors(Xtr, ytr)
        Xva_t, yva_t = to_tensors(Xva, yva)
        Xte_t, yte_t = to_tensors(Xte, yte)

        loader = DataLoader(
            TensorDataset(Xtr_t, ytr_t),
            batch_size=batch_size,
            shuffle=True,
        )

        model     = SeqTransformer(m=m).to(device)
        optimizer = optim.Adam(model.parameters(), lr=lr)
        criterion = nn.CrossEntropyLoss()

        history = []
        for epoch in range(epochs):
            model.train()
            total_loss = 0.0
            for Xb, yb in loader:
                optimizer.zero_grad()
                loss = criterion(model(Xb), yb)
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * len(Xb)

            if verbose and (epoch + 1) % 10 == 0:
                with torch.no_grad():
                    model.eval()
                    preds = model(Xva_t).argmax(1)
                    vacc  = (preds == yva_t).float().mean().item()
                print(f"    Epoch {epoch+1:3d}: loss={total_loss/len(Xtr_t):.4f}  val_acc={vacc:.3f}")
                history.append(vacc)

        # Final evaluation
        model.eval()
        with torch.no_grad():
            def acc(Xb, yb):
                return (model(Xb).argmax(1) == yb).float().mean().item()
            val_acc  = acc(Xva_t, yva_t)
            test_acc = acc(Xte_t, yte_t)

        return model, {
            "val_acc":         val_acc,
            "test_acc":        test_acc,
            "n_train":         len(Xtr),
            "n_val":           len(Xva),
            "n_test":          len(Xte),
            "random_baseline": 1.0 / m,
            "n_params":        model.count_parameters(),
            "history":         history,
        }


    def extract_attention_summary(
        model:    "SeqTransformer",
        X_val:    np.ndarray,
        device:   str = "cpu",
        n_batch:  int = 200,
    ) -> Dict:
        """
        Extract and summarise attention maps for layer 0 over n_batch examples.

        Returns a dict with:
          'mean_attn_L0' : (L_in, L_in) average attention matrix for layer 0
          'max_pos'      : (query_idx, key_idx) position of global maximum
          'entropy'      : average per-row Shannon entropy of attention weights
        """
        X_t = torch.tensor(X_val[:n_batch], dtype=torch.float32, device=device)

        model.eval()
        maps = model.get_attention_maps(X_t)

        if not maps:
            return {"mean_attn_L0": None, "max_pos": None, "entropy": None}

        # Layer-0 attention: (n_batch, L_in, L_in)
        attn0 = maps[0].numpy()                        # (B, L, L)
        mean  = attn0.mean(axis=0)                     # (L, L)

        # Maximum attention position
        qi, ki = np.unravel_index(mean.argmax(), mean.shape)

        # Row-wise entropy: H(row) = -Σ_j w_j log w_j
        eps     = 1e-9
        row_ent = -(attn0 * np.log(attn0 + eps)).sum(axis=-1)  # (B, L)
        avg_ent = float(row_ent.mean())

        return {
            "mean_attn_L0": mean,
            "max_pos":       (int(qi), int(ki)),
            "entropy":       avg_ent,
        }


# ════════════════════════════════════════════════════════════════════════════
# All 11 experimental configurations (Table 4 of the paper)
# ════════════════════════════════════════════════════════════════════════════

def build_all_configs(N: int = 4500, seed: int = 42) -> List[Dict]:
    """
    Build all eleven experimental configurations from Table 4 of the paper.

    Each config dict has keys:
      name, m, T_traj, T_over_L, seq, random_baseline

    Configurations are ordered by T/L_in (ascending) to match the paper.
    """
    sys.path.insert(0, ".")
    from generator import (
        generate_piecewise, generate_linear,
        A0_CANON, b0_CANON, A1_CANON, b1_CANON,
        A0_VIOL,  b0_VIOL,
        A2_3R,    b2_3R,
    )

    # Trajectory periods verified from seed=42, burn=300 (Table 4 / Appendix B)
    configs_raw = [
        # (name, m, T_traj, gen_fn)
        ("PW-3R composite (m=35)",    35,   10,
         lambda: generate_piecewise(35,  [A0_CANON, A1_CANON, A2_3R],
                                         [b0_CANON, b1_CANON, b2_3R],  N=N, seed=seed)),
        ("Linear r=1 (m=5)",           5,   25,
         lambda: generate_linear(   5,   A0_CANON, b0_CANON,           N=N, seed=seed)),
        ("PW-2R H-viol (m=25)",       25,   30,
         lambda: generate_piecewise(25,  [A0_VIOL, A1_CANON],
                                         [b0_VIOL, b1_CANON],           N=N, seed=seed)),
        ("p=11 H-sat (m=11)",         11,   40,
         lambda: generate_piecewise(11,  [A0_CANON, A1_CANON],
                                         [b0_CANON, b1_CANON],           N=N, seed=seed)),
        ("p=7 H-viol (m=49)",         49,   46,
         lambda: generate_piecewise(49,  [A0_VIOL, A1_CANON],
                                         [b0_VIOL, b1_CANON],           N=N, seed=seed)),
        ("p=13 H-sat (m=13)",         13,   74,
         lambda: generate_piecewise(13,  [A0_CANON, A1_CANON],
                                         [b0_CANON, b1_CANON],           N=N, seed=seed)),
        ("p=5 H-sat (m=25)",          25,  125,
         lambda: generate_piecewise(25,  [A0_CANON, A1_CANON],
                                         [b0_CANON, b1_CANON],           N=N, seed=seed)),
        # Hard configurations: T/L_in >= 181
        ("p=7 H-sat (m=49)",          49,  1083,
         lambda: generate_piecewise(49,  [A0_CANON, A1_CANON],
                                         [b0_CANON, b1_CANON],           N=N, seed=seed)),
        ("p=11 H-sat (m=121)",       121,  4912,
         lambda: generate_piecewise(121, [A0_CANON, A1_CANON],
                                         [b0_CANON, b1_CANON],           N=N, seed=seed)),
        ("p=5 H-sat (m=125)",        125,  7295,
         lambda: generate_piecewise(125, [A0_CANON, A1_CANON],
                                         [b0_CANON, b1_CANON],           N=N, seed=seed)),
        ("p=13 H-sat (m=169)",       169, 20475,
         lambda: generate_piecewise(169, [A0_CANON, A1_CANON],
                                         [b0_CANON, b1_CANON],           N=N, seed=seed)),
    ]

    result = []
    for name, m, T_traj, gen_fn in configs_raw:
        seq = gen_fn()
        X, y = make_windowed_dataset(seq, m)
        result.append({
            "name":            name,
            "m":               m,
            "T_traj":          T_traj,
            "T_over_L":        round(T_traj / L_IN, 1),
            "seq":             seq,
            "X":               X,
            "y":               y,
            "random_baseline": 1.0 / m,
        })
    return result


# ════════════════════════════════════════════════════════════════════════════
# Main experiment runner
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    N       = 4500
    EPOCHS  = 50
    N_SEEDS = 5

    print("=" * 80)
    print("neural_attack.py — MLP and Transformer Cryptanalysis Experiments")
    print("=" * 80)
    print(f"\nSetup: N={N}, burn=300, L_in={L_IN}, MLP epochs={EPOCHS}, seeds={N_SEEDS}\n")

    # -- MLP: all 11 configurations --------------------------------------------
    print("[ MLP-(256,128): All 11 Configurations ]")
    print()
    header = (f"  {'Configuration':<30}  {'m':>5}  {'T':>6}  {'T/L':>5}  "
              f"{'mean Acc':>9}  {'std':>6}  {'Baseline':>9}")
    print(header)
    print("  " + "-" * (len(header) - 2))

    configs = build_all_configs(N=N)

    separator_printed = False
    for cfg in configs:
        result = evaluate_mlp_over_seeds(cfg["X"], cfg["y"], cfg["m"],
                                         n_seeds=N_SEEDS, epochs=EPOCHS)
        if cfg["T_over_L"] > 21 and not separator_printed:
            print("  " + "-" * (len(header) - 2) + "  ← phase transition")
            separator_printed = True

        print(f"  {cfg['name']:<30}  {cfg['m']:>5}  {cfg['T_traj']:>6}  "
              f"{cfg['T_over_L']:>5}  "
              f"{result['mean']:>8.1%}  ±{result['std']:>4.1%}  "
              f"{cfg['random_baseline']:>8.1%}")

    # -- Transformer: easy vs hard ---------------------------------------------
    if TORCH_AVAILABLE:
        print()
        print("[ PyTorch Transformer: Easy (m=25) vs Hard (m=125) ]")
        print()

        for cfg_name in ["p=5 H-sat (m=25)", "p=5 H-sat (m=125)"]:
            cfg = next(c for c in configs if c["name"] == cfg_name)
            model, metrics = train_transformer(
                cfg["X"], cfg["y"], cfg["m"],
                epochs=EPOCHS, verbose=False,
            )
            label = "easy" if cfg["m"] == 25 else "hard"
            print(f"  {cfg_name:<30}  val_acc={metrics['val_acc']:.1%}  "
                  f"params={metrics['n_params']:,}  [{label}]")

        # Attention map analysis
        print()
        print("[ Attention Map Analysis: Layer-0 Average Attention ]")
        print()

        for cfg_name, label in [("p=5 H-sat (m=25)", "EASY"), ("p=5 H-sat (m=125)", "HARD")]:
            cfg   = next(c for c in configs if c["name"] == cfg_name)
            model, _ = train_transformer(cfg["X"], cfg["y"], cfg["m"], epochs=EPOCHS)

            _, _, Xva, *_ = train_val_test_split(cfg["X"], cfg["y"])
            summary = extract_attention_summary(model, Xva)

            mean_a = summary["mean_attn_L0"]
            qi, ki = summary["max_pos"]
            ent    = summary["entropy"]

            print(f"  {cfg_name} [{label}]:")
            print(f"    Avg attention entropy: {ent:.3f} bits (higher = more diffuse)")
            print(f"    Max attention: query pos {qi} -> key pos {ki}")
            if mean_a is not None:
                # Describe the pattern
                row_max = mean_a.max(axis=1)
                print(f"    Row-max weights: {[f'{v:.2f}' for v in row_max]}")
            print()
    else:
        print("\n[Transformer experiments skipped — install PyTorch to enable]")

    print()
    print("KEY RESULT: When T/L_in >> 1 (hard configs), both MLP and Transformer")
    print("achieve only near-random accuracy. The phase transition lies in (21, 181).")


def sweep_window_lengths(seq: List[int], m: int, T: int, 
                         L_values: List[int] = L_IN_SWEEP,
                         epochs: int = 50, n_seeds: int = 3) -> Dict:
    """
    Sweep over multiple window lengths to find precise phase transition.
    
    Returns: {L: {'T_over_L': float, 'mean_acc': float, 'std_acc': float}}
    """
    results = {}
    for L in L_values:
        if len(seq) <= L:
            continue
        X, y = make_windowed_dataset(seq, m, L_in=L)
        if len(X) < 100:  # Need minimum data
            continue
        
        stats = evaluate_mlp_over_seeds(X, y, m, n_seeds=n_seeds, epochs=epochs)
        results[L] = {
            'L_in': L,
            'T_over_L': T / L,
            'mean_acc': stats['mean'],
            'std_acc': stats['std'],
            'learnable': stats['mean'] > 0.5
        }
    
    return results
