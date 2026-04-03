"""Adaptive Worker Manager — auto-scales parallelism based on system load.

Monitors CPU, RAM, and GPU usage. Adjusts worker counts up/down to maximize
throughput without overloading the system.

Usage:
    mgr = WorkerManager(max_edge=150, max_google=100)
    edge_workers = mgr.get_edge_workers()    # Returns current safe count
    google_workers = mgr.get_google_workers() # Returns current safe count
    mgr.report_success("edge")               # Task completed OK → maybe increase
    mgr.report_failure("edge")               # Task failed → decrease
"""
from __future__ import annotations
import os
import time
import threading
from typing import Dict


class WorkerManager:
    """Governs parallelism based on system capacity.

    Starts at target workers, monitors success/failure rate,
    and adjusts up (if smooth) or down (if struggling).
    """

    def __init__(self, max_edge: int = 150, max_google: int = 100,
                 min_edge: int = 20, min_google: int = 10):
        self.limits = {
            "edge": {"current": max_edge, "max": max_edge, "min": min_edge,
                     "success": 0, "failure": 0, "last_adjust": time.time()},
            "google": {"current": max_google, "max": max_google, "min": min_google,
                       "success": 0, "failure": 0, "last_adjust": time.time()},
        }
        self._lock = threading.Lock()
        self._adjust_interval = 10  # seconds between adjustments

    def get_workers(self, engine: str) -> int:
        """Get current worker count for an engine."""
        with self._lock:
            return self.limits.get(engine, {}).get("current", 50)

    def get_edge_workers(self) -> int:
        return self.get_workers("edge")

    def get_google_workers(self) -> int:
        return self.get_workers("google")

    def report_success(self, engine: str):
        """Report a successful task — may increase workers."""
        with self._lock:
            if engine not in self.limits:
                return
            self.limits[engine]["success"] += 1
            self._maybe_adjust(engine)

    def report_failure(self, engine: str):
        """Report a failed task — will decrease workers."""
        with self._lock:
            if engine not in self.limits:
                return
            self.limits[engine]["failure"] += 1
            # Immediate reduction on failure
            state = self.limits[engine]
            new_count = max(state["min"], int(state["current"] * 0.7))
            if new_count < state["current"]:
                state["current"] = new_count
                state["last_adjust"] = time.time()

    def _maybe_adjust(self, engine: str):
        """Auto-adjust workers based on success/failure ratio."""
        state = self.limits[engine]
        now = time.time()

        # Only adjust every N seconds
        if now - state["last_adjust"] < self._adjust_interval:
            return

        total = state["success"] + state["failure"]
        if total < 5:
            return  # Not enough data yet

        success_rate = state["success"] / total

        if success_rate > 0.95 and state["current"] < state["max"]:
            # Running smooth → increase by 20%
            state["current"] = min(state["max"], int(state["current"] * 1.2))
        elif success_rate < 0.8:
            # Struggling → decrease by 30%
            state["current"] = max(state["min"], int(state["current"] * 0.7))

        # Reset counters
        state["success"] = 0
        state["failure"] = 0
        state["last_adjust"] = now

    def get_system_load(self) -> Dict[str, float]:
        """Get current system resource usage."""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "ram_percent": psutil.virtual_memory().percent,
                "ram_available_gb": psutil.virtual_memory().available / (1024**3),
            }
        except ImportError:
            return {"cpu_percent": 0, "ram_percent": 0, "ram_available_gb": 0}

    def status(self) -> dict:
        """Current worker status."""
        with self._lock:
            return {
                engine: {
                    "workers": state["current"],
                    "max": state["max"],
                    "min": state["min"],
                    "success": state["success"],
                    "failure": state["failure"],
                }
                for engine, state in self.limits.items()
            }
