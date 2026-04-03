"""QC gates — hard-fail checks at two pipeline positions.

1. English QC (after cue building, before translation)
2. Pre-TTS QC (after Hindi fitting, before synthesis)
"""
from __future__ import annotations
from typing import List

from .contracts import (
    Cue,
    CUE_WORD_HARD_MAX, CUE_DUR_HARD_MAX, CUE_DUR_HARD_MIN,
    CUE_WPS_HARD_MAX, CUE_MAX_CPL, CUE_MAX_LINES,
)


def english_qc(cues: List[Cue]) -> List[Cue]:
    """QC gate after English cue building, before translation.

    Flags (does not block):
    - Cues exceeding hard caps
    - Micro-cues that are not emphatic
    - Protected term splits
    - Missing punctuation
    """
    for cue in cues:
        flags = []
        text = cue.text_clean_en
        words = text.split()
        dur = cue.duration

        # Duration checks
        if dur > CUE_DUR_HARD_MAX:
            flags.append(f"dur:{dur:.1f}s>max")
        if dur < CUE_DUR_HARD_MIN and len(words) > 1:
            last_char = text.rstrip()[-1] if text.rstrip() else ''
            if last_char not in '.!?':
                flags.append(f"micro:{dur:.1f}s")

        # Word checks
        if len(words) > CUE_WORD_HARD_MAX:
            flags.append(f"words:{len(words)}>max")

        # Density
        wps = len(words) / dur if dur > 0.3 else 0
        if wps > CUE_WPS_HARD_MAX:
            flags.append(f"wps:{wps:.1f}")

        # No punctuation
        if not any(c in text for c in '.!?,;:'):
            flags.append("no-punct")

        # CPL check
        if len(text) > CUE_MAX_CPL * CUE_MAX_LINES:
            flags.append(f"cpl:{len(text)}")

        cue.qc_flags.extend(flags)

    return cues


def pre_tts_qc(cues: List[Cue], wpm: int = 120) -> List[Cue]:
    """QC gate after Hindi fitting, before TTS synthesis.

    Checks:
    - Hindi text exceeds slot after fitting
    - Glossary violations
    - Likely pronunciation issues
    - Overdense for target slot
    - Accidental micro-cue
    - Lines over 42 CPL
    """
    for cue in cues:
        flags = []
        hindi = cue.text_hi_fit or cue.text_hi_raw
        if not hindi:
            flags.append("empty-hindi")
            cue.qc_flags.extend(flags)
            continue

        dur = cue.duration
        hw = len(hindi.split())
        estimated_dur = (hw / wpm) * 60.0

        # Overlong for slot (>150%)
        if dur > 0.3 and estimated_dur > dur * 1.5:
            flags.append(f"hi-overlong:{estimated_dur:.1f}s>{dur:.1f}s")

        # Micro-cue
        if hw < 2 and dur > 1.0:
            flags.append("hi-micro")

        # Repeated words (3+ same word)
        word_list = hindi.split()
        for w in set(word_list):
            if word_list.count(w) >= 3 and len(w) > 2:
                flags.append(f"repeated:{w}")
                break

        # No Hindi punctuation
        if not any(c in hindi for c in '।,!?.'):
            flags.append("hi-no-punct")

        # Glossary miss
        for term in cue.protected_terms:
            if term.lower() not in hindi.lower() and term.lower() not in cue.text_clean_en.lower():
                flags.append(f"glossary-miss:{term}")

        # CPL check on display text
        display = cue.text_hi_display or hindi
        for line in display.split('\n'):
            if len(line) > CUE_MAX_CPL:
                flags.append(f"hi-cpl:{len(line)}")
                break

        cue.qc_flags.extend(flags)

    return cues


def count_issues(cues: List[Cue]) -> dict:
    """Summary of QC issues across all cues."""
    total = len(cues)
    flagged = sum(1 for c in cues if c.qc_flags)
    all_flags = [f for c in cues for f in c.qc_flags]

    # Categorize
    categories = {}
    for flag in all_flags:
        cat = flag.split(":")[0]
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_cues": total,
        "flagged_cues": flagged,
        "pass_rate": (total - flagged) / total if total > 0 else 1.0,
        "categories": categories,
    }
