import re
import os

paper_path = "c:/Users/abhij/Downloads/neural-cryptanalysis/paper/Neural_Cryptanalysis.tex"

with open(paper_path, "r", encoding="utf-8") as f:
    tex = f.read()

tex = re.sub(
    r'\\title\{Neural Cryptanalysis of \$p\$-Adic Piecewise Maps: Period Growth Theorems, Architecture-Independent Failure Boundaries\}',
    r'\\title{Neural Predictability of $p$-Adic Piecewise Maps: Empirical Failure Boundaries and Conditional Period Growth}',
    tex
)

tex = tex.replace("computational proofs", "strong computational evidence")

# Also, the user complained about "Abstract still has an oversell problem":
# "fails catastrophically regardless of architecture" -> "is bounded by information-theoretic limits"
tex = tex.replace(
    r"fails catastrophically regardless of architecture",
    r"is strictly bounded by information-theoretic constraints regardless of architecture"
)

# And "No Free Lunch":
tex = tex.replace(
    r"No amount of architectural engineering can overcome this limit.",
    r"Architectural engineering cannot overcome the strict information-theoretic coverage limit."
)

with open(paper_path, "w", encoding="utf-8") as f:
    f.write(tex)

print("Title and abstract fixes applied.")
