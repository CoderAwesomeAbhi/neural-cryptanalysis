# Neural Cryptanalysis Experiments

This directory contains all computational experiments supporting the paper's theoretical claims.

## Core Module

- **`core.py`**: Shared configuration, sequence generator, and period computation used by all experiments

## Experiments

1. **`optimal_bound.py`**: Theorem 11.1 verification - Optimal Prediction Bound
   - Proves neural networks fail below information-theoretic optimum
   - Compares oracle (lookup table) vs neural accuracy

2. **`ergodicity.py`**: Conjecture 9.3 computational support - Ergodicity Analysis
   - Tests equidistribution, autocorrelation decay, n-gram coverage, entropy
   - Shows Hensel-satisfied configs behave ergodically

3. **`separation.py`**: Theorem 12.1 - LC-NC Separation
   - Proves Linear Complexity and Neural Complexity are independent measures
   - Constructs sequences with high LC + low NC and vice versa

4. **`ssm_experiment.py`**: Architecture-independence verification
   - Compares SSM (State Space Models) vs Transformers
   - Shows failure is information-theoretic, not architectural

5. **`verify_theorems.py`**: Master verification script
   - Checks all major theorem claims computationally
   - Outputs PASS/FAIL table for reproducibility

## Running the Experiments

```bash
# Install dependencies
pip install numpy scipy scikit-learn torch

# Run individual experiments
python code/optimal_bound.py
python code/ergodicity.py
python code/separation.py
python code/ssm_experiment.py

# Verify all theorems at once
python code/verify_theorems.py
```

## Dependencies

- numpy
- scipy
- scikit-learn
- torch (for SSM experiment only)

## Configuration

All experiments use the same configurations defined in `core.py`:
- p5k1sat, p5k2sat, p5k3sat (Hensel-satisfied)
- p5k2viol, p7k2viol (Hensel-violated)
- p7k1sat, p7k2sat, p7k3sat (larger primes)

Each config specifies (p, k, m=p^k, sat/viol) for reproducibility.
