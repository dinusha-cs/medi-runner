"""
Activity Logger – structured in-memory + file logging for the robot.

Every significant action (mode change, movement, error, zone detection)
is recorded as a structured dict and kept in a bounded in-memory ring
buffer.  The buffer is exposed via ``/api/logs`` so the web app can
display a live activity feed.

Simultaneously, all entries are written to a rotating log file on disk
for post-mortem analysis.
"""

import logging
import logging.handlers
import threading
import time
from collections import deque
from typing import Deque, Dict, List, Optional

from config import LOGGING as LOG_CFG

logger = logging.getLogger(__name__)


class ActivityRecord:
    """Single activity log entry."""

    __slots__ = ("timestamp", "category", "action", "detail", "level")

    def __init__(
        self,
        category: str,
        action: str,
        detail: str = "",
        level: str = "INFO",
    ):
        self.timestamp: float = time.time()
        self.category = category   # e.g. "motor", "mode", "camera", "zone", "error"
        self.action = action       # e.g. "forward", "switch_to_autonomous"
        self.detail = detail       # free-form human-readable info
        self.level = level

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "category": self.category,
            "action": self.action,
            "detail": self.detail,
            "level": self.level,
        }


class ActivityLogger:
    """
    Thread-safe structured activity logger.

    Usage::

        al = ActivityLogger()
        al.log("motor", "forward", "speed=60, duration=2.0")
        al.log("mode", "switch", "manual → autonomous")
        entries = al.get_logs(limit=20)
    """

    def __init__(self, max_in_memory: int = None):
        self._max = max_in_memory or LOG_CFG.get("MAX_IN_MEMORY", 2000)
        self._buffer: Deque[ActivityRecord] = deque(maxlen=self._max)
        self._lock = threading.Lock()
        self._total_logged: int = 0

        # Also set up a file handler for persistence
        self._setup_file_logger()

        logger.info("ActivityLogger created (buffer_size=%d)", self._max)

    # ── file logging setup ───────────────────────────────────────────────

    def _setup_file_logger(self) -> None:
        """Create a rotating file handler for persistent activity logs."""
        self._file_logger = logging.getLogger("activity_file")
        self._file_logger.setLevel(logging.DEBUG)
        self._file_logger.propagate = False  # don't duplicate to console

        handler = logging.handlers.RotatingFileHandler(
            filename=LOG_CFG.get("FILE", "robot_activity.log"),
            maxBytes=LOG_CFG.get("MAX_FILE_SIZE", 5 * 1024 * 1024),
            backupCount=LOG_CFG.get("BACKUP_COUNT", 3),
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s  %(message)s",
            datefmt=LOG_CFG.get("DATE_FORMAT", "%Y-%m-%d %H:%M:%S"),
        )
        handler.setFormatter(formatter)
        self._file_logger.addHandler(handler)

    # ── core API ─────────────────────────────────────────────────────────

    def log(
        self,
        category: str,
        action: str,
        detail: str = "",
        level: str = "INFO",
    ) -> None:
        """
        Record an activity.

        Parameters
        ----------
        category : str – subsystem (motor, mode, camera, zone, error, system).
        action   : str – what happened (forward, stop, switch, detect, …).
        detail   : str – optional human-readable detail.
        level    : str – INFO, WARNING, ERROR, DEBUG.
        """
        record = ActivityRecord(category, action, detail, level)

        with self._lock:
            self._buffer.append(record)
            self._total_logged += 1

        # Persist to file
        self._file_logger.info("[%s] %s – %s", category, action, detail)

    def get_logs(
        self,
        limit: int = 50,
        category: str = None,
        level: str = None,
        since: float = None,
    ) -> List[dict]:
        """
        Retrieve activity logs, newest first.

        Parameters
        ----------
        limit    : int   – max entries to return.
        category : str   – filter by category.
        level    : str   – filter by level.
        since    : float – only entries after this Unix timestamp.
        """
        with self._lock:
            records = list(self._buffer)
        records.reverse()

        if category:
            records = [r for r in records if r.category == category]
        if level:
            records = [r for r in records if r.level == level]
        if since:
            records = [r for r in records if r.timestamp >= since]

        return [r.to_dict() for r in records[:limit]]

    def clear(self) -> int:
        """Clear the in-memory buffer; return count removed."""
        with self._lock:
            count = len(self._buffer)
            self._buffer.clear()
        logger.info("Activity buffer cleared (%d entries)", count)
        return count

    # ── stats ────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        with self._lock:
            buffered = len(self._buffer)
        return {
            "total_logged": self._total_logged,
            "buffered": buffered,
            "max_buffer": self._max,
        }
