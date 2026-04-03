---
name: Pipeline Architecture v1 — Locked Final
description: Canonical locked architecture for HindiDub pipeline. All design decisions finalized. No Google RT, no manual pauses in auto mode, deterministic TTS routing, per-segment fit only.
type: project
---

## HindiDub Pipeline v1 — Locked Architecture

### Stage A: Source Analysis
- Download + extract audio
- Source separation (demucs — vocals vs background)
- **ASR: Whisper PRIMARY**, YouTube subs AUXILIARY (keyterm signal only)
- Conditional diarization (only when multi_speaker enabled)
- Extract keyterms → glossary lock (protected from rule engine replacements)
- Tag prosody per segment: rate / energy / ending / emotion

### Stage B: Text Optimization
- Merge split sentences into complete ones
- LLM simplify (break compounds, reduce nested clauses, preserve emphasis)
- **No Google round-trip** in the final path

### Stage C: Duration-Aware Translation
- Translate with **ms-based timing targets** per segment
- LLM polish with: continuity (previous line), prosody tags, anti-padding, duration hints
- Generate **3 variants** (short / balanced / expanded), choose best fit using prosody
- Rule engine: 70+ formal→spoken replacements, glossary terms protected

### Stage D: Conditioned Synthesis
- Prepare TTS text (pronunciation dict + keyterms)
- **Deterministic language-family TTS routing:**
  - Indic: Chatterbox → CosyVoice → XTTS → Edge
  - CJK: CosyVoice → Chatterbox → XTTS → Edge
  - European/Other: CosyVoice → Chatterbox → XTTS → Edge
  - English: Chatterbox-Turbo → CosyVoice → XTTS → Edge
- Build continuity memory per segment
- Force-align + trim + **11-metric scoring**: duration, lead/tail silence, spoken_duration, silence_ratio, duration_error_ms, duration_ratio, pause_map_score, pronunciation_hit, fit_score (composite), trimmed
- Split failed segments: punctuation → conjunctions → clauses → pause valleys → midpoint (last resort)
- Per-segment Edge-TTS fallback if primary engine fails

### Stage E: Per-Segment Duration Fit
- **Per-segment only** — no global uniform speedup
- Overflow: speed up individual clips (max 1.1x)
- Underflow: accept natural gap; tiny slowdown (max 5%) only if >40% empty
- Global ratio: **diagnostic only** (logged, never applied as blanket change)

### Stage F: Assembly (priority chain)
1. Text already duration-bounded (Stage C variant selection)
2. TTS already rerendered on QC fail (3 retries)
3. Failed segments already split (Stage D)
4. Per-segment audio micro-fit (Stage E, max 1.1x)
5. Local video slow to 1.1x (if still needed)
6. Freeze last frame (**emergency only** — rare after steps 1-5)
7. Mix background (sidechain duck)
8. Normalize final output

### Speed Philosophy
- Audio NEVER exceeds 1.1x speedup
- Video adaptation is a late fallback, not the primary strategy
- Text adaptation (shorter/longer variants) is the FIRST line of defense
- Freeze-frame is emergency-only

### What is NOT in this pipeline
- No Google Translate round-trip simplification
- No manual review pauses (unless user explicitly enables step_by_step)
- No "first available" TTS — deterministic routing only
- No global uniform speedup applied to all segments
- No "video does all adaptation" as primary strategy
