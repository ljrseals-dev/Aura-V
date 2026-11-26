"""
AURA-V Vocal Processing Chain
Eval-driven, release-gated implementation of the Master Integration Plan.
"""

__version__ = "0.1.0"
__author__ = "Lewis Seals / AURA-V"

from .processor import AURAVProcessor, ChainConfig

__all__ = ["AURAVProcessor", "ChainConfig", "__version__"]
