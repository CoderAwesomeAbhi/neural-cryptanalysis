# Comprehensive List of Empirical Claims to Verify

## Abstract Claims
1. "mean period growth of 27× per extension (maximum 79×)" - Need to verify against prime_sweep_data.json
2. "sharp phase transition at T/L_in ≈ 21" - Need to verify threshold location
3. "all collapse to near-random performance (≤ 16%)" - Need to verify max accuracy above threshold
4. "168 primes" - Count primes in prime_sweep_data.json

## Table 1: Hensel Index Verification (Table in paper)
- p=5: det(A0-I) mod 5 = 2, δ(A0) = 0
- p=7: det(A0-I) mod 7 = 4, δ(A0) = 0
- p=11: det(A0-I) mod 11 = 8, δ(A0) = 0
- p=13: det(A0-I) mod 13 = 10, δ(A0) = 0
- All violated: det(A0^viol-I) mod p = 0, δ ≥ 1

## Table 2: Period Growth (Main Results Table)
### p=5:
- k=1: T_sat=25, T_viol=3, ratio=8.3
- k=2: T_sat=212, T_viol=30, growth_sat=8.48, growth_viol=10.00, ratio=7.1
- k=3: T_sat=7295, T_viol=469, growth_sat=34.41, growth_viol=15.63, ratio=15.6

### p=7:
- k=1: T_sat=29, T_viol=9, ratio=3.2
- k=2: T_sat=1083, T_viol=46, growth_sat=37.34, growth_viol=5.11, ratio=23.5
- k=3: T_sat=62250, T_viol=522, growth_sat=57.48, growth_viol=11.35, ratio=119.3

### p=11:
- k=1: T_sat=40, T_viol=25, ratio=1.6
- k=2: T_sat=4912, T_viol=282, growth_sat=122.80, growth_viol=11.28, ratio=17.4
- k=3: T_sat=14801, growth_sat=3.01

### p=13:
- k=1: T_sat=74, T_viol=6, ratio=12.3
- k=2: T_sat=20475, T_viol=151, growth_sat=276.69, growth_viol=25.17, ratio=135.6
- k=3: T_sat=1938536, growth_sat=94.68

## Table 3: Linear Complexity
- Linear m=5, r=1: LC=3, H=2.32, H_max=2.32
- PW-2R H-sat m=25: LC=125, H=4.49, H_max=4.64
- PW-2R H-sat m=125: LC=150, H=6.63, H_max=6.91
- PW-2R H-viol m=25: LC=27, H=4.08, H_max=4.64

## Table 4: Neural Attack Accuracy (WITH CONFIDENCE INTERVALS)
- PW-3R composite m=35: 100.0% ± 0.0%, CI [100.0, 100.0]
- Linear r=1, m=5: 100.0% ± 0.0%, CI [100.0, 100.0]
- p=11 H-sat, m=11: 100.0% ± 0.0%, CI [100.0, 100.0]
- H-viol m=25: 100.0% ± 0.0%, CI [100.0, 100.0]
- p=7 H-viol, m=49: 100.0% ± 0.0%, CI [100.0, 100.0]
- p=13 H-sat, m=13: 100.0% ± 0.0%, CI [100.0, 100.0]
- p=5 H-sat, m=25: 100.0% ± 0.0%, CI [100.0, 100.0]
- p=7 H-sat, m=49: 16.3% ± 1.1%, CI [14.8, 17.9]
- p=11 H-sat, m=121: 7.3% ± 0.7%, CI [6.3, 8.4]
- p=5 H-sat, m=125: 2.6% ± 0.3%, CI [2.1, 3.2]
- p=13 H-sat, m=169: 2.2% ± 0.5%, CI [1.5, 3.1]

## Table 5: LSTM/Transformer Comparison
- H-sat m=25 (easy): LSTM=100.0%, Transformer=100.0%, MLP=100.0%
- H-sat m=125 (hard): LSTM=3.1%, Transformer≈1.2%, MLP=2.6%

## Table 6: SSM Results
- Easy (m=25, T=125): SSM=91.2%, Transformer=100.0%, MLP=100.0%
- Hard (m=125, T=7295): SSM=0.4%, Transformer=4.6%, MLP=0.8%

## Table 7: Optimal Bound Verification
- p5k2sat (m=25, T=125): Bound=96.8%, Oracle=96.0%, Neural=100.0%
- p5k3sat (m=125, T=7295): Bound=49.8%, Oracle=49.3%, Neural=1.5%
- p7k2sat (m=49, T=1083): Bound=83.5%, Oracle=82.8%, Neural=33.4%

## Table 8: Lattice Attack Results (WITH CONFIDENCE INTERVALS)
- p=5, k=1, m=5: Success=89.2%, CI [86.1, 92.3]
- p=5, k=2, m=25: Success=12.4%, CI [9.8, 15.1]
- p=5, k=3, m=125: Success=2.1%, CI [1.2, 3.4]
- p=7, k=2, m=49: Success=5.7%, CI [4.1, 7.6]
- p=11, k=2, m=121: Success=3.8%, CI [2.5, 5.3]
- p=13, k=2, m=169: Success=1.9%, CI [0.9, 3.2]

## Table 9: Ergodicity Metrics (WITH SIGNIFICANCE)
### Hensel-satisfied:
- p5k2sat: p(χ²)=0.842, ACF=0.043, coverage=0.94, H/Hmax=0.998
- p7k2sat: p(χ²)=0.721, ACF=0.051, coverage=0.91, H/Hmax=0.996

### Hensel-violated:
- p5k2viol: p(χ²)=0.003, ACF=0.182, coverage=0.42, H/Hmax=0.891, Sig=***
- p7k2viol: p(χ²)=0.011, ACF=0.201, coverage=0.38, H/Hmax=0.873, Sig=***

### Effect sizes:
- Cohen's d for p(χ²): 3.82 (large)
- Cohen's d for ACF: -2.91 (large)
- Cohen's d for coverage: 4.15 (large)
- Cohen's d for entropy: 3.67 (large)

## Table 10: p-adic Positional Encoding
- Standard PE: 1.0% (baseline 0.8%)
- p-adic PE: 1.5% (baseline 0.8%)
- Hybrid PE: 0.7% (baseline 0.8%)

## Figure Claims
1. Figure 4 (Prime Sweep): "Mean growth ratio: 26.94× (max 79.42×)" across 168 primes
2. Figure 5 (Phase Transition): Sharp transition at T/L_in ≈ 21
3. Figure 6 (p-adic Attention): Spearman ρ = -0.255, p = 0.159 (not significant)

## Text Claims
1. "Induction head repetition probability ≈ 0.08%" for T=7295, L_in=6
2. "correlation between attention weights and p-adic distances: Mean Spearman ρ = 0.026"
3. "only 1/32 query positions showing significant correlation (p < 0.05)"
4. "corr(LC, neural_acc) = +0.12" vs "corr(T, neural_acc) = -0.89"
5. "N_train = 3600" used throughout
6. "L_in = 6" used throughout
7. "24/24 verification checks pass" in abstract

## Verification Strategy
1. ✅ Run all code and capture outputs
2. ✅ Compare every number in tables against actual results
3. ✅ Verify all confidence intervals are correctly computed
4. ✅ Verify all statistical significance tests
5. ✅ Check all growth ratios are correctly calculated
6. ✅ Verify prime count (168)
7. ✅ Verify all correlations
8. ✅ Check all random baselines match 1/m
