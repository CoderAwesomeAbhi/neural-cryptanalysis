# -*- coding: utf-8 -*-
"""
Comprehensive test suite for all experiments.
Verifies that all code matches paper claims.
"""

import subprocess
import sys

def run_test(script_name, description):
    """Run a test script and report results."""
    print(f"\n{'='*72}")
    print(f"Testing: {description}")
    print(f"Script: {script_name}")
    print('='*72)
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("[OK] Test passed")
            # Print last 20 lines of output
            lines = result.stdout.split('\n')
            for line in lines[-20:]:
                if line.strip():
                    print(f"  {line}")
            return True
        else:
            print(f"[FAIL] Test failed with exit code {result.returncode}")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("[FAIL] Test timed out")
        return False
    except Exception as e:
        print(f"[FAIL] Error running test: {e}")
        return False

def main():
    print("="*72)
    print("COMPREHENSIVE TEST SUITE")
    print("Verifying all experiments match paper claims")
    print("="*72)
    
    tests = [
        ("optimal_bound.py", "Theorem 11.1 - Optimal Prediction Bound"),
        ("separation.py", "Theorem 12.1 - LC-NC Separation"),
        ("ergodicity.py", "Conjecture 9.3 - Ergodicity Verification"),
        ("ssm_proper.py", "Section 6.3 - SSM Architecture Independence"),
    ]
    
    results = []
    for script, desc in tests:
        passed = run_test(script, desc)
        results.append((desc, passed))
    
    print("\n" + "="*72)
    print("TEST SUMMARY")
    print("="*72)
    
    for desc, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {desc}")
    
    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed_count}/{total} tests passed")
    
    if passed_count == total:
        print("\n[CHECK] ALL TESTS PASSED - Repository is PhD-level ready!")
        return 0
    else:
        print("\n[X] SOME TESTS FAILED - Review output above")
        return 1

if __name__ == '__main__':
    sys.exit(main())
