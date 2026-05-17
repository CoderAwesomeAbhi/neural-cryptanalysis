"""
Orchestrator for the PhD-review implementation tasks.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Task:
    name: str
    command: List[str]


def run_task(task: Task, cwd: Path) -> bool:
    print(f"\n{'=' * 88}")
    print(f"RUNNING: {task.name}")
    print(f"COMMAND: {' '.join(task.command)}")
    print(f"{'=' * 88}")
    start = time.time()
    try:
        res = subprocess.run(task.command, cwd=str(cwd))
        ok = res.returncode == 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        ok = False
    elapsed = time.time() - start
    print(f"STATUS: {'PASS' if ok else 'FAIL'} | elapsed={elapsed:.1f}s")
    return ok


def build_tasks(quick: bool) -> List[Task]:
    if quick:
        return [
            Task("Monodromy orbit classification", [sys.executable, "orbit_classification.py", "--primes", "5", "7"]),
            Task("Neural threshold derivation", [sys.executable, "neural_threshold_derivation.py"]),
            Task("Ergodicity diagnostics", [sys.executable, "formal_ergodicity_tests.py", "--pairs", "5:2:sat", "5:2:viol", "--n-steps", "4000", "--n-seeds", "8"]),
            Task("Trivium benchmark", [sys.executable, "trivium_attack.py", "--epochs", "20", "--n-bits", "10000"]),
            Task("Real-cipher generalization", [sys.executable, "real_world_generalization.py", "--epochs", "20", "--n-bits", "12000"]),
            Task("Long-context p-adic attention", [sys.executable, "padic_attention_long_context.py", "--epochs", "10", "--max-context", "64"]),
            Task("Complete-vs-incomplete grokking", [sys.executable, "extended_grokking.py", "--epochs", "200", "--eval-every", "20"]),
        ]

    return [
        Task("Monodromy orbit classification", [sys.executable, "orbit_classification.py", "--primes", "5", "7", "11", "13"]),
        Task("Neural threshold derivation", [sys.executable, "neural_threshold_derivation.py"]),
        Task("Ergodicity diagnostics", [sys.executable, "formal_ergodicity_tests.py", "--pairs", "5:2:sat", "7:2:sat", "5:2:viol", "--n-steps", "10000", "--n-seeds", "20"]),
        Task("Trivium benchmark", [sys.executable, "trivium_attack.py", "--epochs", "50", "--n-bits", "15000"]),
        Task("Real-cipher generalization", [sys.executable, "real_world_generalization.py", "--epochs", "50", "--n-bits", "15000"]),
        Task("Long-context p-adic attention", [sys.executable, "padic_attention_long_context.py", "--epochs", "30", "--max-context", "125"]),
        Task("Complete-vs-incomplete grokking", [sys.executable, "extended_grokking.py", "--epochs", "2000", "--eval-every", "50"]),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PhD-review implementation experiments")
    parser.add_argument("--quick", action="store_true", help="Run reduced-cost configuration")
    args = parser.parse_args()

    code_dir = Path(__file__).resolve().parent
    tasks = build_tasks(quick=args.quick)
    print(f"Running {len(tasks)} tasks ({'quick' if args.quick else 'full'} mode)")

    passed = 0
    for t in tasks:
        if run_task(t, code_dir):
            passed += 1

    print(f"\n{'=' * 88}")
    print(f"SUMMARY: {passed}/{len(tasks)} passed")
    print(f"{'=' * 88}")
    if passed != len(tasks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
