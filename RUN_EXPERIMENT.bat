@echo off
echo ============================================
echo RUNNING CRITICAL p-adic PE EXPERIMENT
echo ============================================
echo.
echo This will take 45-60 minutes (or 25-30 with epochs=50)
echo.
echo Starting experiment...
echo.

cd C:\Users\abhij\Downloads\neural-cryptanalysis\code
python padic_positional_encoding.py

echo.
echo ============================================
echo EXPERIMENT COMPLETE!
echo ============================================
echo.
echo Check the output above for accuracy numbers.
echo Figure saved to: results\padic_encoding_comparison.png
echo.
pause
