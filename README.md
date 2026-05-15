# Neural Cryptanalysis of Piecewise Affine Recurrences

This repository studies period growth and neural predictability for piecewise affine recurrences over residue rings.

## What is in this repo

- `paper/Neural_Cryptanalysis.tex` and `.pdf`: manuscript
- `code/`: reproducibility and analysis scripts
- `results/`: generated figures and data artifacts

## Reproduce the core results

```bash
git clone https://github.com/CoderAwesomeAbhi/neural-cryptanalysis.git
cd neural-cryptanalysis
pip install -r code/requirements.txt
python code/verify_all.py
```

`verify_all.py` reproduces the canonical checks used in the paper (period-growth, linear-complexity, and neural-accuracy tables).

## Scope of claims

- The project provides empirical and mathematical evidence for strong period growth under Hensel-satisfied configurations.
- It reports observed neural-learning behavior as `T / L_in` increases for the tested architectures/settings.
- It does **not** claim a formal cryptographic security proof.

## Optional extended experiments

Scripts in `code/` also include exploratory analyses (prime sweeps, noise robustness, algebraic attacks, attention analysis, positional-encoding variants). These are useful for follow-up work and should be interpreted as experimental evidence unless explicitly proved in the paper.

## Contact

- Author: **Abhijay Gangarapu**
- GitHub: [@CoderAwesomeAbhi](https://github.com/CoderAwesomeAbhi)
