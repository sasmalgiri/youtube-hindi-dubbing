"""
Supabase secondary write-through store for YouTube Hindi Dubbing.

Architecture
------------
- SQLite (jobstore.py) remains the PRIMARY store and source-of-truth.
  load_all() always reads from SQLite on startup.
- Supabase is a SECONDARY store: every save/delete is replicated to
  Supabase in a background daemon thread so the pipeline is NEVER blocked.
- If SUPABASE_URL / SUPABASE_SERVICE_KEY are not set, SupabaseStore
  silently no-ops — the app works fine without Supabase configured.

Usage (see app.py)
------------------
    from supabase_store import SupabaseStore, DualStore
    _store = DualStore(JobStore(BASE_DIR / "jobs.db"), SupabaseStore())
    _store.load_all(JOBS)   # reads from SQLite (primary)
    _store.save(job)        # writes SQLite + Supabase (background)
    _store.delete(job_id)   # deletes from both
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from app import Job
    from jobstore import JobStore

# ── Lazy Supabase client (singleton, created on first use) ────────────────────

_client = None
_client_lock = threading.Lock()


def _get_client():
    """Return a Supabase client, or None if env vars are not set."""
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        url = os.environ.get("SUPABASE_URL", "").strip()
        # Accept either SUPABASE_SERVICE_KEY (preferred) or SUPABASE_KEY
        key = (os.environ.get("SUPABASE_SERVICE_KEY", "")
               or os.environ.get("SUPABASE_KEY", "")).strip()
        if not url or not key:
            return None
        try:
            from supabase import create_client
            _client = create_client(url, key)
            print(f"[Supabase] Connected to {url}", flush=True)
        except Exception as e:
            print(f"[Supabase] Could not connect: {e}", flush=True)
            _client = None
    return _client


# ── Serialisers ───────────────────────────────────────────────────────────────

def _tts_engine_label(req) -> str:
    if not req:
        return "edge"
    if getattr(req, "use_chatterbox", False):  return "chatterbox"
    if getattr(req, "use_elevenlabs", False):   return "elevenlabs"
    if getattr(req, "use_cosyvoice", False):    return "cosyvoice"
    if getattr(req, "use_google_tts", False):   return "google"
    if getattr(req, "use_coqui_xtts", False):   return "coqui_xtts"
    return "edge"


def _job_to_row(job: "Job") -> dict:
    """Serialise a Job dataclass to a Supabase `jobs` row dict."""
    from jobstore import _job_to_dict  # reuse existing serialiser for payload

    req = job.original_req

    # Build payload — same JSON blob jobstore.py writes to SQLite
    try:
        payload = _job_to_dict(job)
    except Exception:
        payload = {}

    return {
        "id":                job.id,
        "state":             job.state,
        "source_url":        job.source_url or "",
        "video_title":       job.video_title or "",
        "target_language":   job.target_language or "hi",
        "source_language":   getattr(req, "source_language", "auto") if req else "auto",

        # Progress
        "current_step":      job.current_step or "",
        "step_progress":     round(job.step_progress, 4),
        "overall_progress":  round(job.overall_progress, 4),
        "message":           job.message or "",
        "error":             job.error,

        # Output paths
        "result_path":       str(job.result_path) if job.result_path else None,
        "saved_folder":      job.saved_folder,
        "saved_video":       job.saved_video,

        # Config (denormalised for easy Supabase queries / dashboards)
        "asr_model":         getattr(req, "asr_model", "large-v3")    if req else "large-v3",
        "translation_engine":getattr(req, "translation_engine", "auto") if req else "auto",
        "tts_engine":        _tts_engine_label(req),
        "audio_bitrate":     getattr(req, "audio_bitrate", "192k")    if req else "192k",
        "encode_preset":     getattr(req, "encode_preset", "veryfast") if req else "veryfast",
        "use_whisperx":      getattr(req, "use_whisperx", False)       if req else False,
        "fast_assemble":     getattr(req, "fast_assemble", True)       if req else True,
        "multi_speaker":     getattr(req, "multi_speaker", False)      if req else False,
        "split_duration":    getattr(req, "split_duration", 0)         if req else 0,
        "dub_duration":      getattr(req, "dub_duration", 0)           if req else 0,

        # Quality / chain
        "qa_score":          job.qa_score,
        "chain_languages":   job.chain_languages or [],
        "chain_parent_id":   job.chain_parent_id,

        # Full original request (for replay / resume)
        "original_req":      payload.get("original_req"),

        # Full serialised Job (mirrors SQLite payload — includes segments list)
        "payload":           payload,

        # Extra
        "description":       job.description,
        "created_at":        job.created_at,
        "updated_at":        time.time(),
    }


def _job_to_segment_rows(job: "Job") -> list:
    """Convert job.segments to a list of `job_segments` row dicts."""
    rows = []
    for i, seg in enumerate(job.segments or []):
        start = float(seg.get("start", 0))
        end   = float(seg.get("end", 0))
        orig_dur = end - start
        dub_dur  = seg.get("dubbed_duration")
        rows.append({
            "job_id":          job.id,
            "segment_index":   i,
            "start_time":      round(start, 3),
            "end_time":        round(end, 3),
            "source_text":     seg.get("text", ""),
            "translated_text": seg.get("text_translated", ""),
            "speaker_id":      seg.get("speaker_id"),
            "tts_engine_used": seg.get("tts_engine"),
            "duration_ratio":  round(dub_dur / orig_dur, 3)
                               if dub_dur and orig_dur > 0 else None,
            "qa_passed":       seg.get("qa_passed"),
        })
    return rows


# ── SupabaseStore ─────────────────────────────────────────────────────────────

class SupabaseStore:
    """
    Fire-and-forget secondary Supabase writer.
    All network calls run in daemon threads — they never block the pipeline.
    """

    def save(self, job: "Job") -> None:
        """Upsert job row (and segments if done) to Supabase in background."""
        try:
            row = _job_to_row(job)
        except Exception as e:
            print(f"[Supabase] Serialisation error for job {job.id}: {e}", flush=True)
            return

        # Only write segments when job is complete and segments exist
        write_segments = (
            job.state == "done"
            and bool(job.segments)
        )
        seg_rows = _job_to_segment_rows(job) if write_segments else []

        def _write():
            client = _get_client()
            if not client:
                return
            try:
                client.table("jobs").upsert(row, on_conflict="id").execute()
                if seg_rows:
                    # Replace all segments atomically
                    client.table("job_segments").delete().eq("job_id", job.id).execute()
                    # Insert in batches of 100 to avoid request size limits
                    for batch_start in range(0, len(seg_rows), 100):
                        client.table("job_segments").insert(
                            seg_rows[batch_start:batch_start + 100]
                        ).execute()
            except Exception as e:
                print(f"[Supabase] Write error for job {job.id}: {e}", flush=True)

        threading.Thread(target=_write, daemon=True, name=f"supa-{job.id[:8]}").start()

    def delete(self, job_id: str) -> None:
        """Delete job (and its segments via FK cascade) from Supabase in background."""
        def _delete():
            client = _get_client()
            if not client:
                return
            try:
                client.table("jobs").delete().eq("id", job_id).execute()
                # job_segments cascade via ON DELETE CASCADE in schema
            except Exception as e:
                print(f"[Supabase] Delete error for job {job_id}: {e}", flush=True)

        threading.Thread(target=_delete, daemon=True, name=f"supa-del-{job_id[:8]}").start()

    def load_all(self, jobs_dict: Dict[str, Any]) -> int:
        """No-op: SQLite is the source of truth on startup."""
        return 0

    def close(self) -> None:
        """No-op: Supabase client has no persistent connection to close."""
        pass


# ── DualStore ─────────────────────────────────────────────────────────────────

class DualStore:
    """
    Drop-in replacement for JobStore that writes to BOTH SQLite and Supabase.

    - load_all() reads from SQLite only (primary / source of truth)
    - save()     writes SQLite first (blocking), then Supabase (background)
    - delete()   deletes from SQLite first (blocking), then Supabase (background)
    - close()    closes SQLite connection

    Usage in app.py:
        from supabase_store import SupabaseStore, DualStore
        _store = DualStore(JobStore(BASE_DIR / "jobs.db"), SupabaseStore())
        _store.load_all(JOBS)
    """

    def __init__(self, primary: "JobStore", secondary: SupabaseStore):
        self._primary   = primary
        self._secondary = secondary

    def load_all(self, jobs_dict: Dict[str, Any]) -> int:
        """Load jobs from SQLite (primary). Supabase is not read on startup."""
        return self._primary.load_all(jobs_dict)

    def save(self, job: "Job") -> None:
        """Write to SQLite (blocking) then Supabase (background thread)."""
        self._primary.save(job)
        self._secondary.save(job)

    def delete(self, job_id: str) -> None:
        """Delete from SQLite (blocking) then Supabase (background thread)."""
        self._primary.delete(job_id)
        self._secondary.delete(job_id)

    def close(self) -> None:
        """Close SQLite connection."""
        self._primary.close()
        self._secondary.close()
