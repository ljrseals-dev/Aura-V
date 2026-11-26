"""
AURA-V end-to-end vocal processor.
Implements the exact order from the Master Integration Plan section 2.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from .modules import (
    DCBlock,
    HighPass,
    VantageOS,
    AirLift,
    FDNReverb,
    JowiphonP,
    TruePeakLimiter,
    ProDither,
    SimpleCompressor,
)


@dataclass
class ChainConfig:
    sample_rate: float = 44100.0
    # Character
    vantage_drive: float = 3.0
    # Dolby-style (exactly one allowed)
    air_amount: float = 0.55
    # Space
    reverb_rt60: float = 1.1
    reverb_wet: float = 0.22
    # Glue
    target_lufs: float = -14.0
    ceiling_dbtp: float = -1.0
    # Noise
    enable_thermal: bool = True
    dither_seed: int = 42
    # Control
    comp_threshold_db: float = -16.0
    comp_ratio: float = 2.5
    # Correction
    hp_cutoff_hz: float = 70.0


class AURAVProcessor:
    """
    Full chain:
    Source → Correction (DC + HP) → Control (Comp) → Character (Vantage + DC)
    → Dolby-style (Air) → Space (FDN) → Glue (Jowiphon-P + Limiter)
    → Motion (pass-through placeholder) → Noise (ProDither last)
    """

    def __init__(self, config: Optional[ChainConfig] = None):
        self.cfg = config or ChainConfig()
        sr = self.cfg.sample_rate

        # Correction
        self.dc1 = DCBlock(sr)
        self.hp = HighPass(sr, cutoff_hz=self.cfg.hp_cutoff_hz)

        # Control
        self.comp = SimpleCompressor(
            sr,
            threshold_db=self.cfg.comp_threshold_db,
            ratio=self.cfg.comp_ratio,
        )

        # Character
        self.vantage = VantageOS(sr, drive=self.cfg.vantage_drive)
        self.dc2 = DCBlock(sr)  # mandatory after Vantage

        # Dolby-style (Air only – stack guard)
        self.air = AirLift(sr, amount=self.cfg.air_amount)

        # Space
        self.reverb = FDNReverb(
            sr, rt60=self.cfg.reverb_rt60, wet=self.cfg.reverb_wet
        )

        # Glue
        self.loudness = JowiphonP(
            sr,
            target_lufs=self.cfg.target_lufs,
            enable_thermal=self.cfg.enable_thermal,
            seed=self.cfg.dither_seed,
        )
        self.limiter = TruePeakLimiter(sr, ceiling_dbtp=self.cfg.ceiling_dbtp)

        # Noise (must be last)
        self.dither = ProDither(sr, seed=self.cfg.dither_seed)

        self._stages = [
            ("dc_block_1", self.dc1),
            ("highpass", self.hp),
            ("compressor", self.comp),
            ("vantage", self.vantage),
            ("dc_block_2", self.dc2),
            ("air_lift", self.air),
            ("fdn_reverb", self.reverb),
            ("jowiphon_p", self.loudness),
            ("true_peak_limiter", self.limiter),
            ("prodither", self.dither),
        ]

    def reset(self, seed: Optional[int] = None):
        for _, stage in self._stages:
            if hasattr(stage, "reset"):
                if "seed" in stage.reset.__code__.co_varnames:
                    stage.reset(seed)
                else:
                    stage.reset()

    @property
    def total_latency_samples(self) -> int:
        return sum(getattr(s, "latency_samples", 0) for _, s in self._stages)

    def process(self, x: np.ndarray) -> np.ndarray:
        """
        Process mono float32/float64 audio in [-1, 1].
        Returns float32, 16-bit grid after final dither.
        """
        y = np.asarray(x, dtype=np.float32)
        if y.ndim > 1:
            y = y.mean(axis=-1).astype(np.float32)

        for name, stage in self._stages:
            y = stage.process(y)
            # NaN/Inf safety gate
            if not np.all(np.isfinite(y)):
                y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)

        return y

    def process_stereo(self, left: np.ndarray, right: np.ndarray):
        """Convenience stereo path (independent channels)."""
        return self.process(left), self.process(right)
