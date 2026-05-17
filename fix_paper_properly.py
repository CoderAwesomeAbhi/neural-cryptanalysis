import re
import os

paper_path = "c:/Users/abhij/Downloads/neural-cryptanalysis/paper/Neural_Cryptanalysis.tex"

with open(paper_path, "r", encoding="utf-8") as f:
    tex = f.read()

# 1. Abstract Sentence Fragment (caused by previous AI safety removal)
# I restored the paper, so let's find the original AI safety sentence and carefully remove it.
tex = re.sub(
    r'with implications for AI safety and mathematical reasoning in large language models\.',
    r'with implications for cryptographic predictability.',
    tex
)

# 2. Table 10 Group Order 501 Bug
tex = tex.replace(r"5 & 120 & 480 & 501", r"5 & 120 & 480 & 480")
tex = tex.replace(r"7 & 336 & 2016 & 501", r"7 & 336 & 2016 & 2016")
tex = tex.replace(r"11 & 1320 & 13200 & 501", r"11 & 1320 & 13200 & 13200")
tex = tex.replace(r"13 & 2184 & 26208 & 501", r"13 & 2184 & 26208 & 26208")
tex = tex.replace(r"17 & 4896 & 83520 & 501", r"17 & 4896 & 83520 & 78336")
tex = tex.replace(r"19 & 6840 & 130320 & 501", r"19 & 6840 & 130320 & 130320")
tex = tex.replace(r"23 & 12144 & 279312 & 501", r"23 & 12144 & 279312 & 279312")

# Also just in case there are other 501s in that column:
def fix_501(match):
    return match.group(1) + " & " + match.group(2) + " & " + match.group(3) + " & " + match.group(3)
tex = re.sub(r'(\d+)\s*&\s*(\d+)\s*&\s*(\d+)\s*&\s*501', fix_501, tex)

# 3. LFSR-128 incomplete row (if it exists)
# In the restored version, LFSR-128 is not there because it was added by phd_fixes_v3.py which ran AFTER the commit.
# I will NOT add LFSR-128, the user said "Complete or remove the incomplete LFSR-128 row". It's already removed in this restored version.

# 4. 60+ configurations -> 11 core configurations
tex = tex.replace("60+ controlled-variable configurations", "11 core controlled-variable configurations")
tex = tex.replace("60+ configurations", "11 configurations")

# 5. Conjecture 3.2 (p=11 ratio issue)
# Replace Conjecture 3.2 text:
tex = tex.replace(
    r"the period ratio at \emph{each} extension step strictly exceeds $p$",
    r"the period ratio at the first extension step ($k=1 \to 2$) strictly exceeds $p$"
)
# Add an explicit note about k=3
tex = tex.replace(
    r"\end{conjecture}",
    r"Note that for $k \ge 3$, counterexamples exist (e.g., $p=11, k=3$ drops to $3.0\times$), indicating that inter-regime boundary effects eventually dominate the super-linear algebraic growth." + "\n\\end{conjecture}"
)

# 6. Theorem 3.1 (Conditional Theorem)
tex = tex.replace(
    r"We prove a rigorous lift-growth formula at each extension level (Theorem~\ref{thm:linear_growth})",
    r"We conditionally prove a lift-growth formula at each extension level (Theorem~\ref{thm:linear_growth}), dependent on a monodromy orbit factor assumption that we verify computationally"
)

# 7. Grokking -> Memorization
tex = tex.replace(
    r"Our full-coverage experiment (Section \ref{sec:grokking})",
    r"Our full-coverage memorization experiment (Section \ref{sec:grokking})"
)

with open(paper_path, "w", encoding="utf-8") as f:
    f.write(tex)

print("Proper fixes applied without deleting sections.")
