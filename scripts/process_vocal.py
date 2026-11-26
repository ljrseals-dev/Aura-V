#!/usr/bin/env python3
"""
Process a dry vocal through the AURA-V chain.
Usage: python scripts/process_vocal.py input.wav output.wav
"""

import argparse
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aura_v import AURAVProcessor, ChainConfig


def read_wav(path):
    try:
        import soundfile as sf
        data, sr = sf.read(path, always_2d=False)
        return data.astype(np.float32), sr
    except ImportError:
        from scipy.io import wavfile
        sr, data = wavfile.read(path)
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data = data.astype(np.float32) / 2147483648.0
        else:
            data = data.astype(np.float32)
        return data, sr


def write_wav(path, data, sr):
    try:
        import soundfile as sf
        sf.write(path, data, sr, subtype="PCM_16")
    except ImportError:
        from scipy.io import wavfile
        pcm = np.clip(data * 32767.0, -32768, 32767).astype(np.int16)
        wavfile.write(path, sr, pcm)


def main():
    parser = argparse.ArgumentParser(description="AURA-V vocal processor")
    parser.add_argument("input", help="Input WAV (dry vocal)")
    parser.add_argument("output", help="Output WAV (processed, 16-bit)")
    parser.add_argument("--drive", type=float, default=3.0, help="Vantage drive (2–6)")
    parser.add_argument("--lufs", type=float, default=-14.0, help="Target LUFS")
    parser.add_argument("--ceiling", type=float, default=-1.0, help="True-peak ceiling dBTP")
    parser.add_argument("--rt60", type=float, default=1.1, help="Reverb RT60 seconds")
    parser.add_argument("--wet", type=float, default=0.22, help="Reverb wet mix")
    args = parser.parse_args()

    print(f"Loading {args.input} …")
    audio, sr = read_wav(args.input)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    cfg = ChainConfig(
        sample_rate=float(sr),
        vantage_drive=args.drive,
        target_lufs=args.lufs,
        ceiling_dbtp=args.ceiling,
        reverb_rt60=args.rt60,
        reverb_wet=args.wet,
    )
    proc = AURAVProcessor(cfg)
    print(f"Processing @ {sr} Hz  (latency {proc.total_latency_samples} samples) …")
    out = proc.process(audio)

    print(f"Writing {args.output} …")
    write_wav(args.output, out, sr)
    print("Done.")


if __name__ == "__main__":
    main()
