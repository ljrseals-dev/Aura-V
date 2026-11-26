# AURA-V Master Integration Plan & Plugin

**Prepared 7 November 2026 for Lewis Seals**  
**Update 21 November 2026**  
**Plugin scaffold built 25 November 2026**

Assumption: "the entire plane no" meant "the entire plan now".  
Every measured number below comes from the original conversation; anything unmeasured is marked.

This repository contains:

1. The full Master Integration Plan (sections 1–11).
2. A working Python implementation of the AURA-V vocal chain (`aura_v` package).
3. Release-gate tests that can be run immediately.
4. Clear extension points for the remaining modules (Dolby stages, AURA-V synth, etc.).

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python -m aura_v.tests.run_gates
python scripts/process_vocal.py input.wav output.wav
```

## Default Decisions Used in This Build

| Decision                    | Choice                          | Reason                          |
|----------------------------|---------------------------------|---------------------------------|
| Dolby-style lift           | Air (Atmos Verb Air stage)      | Lightest measured lift          |
| Even-order character       | Vantage @ 4×                    | Recommended in plan             |
| Loudness / True-peak       | –14 LUFS / –1.0 dBTP            | Streaming target                |
| Sample rate                | 44.1 kHz                        | Verified Lipshitz/Wanner coeffs |
| Shipping form              | Python chain (JUCE/VST3 later)  | Fastest path to measurable gates|

---

# 1. Goal and rules

Build one vocal chain, in the order **Source → Correction → Control → Character → Space → Glue → Motion → Noise**, where every module is verified by a test before it ships.

- **Eval-Driven Engineering**: no claim without a measured number. If it cannot be measured, it does not ship.
- Level, true peak, loudness, aliasing, spurs, noise floor, determinism and NaN safety are release gates.
- Third-party names (Dolby, Bogren) are descriptive only. Nothing here is affiliated with or bit-accurate to any proprietary product.
- WER (intelligibility) can only be run on your machine with Whisper. It is the last open gate.

# 2. Target signal chain

1. **Source**. AURA-V synth (DDSP glottal source + RNN tract; not built), the Harmonia codec scaffold (voice only, no trained weights), or a recorded dry vocal. Guitar is rendered downstream and mixed after the decoder.
2. **Correction**. DC block, high-pass, EQ, de-esser (The Order stages 1–9; Dolby PEQ from Vocal Atmos Chain v0.3 is the alternative EQ).
3. **Control**. Compressor, then peak policy.
4. **Character**. One even-order source only: Vantage at 4× (a between 2 and 6, DC blocker after it). Optional light Jiles-Atherton blend at 4×. Do not stack Vantage with the y-squared term at full strength.
5. **Dolby-style lift**. Exactly one of: Dolby Stretch (Vocal-Hi-Fi), the Dolby A encoder (Vocal Atmos Chain v0.3), or the Atmos Verb Air stage. See section 6.
6. **Space**. Atmos Verb FDN reverb (RT60 within 2 % of the requested decay), optional binaural.
7. **Glue**. Jowiphon-P loudness stage (BS.1770, 400 ms block gating), then a true-peak look-ahead limiter at –1.0 dBTP.
8. **Motion**. ADT (Vocal-Hi-Fi) and the motion modules in The Order.
9. **Noise**. Jowiphon thermal noise (white Johnson floor + 1/f flicker below a 100 Hz corner) as the 8-bit dither source when the Vantage bit-crush path is used, then ProDither 16-bit (Lipshitz, feedback subtracted) as the very last stage.

**Ordering rules learned the hard way**

- Dither belongs before the quantizer it dithers. A 16-bit ProDither after an 8-bit stage does nothing audible.
- The final ProDither must be last. Any gain or clipping after it destroys the 16-bit grid.
- Clippers and limiters that generate harmonics must run inside the oversampled domain or at 4× themselves.
- Chain order is 44.1 kHz until the Lipshitz and Wanner coefficients are verified at 48 kHz.

# 3. Module status

### Verified (measured)

- **Vantage oversampled stage** (`vantage_os.py`): summed non-harmonic residual ≈ –102 dBc at drive a=6, 12 and 25 with the 241-tap Kaiser filter, against –63, –38 and –26 dBc at base rate. Latency 60 host samples (1.25 ms @ 48 kHz). Curve leaves a DC offset (–0.17 at 0.9 amplitude, a=2) → DC blocker mandatory.
- **Jowiphon-P** (`jowiphon_noise.py`, patched): loudness matches independent BS.1770 reference to 0.004 dB. Thermal kind passes spectral-slope gate: –3.02 dB/oct below corner, –0.004 above 300 Hz.
- **ProDither fixed** (`prodither_fixed.py`): feedback sign corrected. Lipshitz sits 17.6 dB below flat TPDF in 1–5 kHz (as shipped it was 5.5 dB worse). At 8-bit with –48 dBFS dither the spurs are buried in 5 of 5 seeds.
- **The Order with AURA stages**: 14 of 14 gates pass.
- **Vocal-Hi-Fi**: heap overflow + soft-clip discontinuity fixed.
- **Atmos Verb DSP core**: Air stage matches its own law to 0.18 dB; RT60 within 2 %; bit-exact when Air/reverb off.
- **Guitar** (`harmonia_guitar.py`): ≤ 0.36 cents error; 6 tests pass.
- **Helix-Bench**: tracker now finds 288/377 voiced frames at 3.3 cents error.

### Present but with defects not yet fixed

- Dolby Stretch, Dolby A encoder, Atmos Verb GUI graph, Perfect Clipper v2, Fenwal/Jiles-Atherton, Jowiphon-C, Shibata table, DTC emphasis.

### Not built

- AURA-V synth itself, Harmonia trained weights, original ProDither from “Seals & Windsor…”, WER run.

# 4. Release gates (all must pass)

- True peak ≤ –1.0 dBTP (tol 0.1 dB), 4× OS measurement on final 16-bit file.
- Loudness within 0.5 LU of target.
- Aliasing: summed non-harmonic residual ≤ –90 dBc @ A=0.9, f0=1013 Hz, a ∈ {6,12,25}, 4×.
- Spurs: 8-bit stage no spur > 6 dB above local floor with –48 dBFS dither.
- Dither: 100 % of samples on 16-bit grid; 1–5 kHz floor ≥ 10 dB below flat TPDF; no spurs.
- DC: mean < 1e-3 after blocker.
- Robustness: NaN/Inf in → finite out; AddressSanitizer/UBSan clean.
- Determinism: same seeds → bit-identical output.
- Latency: every stage declares latency; sum reported.
- Stack guard: build fails if >1 Dolby-style lift is instantiated.
- WER (local): WER(chain)–WER(dry) < 12 points on ≥300 words.

# 5–11. (Full text retained in docs/MASTER_PLAN.md)

See `docs/MASTER_PLAN.md` for the complete original plan including phases, risks, file inventory, guitar-path update, legal notes, and open decisions.

---

## Package Layout

```
aura_v/
├── aura_v/
│   ├── __init__.py
│   ├── processor.py          # End-to-end chain
│   ├── modules/
│   │   ├── dc_block.py
│   │   ├── highpass.py
│   │   ├── vantage.py        # 4× oversampled even-order
│   │   ├── jowiphon_p.py     # BS.1770 loudness + thermal noise
│   │   ├── true_peak_limiter.py
│   │   ├── prodither.py      # Lipshitz 16-bit
│   │   ├── air_lift.py       # Lightweight Air-style high-freq lift
│   │   ├── fdn_reverb.py     # Simple FDN (RT60 controlled)
│   │   └── ...
│   └── tests/
│       ├── run_gates.py
│       └── test_*.py
├── scripts/
│   └── process_vocal.py
├── docs/
│   └── MASTER_PLAN.md
├── pyproject.toml
└── README.md
```

## Next Steps (from plan Phase 1–2)

1. Replace Air stub with real Atmos Verb Air stage once source is available.
2. Wire remaining Correction / Control / Motion stages from The Order.
3. Add stack-guard compile-time check when C++ path is built.
4. Run full gate suite on real vocal material.
5. Local WER with Whisper (Phase 3).

---

**License**: Research / Non-Commercial (change in LICENSE if desired).  
**Disclaimer**: Research-grade approximations only. Not affiliated with Dolby, Bogren, or any proprietary product.
