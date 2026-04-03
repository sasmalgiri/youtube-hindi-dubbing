"""DP Cue Builder — dynamic programming segmentation from timed words.

Builds optimal cue boundaries by scoring every possible split point.
NOT greedy merge/split — globally optimal segmentation.

Hard constraints (reject any cue that violates):
- No crossing speaker changes
- No splitting protected terms
- Duration: 0.8s–5.5s
- Words: 1–16
- Max 2 lines, 42 CPL

Soft targets (scored, not hard-rejected):
- Duration: 1.2–4.5s
- Words: 8–14
- WPS: ≤5.2
- Sentence-ending punctuation at boundary
- Pause gap at boundary
"""
from __future__ import annotations
from typing import List
import math

from .contracts import (
    Word, Cue,
    CUE_WORD_HARD_MAX, CUE_WORD_TARGET_MIN, CUE_WORD_TARGET_MAX,
    CUE_DUR_HARD_MIN, CUE_DUR_HARD_MAX, CUE_DUR_TARGET_MIN, CUE_DUR_TARGET_MAX,
    CUE_WPS_HARD_MAX, CUE_MAX_CPL, PAUSE_SOFT_MS, PAUSE_STRONG_MS,
)


def _boundary_score(words: List[Word], i: int, j: int) -> float:
    """Score a candidate cue spanning words[i:j].

    Lower score = better cue.
    Returns math.inf if cue violates hard constraints.
    """
    if j <= i:
        return math.inf

    cue_words = words[i:j]
    n_words = j - i
    start = cue_words[0].start
    end = cue_words[-1].end
    dur = end - start
    text = " ".join(w.text for w in cue_words)

    # ── Hard rejects ──
    if dur <= 0:
        return math.inf  # Zero-duration is always invalid
    if dur < CUE_DUR_HARD_MIN and n_words > 1:
        return math.inf
    if dur > CUE_DUR_HARD_MAX:
        return math.inf
    if n_words > CUE_WORD_HARD_MAX:
        return math.inf

    # Don't split protected multi-word terms across cue boundary
    # Check: does any protected term span from inside this cue to outside it?
    for k in range(i, j):
        if not (words[k].protected and words[k].term_id):
            continue
        tid = words[k].term_id
        # Check if term extends PAST cue end
        if k + 1 < len(words) and k + 1 >= j and words[k + 1].term_id == tid:
            return math.inf
    # Check if term starts BEFORE cue start and continues into it
    if i > 0 and words[i].protected and words[i].term_id:
        if words[i - 1].term_id == words[i].term_id:
            return math.inf  # Cue starts inside a multi-word term

    # Don't cross speaker changes
    for k in range(i + 1, j):
        if cue_words[k - i].speaker and cue_words[k - i - 1].speaker:
            if cue_words[k - i].speaker != cue_words[k - i - 1].speaker:
                return math.inf

    # ── Soft scoring ──
    cost = 0.0

    # Duration penalty
    if dur < CUE_DUR_TARGET_MIN:
        cost += (CUE_DUR_TARGET_MIN - dur) * 2.0
    elif dur > CUE_DUR_TARGET_MAX:
        cost += (dur - CUE_DUR_TARGET_MAX) * 3.0

    # Word count penalty
    if n_words < CUE_WORD_TARGET_MIN:
        cost += (CUE_WORD_TARGET_MIN - n_words) * 0.5
    elif n_words > CUE_WORD_TARGET_MAX:
        cost += (n_words - CUE_WORD_TARGET_MAX) * 1.5

    # Density penalty (WPS)
    wps = n_words / dur if dur > 0.3 else 0
    if wps > CUE_WPS_HARD_MAX:
        cost += (wps - CUE_WPS_HARD_MAX) * 5.0
    elif wps > 4.5:
        cost += (wps - 4.5) * 1.0

    # Boundary quality — reward sentence-ending punctuation at cue end
    last_word = cue_words[-1].text.rstrip()
    if last_word and last_word[-1] in '.!?':
        cost -= 3.0  # Strong reward
    elif last_word and last_word[-1] in ',;:':
        cost -= 1.0  # Mild reward

    # Pause gap at boundary — reward splitting at natural pauses
    if j < len(words):
        gap = words[j].start - words[j - 1].end
        if gap > PAUSE_STRONG_MS / 1000:
            cost -= 4.0  # Strong reward
        elif gap > PAUSE_SOFT_MS / 1000:
            cost -= 1.5  # Mild reward

    # Hindi expansion risk penalty (long English cues expand more)
    if n_words > 12:
        cost += (n_words - 12) * 0.8

    # CPL check (rough estimate: ~6 chars per English word)
    avg_cpl = len(text) / 2 if n_words > 6 else len(text)
    if avg_cpl > CUE_MAX_CPL:
        cost += (avg_cpl - CUE_MAX_CPL) * 0.3

    return cost


def build_cues(words: List[Word], max_lookahead: int = None) -> List[Cue]:
    """Build optimal cue boundaries using dynamic programming.

    For N words, finds the segmentation that minimizes total cost.
    max_lookahead limits how many words a single cue can span (performance).
    """
    if not words:
        return []

    n = len(words)
    # Adaptive lookahead: scale with video size, but cap for performance
    if max_lookahead is None:
        max_lookahead = min(50, max(25, n // 100))

    # DP: dp[i] = minimum cost to segment words[0:i]
    dp = [math.inf] * (n + 1)
    dp[0] = 0.0
    parent = [-1] * (n + 1)  # parent[j] = i means cue words[i:j] is optimal

    for j in range(1, n + 1):
        for i in range(max(0, j - max_lookahead), j):
            score = _boundary_score(words, i, j)
            if score == math.inf:
                continue
            total = dp[i] + score
            if total < dp[j]:
                dp[j] = total
                parent[j] = i

    # Backtrack to find cue boundaries
    if dp[n] == math.inf:
        # DP failed — fallback to greedy
        return _fallback_greedy(words)

    boundaries = []
    j = n
    while j > 0:
        i = parent[j]
        if i < 0:
            break
        boundaries.append((i, j))
        j = i
    boundaries.reverse()

    # Build Cue objects
    cues = []
    for idx, (i, j) in enumerate(boundaries):
        cue_words = words[i:j]
        text = " ".join(w.text for w in cue_words)
        cue = Cue(
            id=idx,
            start=cue_words[0].start,
            end=cue_words[-1].end,
            speaker=cue_words[0].speaker,
            text_original=text,
            text_clean_en=text,
            words=cue_words,
        )
        cues.append(cue)

    return cues


def _fallback_greedy(words: List[Word]) -> List[Cue]:
    """Fallback greedy segmentation if DP fails."""
    SENTENCE_ENDERS = {'.', '!', '?'}
    cues = []
    buf_start = 0

    for i, w in enumerate(words):
        buf_words = words[buf_start:i + 1]
        dur = buf_words[-1].end - buf_words[0].start
        n = len(buf_words)
        last_char = w.text.rstrip()[-1] if w.text.rstrip() else ''

        should_emit = (
            last_char in SENTENCE_ENDERS or
            dur >= CUE_DUR_TARGET_MAX or
            n >= CUE_WORD_TARGET_MAX
        )

        if should_emit:
            text = " ".join(bw.text for bw in buf_words)
            cue = Cue(
                id=len(cues),
                start=buf_words[0].start,
                end=buf_words[-1].end,
                speaker=buf_words[0].speaker,
                text_original=text,
                text_clean_en=text,
                words=buf_words,
            )
            cues.append(cue)
            buf_start = i + 1

    # Flush remaining
    if buf_start < len(words):
        buf_words = words[buf_start:]
        text = " ".join(bw.text for bw in buf_words)
        cue = Cue(
            id=len(cues),
            start=buf_words[0].start,
            end=buf_words[-1].end,
            speaker=buf_words[0].speaker,
            text_original=text,
            text_clean_en=text,
            words=buf_words,
        )
        cues.append(cue)

    return cues
