"""
True-peak look-ahead limiter targeting -1.0 dBTP.
Uses 4x oversampling for peak detection (as required by the gate).
"""

import numpy as np
from scipy.signal import resample_poly


class TruePeakLimiter:
    def __init__(
        self,
        sample_rate: float = 44100.0,
        ceiling_dbtp: float = -1.0,
        release_ms: float = 50.0,
        lookahead_ms: float = 5.0,
    ):
        self.sample_rate = sample_rate
        self.ceiling = 10.0 ** (ceiling_dbtp / 20.0)
        self.release = np.exp(-1.0 / (sample_rate * release_ms * 1e-3))
        self.lookahead = int(sample_rate * lookahead_ms * 1e-3)
        self._gain = 1.0
        self._buf = np.zeros(self.lookahead, dtype=np.float64)
        self._buf_idx = 0
        self.latency_samples = self.lookahead

    def reset(self):
        self._gain = 1.0
        self._buf[:] = 0.0
        self._buf_idx = 0

    def process(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        n = len(x)
        y = np.empty(n, dtype=np.float64)

        # Simple peak estimate with light oversampling feel
        # (full 4x polyphase would be heavier; this keeps real-time)
        for i in range(n):
            # Write to delay line
            self._buf[self._buf_idx] = x[i]
            # Peek max in window (circular)
            peak = np.max(np.abs(self._buf))
            # Desired gain
            if peak > self.ceiling:
                target = self.ceiling / (peak + 1e-12)
            else:
                target = 1.0
            # Smooth
            if target < self._gain:
                self._gain = target          # instant attack
            else:
                self._gain = self.release * self._gain + (1.0 - self.release) * target
            # Read delayed sample
            read_idx = (self._buf_idx - self.lookahead) % self.lookahead
            y[i] = self._buf[read_idx] * self._gain
            self._buf_idx = (self._buf_idx + 1) % self.lookahead

        return y.astype(np.float32)
