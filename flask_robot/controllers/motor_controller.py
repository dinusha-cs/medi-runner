"""
Motor Controller – high-level movement interface.

Sits between the Flask API and the low-level ``MotorDriver``.
Provides:

* Direction commands with optional duration.
* Speed management & clamping.
* Emergency stop.
* Status snapshot for the API.
"""

import logging
import threading
import time
from typing import Optional

from hardware.motor_driver import MotorDriver
from config import MOTOR

logger = logging.getLogger(__name__)


class MotorController:
    """
    High-level wrapper around :class:`MotorDriver`.

    All movement commands are *immediate* – they set the motor state and
    return.  If a ``duration`` is given the motors run for that many seconds
    then stop automatically in a background timer.
    """

    VALID_DIRECTIONS = {"forward", "backward", "left", "right", "stop"}

    def __init__(self, motor_driver: MotorDriver):
        self._driver = motor_driver
        self._default_speed: float = MOTOR["DEFAULT_SPEED"]
        self._current_speed: float = 0.0
        self._stop_timer: Optional[threading.Timer] = None
        logger.info("MotorController created (default_speed=%d)", self._default_speed)

    # ── movement API ─────────────────────────────────────────────────────

    def move(self, direction: str, speed: float = None, duration: float = 0) -> dict:
        """
        Execute a movement command.

        Parameters
        ----------
        direction : str
            One of ``forward``, ``backward``, ``left``, ``right``, ``stop``.
        speed : float, optional
            0 – 100.  Defaults to ``MOTOR.DEFAULT_SPEED``.
        duration : float
            If > 0, auto-stop after this many seconds.

        Returns
        -------
        dict  – confirmation payload.
        """
        direction = direction.strip().lower()
        if direction not in self.VALID_DIRECTIONS:
            raise ValueError(f"Unknown direction '{direction}'. Use: {self.VALID_DIRECTIONS}")

        speed = self._clamp_speed(speed if speed is not None else self._default_speed)
        self._cancel_stop_timer()

        if direction == "forward":
            self._driver.forward(speed)
        elif direction == "backward":
            self._driver.backward(speed)
        elif direction == "left":
            self._driver.turn_left(speed)
        elif direction == "right":
            self._driver.turn_right(speed)
        elif direction == "stop":
            self._driver.stop()

        self._current_speed = speed if direction != "stop" else 0.0

        # Optional timed stop
        if duration > 0 and direction != "stop":
            self._stop_timer = threading.Timer(duration, self._timed_stop)
            self._stop_timer.daemon = True
            self._stop_timer.start()
            logger.info("MOVE %s speed=%.0f duration=%.2f s", direction, speed, duration)
        else:
            logger.info("MOVE %s speed=%.0f", direction, speed)

        return {
            "direction": direction,
            "speed": speed,
            "duration": duration,
        }

    def emergency_stop(self) -> dict:
        """Immediately halt all motors – highest priority."""
        self._cancel_stop_timer()
        self._driver.stop()
        self._current_speed = 0.0
        logger.warning("EMERGENCY STOP executed")
        return {"status": "emergency_stop"}

    def set_speed(self, speed: float) -> dict:
        """Update the default speed for subsequent commands."""
        self._default_speed = self._clamp_speed(speed)
        logger.info("Default speed set to %.0f", self._default_speed)
        return {"default_speed": self._default_speed}

    # ── helpers ──────────────────────────────────────────────────────────

    def _clamp_speed(self, speed: float) -> float:
        return max(float(MOTOR["MIN_SPEED"]), min(float(MOTOR["MAX_SPEED"]), float(speed)))

    def _timed_stop(self) -> None:
        """Called by the background timer to auto-stop."""
        self._driver.stop()
        self._current_speed = 0.0
        logger.info("Timed auto-stop triggered")

    def _cancel_stop_timer(self) -> None:
        if self._stop_timer and self._stop_timer.is_alive():
            self._stop_timer.cancel()
            self._stop_timer = None

    # ── status ───────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "default_speed": self._default_speed,
            "current_speed": self._current_speed,
            **self._driver.get_status(),
        }
