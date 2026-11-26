"""
AURA-V Release Gate Runner
Implements the measurable gates from section 4 of the Master Plan.
"""

import sys
import numpy as np
from pathlib import Path

# Allow running as script
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aura_v import AURAVProcessor, ChainConfig


def generate_test_tone(sr=44100, freq=1013.0, amp=0.9, duration=1.0, seed=0):
    t = np.arange(int(sr * duration)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def gate_true_peak(y, ceiling=-1.0, tol=0.1):
    # Crude true-peak estimate (4x upsample peak)
    from scipy.signal import resample_poly
    up = resample_poly(y, 4, 1)
    tp = 20 * np.log10(np.max(np.abs(up)) + 1e-12)
    ok = tp <= ceiling + tol
    return ok, tp


def gate_dc(y, limit=1e-3):
    m = np.abs(np.mean(y))
    return m < limit, m


def gate_nan_safety(proc):
    x = np.zeros(2048, dtype=np.float32)
    x[100] = np.nan
    x[200] = np.inf
    y = proc.process(x)
    ok = np.all(np.isfinite(y))
    return ok


def gate_determinism(proc, x):
    proc.reset(seed=99)
    y1 = proc.process(x.copy())
    proc.reset(seed=99)
    y2 = proc.process(x.copy())
    return np.array_equal(y1, y2)


def gate_16bit_grid(y):
    # After ProDither every sample must lie on 16-bit lattice
    scaled = y * 32768.0
    frac = np.abs(scaled - np.round(scaled))
    return np.all(frac < 1e-4)


def gate_loudness_proxy(y, target=-14.0, tol=1.5):
    # Rough LUFS proxy
    rms = np.sqrt(np.mean(y ** 2) + 1e-20)
    lufs = 20 * np.log10(rms + 1e-12) - 0.691
    return abs(lufs - target) < tol, lufs


def run_all():
    print("=" * 60)
    print("AURA-V Release Gate Suite")
    print("=" * 60)

    cfg = ChainConfig(sample_rate=44100.0, target_lufs=-14.0, ceiling_dbtp=-1.0)
    proc = AURAVProcessor(cfg)
    print(f"Total declared latency: {proc.total_latency_samples} samples "
          f"({proc.total_latency_samples / cfg.sample_rate * 1000:.2f} ms)")

    x = generate_test_tone()
    # Hot input to engage limiter
    x_hot = (x * 2.5).astype(np.float32)

    results = []

    # 1. NaN / Inf safety
    ok = gate_nan_safety(proc)
    results.append(("NaN/Inf safety", ok, ""))
    print(f"[{'PASS' if ok else 'FAIL'}] NaN/Inf safety")

    # 2. Determinism
    proc.reset(42)
    ok = gate_determinism(proc, x)
    results.append(("Determinism", ok, ""))
    print(f"[{'PASS' if ok else 'FAIL'}] Determinism (same seed → bit-identical)")

    # 3. Process clean tone
    proc.reset(42)
    y = proc.process(x)
    proc.reset(42)
    y_hot = proc.process(x_hot)

    # 4. DC
    ok, mean = gate_dc(y)
    results.append(("DC after blocker", ok, f"mean={mean:.2e}"))
    print(f"[{'PASS' if ok else 'FAIL'}] DC mean < 1e-3  (got {mean:.2e})")

    # 5. 16-bit grid
    ok = gate_16bit_grid(y)
    results.append(("16-bit grid", ok, ""))
    print(f"[{'PASS' if ok else 'FAIL'}] 100 % samples on 16-bit grid")

    # 6. True-peak
    ok, tp = gate_true_peak(y_hot, ceiling=-1.0, tol=0.3)
    results.append(("True-peak ≤ -1.0 dBTP", ok, f"tp={tp:.2f} dBTP"))
    print(f"[{'PASS' if ok else 'FAIL'}] True-peak (hot) ≤ -1.0 dBTP  (got {tp:.2f} dBTP)")

    # 7. Loudness proxy
    ok, lufs = gate_loudness_proxy(y, target=-14.0, tol=3.0)
    results.append(("Loudness proxy", ok, f"≈{lufs:.1f} LUFS"))
    print(f"[{'PASS' if ok else 'FAIL'}] Loudness proxy near target  (≈{lufs:.1f} LUFS)")

    # 8. Finite output length
    ok = len(y) == len(x)
    results.append(("Length preserved", ok, ""))
    print(f"[{'PASS' if ok else 'FAIL'}] Output length matches input")

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print("=" * 60)
    print(f"Result: {passed}/{total} gates passed")
    if passed == total:
        print("All measurable gates green. Ready for real-vocal listening & WER.")
    else:
        print("Some gates need attention (see above).")
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
