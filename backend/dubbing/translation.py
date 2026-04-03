"""Translation module — Hindi translation with glossary lock and duration hints.

Input: Cue with text_clean_en, protected_terms, duration
Output: Cue with text_hi_raw populated
"""
from __future__ import annotations
import os
from typing import List

from .contracts import Cue

# Hindi speaking rate
HINDI_WPM = 120


def translate_cues(cues: List[Cue], engine: str = "auto",
                   source_lang: str = "en", target_lang: str = "hi",
                   on_progress=None) -> List[Cue]:
    """Translate all cues from English to Hindi.

    For each cue, sends:
    - text_clean_en
    - duration in ms
    - protected terms (glossary lock)
    - speaker context
    """
    # This is a thin wrapper — actual translation engines are in pipeline.py
    # The module structure allows swapping engines cleanly
    for i, cue in enumerate(cues):
        if not cue.text_clean_en.strip():
            continue

        # Build duration hint
        target_words = max(3, int((cue.duration / 60.0) * HINDI_WPM))
        dur_ms = int(cue.duration * 1000)

        # Store metadata for translation prompt
        cue._translation_hints = {
            "duration_ms": dur_ms,
            "target_words": target_words,
            "protected_terms": cue.protected_terms,
            "speaker": cue.speaker,
            "emotion": cue.emotion,
        }

        if on_progress and (i + 1) % 20 == 0:
            on_progress(f"Translating {i + 1}/{len(cues)}...")

    return cues


def build_translation_prompt(cue: Cue) -> dict:
    """Build the translation prompt for a single cue.

    Returns dict with system_msg and user_msg for LLM API call.
    """
    hints = getattr(cue, '_translation_hints', {})
    dur_ms = hints.get('duration_ms', 0)
    target_words = hints.get('target_words', 0)
    protected = hints.get('protected_terms', [])

    protected_note = ""
    if protected:
        protected_note = f"\nPROTECTED TERMS (keep as-is): {', '.join(protected)}"

    system_msg = (
        "You are a Hindi dubbing translator. Translate to natural spoken Hindi.\n"
        "Rules:\n"
        "- Natural daily-spoken Hindi, not textbook\n"
        "- Keep protected terms unchanged\n"
        "- Use commas for breath pauses, purna viram (।) for stops\n"
        "- Output ONLY the Hindi translation, nothing else\n"
        f"{protected_note}"
    )

    dur_hint = f" [{dur_ms}ms | ~{target_words}w]" if dur_ms > 0 else ""

    user_msg = f"{cue.text_clean_en}{dur_hint}"

    return {"system": system_msg, "user": user_msg}
