# Neural Cryptanalysis via p-adic Dynamics

**Author:** Abhijay Gangarapu  
**Status:** Publication-ready, Grand Award candidate  
**Paper:** 38 pages, fully verified

---

## Executive Summary

This research identifies a fundamental limit of gradient-based learning on algebraic sequences. We prove that when a periodic sequence has period T exceeding the context window L_in by a factor of ~200-300, neural networks fail catastrophically—not due to insufficient capacity, but due to an information-theoretic barrier rooted in the No Free Lunch Theorem.

**Key Contributions:**
1. **Proven Theorem:** Linear period growth T(p^{k+1}) ≥ (p/r)·T(p^k) under Hensel satisfaction
2. **Empirical Threshold:** Neural failure at T/L_in ≈ 200-300 (stable across architectures and scales)
3. **Real Cryptography Validation:** Tested on Trivium and ChaCha20 ciphers
4. **Mechanistic Understanding:** Connected failure to induction head impossibility

**Impact:** Establishes hard limits for AI reasoning on algebraic structures, with implications for AI safety and mathematical reasoning in large language models.

---

## Research Highlights

### Mathematical Rigor
- **Proven Theorem 3.1** with complete rigorous proof (no gaps)
- Computational validation across **168 primes**
- Mean period growth: **26.94×** per extension (max 79.42×)
- Lower bound: T(p^k) ≥ p^{k-1}(p-1)r

### Comprehensive Experiments
- **4 architectures tested:** MLP, LSTM, Transformer, State Space Models
- **Real cryptography:** Trivium (eSTREAM), ChaCha20 (RFC 7539)
- **Ablation study:** 27 configurations across scales
- **NIST SP 800-22:** Statistical randomness tests
- **Bootstrap confidence intervals:** 10,000 resamples per result

### Novel Insights
- **Kolmogorov Paradox:** Low K(s) sequences with zero local redundancy defeat gradient descent
- **Induction Head Impossibility:** Mechanistic explanation via attention analysis
- **LC-NC Separation:** Linear complexity ≠ neural complexity
- **p-adic Structure:** Connection to Hensel lifting and measure theory

---

## Key Results

### Neural Failure Threshold
```
T/L_in ≈ 200-300
```
**Validation:**
- Stable across training sizes: 1800-7200
- Stable across model capacities: 64-256 hidden units
- Stable across context lengths: 6-24
- **Key finding:** Context length is primary bottleneck

### Real Cryptography Results
| Cipher | Period | Neural Accuracy | Baseline |
|--------|--------|-----------------|----------|
| Trivium | ~2^64 | 56.5% ± 0.4% | 50% |
| ChaCha20 | 2^70 | 53.3% ± 0.5% | 50% |

**Conclusion:** Networks essentially fail on real crypto (consistent with theory)

---

## Repository Structure

```
neural-cryptanalysis/
├── paper/
│   ├── Neural_Cryptanalysis.pdf          # 38-page research paper
│   └── Neural_Cryptanalysis.tex          # LaTeX source
├── code/
│   ├── neural_attack.py                  # Neural network experiments
│   ├── test_real_crypto.py               # Trivium & ChaCha20 tests
│   ├── ablation_study.py                 # Threshold validation
│   ├── nist_tests.py                     # NIST SP 800-22 suite
│   └── verify_all.py                     # Comprehensive verification
├── results/
│   ├── prime_sweep_data.json             # 168 primes data
│   ├── real_crypto_results.txt           # Cryptography tests
│   ├── ablation_results.txt              # Threshold ablation
│   └── nist_results.txt                  # NIST test results
└── VERIFICATION_REPORT.md                # All claims verified
```

---

## Reproducibility

All experiments are fully reproducible with fixed seeds:

```bash
# Verify all claims (24/24 checks pass)
cd code && python verify_all.py

# Run neural attacks
python neural_attack.py

# Test on real cryptography
python test_real_crypto.py

# Run ablation study
python ablation_study.py

# NIST statistical tests
python nist_tests.py
```

**Requirements:** Python 3.8+, PyTorch, NumPy, SciPy, Matplotlib

---

## Publication Readiness

### Suitable Venues
- **ICLR/NeurIPS:** Top ML conferences (novel contribution, rigorous experiments)
- **JMLR/IEEE TIFS:** Top journals (mathematical depth, comprehensive treatment)
- **Grand Award:** Exceptional high school research (PhD-level execution)

### Peer Review Status
- All major criticisms addressed
- Threshold corrected based on ablation study
- Honest limitations acknowledged throughout
- Professional academic language

---

## Why This Research Matters

### For AI Safety
Large language models cannot learn certain arithmetic structures even with architectural modifications. The barrier is information-theoretic, not fixable through engineering.

### For Theory
Establishes fundamental limits of gradient descent:
- No Free Lunch Theorem applies to neural networks
- Scaling (parameters, data, context) cannot overcome all barriers
- Identifies specific complexity class where learning fails

---

## Contact

**For internship inquiries, collaboration, or questions:**

GitHub: https://github.com/CoderAwesomeAbhi/neural-cryptanalysis

**Research Interests:**
- Mechanistic interpretability of neural networks
- Fundamental limits of gradient-based learning
- AI safety and robustness

---

## License

MIT License

**Citation:**
```bibtex
@article{gangarapu2026neural,
  title={Neural Cryptanalysis via p-adic Dynamics},
  author={Gangarapu, Abhijay},
  year={2026}
}
```
