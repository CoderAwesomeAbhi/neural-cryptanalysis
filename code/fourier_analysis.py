"""
FOURIER ANALYSIS - Spectral Structure of Sequences
===================================================
Analyzes frequency domain properties to detect periodic structure.

Author: Abhijay Gangarapu
"""
import numpy as np
import matplotlib.pyplot as plt
from generator import PiecewiseAffineGenerator

def compute_spectral_flatness(power_spectrum):
    """
    Compute spectral flatness (Wiener entropy).
    
    SF = geometric_mean / arithmetic_mean
    
    SF = 1: white noise (flat spectrum)
    SF = 0: pure tone (single frequency)
    """
    power_spectrum = power_spectrum[power_spectrum > 0]
    geometric_mean = np.exp(np.mean(np.log(power_spectrum)))
    arithmetic_mean = np.mean(power_spectrum)
    return geometric_mean / arithmetic_mean


def compute_spectral_entropy(power_spectrum):
    """
    Compute spectral entropy.
    
    High entropy: spread across many frequencies
    Low entropy: concentrated in few frequencies
    """
    power_spectrum = power_spectrum / np.sum(power_spectrum)  # Normalize
    power_spectrum = power_spectrum[power_spectrum > 0]
    return -np.sum(power_spectrum * np.log2(power_spectrum))


def analyze_sequence_spectrum(p, k, hensel_satisfied=True, n_samples=8192):
    """Analyze frequency domain properties of sequence."""
    m = p ** k
    gen = PiecewiseAffineGenerator(p, k, hensel_satisfied=hensel_satisfied)
    
    # Generate sequence
    sequence = np.array(gen.generate(n_samples))
    
    # Normalize to [-1, 1]
    sequence_norm = 2 * (sequence / m) - 1
    
    # Compute FFT
    fft = np.fft.fft(sequence_norm)
    power_spectrum = np.abs(fft[:n_samples//2])**2
    freqs = np.fft.fftfreq(n_samples, d=1.0)[:n_samples//2]
    
    # Compute metrics
    spectral_flatness = compute_spectral_flatness(power_spectrum)
    spectral_entropy = compute_spectral_entropy(power_spectrum)
    max_entropy = np.log2(len(power_spectrum))
    
    # Find dominant frequencies
    top_k = 5
    top_indices = np.argsort(power_spectrum)[-top_k:][::-1]
    top_freqs = freqs[top_indices]
    top_powers = power_spectrum[top_indices]
    total_power = np.sum(power_spectrum)
    
    # Autocorrelation
    autocorr = np.correlate(sequence_norm, sequence_norm, mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    autocorr = autocorr / autocorr[0]  # Normalize
    
    return {
        'p': p,
        'k': k,
        'm': m,
        'hensel': 'SAT' if hensel_satisfied else 'VIOL',
        'period': gen.period,
        'spectral_flatness': spectral_flatness,
        'spectral_entropy': spectral_entropy,
        'entropy_ratio': spectral_entropy / max_entropy,
        'top_freqs': top_freqs,
        'top_powers': top_powers / total_power,
        'power_spectrum': power_spectrum,
        'freqs': freqs,
        'autocorr': autocorr[:100]  # First 100 lags
    }


def run_fourier_analysis():
    """Run Fourier analysis on key configurations."""
    configs = [
        (5, 1, True),
        (5, 2, True),
        (5, 3, True),
        (5, 2, False),
    ]
    
    results = []
    
    print("="*60)
    print("FOURIER ANALYSIS - SPECTRAL STRUCTURE")
    print("="*60)
    
    for p, k, hensel_sat in configs:
        config_name = f"p={p}, k={k}, m={p**k}, {'SAT' if hensel_sat else 'VIOL'}"
        print(f"\n{config_name}")
        print("-"*60)
        
        result = analyze_sequence_spectrum(p, k, hensel_sat)
        results.append(result)
        
        print(f"Period: {result['period']}")
        print(f"Spectral flatness: {result['spectral_flatness']:.4f}")
        print(f"Spectral entropy: {result['spectral_entropy']:.2f} / {np.log2(4096):.2f}")
        print(f"Entropy ratio: {result['entropy_ratio']*100:.1f}%")
        print(f"\nTop 5 frequencies:")
        for i, (freq, power) in enumerate(zip(result['top_freqs'], result['top_powers'])):
            print(f"  {i+1}. f={freq:.4f}, power={power*100:.2f}%")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"{'Config':>15s} | {'Flatness':>10s} | {'Entropy':>10s}")
    print("-"*60)
    
    for r in results:
        config = f"{r['hensel']} m={r['m']}"
        flatness = f"{r['spectral_flatness']:.4f}"
        entropy = f"{r['entropy_ratio']*100:.1f}%"
        print(f"{config:>15s} | {flatness:>10s} | {entropy:>10s}")
    
    print("\n" + "="*60)
    print("INTERPRETATION")
    print("="*60)
    print("Low spectral entropy (9-17%) indicates structure is NOT white noise")
    print("Structure is periodic and concentrated in specific frequencies")
    print("This is consistent with high linear complexity and neural unpredictability")
    
    return results


if __name__ == '__main__':
    results = run_fourier_analysis()
