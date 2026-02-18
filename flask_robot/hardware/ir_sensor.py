"""
IR Sensor Array – reads 5-channel TCRT5000 line sensor.

Each sensor returns a digital HIGH (1) or LOW (0):
    1 → line detected (black surface / dark)
    0 → no line (white / reflective surface)

The array is laid out left-to-right:
    S1 (far-left)  S2 (left)  S3 (centre)  S4 (right)  S5 (far-right)

Wiring – Raspberry Pi 4 Model B → TCRT5000 5-channel IR array
==============================================================

    Raspberry Pi 4                        TCRT5000 IR Array
    ┌──────────────┐                   ┌─────────────────────┐
    │              │                   │  S1  S2  S3  S4  S5 │
    │  5V  (pin 4) ├───── red ────────►│  VCC               │
    │  GND (pin 6) ├───── black ──────►│  GND               │
    │              │                   │                     │
    │  GPIO5  (29) ├───── white ──────►│  S1  (far-left)    │
    │  GPIO6  (31) ├───── grey ───────►│  S2  (left)        │
    │  GPIO13 (33) ├───── yellow ─────►│  S3  (centre)      │
    │  GPIO19 (35) ├───── blue ───────►│  S4  (right)       │
    │  GPIO26 (37) ├───── brown ──────►│  S5  (far-right)   │
    └──────────────┘                   └─────────────────────┘

    Physical pin layout on the Pi header (relevant pins only):
    ┌────────────────────────────────────────┐
    │  Pi 40-pin header (top view)           │
    │  ...                                   │
    │  pin 4  [5V]  ●  ○  pin 3             │
    │  pin 6  [GND] ●  ○  pin 5             │
    │  ...                                   │
    │  pin 29 [GPIO5]  ●  ○  pin 30         │
    │  pin 31 [GPIO6]  ●  ○  pin 32         │
    │  pin 33 [GPIO13] ●  ○  pin 34         │
    │  pin 35 [GPIO19] ●  ○  pin 36         │
    │  pin 37 [GPIO26] ●  ○  pin 38         │
    │  ...                                   │
    └────────────────────────────────────────┘

Sensor weighting (for PID error calculation):
    S1=-2   S2=-1   S3=0   S4=+1   S5=+2
    ◄─── LEFT ────  CENTRE  ──── RIGHT ───►

    error < 0 → line is left  → robot turns left
    error = 0 → line centred  → go straight
    error > 0 → line is right → robot turns right

PID Algorithm
=============
The weighted error feeds a PID controller that generates a
motor correction value:

    correction = Kp × error + Ki × ∫error·dt + Kd × d(error)/dt

    left_motor  = base_speed + correction
    right_motor = base_speed - correction

    - Kp (proportional): reacts to current error magnitude
    - Ki (integral):     eliminates steady-state drift
    - Kd (derivative):   dampens oscillation / overshoot

Example sensor patterns:
    [0,0,1,0,0] → error= 0.0  → centred, go straight
    [0,1,1,0,0] → error=-0.5  → slightly left, steer left gently
    [1,0,0,0,0] → error=-2.0  → far left, hard steer left
    [0,0,0,1,1] → error=+1.5  → right, steer right
    [0,0,0,0,0] → line lost   → trigger recovery search
    [1,1,1,1,1] → intersection → pause, then go straight

In simulation mode the readings are driven by ``set_simulated_readings()``
so that the line-follower can be tested without hardware.
"""

import logging
import time
from typing import List, Optional, Tuple

from hardware.gpio_manager import GPIO, GPIOManager

logger = logging.getLogger(__name__)


class IRSensorArray:
    """
    Reads a 5-channel digital IR sensor array and computes an
    error value suitable for PID line-following.

    Sensor weights: [-2, -1, 0, +1, +2]
        Negative → line is to the LEFT  → robot should steer left
        Positive → line is to the RIGHT → robot should steer right
    """

    WEIGHTS = [-2, -1, 0, 1, 2]

    def __init__(
        self,
        pin_cfg: dict,
        gpio: GPIOManager,
        simulation: bool = False,
    ):
        """
        Parameters
        ----------
        pin_cfg : dict
            Must contain IR_SENSOR_1 … IR_SENSOR_5.
        gpio : GPIOManager
        simulation : bool
        """
        self._gpio = gpio
        self._simulation = simulation

        # Map ordered sensor pins
        self._pins: List[int] = [
            pin_cfg["IR_SENSOR_1"],
            pin_cfg["IR_SENSOR_2"],
            pin_cfg["IR_SENSOR_3"],
            pin_cfg["IR_SENSOR_4"],
            pin_cfg["IR_SENSOR_5"],
        ]

        # Simulation buffer
        self._sim_readings: List[int] = [0, 0, 1, 0, 0]  # default: line in centre

        self._initialised = False
        logger.info("IRSensorArray created (pins=%s, sim=%s)", self._pins, simulation)

    # ── lifecycle ────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """Configure sensor GPIO pins as inputs."""
        if not self._simulation:
            GPIO.setmode(GPIO.BCM)
            for pin in self._pins:
                self._gpio.setup_input(pin)
        self._initialised = True
        logger.info("IRSensorArray initialised")

    # ── reading ──────────────────────────────────────────────────────────

    def read_raw(self) -> List[int]:
        """
        Return a list of 5 digital readings [S1 … S5].
        1 = line detected, 0 = no line.
        """
        if self._simulation:
            return list(self._sim_readings)

        readings = [self._gpio.read(pin) for pin in self._pins]
        logger.debug("IR raw: %s", readings)
        return readings

    def read_error(self) -> Tuple[float, bool, bool]:
        """
        Compute a weighted error from the sensor array.

        Returns
        -------
        error : float
            Weighted average position of the line.
            0.0 = centred, negative = left, positive = right.
        on_line : bool
            True if at least one sensor sees the line.
        all_black : bool
            True if every sensor sees the line (intersection / T-junction).
        """
        raw = self.read_raw()

        active = sum(raw)
        all_black = active == len(raw)
        on_line = active > 0

        if not on_line:
            # No sensor sees the line – return last-known direction bias
            return 0.0, False, False

        # Weighted average
        weighted_sum = sum(w * v for w, v in zip(self.WEIGHTS, raw))
        error = weighted_sum / active
        return error, on_line, all_black

    # ── simulation helpers ───────────────────────────────────────────────

    def set_simulated_readings(self, readings: List[int]) -> None:
        """Override sensor values in simulation mode."""
        if len(readings) != 5:
            raise ValueError("Expected exactly 5 sensor values")
        self._sim_readings = list(readings)

    # ── status ───────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        raw = self.read_raw()
        error, on_line, all_black = self.read_error()
        return {
            "raw": raw,
            "error": round(error, 3),
            "on_line": on_line,
            "all_black": all_black,
            "simulation": self._simulation,
        }
