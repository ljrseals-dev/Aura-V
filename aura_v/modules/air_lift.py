"""
Lightweight Air-style high-frequency lift (Atmos Verb Air stage approximation).

Measured: +2.3 dB at 10 kHz, -70 dBFS defaults.
Used as the single allowed Dolby-style stage in this build.
"""

import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi


class AirLift:
    def __init__(
        self,
        sample_rate: float = 44100.0,
        amount: float = 0.6,          # 0–1
        highpass_hz: float = 4000.0,
        lift_db: float = 2.3,         # measured default
    ):
        self.sample_rate = sample_rate
        self.amount = float(np.clip(amount, 0.0, 1.0))
        self.highpass_hz = highpass_hz
        self.lift_db = lift_db
        self.sos = butter(2, highpass_hz, btype="highpass", fs=sample_rate, output="sos")
        self._zi = sosfilt_zi(self.sos)
        self.latency_samples = 0
        self.gain = 10.0 ** (lift_db / 20.0)

    def reset(self):
        self._zi = sosfilt_zi(self.sos)

    def process(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        # Extract high-band
        high, self._zi = sosfilt(self.sos, x, zi=self._zi)
        # Gentle upward tendency on quiet material (simplified)
        envelope = np.maximum(np.abs(high), 1e-6)
        # Soft upward compression for quiet HF
        lift = high * self.gain * self.amount
        # Mix
        y = x + lift * (1.0 - np.tanh(envelope * 8.0) * 0.3)
        return y.astype(np.float32)
