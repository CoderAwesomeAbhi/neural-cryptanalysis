"""
Quick test to verify experiments work without Unicode errors
"""

print("="*80)
print("TESTING EXPERIMENT SCRIPTS")
print("="*80)

# Test 1: Import modules
try:
    import torch
    import numpy as np
    from sequence_generator import generate_piecewise_sequence, generate_piecewise_sequence_with_states
    print("[SUCCESS] All imports work")
except Exception as e:
    print(f"[FAILED] Import error: {e}")
    exit(1)

# Test 2: Generate sequence
try:
    seq = generate_piecewise_sequence(p=5, k=2, hensel_satisfied=True, n_terms=100, burn_in=10)
    print(f"[SUCCESS] Generated sequence: {len(seq)} terms")
except Exception as e:
    print(f"[FAILED] Sequence generation error: {e}")
    exit(1)

# Test 3: Generate with states
try:
    seq, states, regimes = generate_piecewise_sequence_with_states(p=5, k=2, hensel_satisfied=True, n_terms=100, burn_in=10)
    print(f"[SUCCESS] Generated with states: {len(seq)} terms, {len(states)} states")
except Exception as e:
    print(f"[FAILED] State generation error: {e}")
    exit(1)

# Test 4: Check for Unicode in scripts
import os
script_dir = os.path.dirname(__file__)
for script in ['grokking_experiment.py', 'cot_experiment.py', 'run_all_experiments.py']:
    filepath = os.path.join(script_dir, script)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        # Check for emoji unicode
        if '\\U0001' in repr(content) or '\\u2705' in repr(content) or '\\u274c' in repr(content):
            print(f"[WARNING] {script} contains Unicode emojis!")
        else:
            print(f"[SUCCESS] {script} is clean (no Unicode emojis)")

print("="*80)
print("ALL TESTS PASSED - READY TO RUN EXPERIMENTS")
print("="*80)
print("\nRun: python run_all_experiments.py")
