"""ASR Runner — dual-engine transcription with reconciliation.

Text source:  Parakeet (best punctuation/capitalization)
Timing source: WhisperX (best word-level alignment)
Reconciled:   Parakeet text aligned to WhisperX timing
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Callable
import re

from .contracts import Word


def run_parakeet(wav_path: Path, on_progress: Callable = None) -> List[Word]:
    """Run NVIDIA Parakeet TDT — returns words with timestamps."""
    try:
        import nemo.collections.asr as nemo_asr
        import torch
    except ImportError:
        raise RuntimeError("NeMo not installed: pip install nemo_toolkit[asr]")

    if on_progress:
        on_progress("Loading Parakeet TDT 0.6B...")

    model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v2")
    if torch.cuda.is_available():
        model = model.cuda()

    if on_progress:
        on_progress("Parakeet: transcribing...")

    output = model.transcribe([str(wav_path)], timestamps=True, batch_size=1)

    words: List[Word] = []
    if output:
        hyp = output[0] if isinstance(output, list) else output
        if hasattr(hyp, 'timestep') and hyp.timestep:
            for w in hyp.timestep.get('word', []):
                text = w.get('word', w.get('char', '')).strip()
                if text:
                    words.append(Word(
                        text=text,
                        start=float(w.get('start_offset', 0)),
                        end=float(w.get('end_offset', 0)),
                        source="parakeet",
                        confidence=w.get('score', None),
                    ))
        elif hasattr(hyp, 'text'):
            # Fallback: full text without word timestamps
            text = hyp.text if isinstance(hyp.text, str) else str(hyp)
            if text.strip():
                words.append(Word(text=text.strip(), start=0, end=0, source="parakeet"))

    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return words


def run_whisperx(wav_path: Path, language: str = "en",
                 model_size: str = "large-v3",
                 on_progress: Callable = None) -> List[Word]:
    """Run faster-whisper + WhisperX alignment — returns words with precise timing."""
    from faster_whisper import WhisperModel
    import torch

    device, compute = "cpu", "int8"
    if torch.cuda.is_available():
        device, compute = "cuda", "float16"

    if on_progress:
        on_progress(f"Loading Whisper {model_size} on {device.upper()}...")

    model = WhisperModel(model_size, device=device, compute_type=compute)

    if on_progress:
        on_progress("Whisper: transcribing with VAD...")

    kwargs = {
        "vad_filter": True,
        "word_timestamps": True,
        "beam_size": 1,
        "condition_on_previous_text": True,
        "no_speech_threshold": 0.5,
        "vad_parameters": {"min_silence_duration_ms": 300},
    }
    if language and language != "auto":
        kwargs["language"] = language

    seg_iter, info = model.transcribe(str(wav_path), **kwargs)

    # Collect all words
    words: List[Word] = []
    for seg in seg_iter:
        if hasattr(seg, "words") and seg.words:
            for w in seg.words:
                words.append(Word(
                    text=w.word.strip(),
                    start=float(w.start),
                    end=float(w.end),
                    source="whisperx",
                    confidence=getattr(w, 'probability', None),
                ))
        else:
            # Segment without word timestamps
            words.append(Word(
                text=seg.text.strip(),
                start=float(seg.start),
                end=float(seg.end),
                source="whisperx",
            ))

    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Optional: run WhisperX forced alignment for better timing
    try:
        import whisperx

        if on_progress:
            on_progress("WhisperX: forced alignment...")

        lang = language if language and language != "auto" else "en"
        align_model, metadata = whisperx.load_align_model(
            language_code=lang,
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
        # Build segments for alignment
        segments_for_align = []
        current_seg = {"start": 0, "end": 0, "text": ""}
        for w in words:
            if w.start - current_seg["end"] > 1.0 and current_seg["text"]:
                segments_for_align.append(current_seg)
                current_seg = {"start": w.start, "end": w.end, "text": w.text}
            else:
                if not current_seg["text"]:
                    current_seg["start"] = w.start
                current_seg["text"] += " " + w.text
                current_seg["end"] = w.end
        if current_seg["text"]:
            segments_for_align.append(current_seg)

        result = whisperx.align(
            segments_for_align,
            align_model, metadata,
            whisperx.load_audio(str(wav_path)),
            "cuda" if torch.cuda.is_available() else "cpu",
        )

        # Replace words with aligned versions
        aligned_words = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                aligned_words.append(Word(
                    text=w.get("word", "").strip(),
                    start=float(w.get("start", 0)),
                    end=float(w.get("end", 0)),
                    source="whisperx",
                    confidence=w.get("score", None),
                ))
        if aligned_words:
            words = aligned_words

        del align_model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    except ImportError:
        pass  # WhisperX not installed, use faster-whisper timing

    return words


def reconcile(parakeet_words: List[Word], whisperx_words: List[Word]) -> List[Word]:
    """Reconcile two ASR outputs: Parakeet text + WhisperX timing.

    Rules:
    - Use Parakeet text (better punctuation/capitalization)
    - Use WhisperX timing (better word-level alignment)
    - If disagreement is large, flag for repair
    - Align by time overlap between words
    """
    if not parakeet_words:
        return whisperx_words
    if not whisperx_words:
        return parakeet_words

    # Build time-indexed lookup from WhisperX
    reconciled: List[Word] = []

    # Simple approach: for each Parakeet word, find closest WhisperX word by time
    wx_idx = 0
    for pw in parakeet_words:
        # Find WhisperX word with best time overlap
        best_wx = None
        best_overlap = -1

        search_start = max(0, wx_idx - 3)
        search_end = min(len(whisperx_words), wx_idx + 10)

        for i in range(search_start, search_end):
            wx = whisperx_words[i]
            overlap_start = max(pw.start, wx.start)
            overlap_end = min(pw.end, wx.end)
            overlap = max(0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_wx = wx
                wx_idx = i

        if best_wx and best_overlap > 0:
            # Use Parakeet text, WhisperX timing
            reconciled.append(Word(
                text=pw.text,
                start=best_wx.start,
                end=best_wx.end,
                source="reconciled",
                speaker=best_wx.speaker or pw.speaker,
                confidence=pw.confidence,
                protected=pw.protected,
                term_id=pw.term_id,
            ))
        else:
            # No match — use Parakeet as-is
            reconciled.append(Word(
                text=pw.text,
                start=pw.start,
                end=pw.end,
                source="parakeet",
                speaker=pw.speaker,
                confidence=pw.confidence,
            ))

    return reconciled


def normalize_words(words: List[Word]) -> List[Word]:
    """Clean up word list: strip junk, normalize whitespace, fix apostrophes."""
    cleaned = []
    for w in words:
        text = w.text.strip()
        if not text:
            continue
        # Normalize apostrophes
        text = text.replace('\u2019', "'").replace('\u2018', "'")
        # Strip non-speech garbage
        text = re.sub(r'^\[.*\]$', '', text).strip()
        text = re.sub(r'^\(.*\)$', '', text).strip()
        text = re.sub(r'^♪.*♪$', '', text).strip()
        if not text:
            continue
        w.text = text
        cleaned.append(w)
    return cleaned
