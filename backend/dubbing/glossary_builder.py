"""Glossary Builder — OFFLINE term extraction (not runtime).

Run this to build/update glossary files. NOT called during normal pipeline runs.
Runtime only loads pre-built glossaries via glossary.py.
"""
from __future__ import annotations
import re
import json
from pathlib import Path
from typing import List, Dict
from collections import Counter

from .contracts import Word, GlossaryTerm


def extract_terms_from_words(words: List[Word]) -> List[GlossaryTerm]:
    """Auto-extract candidate terms from a word stream.

    Returns candidates for human review — not automatically locked.
    """
    if not words:
        return []

    all_text = " ".join(w.text for w in words)
    terms: Dict[str, GlossaryTerm] = {}

    # Capitalized multi-word phrases
    for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', all_text):
        name = match.group(1)
        if name not in terms:
            terms[name] = GlossaryTerm(canonical=name, action="keep")

    # Rank patterns
    for match in re.finditer(r'\b([A-Z]{1,2}[-\s]?(?:rank|class|tier|level)(?:ed)?)\b', all_text, re.IGNORECASE):
        rank = match.group(1)
        if rank not in terms:
            terms[rank] = GlossaryTerm(canonical=rank, action="keep")

    # Repeated proper nouns (3+ times)
    word_texts = [w.text for w in words if len(w.text) > 2 and w.text[0].isupper() and not w.text.isupper()]
    for word, count in Counter(word_texts).items():
        if count >= 3 and word not in terms:
            terms[word] = GlossaryTerm(canonical=word, action="keep")

    return list(terms.values())


def save_glossary(terms: List[GlossaryTerm], path: Path):
    """Save glossary to JSON file."""
    data = []
    for t in terms:
        data.append({
            "canonical": t.canonical,
            "aliases": t.aliases,
            "source_spelling": t.source_spelling,
            "target_spelling": t.target_spelling,
            "action": t.action,
            "pronunciation": t.pronunciation,
        })
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# load_glossary() is in glossary.py (runtime only)
# Do NOT duplicate it here — this module is offline-only
