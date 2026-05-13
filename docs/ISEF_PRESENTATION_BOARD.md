# ISEF PRESENTATION BOARD DESIGN
## 12-Slide Visual Layout for Heavy Theoretical Work

**Category:** Mathematics  
**Title:** Period Growth and Neural Predictability in Piecewise Affine Systems

---

## 📐 **BOARD LAYOUT (48" × 36")**

```
┌─────────────────────────────────────────────────────────────┐
│                         TITLE PANEL                          │
│  Period Growth & Neural Predictability in Piecewise Affine  │
│              Systems over Residue Rings                      │
│                  Abhijay Gangarapu                          │
│              UT Austin · ISEF 2026                          │
└─────────────────────────────────────────────────────────────┘

┌──────────────┬──────────────┬──────────────┬──────────────┐
│   SLIDE 1    │   SLIDE 2    │   SLIDE 3    │   SLIDE 4    │
│   Problem    │  Hensel      │  Main        │  Theorem 1   │
│              │  Index       │  Results     │  Proof       │
└──────────────┴──────────────┴──────────────┴──────────────┘

┌──────────────┬──────────────┬──────────────┬──────────────┐
│   SLIDE 5    │   SLIDE 6    │   SLIDE 7    │   SLIDE 8    │
│   Period     │  Neural      │  All 3       │  p-adic      │
│   Table      │  Threshold   │  Fail        │  Test        │
└──────────────┴──────────────┴──────────────┴──────────────┘

┌──────────────┬──────────────┬──────────────┬──────────────┐
│   SLIDE 9    │   SLIDE 10   │   SLIDE 11   │   SLIDE 12   │
│   Attack     │  Code        │  Impact      │  Future      │
│   Analysis   │  Demo        │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 🎨 **SLIDE-BY-SLIDE CONTENT**

### **SLIDE 1: The Problem** 🎯
**Visual:** Simple diagram of sequence prediction

```
Given: 1, 4, 2, 3, 1, 4, 2, 3, ...
Predict: ?

Linear sequences → EASY (Berlekamp-Massey cracks them)
Piecewise affine → HARD (but why?)
```

**Key Question (Large Font):**
> "What makes a sequence hard to predict?"

**One Sentence:**
"We prove that the Hensel index δ(A) controls both period growth and neural predictability."

---

### **SLIDE 2: The Hensel Index** 🔑
**Visual:** Color-coded formula

```
δ(A) = νₚ(det(A - I))
       ↑    ↑
    p-adic  determinant
   valuation
```

**Two Cases (Side-by-Side):**

| δ = 0 (Satisfied) | δ ≥ 1 (Violated) |
|-------------------|------------------|
| ✅ Fast growth | ❌ Slow growth |
| ✅ Long periods | ❌ Short periods |
| ✅ Neural hard | ❌ Neural easy |

**Example:**
```
A₀ = [1 1]  →  det(A₀-I) = 2 mod 5  →  δ = 0 ✅
     [3 1]
```

---

### **SLIDE 3: Main Results** 🏆
**Visual:** Trophy icons + checkmarks

**✅ THEOREM 1 (PROVEN):**
```
T(p^(k+1)) > p · T(p^k)
```
"Periods grow FASTER than linear"

**✅ THEOREM 2 (PROVEN):**
```
T(p^k) ≥ p^(k-1)(p-1)·r
```
"Explicit lower bound"

**✅ OBSERVATION 3 (TESTED):**
```
T_critical ≈ N_train / 25
```
"Neural threshold discovered"

**✅ OBSERVATION 4 (TESTED):**
```
p-adic attention: NOT SUPPORTED
```
"Negative result (good science!)"

---

### **SLIDE 4: Theorem 1 Proof (Visual)** 📊
**Visual:** Flowchart with 3 boxes

```
┌─────────────────────┐
│ Fixed Point         │
│ Multiplication      │
│ Factor: p           │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│ Boundary Orbit      │
│ Splitting           │
│ Factor: (p-1)/2     │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│ RESULT:             │
│ T(p^(k+1)) > p·T(p^k)│
└─────────────────────┘
```

**Key Insight (Large):**
"Regime boundaries create NEW orbits at each level"

---

### **SLIDE 5: Period Table** 📈
**Visual:** Bar chart + table

```
        Hensel-Satisfied vs Violated
        
20,000 |                    ▓▓▓
       |                    ▓▓▓
15,000 |                    ▓▓▓
       |                    ▓▓▓
10,000 |          ▓▓▓       ▓▓▓
       |          ▓▓▓       ▓▓▓
 5,000 |    ▓▓▓   ▓▓▓       ▓▓▓
       |    ▓▓▓   ▓▓▓       ▓▓▓
     0 |────────────────────────
        p=5  p=7  p=11  p=13
        
        ▓ Satisfied  ░ Violated
```

**Key Numbers:**
- p=5, k=2: 212 vs 30 (7.1×)
- p=13, k=2: 20,475 vs 151 (135.6×)

---

### **SLIDE 6: Neural Threshold** 🧠
**Visual:** Phase transition graph

```
Accuracy
100% |●●●●●●●
     |        ╲
 50% |         ╲
     |          ╲___________
  0% |                    ●●●
     └─────────────────────────
      1   10  100  1000
         T/L_in (log scale)
         
     EASY │ TRANSITION │ HARD
     ←21→ │  ←─160─→  │ →181
```

**Discovery:**
"T/L_in ≈ 21-181 separates learnable from hard"

---

### **SLIDE 7: All 3 Architectures Fail** 🤖
**Visual:** Three model icons with results

```
┌─────────┐  ┌─────────┐  ┌─────────┐
│   MLP   │  │  LSTM   │  │Transform│
│ (256,   │  │ (128,   │  │  (2L,   │
│  128)   │  │  2L)    │  │  4H)    │
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     ↓            ↓            ↓
  Easy: 100%   100%         100%
  Hard:  2.6%   3.1%         1.2%
  
  Random: 0.8%
```

**Conclusion (Bold):**
"Architecture-independent failure"

---

### **SLIDE 8: p-adic Attention Test** 🔬
**Visual:** Attention heatmap comparison

```
Hypothesis: Attention ∝ p^(-νₚ(n-j))

Test: L_in = 32, m = 125

Result:
┌─────────────────────┐
│ Mean correlation:   │
│   ρ = -0.004        │
│                     │
│ Significant: 0/32   │
│                     │
│ ❌ NOT SUPPORTED    │
└─────────────────────┘
```

**Interpretation:**
"Transformers don't learn p-adic structure"

---

### **SLIDE 9: Attack Resistance** 🛡️
**Visual:** Traffic light system

```
Attack Vector         m=125  m=169
─────────────────────────────────
Polynomial System      🟡     🟢
CRT Decomposition      🟢     🟢
Lattice (LLL)          🟡     🟢
─────────────────────────────────
Overall                🟡     🟢

🟢 HIGH  🟡 MEDIUM  🔴 LOW
```

**Recommendation:**
"Use prime power moduli with m ≥ 100"

---

### **SLIDE 10: Code Demo** 💻
**Visual:** QR code + terminal screenshot

```
┌─────────────────────────────┐
│  [QR CODE]                  │
│                             │
│  github.com/                │
│  CoderAwesomeAbhi/          │
│  neural-cryptanalysis       │
└─────────────────────────────┘

$ python verify_all.py

Total checks: 24
Passed:       24
Failed:       0

✓ ALL CHECKS PASSED
```

**Highlight:**
"100% reproducible • All data verified"

---

### **SLIDE 11: Impact** 🌟
**Visual:** Three columns

```
┌──────────┬──────────┬──────────┐
│  MATH    │    CS    │  CRYPTO  │
├──────────┼──────────┼──────────┤
│ Novel    │ Neural   │ Hensel   │
│ use of   │ hardness │ index    │
│ Hensel's │ threshold│ predicts │
│ lemma    │ T/L_in   │ security │
│          │          │          │
│ Rigorous │ Negative │ Attack   │
│ proofs   │ result   │ analysis │
│          │ (p-adic) │          │
└──────────┴──────────┴──────────┘
```

**One Sentence:**
"First work to connect p-adic number theory with neural sequence prediction"

---

### **SLIDE 12: Future Directions** 🚀
**Visual:** Roadmap

```
✅ COMPLETED:
  • Complete proofs
  • Cross-prime validation
  • 3 architectures tested
  • p-adic hypothesis tested

🔮 NEXT STEPS:
  • Test state space models (Mamba, S4)
  • Real-world noisy data
  • Spectral analysis
  • Information-theoretic formalization
```

**Honest Statement:**
"Toy problem → Real-world validation needed"

---

## 🎨 **DESIGN PRINCIPLES**

### **Color Scheme:**
- **Primary:** Deep blue (#1a365d) - Math/Theory
- **Secondary:** Green (#22543d) - Proven results
- **Accent:** Orange (#c05621) - Negative results
- **Background:** White/Light gray

### **Typography:**
- **Headers:** 48pt Bold
- **Body:** 24pt Regular
- **Captions:** 18pt Italic
- **Code:** 20pt Monospace

### **Visual Elements:**
- ✅ Checkmarks for proven results
- ❌ X-marks for negative results
- 📊 Charts for data
- 🔬 Icons for experiments
- 💻 Terminal screenshots for code

---

## 📋 **JUDGE INTERACTION SCRIPT**

### **30-Second Pitch:**
"I discovered that a single number—the Hensel index—predicts both how fast periods grow in piecewise affine systems AND whether neural networks can predict them. I proved two theorems with complete rigorous proofs, tested three neural architectures, and found a negative result on p-adic attention. All code is open-source and verified."

### **Key Talking Points:**
1. "The Hensel index δ(A) = νₚ(det(A-I)) is the key parameter"
2. "I proved super-linear growth with a complete 5-step proof"
3. "All three architectures—MLP, LSTM, Transformer—fail identically"
4. "I tested the p-adic hypothesis and found it's NOT supported (negative result)"
5. "All 24 verification checks pass—100% reproducible"

### **Handling Questions:**
- **"Is this real-world?"** → "No, it's a toy problem. I'm honest about that in the paper. Real-world validation is future work."
- **"Why negative result?"** → "That's good science! I hypothesized, tested, and found it false. That's valuable."
- **"Can I run your code?"** → "Yes! Here's the QR code. Run `python verify_all.py` and all 24 checks pass."

---

## ✅ **FINAL CHECKLIST**

### Board:
- [ ] Print all 12 slides (11×17 each)
- [ ] Mount on foam board
- [ ] Add title panel
- [ ] QR code to GitHub repo
- [ ] Laminate for durability

### Materials:
- [ ] Printed paper (copy)
- [ ] Laptop with code demo
- [ ] Business cards with GitHub link
- [ ] 1-page summary handout

### Practice:
- [ ] 30-second pitch (memorize)
- [ ] 5-minute deep dive (prepare)
- [ ] Q&A responses (rehearse)

---

**This board translates heavy theory into scannable visuals while maintaining scientific rigor.**

**Ready for ISEF judging.**
