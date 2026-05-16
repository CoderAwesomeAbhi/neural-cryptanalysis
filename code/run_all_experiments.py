"""
GRAND AWARD EXPERIMENTS - Master Runner
Executes all breakthrough experiments for the paper
"""

import subprocess
import sys
from pathlib import Path
import time

def run_experiment(script_name, description):
    """Run an experiment script and report results"""
    print(f"\n{'='*80}")
    print(f"RUNNING: {description}")
    print(f"Script: {script_name}")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"\n✅ SUCCESS: {description}")
            print(f"   Time: {elapsed/60:.1f} minutes")
            print(f"\n{result.stdout}")
        else:
            print(f"\n❌ FAILED: {description}")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"\n❌ EXCEPTION: {description}")
        print(f"   Error: {str(e)}")
        return False
    
    return True

def main():
    """Run all Grand Award experiments"""
    
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║              GRAND AWARD BREAKTHROUGH EXPERIMENTS                         ║
║                                                                           ║
║  These experiments will transform your paper from "excellent" to         ║
║  "Grand Award winner" by addressing the critical PhD-level critiques.    ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    experiments = [
        {
            'script': 'grokking_experiment.py',
            'description': 'Grokking Experiment (100k epochs)',
            'purpose': 'Tests whether networks can eventually learn with massive training',
            'impact': 'Proves whether failure is optimization or information-theoretic'
        },
        {
            'script': 'cot_experiment.py',
            'description': 'Chain-of-Thought State-Space Experiment',
            'purpose': 'Tests whether explicit state supervision bypasses T/L_in barrier',
            'impact': 'Separates computational depth from sample complexity limits'
        }
    ]
    
    print("\nEXPERIMENTS TO RUN:\n")
    for i, exp in enumerate(experiments, 1):
        print(f"{i}. {exp['description']}")
        print(f"   Purpose: {exp['purpose']}")
        print(f"   Impact: {exp['impact']}\n")
    
    input("\nPress Enter to start experiments (this will take several hours)...")
    
    # Run experiments
    results = []
    for exp in experiments:
        success = run_experiment(exp['script'], exp['description'])
        results.append({
            'experiment': exp['description'],
            'success': success
        })
    
    # Summary
    print(f"\n{'='*80}")
    print("EXPERIMENT SUMMARY")
    print(f"{'='*80}\n")
    
    for result in results:
        status = "✅ COMPLETED" if result['success'] else "❌ FAILED"
        print(f"{status}: {result['experiment']}")
    
    all_success = all(r['success'] for r in results)
    
    if all_success:
        print(f"\n{'='*80}")
        print("🎉 ALL EXPERIMENTS COMPLETED SUCCESSFULLY!")
        print(f"{'='*80}")
        print("\nNEXT STEPS:")
        print("1. Check results/ folder for generated plots")
        print("2. Review JSON files for detailed metrics")
        print("3. Add results to paper (see PAPER_UPDATES.md)")
        print("4. Recompile paper with new sections")
        print("\nYour paper is now GRAND AWARD READY! 🏆")
    else:
        print(f"\n{'='*80}")
        print("⚠️  SOME EXPERIMENTS FAILED")
        print(f"{'='*80}")
        print("\nPlease check error messages above and:")
        print("1. Ensure all dependencies are installed (torch, numpy, matplotlib)")
        print("2. Check that sequence_generator.py exists")
        print("3. Verify you have enough disk space for results")
    
    print(f"\n{'='*80}\n")

if __name__ == '__main__':
    main()
