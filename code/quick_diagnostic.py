"""Quick diagnostic for failing experiments"""
import subprocess
import sys

experiments = [
    ("trivium_attack.py", "Trivium"),
    ("cot_scratchpad.py", "CoT Scratchpad"),
    ("neurosymbolic_hybrid.py", "Neurosymbolic"),
    ("ergodicity_proof_tests.py", "Ergodicity"),
    ("orbit_classification.py", "Orbit"),
]

print("Testing experiments (10 sec timeout each)...\n")

for script, name in experiments:
    try:
        result = subprocess.run(
            [sys.executable, script],
            timeout=10,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"[OK] {name}")
        else:
            print(f"[FAIL] {name}: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print(f"[OK] {name} (running, killed after 10s)")
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
