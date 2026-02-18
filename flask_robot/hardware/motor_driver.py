"""
Motor Driver – low-level L298N control.

Translates high-level commands (forward, backward, left, right, stop)
into GPIO pin states and PWM duty-cycle values.

Wiring (BCM):
    ENA → left-motor speed (PWM)
    IN1, IN2 → left-motor direction
    ENB → right-motor speed (PWM)
    IN3, IN4 → right-motor direction

This module does NOT know about PID or line-following; it purely
drives the H-bridge.
"""

import logging
import time
from typing import Optional

from hardware.gpio_manager import GPIO, GPIOManager

logger = logging.getLogger(__name__)


class MotorDriver:
    """
    Drives two DC motors through an L298N H-bridge.

    Usage::

        driver = MotorDriver(pin_cfg, gpio, pwm_freq=1000)
        driver.initialise()
        driver.forward(speed=60)
        driver.stop()
        driver.cleanup()
    """

    # ── constructor ──────────────────────────────────────────────────────

    def __init__(
        self,
        pin_cfg: dict,
        gpio: GPIOManager,
        pwm_freq: int = 1000,
    ):
        """
        Parameters
        ----------
        pin_cfg : dict
            Must contain keys: MOTOR_ENA, MOTOR_IN1, MOTOR_IN2,
            MOTOR_ENB, MOTOR_IN3, MOTOR_IN4.
        gpio : GPIOManager
            Shared GPIO manager instance.
        pwm_freq : int
            PWM frequency in Hz (default 1 000).
        """
        self._gpio = gpio
        self._freq = pwm_freq

        # Pin mapping
        self._ena = pin_cfg["MOTOR_ENA"]
        self._in1 = pin_cfg["MOTOR_IN1"]
        self._in2 = pin_cfg["MOTOR_IN2"]
        self._enb = pin_cfg["MOTOR_ENB"]
        self._in3 = pin_cfg["MOTOR_IN3"]
        self._in4 = pin_cfg["MOTOR_IN4"]

        # PWM handles (set during initialise)
        self._pwm_left: Optional[object] = None
        self._pwm_right: Optional[object] = None

        # State tracking
        self._left_speed: float = 0.0
        self._right_speed: float = 0.0
        self._direction: str = "stopped"
        self._initialised: bool = False

        logger.info("MotorDriver created (ENA=%d ENB=%d)", self._ena, self._enb)

    # ── lifecycle ────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """Set up GPIO pins and start PWM at 0 % duty."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Direction pins
        for pin in (self._in1, self._in2, self._in3, self._in4):
            self._gpio.setup_output(pin)

        # PWM enable pins
        self._gpio.setup_output(self._ena)
        self._gpio.setup_output(self._enb)

        self._pwm_left = self._gpio.create_pwm(self._ena, self._freq)
        self._pwm_right = self._gpio.create_pwm(self._enb, self._freq)

        self._pwm_left.start(0)   # type: ignore[union-attr]
        self._pwm_right.start(0)  # type: ignore[union-attr]

        self._initialised = True
        logger.info("MotorDriver initialised")

    def cleanup(self) -> None:
        """Stop motors and release resources."""
        self.stop()
        self._initialised = False
        logger.info("MotorDriver cleaned up")

    # ── primitive movements ──────────────────────────────────────────────

    def forward(self, speed: float = 50) -> None:
        """Drive both motors forward at *speed* (0–100 %)."""
        self._set_direction("forward")
        # Left motor forward
        self._gpio.write(self._in1, GPIO.HIGH)
        self._gpio.write(self._in2, GPIO.LOW)
        # Right motor forward
        self._gpio.write(self._in3, GPIO.HIGH)
        self._gpio.write(self._in4, GPIO.LOW)
        self._set_speed(speed, speed)
        logger.debug("FORWARD speed=%d", speed)

    def backward(self, speed: float = 50) -> None:
        """Drive both motors in reverse."""
        self._set_direction("backward")
        self._gpio.write(self._in1, GPIO.LOW)
        self._gpio.write(self._in2, GPIO.HIGH)
        self._gpio.write(self._in3, GPIO.LOW)
        self._gpio.write(self._in4, GPIO.HIGH)
        self._set_speed(speed, speed)
        logger.debug("BACKWARD speed=%d", speed)

    def turn_left(self, speed: float = 45) -> None:
        """Pivot left: right motor forward, left motor backward."""
        self._set_direction("left")
        self._gpio.write(self._in1, GPIO.LOW)
        self._gpio.write(self._in2, GPIO.HIGH)
        self._gpio.write(self._in3, GPIO.HIGH)
        self._gpio.write(self._in4, GPIO.LOW)
        self._set_speed(speed, speed)
        logger.debug("TURN LEFT speed=%d", speed)

    def turn_right(self, speed: float = 45) -> None:
        """Pivot right: left motor forward, right motor backward."""
        self._set_direction("right")
        self._gpio.write(self._in1, GPIO.HIGH)
        self._gpio.write(self._in2, GPIO.LOW)
        self._gpio.write(self._in3, GPIO.LOW)
        self._gpio.write(self._in4, GPIO.HIGH)
        self._set_speed(speed, speed)
        logger.debug("TURN RIGHT speed=%d", speed)

    def stop(self) -> None:
        """Immediately stop both motors (brake)."""
        self._gpio.write(self._in1, GPIO.LOW)
        self._gpio.write(self._in2, GPIO.LOW)
        self._gpio.write(self._in3, GPIO.LOW)
        self._gpio.write(self._in4, GPIO.LOW)
        self._set_speed(0, 0)
        self._direction = "stopped"
        logger.debug("STOP")

    # ── differential drive (used by PID) ─────────────────────────────────

    def set_motor_speeds(self, left: float, right: float) -> None:
        """
        Set each motor independently.  Positive = forward, negative = backward.
        Values are clamped to [-100, 100].
        """
        left = max(-100.0, min(100.0, left))
        right = max(-100.0, min(100.0, right))

        # Left motor direction
        if left >= 0:
            self._gpio.write(self._in1, GPIO.HIGH)
            self._gpio.write(self._in2, GPIO.LOW)
        else:
            self._gpio.write(self._in1, GPIO.LOW)
            self._gpio.write(self._in2, GPIO.HIGH)

        # Right motor direction
        if right >= 0:
            self._gpio.write(self._in3, GPIO.HIGH)
            self._gpio.write(self._in4, GPIO.LOW)
        else:
            self._gpio.write(self._in3, GPIO.LOW)
            self._gpio.write(self._in4, GPIO.HIGH)

        self._set_speed(abs(left), abs(right))
        self._direction = "differential"
        logger.debug("DIFFERENTIAL left=%.1f right=%.1f", left, right)

    # ── internal helpers ─────────────────────────────────────────────────

    def _set_speed(self, left: float, right: float) -> None:
        """Apply PWM duty-cycle to both channels."""
        left = max(0.0, min(100.0, left))
        right = max(0.0, min(100.0, right))

        if self._pwm_left:
            self._pwm_left.ChangeDutyCycle(left)   # type: ignore[union-attr]
        if self._pwm_right:
            self._pwm_right.ChangeDutyCycle(right)  # type: ignore[union-attr]

        self._left_speed = left
        self._right_speed = right

    def _set_direction(self, direction: str) -> None:
        self._direction = direction

    # ── status ───────────────────────────────────────────────────────────

    @property
    def is_initialised(self) -> bool:
        return self._initialised

    def get_status(self) -> dict:
        """Return a snapshot of motor state for API consumers."""
        return {
            "initialised": self._initialised,
            "direction": self._direction,
            "left_speed": self._left_speed,
            "right_speed": self._right_speed,
        }
