"""
Line Follower – PID-based autonomous line tracking.

Uses the 5-channel IR sensor array to compute a positional error
and applies a PID controller to generate differential motor speeds.

The controller runs in its own daemon thread so the Flask server
stays responsive.  Call ``start()`` / ``stop()`` to toggle.

Recovery strategies
-------------------
* **Line lost** – robot spins in the direction of the last known error
  for up to ``LOST_LINE_TIMEOUT`` seconds.
* **All-black** (intersection) – pauses briefly then continues straight.
* **Stall** – if error doesn't change for ``MOTOR_STALL_TIMEOUT`` seconds
  the controller stops and raises an event.
"""

import logging
import threading
import time
from typing import Callable, Optional

from hardware.motor_driver import MotorDriver
from hardware.ir_sensor import IRSensorArray
from config import PID as PID_CFG, LINE_FOLLOW as LF_CFG, RECOVERY

logger = logging.getLogger(__name__)


class PIDController:
    """
    Textbook PID with integral wind-up clamping.

    Attributes
    ----------
    kp, ki, kd : float   – gains
    setpoint   : float   – desired value (0.0 for centred line)
    """

    def __init__(self, kp: float, ki: float, kd: float):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint: float = 0.0

        # Internal state
        self._prev_error: float = 0.0
        self._integral: float = 0.0
        self._last_time: float = time.time()

        # Limits
        self.integral_limit: float = PID_CFG["INTEGRAL_LIMIT"]
        self.output_limit: float = PID_CFG["MAX_CORRECTION"]

    def reset(self) -> None:
        """Zero the accumulated integral and derivative memory."""
        self._prev_error = 0.0
        self._integral = 0.0
        self._last_time = time.time()
        logger.debug("PID state reset")

    def compute(self, measured: float) -> float:
        """
        Run one PID iteration.

        Parameters
        ----------
        measured : float
            Current sensor error (from IR array).

        Returns
        -------
        float
            Correction value to be added/subtracted from motor speeds.
        """
        now = time.time()
        dt = now - self._last_time
        if dt <= 0:
            return 0.0

        error = self.setpoint - measured

        # ── Proportional ──
        p = self.kp * error

        # ── Integral (with anti-windup clamp) ──
        self._integral += error * dt
        self._integral = max(-self.integral_limit, min(self.integral_limit, self._integral))
        i = self.ki * self._integral

        # ── Derivative ──
        d = self.kd * (error - self._prev_error) / dt

        self._prev_error = error
        self._last_time = now

        output = p + i + d
        return max(-self.output_limit, min(self.output_limit, output))

    def get_gains(self) -> dict:
        return {"kp": self.kp, "ki": self.ki, "kd": self.kd}

    def set_gains(self, kp: float = None, ki: float = None, kd: float = None) -> dict:
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
        if kd is not None:
            self.kd = kd
        self.reset()
        logger.info("PID gains updated: kp=%.2f ki=%.4f kd=%.2f", self.kp, self.ki, self.kd)
        return self.get_gains()


class LineFollower:
    """
    High-level autonomous line-following controller.

    Lifecycle::

        follower = LineFollower(motor_driver, ir_sensor)
        follower.start(base_speed=50)   # begins tracking in background
        follower.stop()                 # halts the loop & motors
    """

    def __init__(
        self,
        motor: MotorDriver,
        sensors: IRSensorArray,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """
        Parameters
        ----------
        motor : MotorDriver
        sensors : IRSensorArray
        on_error : callable, optional
            Callback invoked with an error description string when recovery
            fails (e.g. line permanently lost).
        """
        self._motor = motor
        self._sensors = sensors
        self._on_error = on_error

        # PID controller
        self._pid = PIDController(
            kp=PID_CFG["KP"],
            ki=PID_CFG["KI"],
            kd=PID_CFG["KD"],
        )

        # Runtime state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._base_speed: float = PID_CFG["BASE_SPEED"]
        self._last_known_error: float = 0.0
        self._line_lost_since: Optional[float] = None
        self._last_error_change: float = time.time()
        self._prev_raw_error: float = 0.0

        logger.info("LineFollower created")

    # ── public control ───────────────────────────────────────────────────

    def start(self, base_speed: float = None) -> None:
        """Begin autonomous line following in a daemon thread."""
        if self._running:
            logger.warning("LineFollower already running")
            return

        if base_speed is not None:
            self._base_speed = base_speed

        self._pid.reset()
        self._running = True
        self._line_lost_since = None
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="line-follower")
        self._thread.start()
        logger.info("LineFollower STARTED (base_speed=%.1f)", self._base_speed)

    def stop(self) -> None:
        """Stop the line-following loop and halt the motors."""
        if not self._running:
            return
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._motor.stop()
        logger.info("LineFollower STOPPED")

    @property
    def is_running(self) -> bool:
        return self._running

    # ── PID tuning helpers ───────────────────────────────────────────────

    def get_pid_gains(self) -> dict:
        return self._pid.get_gains()

    def set_pid_gains(self, **kwargs) -> dict:
        return self._pid.set_gains(**kwargs)

    def reset_pid(self) -> None:
        self._pid.reset()

    # ── main loop (runs in thread) ───────────────────────────────────────

    def _run_loop(self) -> None:
        """Core PID loop – reads sensors, computes correction, drives motors."""
        logger.info("Line-follow loop entered")
        try:
            while self._running:
                error, on_line, all_black = self._sensors.read_error()

                # ── Handle intersection (all sensors see line) ───────────
                if all_black:
                    logger.info("Intersection detected – pausing briefly")
                    self._motor.forward(self._base_speed * 0.5)
                    time.sleep(LF_CFG["ALL_BLACK_PAUSE"])
                    continue

                # ── Handle line lost ─────────────────────────────────────
                if not on_line:
                    self._handle_line_lost()
                    time.sleep(LF_CFG["LOOP_INTERVAL"])
                    continue
                else:
                    # Line found – clear lost timer
                    self._line_lost_since = None

                # ── PID correction ───────────────────────────────────────
                correction = self._pid.compute(error)
                left_speed = self._base_speed + correction
                right_speed = self._base_speed - correction

                self._motor.set_motor_speeds(left_speed, right_speed)

                # Track for stall detection
                self._update_stall_monitor(error)

                # Remember last valid error direction
                self._last_known_error = error

                time.sleep(LF_CFG["LOOP_INTERVAL"])

        except Exception as exc:
            logger.exception("LineFollower loop crashed: %s", exc)
            self._motor.stop()
            if self._on_error:
                self._on_error(f"Line-follow loop exception: {exc}")
        finally:
            self._running = False
            logger.info("Line-follow loop exited")

    # ── recovery strategies ──────────────────────────────────────────────

    def _handle_line_lost(self) -> None:
        """Attempt to re-acquire the line by spinning toward last known side."""
        now = time.time()

        if self._line_lost_since is None:
            self._line_lost_since = now
            logger.warning("Line LOST – starting search")

        elapsed = now - self._line_lost_since

        if elapsed > LF_CFG["LOST_LINE_TIMEOUT"]:
            # Recovery failed
            logger.error("Line recovery FAILED after %.1f s", elapsed)
            self._motor.stop()
            self._running = False
            if self._on_error:
                self._on_error("Line lost – recovery timed out")
            return

        # Spin in the direction of last known error
        search_speed = LF_CFG["SEARCH_TURN_SPEED"]
        if self._last_known_error <= 0:
            # Line was to the left → spin left
            self._motor.set_motor_speeds(-search_speed, search_speed)
        else:
            # Line was to the right → spin right
            self._motor.set_motor_speeds(search_speed, -search_speed)

        logger.debug("Searching for line (%.1f s elapsed)", elapsed)

    def _update_stall_monitor(self, current_error: float) -> None:
        """Detect if the robot appears stalled (no error change)."""
        if abs(current_error - self._prev_raw_error) > 0.05:
            self._last_error_change = time.time()
        self._prev_raw_error = current_error

        stall_duration = time.time() - self._last_error_change
        if stall_duration > RECOVERY["MOTOR_STALL_TIMEOUT"]:
            logger.warning("Motor stall detected (%.1f s unchanged)", stall_duration)
            # Nudge forward briefly to escape
            self._motor.forward(self._base_speed * 0.6)
            time.sleep(0.3)
            self._last_error_change = time.time()

    # ── status ───────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "base_speed": self._base_speed,
            "last_error": round(self._last_known_error, 3),
            "pid": self._pid.get_gains(),
            "line_lost": self._line_lost_since is not None,
        }
