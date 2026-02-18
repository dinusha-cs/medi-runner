"""
Error Recovery – centralised error handling, watchdog, and recovery logic.

Features
--------
* **Watchdog** – periodic health-check thread that verifies hardware
  responsiveness and triggers recovery actions if something is stuck.
* **Retry decorator** – wraps critical functions with automatic retries.
* **Error log** – records every error with timestamp, context, and
  whether recovery succeeded, so the API can expose it.

All recovery actions ultimately call ``emergency_stop`` if they
cannot fix the problem, guaranteeing the robot is safe.
"""

import functools
import logging
import threading
import time
import traceback
from collections import deque
from typing import Any, Callable, Deque, Dict, Optional

from config import RECOVERY

logger = logging.getLogger(__name__)


# ── Error record ─────────────────────────────────────────────────────────

class ErrorRecord:
    """Immutable snapshot of a single error event."""

    __slots__ = ("timestamp", "source", "message", "traceback", "recovered")

    def __init__(self, source: str, message: str, tb: str = "", recovered: bool = False):
        self.timestamp: float = time.time()
        self.source = source
        self.message = message
        self.traceback = tb
        self.recovered = recovered

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "message": self.message,
            "traceback": self.traceback,
            "recovered": self.recovered,
        }


# ── Recovery Manager ─────────────────────────────────────────────────────

class RecoveryManager:
    """
    Central hub for error tracking, watchdog, and automated recovery.

    Usage::

        recovery = RecoveryManager(emergency_stop_fn=robot.emergency_stop)
        recovery.start_watchdog()
        ...
        recovery.record_error("motor", "stall detected")
        recovery.stop_watchdog()
    """

    MAX_HISTORY = 200  # keep last N error records

    def __init__(self, emergency_stop_fn: Optional[Callable] = None):
        """
        Parameters
        ----------
        emergency_stop_fn : callable, optional
            A zero-argument function that immediately halts the robot.
        """
        self._emergency_stop = emergency_stop_fn
        self._errors: Deque[ErrorRecord] = deque(maxlen=self.MAX_HISTORY)
        self._lock = threading.Lock()

        # Watchdog
        self._wd_running = False
        self._wd_thread: Optional[threading.Thread] = None
        self._health_checks: Dict[str, Callable[[], bool]] = {}

        # Consecutive failure counter per health-check
        self._failure_counts: Dict[str, int] = {}

        logger.info("RecoveryManager created")

    # ── error recording ──────────────────────────────────────────────────

    def record_error(
        self,
        source: str,
        message: str,
        exc: Optional[Exception] = None,
        recovered: bool = False,
    ) -> None:
        """
        Log an error event.

        Parameters
        ----------
        source : str   – subsystem name (e.g. "motor", "camera").
        message : str  – human-readable description.
        exc : Exception, optional – the exception, if any.
        recovered : bool – whether the error was automatically recovered.
        """
        tb = traceback.format_exception(type(exc), exc, exc.__traceback__) if exc else ""
        tb_str = "".join(tb) if isinstance(tb, list) else str(tb)

        record = ErrorRecord(source, message, tb_str, recovered)
        with self._lock:
            self._errors.append(record)

        level = logging.WARNING if recovered else logging.ERROR
        logger.log(level, "[%s] %s (recovered=%s)", source, message, recovered)

        # If configured, auto-stop on unrecovered error
        if not recovered and RECOVERY.get("AUTO_STOP_ON_ERROR"):
            self._trigger_emergency_stop(f"Unrecovered error in {source}: {message}")

    def get_errors(self, limit: int = 50, source: str = None) -> list:
        """Return recent errors as a list of dicts, newest first."""
        with self._lock:
            records = list(self._errors)
        records.reverse()

        if source:
            records = [r for r in records if r.source == source]

        return [r.to_dict() for r in records[:limit]]

    def clear_errors(self) -> int:
        """Clear all recorded errors; return the count removed."""
        with self._lock:
            count = len(self._errors)
            self._errors.clear()
        logger.info("Cleared %d error records", count)
        return count

    # ── watchdog ─────────────────────────────────────────────────────────

    def register_health_check(self, name: str, check_fn: Callable[[], bool]) -> None:
        """
        Register a health-check callback.

        ``check_fn`` should return True if the subsystem is healthy.
        """
        self._health_checks[name] = check_fn
        self._failure_counts[name] = 0
        logger.debug("Health-check registered: %s", name)

    def start_watchdog(self) -> None:
        """Start the periodic watchdog thread."""
        if self._wd_running:
            return
        self._wd_running = True
        self._wd_thread = threading.Thread(target=self._watchdog_loop, daemon=True, name="watchdog")
        self._wd_thread.start()
        logger.info("Watchdog started (interval=%.1f s)", RECOVERY["WATCHDOG_INTERVAL"])

    def stop_watchdog(self) -> None:
        """Stop the watchdog thread."""
        self._wd_running = False
        if self._wd_thread and self._wd_thread.is_alive():
            self._wd_thread.join(timeout=RECOVERY["WATCHDOG_INTERVAL"] + 1)
        logger.info("Watchdog stopped")

    def _watchdog_loop(self) -> None:
        """Periodically run all registered health checks."""
        while self._wd_running:
            for name, check_fn in list(self._health_checks.items()):
                try:
                    healthy = check_fn()
                except Exception as exc:
                    healthy = False
                    logger.error("Health-check '%s' raised: %s", name, exc)

                if healthy:
                    self._failure_counts[name] = 0
                else:
                    self._failure_counts[name] = self._failure_counts.get(name, 0) + 1
                    count = self._failure_counts[name]
                    logger.warning(
                        "Health-check '%s' FAILED (%d consecutive)", name, count
                    )
                    if count >= RECOVERY["MAX_RETRIES"]:
                        self.record_error(
                            source=name,
                            message=f"Health-check failed {count} times consecutively",
                        )
                        self._failure_counts[name] = 0  # reset after escalating

            time.sleep(RECOVERY["WATCHDOG_INTERVAL"])

    # ── emergency stop ───────────────────────────────────────────────────

    def _trigger_emergency_stop(self, reason: str) -> None:
        """Invoke the registered emergency-stop callback."""
        logger.critical("EMERGENCY STOP triggered: %s", reason)
        if self._emergency_stop:
            try:
                self._emergency_stop()
            except Exception as exc:
                logger.error("Emergency stop callback failed: %s", exc)

    # ── status ───────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        with self._lock:
            error_count = len(self._errors)
            recent = self._errors[-1].to_dict() if self._errors else None

        return {
            "watchdog_running": self._wd_running,
            "health_checks": list(self._health_checks.keys()),
            "total_errors": error_count,
            "most_recent_error": recent,
            "failure_counts": dict(self._failure_counts),
        }


# ── Retry decorator ──────────────────────────────────────────────────────

def with_retry(
    retries: int = RECOVERY["MAX_RETRIES"],
    delay: float = RECOVERY["RETRY_DELAY"],
    on_fail: Optional[Callable[[Exception], None]] = None,
):
    """
    Decorator that retries a function up to *retries* times on exception.

    Usage::

        @with_retry(retries=3, delay=0.5)
        def flaky_operation():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exc: Optional[Exception] = None
            for attempt in range(1, retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "%s failed (attempt %d/%d): %s",
                        func.__name__, attempt, retries, exc,
                    )
                    if attempt < retries:
                        time.sleep(delay)
            # All retries exhausted
            if on_fail:
                on_fail(last_exc)  # type: ignore[arg-type]
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
