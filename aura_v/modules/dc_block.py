"""
DC Blocker – mandatory after Vantage (measured DC offset -0.17 at a=2, 0.9 amp).
Simple 1-pole high-pass at ~5 Hz.
"""

import numpy as np


class DCBlock:
    def __init__(self, sample_rate: float = 44100.0, cutoff_hz: float = 5.0):
        self.sample_rate = sample_rate
        self.cutoff_hz = cutoff_hz
        # 1-pole coefficient
        self.R = 1.0 - (2.0 * np.pi * cutoff_hz / sample_rate)
        self._x1 = 0.0
        self._y1 = 0.0
        self.latency_samples = 0

    def reset(self):
        self._x1 = 0.0
        self._y1 = 0.0

    def process(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        y = np.empty_like(x)
        R = self.R
        x1, y1 = self._x1, self._y1
        for i in range(len(x)):
            y[i] = x[i] - x1 + R * y1
            x1 = x[i]
            y1 = y[i]
        self._x1, self._y1 = x1, y1
        return y.astype(np.float32)
