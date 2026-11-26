# AURA-V Master Integration Plan
Prepared 7 November 2026 for Lewis Seals.  
Assumption: "the entire plane no" meant "the entire plan now".  
Every number below was measured in this conversation; anything unmeasured is marked as such.

## 1. Goal and rules

Build one vocal chain, in the order Source, Correction, Control, Character, Space, Glue, Motion, Noise, where every module is verified by a test before it ships.

• Eval-Driven Engineering: no claim without a measured number. If it cannot be measured, it does not ship.  
• Level, true peak, loudness, aliasing, spurs, noise floor, determinism and NaN safety are release gates.  
• Third-party names (Dolby, Bogren) are descriptive only. Nothing here is affiliated with or bit-accurate to any proprietary product.  
• WER (intelligibility) can only be run on your machine with Whisper. It is the last open gate.

## 2. Target signal chain

1. Source. AURA-V synth (DDSP glottal source plus RNN tract; not built), the Harmonia codec scaffold (voice only, no trained weights), or a recorded dry vocal. Guitar is rendered downstream and mixed after the decoder.
2. Correction. DC block, high-pass, EQ, de-esser (The Order stages 1 to 9; Dolby PEQ from the Vocal Atmos Chain v0.3 is the alternative EQ).
3. Control. Compressor, then peak policy.
4. Character. One even-order source only: Vantage at 4x (a between 2 and 6, DC blocker after it). Optional light Jiles-Atherton blend at 4x. Do not stack Vantage with the y-squared term at full strength.
5. Dolby-style lift. Exactly one of: Dolby Stretch (Vocal-Hi-Fi), the Dolby A encoder (Vocal Atmos Chain v0.3), or the Atmos Verb Air stage. See section 6.
6. Space. Atmos Verb FDN reverb (RT60 within 2 percent of the requested decay), optional binaural.
7. Glue. Jowiphon-P loudness stage (BS.1770, 400 ms block gating), then a true-peak look-ahead limiter at -1.0 dBTP.
8. Motion. ADT (Vocal-Hi-Fi) and the motion modules in The Order.
9. Noise. Jowiphon thermal noise (white Johnson floor plus 1/f flicker below a 100 Hz corner) as the 8-bit dither source when the Vantage bit-crush path is used, then ProDither 16-bit (Lipshitz, feedback subtracted) as the very last stage.

Ordering rules learned the hard way:

• Dither belongs before the quantizer it dithers. A 16-bit ProDither after an 8-bit stage does nothing audible.  
• The final ProDither must be last. Any gain or clipping after it destroys the 16-bit grid.  
• Clippers and limiters that generate harmonics must run inside the oversampled domain or at 4x themselves.  
• Chain order is 44.1 kHz until the Lipshitz and Wanner coefficients are verified at 48 kHz.

## 3. Module status

### Verified (measured here)

• Vantage oversampled stage (vantage_os.py): summed non-harmonic residual about -102 dBc at drive a=6, 12 and 25 with the 241-tap Kaiser filter, against -63, -38 and -26 dBc at base rate. Latency 60 host samples (1.25 ms at 48 kHz). The curve leaves a DC offset (-0.17 at 0.9 amplitude, a=2), so a DC blocker is mandatory.  
• Jowiphon-P (jowiphon_noise.py, patched): loudness matches an independent BS.1770 reference to 0.004 dB. The new thermal kind passes the spectral-slope gate: -3.02 dB/oct below the corner, -0.004 above 300 Hz.  
• ProDither fixed (prodither_fixed.py): feedback sign corrected. Lipshitz sits 17.6 dB below flat TPDF in 1 to 5 kHz ( (as shipped it was 5.5 dB worse). Wanner similar. At 8-bit with -48 dBFS dither the spurs are buried in 5 of 5 seeds.  
• The Order with AURA stages (The-Order-CASE-22-EAR-4-aura.zip): 14 of 14 gates pass (Vantage saturation, true-peak limiter, ProDither).  
• Vocal-Hi-Fi (Vocal-Hi-Fi-fixed.zip): heap overflow in processInterleaved and a soft-clip discontinuity fixed; new tests fail on the old code and pass on the new.  
• Atmos Verb DSP core: Air stage matches its own law to 0.18 dB; reverb RT60 within 2 percent; bit-exact when Air and reverb are off.  
• Guitar (harmonia_guitar.py): tuning error at most 0.36 cents across seven notes; six tests pass.  
• Helix-Bench engine: resonator gain and tracker energy gate fixed; the tracker now finds 288 of 377 voiced frames at 3.3 cents error (it found 1 before).

### Present but with defects not yet fixed

• Dolby Stretch: boosts quiet signal (upward compression); gain pins at 9 to 18 dB below about -50 dBFS; THD -41 dBc at 60 Hz; default mix and trim lose 0.5 dB when loud; the non-stretch mode is unreachable from VocalProcessor; most preset keys are ignored by the C ABI.  
• Dolby A encoder (v0.3): bands are not complementary, so the response dips 7 dB around 120 Hz at -6 dBFS and about 5 dB near 9 kHz at -60 dBFS; it attenuates loud material by up to 9.9 dB; vectors are resized on the audio thread. NaN safety fixed.  
• Atmos Verb: GUI lift graph ignores Air Wet and the high-pass response (graph +6.2 dB versus DSP +2.3 dB at defaults). NaN safety fixed. The VST3 and GUI sources were not built (no Steinberg SDK here).  
• Perfect Clipper v2: its own 10 tests pass, but the real threshold is -0.40 dBFS (not -0.2), it never reaches its 0.9995 ceiling (steady output -0.30 dBFS), and at base rate it raises aliasing from -103 to -45 dBc at a=12. Inside the shared 4x domain with its own extra 2x it reaches about -89 dBc. True peak still exceeds -1 dBTP, so it cannot replace the limiter.  
• Fenwal / Jiles-Atherton: delivered stems peak at -49 dBFS instead of -1 dBTP (fixed generator: generate_fenwal_stem_fixed.py). The JA stage is odd-harmonic only and not strictly Jiles-Atherton; even-order content comes from the explicit polynomial term.  
• Jowiphon-C (static core): fixed gain only; wrong 44.1 kHz coefficient labeling; per-sample gate biases loudness upward; boosts +46 dB if the whole buffer is below -70. Kept as an optional "character" mode, not a mastering stage.  
• Shibata noise-shaping table: ineffective in either sign. DTC emphasis mode in ProDither is wrong (pre-filter cuts instead of boosts; round trip +3.1 dB). Both stay disabled.

### Not built or not available

• AURA-V synth itself (DDSP source plus RNN tract).  
• Harmonia trained weights.  
• Your original ProDither from "Seals & Windsor Audio Plugin.txt".  
• The "hi-def" and "another chain" repos you mentioned were not located; Vocal-Hi-Fi (redesigned-octo-tribble) was found.  
• The WER run.

## 4. Release gates (all must pass)

• True peak: at most -1.0 dBTP, tolerance 0.1 dB, measured with 4x oversampling on the final 16-bit file.  
• Loudness: within 0.5 LU of target (for example -14 LUFS streaming or -23 EBU R128). A miss caused by a trim is a failure; it needs a limiter, not a scalar.  
• Aliasing: summed non-harmonic residual of 90 dBc or lower below the fundamental at A=0.9, f0=1013 Hz, a in {6, 12, 25}, 4x. Use the summed metric, not the single largest bin.  
• Spurs: 8-bit stage shows no spur more than 6 dB above the local floor with dither at -48 dBFS RMS (or 0.5 LSB); the detector must see spurs at -54 dBFS (sensitivity check).  
• Dither: 100 percent of output samples on the 16-bit grid; 1 to 5 kHz error floor at least 10 dB below flat TPDF; no spurs.  
• DC: after the blocker, mean under 1e-3.  
• Robustness: one NaN or Inf in produces no non-finite output; blocks larger than the scratch buffer are safe (run with AddressSanitizer and UBSan).  
• Determinism: same seeds give bit-identical output.  
• Latency: every stage declares its latency; the sum is reported.  
• Stack guard: the build fails if more than one Dolby-style lift stage is instantiated (section 6).  
• WER: on your machine, with Whisper at temperature 0, at least 300 words with plosives and fricatives, paired comparison on the same transcript. Gate: WER(chain) minus WER(dry) under 12 points, and Chain A versus Chain B decided with enough words that a 2 to 3 point gap is not noise.

## 5. Aliasing and drive settings

• Vantage at a=2 does not alias measurably, so oversampling gains nothing there. From a=6 it matters, and a short filter is not enough: the 241-tap Kaiser (beta 9) is what reaches the floor.  
• The Jiles-Atherton stage aliases at base rate (-64 dBc at 0.9 amplitude, 1013 Hz) and improves to -78 dBc at 4x; its output level also shifts about 1.3 dB between 48 and 192 kHz, so it must be tuned at the final rate.  
• The memoryless Vantage curve is rate-independent (RMS identical at 48 and 192 kHz).

## 6. Dolby-style stages and the stack guard

Three different stages in your work lift quiet high-frequency material. Stacked, they add a lot. Measured at 10 kHz with default settings:

• At -70 dBFS: Dolby A +4.0 dB, Stretch +12.0 dB, Air +2.3 dB. Dolby A plus Stretch +16.0 dB. All three +18.3 dB.  
• At -50 dBFS: Stretch +9.7 dB; Dolby A plus Stretch +11.9 dB; all three +13.7 dB.  
• With Stretch at mix 1 and Air at full amount and wet, the lift reached +27.0 dB at -70 dBFS.

Rule: one of {Dolby Stretch, Dolby A encoder, Air} per chain. The guard is a build-time check; "Bogren A-Class Vocal" does not exist anywhere in the code you uploaded, so the guard must be written against these three module names instead. Raising the noise floor is the main cost: any hiss or dither below -50 dBFS gets boosted.

## 7. Phases

**Phase 0: housekeeping (one session)**  
• Put every verified file in one repository with a single test entry point. Remove committed binaries (libvocalhifi.so and the prebuilt selftest were in the repo).  
• Record that the v0.3 zip was truncated and keep the recovered source in recovered_v0_3/.

**Phase 1: close known defects**  
• Fix the Dolby A band split (complementary crossover) and add a gain-reduction cap; fix the Atmos Verb GUI graph so it includes Air Wet and the high-pass response.  
• Expose stretch and the missing preset keys in Vocal-Hi-Fi.  
• Move the Perfect Clipper into the 4x Vantage domain, or drop it and rely on the true-peak limiter.  
• Add the real limiter to the loudness path so -14 LUFS at -1 dBTP is reachable (the integration test missed that target by 5.6 and 7.2 LU).

**Phase 2: one chain, one test**  
• Wire the final order from section 2 into The Order (replace_stage), add the stack guard, and run every gate in section 4 end to end, including a hot input that actually engages the limiter.  
• Re-run at 44.1 kHz and decide whether to keep 48 kHz (needs verified noise-shaping coefficients).

**Phase 3: intelligibility (you)**  
• Render the dry, Chain A (no anti-aliasing filter) and Chain B (with it), plus Chain B with ProDither, from a 300-word script. Run aura_v_wer_gate.py locally. Report the four WER numbers.

**Phase 4: listening and product**  
• Listening tests on real vocals; presets; JUCE or Steinberg VST3 packaging (the Atmos Verb sources and the Vocal-Hi-Fi C ABI are the starting points); manuals.

**Phase 5: synth and codec**  
• AURA-V source and tract, Harmonia training, and the guitar path (already rendered downstream).

## 8. Decisions I need from you

1. Dolby stage: which of Stretch, Dolby A encoder or Air is the primary one?  
2. Even-order source: Vantage (recommended), the polynomial term, or a Jiles-Atherton blend?  
3. Targets: loudness and true-peak (for example -14 LUFS / -1 dBTP streaming, or -23 LUFS EBU).  
4. Sample rate: 44.1 kHz (verified coefficients) or 48 kHz (needs new shaping coefficients).  
5. Shipping form: Python chain, JUCE plugin, or Steinberg VST3.  
6. Originals: can you upload "Seals & Windsor Audio Plugin.txt" and the real "hi-def" and other repo URLs, so I can swap them in where mine are stand-ins?

## 9. Risks

• The Wanner and Lipshitz tables are published for 44.1 kHz. Other rates are unverified.  
• Boosting quiet material raises hiss; the noise-floor budget has to be measured on real vocals.  
• Several uploads were incomplete (truncated zip, corrupt earlier zip, a README with instructions aimed at AI agents that I ignored).  
• Single-tone tests do not prove speech behavior. The aliasing and WER gates need real vocals.  
• Every stage in this plan is a research-grade approximation, not a certified emulation of any hardware or product.

## 10. File inventory (all in the shared outputs folder)

• Harness and tests: aura_v_edd_harness.py, aura_v_edd_harness2.py, aura_v_alias_fix.py, aura_v_wer_gate.py, aura_v_integration_test.py, plots aura_v_tests_1_2.png, aura_v_gate3b.png.  
• Verified modules: vantage_os.py, jowiphon_noise.py, prodither_fixed.py, generate_fenwal_stem_fixed.py.  
• Harmonia and guitar: HarmoniaCodec-Music-guitar.zip, harmonia_guitar.py, test_guitar.py, harmonia_guitar_demo.wav.  
• The Order with AURA stages: The-Order-CASE-22-EAR-4-aura.zip.  
• Dolby sources: Vocal-Hi-Fi-fixed.zip, Vocal-Atmos-recovered.zip.  
• Helix-Bench: helix-bench-standalone.html.

## 11. Update, 21 November 2026

Everything below was measured in this conversation unless marked otherwise. All audio tests used synthetic plucked notes, not recordings of a real guitar.

### 11.1 What changed

• Guitar path integrated and gated (9 of 9 pass). AURA-G transcription, tuned waveguide string, talk-box tract, LA-2A leveler, loudness match, true-peak limiter, ProDither 16-bit at 44.1 kHz. Result: 10 of 10 notes transcribed, -14.06 LUFS, -1.05 dBTP, 100 percent of samples on the 16-bit grid, 1 to 5 kHz noise floor 17.6 dB below flat TPDF, NaN and Inf safe, bit-identical reruns. Package: AURA-G-Adapter.zip.  
• Why the LA-2A is in that chain. The talk-box output has a 30 dB crest factor (each pluck peaks about 5 ms in) and note levels vary by 14.8 dB. Without a leveler the limiter needed 22 dB of gain reduction to reach -14 LUFS. At Peak Reduction 0.30 the crest drops to 20 dB, the spread to 4.6 dB, and the limiter needs 6.5 dB.  
• LA-2A module (from the LA2A-compressor repo's la2a_core.h): attack to 90 percent in 0.15 ms, 50 percent release in 61 ms, THD 4.4 percent at 30 Hz and 1.7 percent at 100 Hz under heavy limiting. Peak Reduction is steep (0.04 to 0.10 gives 1 to 6 dB at vocal peaks; 0.5 is about 30 dB). It does not compile as a plugin here and is unvalidated against hardware. NaN fix applied. It is available as the optional slow_comp stage in The Order.  
• Talk-box mouth model. The Cmajor tract in the uploaded repo uses 8 one-sample sections, which is a 2.9 cm tract with resonances at 5 to 15 kHz, so it cannot make vowels. The corrected model has 48 sections (17 cm) with vowel shapes fitted to textbook formants (F1 and F2 within about 10 percent). The rendered guitar follows the tract's own response to within 1.33 dB per harmonic.  
• AURA-G defects found and fixed in the adapter. The front end's YIN picks the lowest minimum and reports octave-low pitches on plucks; the stock transcription engine emits one event per onset frame (79 events for 10 notes, F1 0.22) with no durations; DigitalWaveguideString runs +2.8 to +33.5 cents sharp, ignores the fret for pitch, and damps each loop by 1 - 0.05 x fret so fretted notes die in milliseconds.  
• AURA-G C++ engine (AuraGEngine.cpp): did not compile (uses juce::jlimit without JUCE, uses a private type), ran 7 to 15 cents flat, and the waveguide never decayed. Fixed in AuraGEngine-fixed.zip (within 0.4 cents, decay now set by wgDamp). The JUCE plugin files themselves were not built.  
• Melody and MIDI. The VME melody generator drives the guitar and talk box (its README metrics reproduce exactly). The MIDI bridge reads and writes standard MIDI files and has a monophonic transcriber (9 of 10 notes).

### 11.2 Other repos checked since the first version

• Vocal-Hi-Fi: heap overflow in the interleaved wrapper and a soft-clip discontinuity fixed; Dolby Stretch measured (see section 3).  
• Fenwal stems: delivered files peak at -49 dBFS; fixed generator written.  
• DarkMind Vocoder: startup crash fixed (band edge above Nyquist); its block-continuity test still fails and its Python reference is not reliably real-time. A vocoder cannot enforce "not usable for real-time TTS", and no repo mentions the claimed Yale or Musk origin.  
• Open-TTS-Eval and MagneticOracle / solid-disco: read; the oracle pipeline ran with a numpy stand-in for torch and reproduced only approximately.  
• MajorGuitar and Juncture: the repo's Juncture.html is a mock (random rectangles, no audio); a pasted version has a syntax error, and its string runs flat by 1.7 to 15 cents (a half-sample correction fixes most notes).  
• Not yet reviewed: schema-main, ElevenX-main, AURA-G parts 3 and 4 beyond the file list, and self-sealing-apocryphon.

### 11.3 Legal notes (not legal advice)

• By the dates in the notes you supplied (unverified), the matrix, Pro Logic, AC-3 and 1991 sound-field patents are expired. US 11,972,767 (covariance smoothing, filed 2020) runs to about 2040 and has a continuation; the 2010 to 2012 filings may still be live if granted.  
• Expired patents do not free trademarks, copyright in code or manuals, or trade secrets. Neutral stage names are the safer choice for anything shipped. Have counsel review the design-around analysis before a commercial launch.

### 11.4 Gates added for the guitar path

• 10 of 10 test notes transcribed; loudness within 0.5 LU of target; true peak at most -0.9 dBTP; limiter gain reduction at most 8 dB; 100 percent on the 16-bit grid; 1 to 5 kHz floor at least 10 dB below flat TPDF; DC under 1e-3; bit-identical reruns; one NaN and one Inf in the input give finite output. Run python guitar_gates.py.

### 11.5 Still open

1. WER on a real vocal, run on your machine (unchanged).  
2. Listening tests of the talk box and guitar chain; real guitar recordings through the transcriber.  
3. Chords: the transcriber is monophonic.  
4. AURA-G torch parts (DDSP amp, RNN effects, blind extractor, mixer) and the FPGA and training files have not been run.  
5. The Dolby A crossover and Atmos Verb graph fixes from section 7, and a decision on which single Dolby-style stage to use.  
6. Review of the remaining uploads listed in 11.2.

### 11.6 Decisions still needed

Primary Dolby-style stage; even-order source (Vantage recommended); loudness and true-peak targets; sample rate (the guitar chain is locked to 44.1 kHz because the dither coefficients are verified there); shipping form; and the license for the talk-box package (Research / Non-Commercial versus MIT).

### 11.7 Files added

AURA-G-Adapter.zip, AuraGEngine-fixed.zip, HarmoniaTalkbox-5.zip, VME-Guitar-TalkBox.zip, The-Order-CASE-22-EAR-4-aura.zip (now includes the LA-2A block), Vocal-Atmos-recovered.zip, Vocal-Hi-Fi-fixed.zip, darkmind_vocoder_v2_fixed.py, generate_fenwal_stem_fixed.py, mouth_tract.py, mouth_guitar_talkbox.py, torch_shim_for_oracle.zip.
