"""
Simple feed-forward compressor for the Control stage.
"""

import numpy as np


class SimpleCompressor:
    def __init__(
        self,
        sample_rate: float = 44100.0,
        threshold_db: float = -18.0,
        ratio: float = 3.0,
        attack_ms: float = 5.0,
        release_ms: float = 50.0,
        makeup_db: float = 0.0,
    ):
        self.sample_rate = sample_rate
        self.threshold = 10.0 ** (threshold_db / 20.0)
        self.ratio = max(1.0, ratio)
        self.attack = np.exp(-1.0 / (sample_rate * attack_ms * 1e-3))
        self.release = np.exp(-1.0 / (sample_rate * release_ms * 1e-3))
        self.makeup = 10.0 ** (makeup_db / 20.0)
        self._env = 0.0
        self.latency_samples = 0

    def reset(self):
        self._env = 0.0

    def process(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        y = np.empty_like(x)
        env = self._env
        thr = self.threshold
        ratio = self.ratio
        att, rel = self.attack, self.release
        for i, s in enumerate(x):
            level = abs(s)
            if level > env:
                env = att * env + (1.0 - att) * level
            else:
                env = rel * env + (1.0 - rel) * level
            if env > thr:
                # Gain reduction
                over = env / thr
                gr = over ** (1.0 / ratio - 1.0)
            else:
                gr = 1.0
            y[i] = s * gr * self.makeup
        self._env = env
        return y.astype(np.float32)
