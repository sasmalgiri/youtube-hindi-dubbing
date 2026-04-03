"""Hindi Fitting — dub-fit rewrite ONLY.

Takes text_hi_raw and produces text_hi_fit.
Formatting (line breaks) is in format_hi.py — runs AFTER this.

Rules:
- Spoken Hindi only, not written
- Compress only when needed
- Preserve meaning before elegance
- Preserve emotional force
- Remove literal English syntax carryover
- Keep TTS-safe phrasing
- Never change timing — change wording
"""
from __future__ import annotations
import re
from typing import List

from .contracts import Cue, GlossaryTerm

HINDI_WPM = 120

FORMAL_TO_SPOKEN = {
    "किन्तु": "लेकिन", "परन्तु": "लेकिन", "परंतु": "लेकिन",
    "अतः": "इसलिए", "एवं": "और", "अथवा": "या", "तथा": "और",
    "यद्यपि": "भले ही", "तथापि": "फिर भी",
    "आवश्यकता": "ज़रूरत", "आवश्यक": "ज़रूरी",
    "सम्पूर्ण": "पूरा", "संपूर्ण": "पूरा",
    "प्रारम्भ": "शुरू", "प्रारंभ": "शुरू", "समाप्त": "खत्म",
    "वर्ष": "साल", "वर्षों": "सालों",
    "मानवता": "इंसानों", "व्यक्ति": "इंसान",
    "यदि": "अगर", "कृपया": "प्लीज़",
    "के द्वारा": "से", "के माध्यम से": "से",
    "वर्तमान में": "अभी", "इसके पश्चात": "इसके बाद",
    "निश्चित रूप से": "बिल्कुल", "विशेष रूप से": "खासकर",
    "उपयोग": "इस्तेमाल", "कठिन": "मुश्किल",
    "शीघ्र": "जल्दी", "अवश्य": "ज़रूर",
}

# ── Length-based synonym substitutions (long → short, meaning preserved) ──
# Used when text is too long for the time slot.
# Sorted by character savings at application time.
LONG_TO_SHORT = {
    # Formal/long → natural/short (safe always)
    "आवश्यकता": "ज़रूरत",
    "प्रतीक्षा": "इंतज़ार",
    "सुरक्षित": "सेफ",
    "जानकारी": "खबर",
    "इस्तेमाल": "यूज़",
    "ज़िम्मेदारी": "duty",
    "ज़िम्मेदार": "responsible",
    "अस्पताल": "hospital",
    "खतरनाक": "ख़तरा",
    "परेशान": "टेंशन में",
    "महत्वपूर्ण": "ज़रूरी",
    "अलौकिक": "magical",
    "कर रहा था": "कर रहा",
    "हो रहा था": "हो रहा",
    "चल रहा था": "चल रहा",
    "कर रही थी": "कर रही",
    "हो रही थी": "हो रही",
    "चल रही थी": "चल रही",
    "के अंदर": "में",
    "के ऊपर": "पे",
    "की तरफ": "ओर",
    "के सामने": "आगे",
    "के पीछे": "पीछे",
    "के बारे में": "बारे",
    "की वजह से": "से",
    "के कारण": "से",
    "इसलिए": "तो",
    "लेकिन": "पर",
    "हालांकि": "पर",
    "इसके बाद": "फिर",
    "उसके बाद": "फिर",
    "अचानक से": "अचानक",
    "तुरंत ही": "तुरंत",
    "बिल्कुल भी नहीं": "बिल्कुल नी",
    "कुछ भी नहीं": "कुछ नी",
    "एक दम से": "एकदम",
    "बहुत ज़्यादा": "बहुत",
    "काफी ज़्यादा": "काफी",
    "सच में": "सच",
    "वास्तव में": "असल में",
    "विश्वास नहीं हो रहा": "यकीन नी हो रहा",
    "समझ में नहीं आया": "समझ नी आया",
    "कह रहा था": "बोल रहा",
    "कह रही थी": "बोल रही",
    "बता रहा था": "बोल रहा",
    "देख रहा था": "देख रहा",
    "देख रही थी": "देख रही",
    "सोच रहा था": "सोच रहा",
    "सोच रही थी": "सोच रही",
}


def fit_cues(cues: List[Cue], glossary: List[GlossaryTerm] = None) -> List[Cue]:
    """Apply dub-fit rewrite to all cues. Does NOT format lines.

    Order:
    1. Formal → spoken (skip glossary-locked terms)
    2. Punctuation normalization for TTS
    3. Duration-aware compression (only when needed)
    """
    protected_set = set()
    if glossary:
        for t in glossary:
            protected_set.add(t.canonical)
            if t.target_spelling:
                protected_set.add(t.target_spelling)

    for cue in cues:
        hindi = cue.text_hi_raw
        if not hindi:
            cue.text_hi_fit = ""
            continue

        # 1. Formal → spoken (protect glossary terms, use word boundaries)
        # Sort by length desc to replace longer phrases first ("के माध्यम से" before "के")
        for formal, spoken in sorted(FORMAL_TO_SPOKEN.items(), key=lambda x: len(x[0]), reverse=True):
            if formal in protected_set:
                continue
            # Use space-bounded matching to avoid partial word replacement
            # Hindi doesn't have strict word boundaries, so match with space/start/end
            hindi = re.sub(r'(?<![ँ-ॿ])' + re.escape(formal) + r'(?![ँ-ॿ])', spoken, hindi)
            # Fallback: exact multi-word phrase match (for phrases with spaces)
            if ' ' in formal:
                hindi = hindi.replace(formal, spoken)

        # 2. Punctuation normalization
        hindi = normalize_punctuation(hindi)

        # 3. Duration-aware compression (with protected term awareness)
        hindi = compress_if_needed(hindi, cue.duration, protected_set)

        cue.text_hi_fit = hindi

    return cues


def normalize_punctuation(text: str) -> str:
    """Normalize Hindi punctuation for natural TTS speech."""
    text = text.replace("।।", "।").replace("।.", "।")
    text = re.sub(r'(?<=[ँ-ॿ])\.(?=\s|$)', '।', text)
    text = re.sub(r'[,]{2,}', ',', text)
    text = re.sub(r'[।]{2,}', '।', text)
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r',\s*([।!?])', r'\1', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s+([।!?,])', r'\1', text)
    return text.strip()


def shorten_by_substitution(text: str, target_words: int, protected: set = None) -> str:
    """Shorten Hindi text by substituting long words/phrases with shorter equivalents.

    Priority order (preserves meaning):
    1. Apply LONG_TO_SHORT synonym substitutions (biggest savings first)
    2. Remove filler words
    3. Remove shortest non-essential clause (between commas, no protected terms)
    4. NEVER hard-truncate mid-thought — return best attempt if still over target
    """
    if not text or len(text.split()) <= target_words:
        return text

    protected = protected or set()

    # 1. Apply LONG_TO_SHORT substitutions, sorted by character savings (largest first)
    subs = sorted(LONG_TO_SHORT.items(), key=lambda x: len(x[0]) - len(x[1]), reverse=True)
    for long_form, short_form in subs:
        if len(text.split()) <= target_words:
            break
        if long_form in protected or short_form in protected:
            continue
        if long_form in text:
            text = text.replace(long_form, short_form, 1)
            text = re.sub(r'\s{2,}', ' ', text).strip()

    if len(text.split()) <= target_words:
        return text

    # 2. Remove filler words
    fillers = ["बस ", "तो ", "ना ", "जो कि ", "असल में ", "और साथ में ",
               "और साथ ही ", "इसके अलावा ", "जिससे कि ", "ताकि "]
    for filler in fillers:
        if len(text.split()) <= target_words:
            break
        text = text.replace(filler, "", 1)
    text = re.sub(r'\s{2,}', ' ', text).strip()

    if len(text.split()) <= target_words:
        return text

    # 3. Remove shortest non-essential clause (between commas/purna viram)
    # Prefer removing from the end, skip clauses with protected terms
    for sep in (',', '।'):
        parts = text.split(sep)
        if len(parts) < 2:
            continue
        # Find shortest non-protected clause from the end
        best_idx = -1
        best_len = float('inf')
        for pi in range(len(parts) - 1, 0, -1):  # skip first clause
            clause = parts[pi].strip()
            clause_words = clause.split()
            if not clause_words:
                continue
            has_protected = any(p in clause for p in protected)
            if not has_protected and len(clause_words) < best_len:
                best_len = len(clause_words)
                best_idx = pi
        if best_idx > 0:
            parts.pop(best_idx)
            text = sep.join(parts).strip()
            text = re.sub(r'\s{2,}', ' ', text).strip()
            # Ensure proper ending
            if text and text[-1] not in '।!?,':
                text = text + '।'
            if len(text.split()) <= target_words:
                return text

    # 4. NEVER hard-truncate — return best attempt
    return text.strip()


def compress_if_needed(text: str, slot_duration: float, protected: set = None) -> str:
    """Compress Hindi text via word substitution ONLY if it doesn't fit the slot.

    Uses shorten_by_substitution() instead of hard truncation.
    """
    if slot_duration <= 0.3:
        return text

    words = text.split()
    estimated_dur = (len(words) / HINDI_WPM) * 60.0

    if estimated_dur <= slot_duration * 1.25:
        return text

    target_words = max(3, int((slot_duration * 1.25 / 60.0) * HINDI_WPM))
    return shorten_by_substitution(text, target_words, protected)
