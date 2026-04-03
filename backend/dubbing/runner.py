"""Pipeline Runner — the NEW modular pipeline orchestrator.

Replaces monolith logic with clean module calls.
pipeline.py becomes a thin wrapper that calls this.

Flow:
  Audio → Parakeet + WhisperX → normalize → glossary tag → reconcile
  → DP cue build → English QC → glossary lock → surgical repair
  → Hindi translate → Hindi fit → glossary validate → format
  → pre-TTS QC → TTS segments export
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Callable
import json

from . import asr_runner, glossary, glossary_builder, cue_builder, qc
from . import translation, fit_hi, format_hi, tts_bridge
from .contracts import Word, Cue, GlossaryTerm
from .defaults import PRODUCTION


ProgressFn = Callable[[str, float, str], None]


class DubbingRunner:
    """New modular dubbing pipeline runner.

    Single source of truth at each layer:
    - Text source: Parakeet
    - Timing source: WhisperX
    - Cue source: DP cue builder
    - Speech source: fitted Hindi cues
    """

    def __init__(self, work_dir: Path, source_lang: str = "en",
                 target_lang: str = "hi", on_progress: ProgressFn = None):
        self.work_dir = work_dir
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._progress = on_progress or (lambda *_: None)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # State
        self.words: List[Word] = []
        self.cues: List[Cue] = []
        self.glossary_terms: List[GlossaryTerm] = []

    def report(self, step: str, progress: float, msg: str):
        self._progress(step, progress, msg)

    # ════════════════════════════════════════════════════════════════
    # STAGE A: ASR
    # ════════════════════════════════════════════════════════════════

    def run_asr(self, wav_path: Path, use_parakeet: bool = True) -> List[Word]:
        """Run dual ASR: Parakeet text + WhisperX timing → reconciled words."""

        parakeet_words = []
        whisperx_words = []

        # 1. Parakeet (text source)
        if use_parakeet:
            try:
                self.report("transcribe", 0.05, "Running Parakeet TDT (text source)...")
                parakeet_words = asr_runner.run_parakeet(
                    wav_path, on_progress=lambda msg: self.report("transcribe", 0.1, msg))
                self.report("transcribe", 0.3, f"Parakeet: {len(parakeet_words)} words")
            except Exception as e:
                self.report("transcribe", 0.1, f"Parakeet failed: {e}, using WhisperX only")

        # 2. WhisperX (timing source)
        try:
            self.report("transcribe", 0.35, "Running WhisperX (timing source)...")
            whisperx_words = asr_runner.run_whisperx(
                wav_path, language=self.source_lang,
                on_progress=lambda msg: self.report("transcribe", 0.5, msg))
            self.report("transcribe", 0.6, f"WhisperX: {len(whisperx_words)} words")
        except Exception as e:
            self.report("transcribe", 0.4, f"WhisperX failed: {e}")
            if not parakeet_words:
                raise RuntimeError(f"Both ASR engines failed: {e}")

        # 3. Normalize
        if parakeet_words:
            parakeet_words = asr_runner.normalize_words(parakeet_words)
        if whisperx_words:
            whisperx_words = asr_runner.normalize_words(whisperx_words)

        # 4. Reconcile: Parakeet text + WhisperX timing
        if parakeet_words and whisperx_words:
            self.report("transcribe", 0.65, "Reconciling ASR outputs...")
            self.words = asr_runner.reconcile(parakeet_words, whisperx_words)
        elif parakeet_words:
            self.words = parakeet_words
        else:
            self.words = whisperx_words

        self.report("transcribe", 0.7, f"ASR complete: {len(self.words)} reconciled words")
        return self.words

    def load_words_from_segments(self, segments: List[dict]) -> List[Word]:
        """Load words from existing pipeline segments (for gradual migration)."""
        self.words = []
        for seg in segments:
            # If segment has word-level data
            if seg.get("words"):
                for w in seg["words"]:
                    self.words.append(Word(
                        text=w.get("word", w.get("text", "")),
                        start=w.get("start", 0),
                        end=w.get("end", 0),
                        source="imported",
                    ))
            else:
                # Segment-level: treat whole segment as one "word"
                text = seg.get("text", "").strip()
                if text:
                    for word_text in text.split():
                        self.words.append(Word(
                            text=word_text,
                            start=seg.get("start", 0),
                            end=seg.get("end", 0),
                            source="imported",
                        ))
        self.words = asr_runner.normalize_words(self.words)
        return self.words

    # ════════════════════════════════════════════════════════════════
    # STAGE B: GLOSSARY + CUE BUILDING
    # ════════════════════════════════════════════════════════════════

    def load_glossary(self, glossary_path: Path = None):
        """Load glossary from file, or auto-extract if no file exists."""
        if glossary_path and glossary_path.exists():
            self.glossary_terms = glossary.load_glossary(glossary_path)
            self.report("transcribe", 0.72, f"Loaded {len(self.glossary_terms)} glossary terms")
        else:
            # Auto-extract as fallback (offline ideally, but acceptable for first run)
            self.glossary_terms = glossary_builder.extract_terms_from_words(self.words)
            self.report("transcribe", 0.72, f"Auto-extracted {len(self.glossary_terms)} glossary terms")
            # Save for next run
            if glossary_path:
                glossary_builder.save_glossary(self.glossary_terms, glossary_path)

    def build_cues(self) -> List[Cue]:
        """Tag words → DP cue build → English QC."""

        # 1. Tag words (protect glossary terms from being split)
        self.report("transcribe", 0.75, "Tagging glossary terms on word stream...")
        self.words = glossary.tag_words(self.words, self.glossary_terms)

        # 2. DP cue building
        self.report("transcribe", 0.8, "Building optimal cue boundaries (DP)...")
        self.cues = cue_builder.build_cues(self.words)
        self.report("transcribe", 0.85, f"Built {len(self.cues)} cues")

        # 3. Tag cues with glossary (for translation lock)
        self.cues = glossary.tag_cues(self.cues, self.glossary_terms)

        # 4. English QC
        self.report("transcribe", 0.9, "Running English QC...")
        self.cues = qc.english_qc(self.cues)
        issues = qc.count_issues(self.cues)
        self.report("transcribe", 0.95,
                     f"English QC: {issues['pass_rate']:.0%} pass "
                     f"({issues['flagged_cues']}/{issues['total_cues']} flagged)")

        return self.cues

    # ════════════════════════════════════════════════════════════════
    # STAGE C: TRANSLATION + HINDI FITTING
    # ════════════════════════════════════════════════════════════════

    def translate(self, translate_fn: Callable = None) -> List[Cue]:
        """Translate cues to Hindi.

        translate_fn: external function that takes (cue.text_clean_en, hints) → Hindi text
        If not provided, translate_cues() must be called with an actual translator.
        """
        self.report("translate", 0.0, f"Translating {len(self.cues)} cues to Hindi...")

        # Build translation hints for ALL cues (duration, word targets, etc.)
        for cue in self.cues:
            if not cue.text_clean_en.strip():
                continue
            target_words = max(3, int((cue.duration / 60.0) * translation.HINDI_WPM))
            cue._translation_hints = {
                "duration_ms": int(cue.duration * 1000),
                "target_words": target_words,
                "protected_terms": cue.protected_terms,
                "speaker": cue.speaker,
                "emotion": cue.emotion,
            }

        if translate_fn:
            # Use external translator (e.g., monolith's _translate_segments)
            for i, cue in enumerate(self.cues):
                if cue.text_clean_en.strip():
                    hints = getattr(cue, '_translation_hints', {})
                    cue.text_hi_raw = translate_fn(cue.text_clean_en, hints)
                if (i + 1) % 20 == 0:
                    self.report("translate", 0.1 + 0.7 * ((i + 1) / len(self.cues)),
                                f"Translated {i + 1}/{len(self.cues)}")
        else:
            # No translator provided — cues stay with empty text_hi_raw
            self.report("translate", 0.5,
                        "WARNING: No translate_fn provided — Hindi text will be empty")

        self.report("translate", 0.8, "Translation complete")
        return self.cues

    def fit_hindi(self) -> List[Cue]:
        """Hindi fitting → glossary validation → formatting → pre-TTS QC."""

        # 1. Dub-fit rewrite (formal→spoken, compression)
        self.report("translate", 0.85, "Hindi fitting...")
        self.cues = fit_hi.fit_cues(self.cues, self.glossary_terms)

        # 2. Glossary validation (check terms survived)
        self.report("translate", 0.9, "Validating glossary terms in Hindi...")
        self.cues = glossary.validate_hindi(self.cues, self.glossary_terms)

        # 3. Subtitle formatting (AFTER validation)
        self.report("translate", 0.92, "Formatting Hindi subtitles...")
        self.cues = format_hi.format_cues(self.cues)

        # 4. Pre-TTS QC gate
        self.report("translate", 0.95, "Pre-TTS QC gate...")
        self.cues = qc.pre_tts_qc(self.cues)
        issues = qc.count_issues(self.cues)
        self.report("translate", 0.98,
                     f"Pre-TTS QC: {issues['pass_rate']:.0%} pass "
                     f"({issues['flagged_cues']}/{issues['total_cues']} flagged)")

        return self.cues

    # ════════════════════════════════════════════════════════════════
    # STAGE D: EXPORT
    # ════════════════════════════════════════════════════════════════

    def export_for_tts(self) -> List[dict]:
        """Export cues as pipeline-compatible TTS segments."""
        return tts_bridge.export_tts_segments(self.cues)

    def export_srt(self, output_path: Path, text_key: str = "text_hi_display"):
        """Export Hindi SRT subtitle file."""
        tts_bridge.export_srt(self.cues, output_path, text_key)

    def export_csv(self, output_path: Path):
        """Export for ElevenLabs manual dub format."""
        tts_bridge.export_csv(self.cues, output_path)

    def export_json(self, output_path: Path):
        """Export full cue data for debugging."""
        tts_bridge.export_json(self.cues, output_path)

    def export_source_srt(self, output_path: Path):
        """Export English source SRT."""
        tts_bridge.export_srt(self.cues, output_path, text_key="text_clean_en")

    # ════════════════════════════════════════════════════════════════
    # CONVENIENCE: Full run
    # ════════════════════════════════════════════════════════════════

    def run_full(self, wav_path: Path, translate_fn: Callable = None,
                 glossary_path: Path = None, use_parakeet: bool = True) -> List[dict]:
        """Run the complete pipeline: ASR → cues → translate → fit → export.

        Returns TTS-ready segments for pipeline.py to synthesize.
        """
        # ASR
        self.run_asr(wav_path, use_parakeet=use_parakeet)

        # Glossary
        self.load_glossary(glossary_path)

        # Cue building
        self.build_cues()

        # Translation
        self.translate(translate_fn)

        # Hindi fitting + QC
        self.fit_hindi()

        # Export
        segments = self.export_for_tts()

        # Also save debug artifacts
        self.export_json(self.work_dir / "cues_debug.json")
        self.export_csv(self.work_dir / "cues_elevenlabs.csv")

        self.report("translate", 1.0, f"Pipeline complete: {len(segments)} segments ready for TTS")

        return segments
