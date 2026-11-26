"""
Simple Butterworth-style high-pass for Correction stage.
Default 80 Hz (typical vocal high-pass).
"""

import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi


class HighPass:
    def __init__(self, sample_rate: float = 44100.0, cutoff_hz: float = 80.0, order: int = 2):
        self.sample_rate = sample_rate
        self.cutoff_hz = cutoff_hz
        self.order = order
        self.sos = butter(order, cutoff_hz, btype="highpass", fs=sample_rate, output="sos")
        self._zi = sosfilt_zi(self.sos)
        self.latency_samples = 0

    def reset(self):
        self._zi = sosfilt_zi(self.sos)

    def process(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        y, self._zi = sosfilt(self.sos, x, zi=self._zi)
        return y.astype(np.float32)
