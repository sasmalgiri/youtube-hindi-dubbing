"""Glossary — RUNTIME ONLY: load, tag, lock, validate.

Term extraction is in glossary_builder.py (offline).
This module only:
1. Loads pre-built glossary
2. Tags words (before cue building)
3. Tags cues (before translation)
4. Validates Hindi (after fitting)
"""
from __future__ import annotations
from typing import List, Dict
from pathlib import Path
import json

from .contracts import Word, Cue, GlossaryTerm


def load_glossary(path: Path) -> List[GlossaryTerm]:
    """Load glossary from JSON file."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [GlossaryTerm(
            canonical=d.get("canonical", ""),
            aliases=d.get("aliases", []),
            source_spelling=d.get("source_spelling", ""),
            target_spelling=d.get("target_spelling", ""),
            action=d.get("action", "keep"),
            pronunciation=d.get("pronunciation", ""),
        ) for d in data]
    except Exception:
        return []


def tag_words(words: List[Word], glossary: List[GlossaryTerm]) -> List[Word]:
    """Tag words that are part of glossary terms as protected.

    Runs BEFORE cue building so the DP segmenter won't split inside terms.
    """
    term_words: Dict[str, str] = {}
    for term in glossary:
        for w in term.canonical.split():
            term_words[w.lower()] = term.canonical
        for alias in term.aliases:
            for w in alias.split():
                term_words[w.lower()] = term.canonical

    for word in words:
        if word.text.lower() in term_words:
            word.protected = True
            word.term_id = term_words[word.text.lower()]

    return words


def tag_cues(cues: List[Cue], glossary: List[GlossaryTerm]) -> List[Cue]:
    """Tag cues with protected terms + pronunciation overrides.

    Runs BEFORE translation so the translator knows what to lock.
    """
    for cue in cues:
        text_lower = cue.text_clean_en.lower()
        found = []
        for term in glossary:
            if term.canonical.lower() in text_lower:
                found.append(term.canonical)
                if term.pronunciation:
                    cue.pronunciation_overrides[term.target_spelling or term.canonical] = term.pronunciation
        cue.protected_terms = found

    return cues


def validate_hindi(cues: List[Cue], glossary: List[GlossaryTerm]) -> List[Cue]:
    """After Hindi fitting: check terms survived, restore drift, attach pronunciation."""
    for cue in cues:
        hindi = cue.text_hi_fit or cue.text_hi_raw
        if not hindi:
            continue

        for term in glossary:
            if term.canonical.lower() not in cue.text_clean_en.lower():
                continue

            if term.action == "keep" and term.canonical.lower() not in hindi.lower():
                cue.qc_flags.append(f"glossary-miss:{term.canonical}")
            elif term.action == "fixed_translation" and term.target_spelling:
                if term.target_spelling not in hindi:
                    cue.qc_flags.append(f"glossary-drift:{term.canonical}")

            if term.pronunciation:
                key = term.target_spelling or term.canonical
                cue.pronunciation_overrides[key] = term.pronunciation

    return cues
