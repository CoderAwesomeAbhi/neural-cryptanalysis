@echo off
echo ============================================
echo RUNNING ALL THREE CRITICAL EXPERIMENTS
echo ============================================
echo.
echo This will take 2-3 hours total:
echo   1. Spectral Gap Analysis (30 min)
echo   2. Fourier Analysis (15 min)
echo   3. SSM Comparison (90 min)
echo.
echo These experiments will make your paper bulletproof.
echo.
pause
echo.

cd C:\Users\abhij\Downloads\neural-cryptanalysis\code

echo ============================================
echo [1/3] SPECTRAL GAP ANALYSIS
echo ============================================
python spectral_gap_analysis.py
echo.

echo ============================================
echo [2/3] FOURIER ANALYSIS
echo ============================================
python fourier_analysis.py
echo.

echo ============================================
echo [3/3] SSM COMPARISON
echo ============================================
python ssm_comparison.py
echo.

echo ============================================
echo ALL EXPERIMENTS COMPLETE!
echo ============================================
echo.
echo Check the output above for results.
echo Now update the paper with these findings.
echo.
pause
