"""
Mode Manager – switches between MANUAL and AUTONOMOUS modes.

Modes
-----
* **manual** – robot responds only to explicit direction commands
  from the web app.  Line-follower is stopped.
* **autonomous** – the PID line-follower is active.  Manual move
  commands are rejected (except emergency stop).

State transitions are logged and broadcast so the web app can
update its UI.
"""

import logging
import time
from enum import Enum
from typing import Optional

from controllers.motor_controller import MotorController
from controllers.line_follower import LineFollower

logger = logging.getLogger(__name__)


class RobotMode(str, Enum):
    MANUAL = "manual"
    AUTONOMOUS = "autonomous"


class ModeManager:
    """
    Single source of truth for the current operating mode.

    Usage::

        mgr = ModeManager(motor_ctrl, line_follower)
        mgr.set_mode(RobotMode.AUTONOMOUS)
        mgr.set_mode(RobotMode.MANUAL)
    """

    def __init__(
        self,
        motor_ctrl: MotorController,
        line_follower: LineFollower,
    ):
        self._motor = motor_ctrl
        self._lf = line_follower
        self._mode: RobotMode = RobotMode.MANUAL
        self._mode_changed_at: float = time.time()
        logger.info("ModeManager created (initial=%s)", self._mode.value)

    # ── mode switching ───────────────────────────────────────────────────

    def set_mode(self, mode: RobotMode, base_speed: float = None) -> dict:
        """
        Switch operating mode.

        If switching **to autonomous** the line-follower starts.
        If switching **to manual** the line-follower and motors stop.
        """
        if mode == self._mode:
            logger.info("Already in %s mode – no change", mode.value)
            return self.get_status()

        old = self._mode

        # ── Leaving autonomous → stop line-follower ──
        if self._mode == RobotMode.AUTONOMOUS:
            self._lf.stop()

        self._mode = mode
        self._mode_changed_at = time.time()

        # ── Entering autonomous → start line-follower ──
        if mode == RobotMode.AUTONOMOUS:
            self._lf.start(base_speed=base_speed)
            logger.info("Mode changed: %s → %s (line-follower started)", old.value, mode.value)
        else:
            # Entering manual – make sure motors are stopped so the
            # operator has a clean slate.
            self._motor.move("stop")
            logger.info("Mode changed: %s → %s (motors stopped)", old.value, mode.value)

        return self.get_status()

    def get_mode(self) -> RobotMode:
        return self._mode

    def is_manual(self) -> bool:
        return self._mode == RobotMode.MANUAL

    def is_autonomous(self) -> bool:
        return self._mode == RobotMode.AUTONOMOUS

    # ── guards ───────────────────────────────────────────────────────────

    def require_manual(self) -> None:
        """Raise if not in manual mode (used by move endpoints)."""
        if self._mode != RobotMode.MANUAL:
            raise RuntimeError(
                f"Cannot execute manual command – currently in {self._mode.value} mode. "
                "Switch to manual first."
            )

    # ── status ───────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "mode": self._mode.value,
            "mode_since": self._mode_changed_at,
            "line_follower_active": self._lf.is_running,
        }
