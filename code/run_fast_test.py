"""
FAST TEST VERSION - Run experiments quickly to verify they work
Then run full version overnight
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║              FAST TEST VERSION (10k epochs)                               ║
║                                                                           ║
║  This will complete in ~1 hour to verify everything works.               ║
║  Then run the full 100k version overnight.                               ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    print("RUNNING FAST GROKKING TEST (10,000 epochs instead of 100,000)")
    print("Expected time: ~30-45 minutes")
    print("="*80)
    
    # Run grokking with 10k epochs
    result = subprocess.run(
        [sys.executable, "grokking_experiment.py", "--max-epochs", "10000", "--log-every", "500"],
        cwd=Path(__file__).parent,
        capture_output=False,
        text=True
    )
    
    if result.returncode == 0:
        print("\n[SUCCESS] Fast test completed!")
        print("\nNEXT STEPS:")
        print("1. Check results/ folder for plots")
        print("2. If everything looks good, run full version:")
        print("   python run_all_experiments.py")
        print("3. Let it run overnight (6-8 hours)")
    else:
        print("\n[FAILED] Test failed - check errors above")

if __name__ == '__main__':
    main()
