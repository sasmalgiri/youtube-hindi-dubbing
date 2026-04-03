"""Data contracts for the dubbing pipeline.

Every module reads and writes these structures.
Never overwrite earlier layers — keep all text versions for debugging.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Word:
    """Single word with timing and metadata."""
    text: str
    start: float
    end: float
    speaker: Optional[str] = None
    confidence: Optional[float] = None
    source: Optional[str] = None  # "parakeet" | "whisperx" | "reconciled"
    protected: bool = False
    term_id: Optional[str] = None


@dataclass
class GlossaryTerm:
    """A protected term that must survive translation intact."""
    canonical: str           # "Zero", "E-rank", "Dragon Nation"
    aliases: list[str] = field(default_factory=list)   # ["zero", "ZERO"]
    source_spelling: str = ""    # How it appears in English ASR
    target_spelling: str = ""    # Hindi transliteration or keep-as-is
    action: str = "keep"         # "keep" | "transliterate" | "fixed_translation"
    pronunciation: str = ""      # TTS pronunciation override


@dataclass
class Cue:
    """One subtitle/dubbing cue — the core unit through the entire pipeline.

    Text layers (never overwrite — always add):
        text_original    — raw ASR output
        text_clean_en    — after cleanup + cue rebuild
        text_hi_raw      — raw Hindi translation
        text_hi_fit      — Hindi after dub-fit rewrite
        text_hi_display  — final formatted Hindi (1-2 lines)
    """
    id: int
    start: float
    end: float
    speaker: Optional[str] = None

    # Text layers
    text_original: str = ""
    text_clean_en: str = ""
    text_hi_raw: str = ""
    text_hi_fit: str = ""
    text_hi_display: str = ""

    # Metadata
    words: list[Word] = field(default_factory=list)
    protected_terms: list[str] = field(default_factory=list)
    pronunciation_overrides: dict[str, str] = field(default_factory=dict)
    qc_flags: list[str] = field(default_factory=list)
    emotion: str = "neutral"  # neutral | punchy | emotional | comedic

    # Timing
    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def word_count(self) -> int:
        text = self.text_hi_fit or self.text_clean_en or self.text_original
        return len(text.split())

    @property
    def wps(self) -> float:
        """Words per second."""
        if self.duration <= 0:
            return 0
        return self.word_count / self.duration

    def to_dict(self) -> dict:
        """Export for JSON/SRT/TTS bridge."""
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "speaker": self.speaker,
            "text_original": self.text_original,
            "text_clean_en": self.text_clean_en,
            "text_hi_raw": self.text_hi_raw,
            "text_hi_fit": self.text_hi_fit,
            "text_hi_display": self.text_hi_display,
            "protected_terms": self.protected_terms,
            "pronunciation_overrides": self.pronunciation_overrides,
            "qc_flags": self.qc_flags,
            "emotion": self.emotion,
            "duration": self.duration,
        }

    def to_tts_row(self) -> dict:
        """Export one row for TTS bridge / ElevenLabs manual dub format."""
        return {
            "speaker": self.speaker or "S1",
            "start_time": round(self.start, 3),
            "end_time": round(self.end, 3),
            "transcription": self.text_clean_en,
            "translation": self.text_hi_fit or self.text_hi_raw,
            "pronunciation_overrides": self.pronunciation_overrides,
        }


# ── Constants ──────────────────────────────────────────────────────────────

# Cue building targets
CUE_WORD_MIN = 6
CUE_WORD_TARGET_MIN = 8
CUE_WORD_TARGET_MAX = 14
CUE_WORD_HARD_MAX = 16
CUE_DUR_HARD_MIN = 0.8
CUE_DUR_TARGET_MIN = 1.2
CUE_DUR_TARGET_MAX = 4.5
CUE_DUR_HARD_MAX = 5.5
CUE_WPS_HARD_MAX = 5.2
CUE_MAX_LINES = 2
CUE_MAX_CPL = 42  # Characters per line

# Audio speed
AUDIO_SPEED_MIN = 0.95
AUDIO_SPEED_MAX = 1.25

# Merge/split
PAUSE_SOFT_MS = 300    # Candidate break when cue is already long
PAUSE_STRONG_MS = 500  # Always a break candidate
MERGE_MIN_WORDS = 4
MERGE_MIN_DUR = 0.6
