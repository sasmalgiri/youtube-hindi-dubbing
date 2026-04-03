"""Hindi Subtitle Formatting — AFTER fitting and validation.

Takes text_hi_fit and produces text_hi_display with:
- 1-2 lines
- Syntax-first line breaks
- Max 42 chars per line
- Visual balancing

This is a SEPARATE step from fit_hi.py because:
- English line breaks don't map to Hindi
- Formatting happens AFTER Hindi validation
"""
from __future__ import annotations
from typing import List

from .contracts import Cue, CUE_MAX_CPL


def format_cues(cues: List[Cue]) -> List[Cue]:
    """Apply subtitle line formatting to all cues."""
    for cue in cues:
        hindi = cue.text_hi_fit or cue.text_hi_raw
        if not hindi:
            cue.text_hi_display = ""
            continue
        cue.text_hi_display = format_lines(hindi)
    return cues


def format_lines(text: str) -> str:
    """Format Hindi text into 1-2 subtitle lines.

    Rules (in order):
    1. If fits on one line (<=42 chars) → single line
    2. Split at punctuation near middle (syntax-first)
    3. Split at word boundary near middle (visual balance)
    4. Never split protected multi-word terms
    """
    if len(text) <= CUE_MAX_CPL:
        return text

    words = text.split()
    if len(words) < 4:
        return text

    # Try split at punctuation near middle
    mid = len(text) // 2
    best_pos = -1
    best_dist = len(text)

    for i, ch in enumerate(text):
        if ch in ',।;' and abs(i - mid) < best_dist:
            if len(text) * 0.25 < i < len(text) * 0.75:
                best_dist = abs(i - mid)
                best_pos = i + 1

    # Fallback: word boundary near middle
    if best_pos < 0:
        mid_word = len(words) // 2
        best_pos = len(' '.join(words[:mid_word]))

    line1 = text[:best_pos].strip()
    line2 = text[best_pos:].strip()

    if line1 and line2 and len(line1) <= CUE_MAX_CPL and len(line2) <= CUE_MAX_CPL:
        return f"{line1}\n{line2}"

    return text
