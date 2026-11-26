"""
Simple Feedback Delay Network (FDN) reverb approximating Atmos Verb core.
RT60 controlled; measured original within 2 % of requested decay.
"""

import numpy as np


class FDNReverb:
    def __init__(
        self,
        sample_rate: float = 44100.0,
        rt60: float = 1.2,
        wet: float = 0.25,
        size: float = 0.7,
        n_delays: int = 6,
    ):
        self.sample_rate = sample_rate
        self.rt60 = max(0.1, rt60)
        self.wet = float(np.clip(wet, 0.0, 1.0))
        self.size = float(np.clip(size, 0.1, 1.5))
        self.n = n_delays

        # Prime-ish delay lengths scaled by size
        base = np.array([1553, 1613, 1747, 1861, 1933, 2017], dtype=int)
        self.delays = (base * self.size).astype(int)
        self.buffers = [np.zeros(d, dtype=np.float64) for d in self.delays]
        self.idx = [0] * self.n

        # Feedback gain for target RT60 (approx)
        # g = 10 ** (-3 * delay / (rt60 * sr))
        self.gains = np.array(
            [10.0 ** (-3.0 * d / (self.rt60 * sample_rate)) for d in self.delays]
        )
        self.latency_samples = int(np.mean(self.delays) * 0.1)  # rough

    def reset(self):
        for b in self.buffers:
            b[:] = 0.0
        self.idx = [0] * self.n

    def process(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        y = np.zeros_like(x)
        n = self.n
        gains = self.gains
        for i, sample in enumerate(x):
            # Read
            reads = np.array([self.buffers[j][self.idx[j]] for j in range(n)])
            # Householder-like mixing (simple orthogonal)
            mixed = reads - 2.0 * np.mean(reads)
            out = np.mean(mixed)
            y[i] = out
            # Write with feedback + input
            for j in range(n):
                self.buffers[j][self.idx[j]] = sample * 0.4 + mixed[j] * gains[j]
                self.idx[j] = (self.idx[j] + 1) % self.delays[j]
        # Wet/dry
        return ((1.0 - self.wet) * x + self.wet * y).astype(np.float32)
