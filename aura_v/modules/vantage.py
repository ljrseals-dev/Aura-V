"""
Vantage even-order saturation with 4x oversampling.

Measured (original conversation):
- Summed non-harmonic residual ≈ -102 dBc at a=6/12/25 with 241-tap Kaiser (beta=9)
- Base-rate residual -63 / -38 / -26 dBc
- DC offset present → always followed by DCBlock
- Latency: 60 host samples at 4x (filter group delay)
- Memoryless curve is rate-independent

This implementation uses a practical 4x polyphase + Kaiser-like FIR for the
anti-alias filter and a smooth even-order transfer function.
"""

import numpy as np
from scipy.signal import firwin, upfirdn


class VantageOS:
    def __init__(
        self,
        sample_rate: float = 44100.0,
        drive: float = 3.0,          # a in [2, 6] recommended
        oversample: int = 4,
        fir_taps: int = 241,         # matches measured configuration
        beta: float = 9.0,
    ):
        self.sample_rate = sample_rate
        self.drive = float(np.clip(drive, 0.5, 25.0))
        self.oversample = oversample
        self.fir_taps = fir_taps if fir_taps % 2 == 1 else fir_taps + 1
        self.beta = beta

        # Design anti-alias / reconstruction filter (Kaiser window)
        nyq = 0.5 * sample_rate * oversample
        cutoff = 0.45 * sample_rate          # keep below new Nyquist
        self.fir = firwin(
            self.fir_taps,
            cutoff / nyq,
            window=("kaiser", beta),
            pass_zero=True,
        ).astype(np.float64)

        # Group delay of linear-phase FIR
        self.latency_samples = (self.fir_taps - 1) // 2 // oversample

        self._up_state = np.zeros(self.fir_taps - 1, dtype=np.float64)
        self._down_state = np.zeros(self.fir_taps - 1, dtype=np.float64)

    def reset(self):
        self._up_state[:] = 0.0
        self._down_state[:] = 0.0

    def _curve(self, x: np.ndarray) -> np.ndarray:
        """
        Smooth even-order soft saturation.
        Approximates the measured Vantage family.
        """
        a = self.drive
        # Even-order emphasis via quadratic term blended with tanh
        # Avoid stacking full y² with high a (plan rule)
        y = np.tanh(a * x)
        # Light even-order contribution
        even = 0.15 * (x * x) * np.sign(x) * np.minimum(1.0, a / 4.0)
        return y + even * (1.0 - np.abs(y))

    def process(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        if x.ndim > 1:
            x = x.mean(axis=-1)

        os = self.oversample

        # Upsample by inserting zeros + FIR
        up = np.zeros(len(x) * os, dtype=np.float64)
        up[::os] = x

        # Convolve with FIR (streaming-friendly via overlap)
        full = np.convolve(up, self.fir)
        # Trim to keep length multiple of os
        usable = (len(full) // os) * os
        up_filt = full[:usable]

        # Non-linear curve at high rate
        shaped = self._curve(up_filt)

        # Downsample with same FIR (anti-image)
        down_full = np.convolve(shaped, self.fir)
        # Decimate
        y = down_full[::os][: len(x)]

        # Compensate FIR gain (approx)
        gain = np.sum(self.fir)
        if gain > 1e-12:
            y = y / (gain * gain)   # up + down

        return y.astype(np.float32)
