"""
GPIO Manager – thin abstraction over RPi.GPIO.

Provides a uniform interface whether we are running on a real Raspberry Pi
or in simulation mode on a desktop/laptop.  Every other module imports *this*
instead of RPi.GPIO directly.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Try to import the real library; fall back to a mock ─────────────────────

try:
    import RPi.GPIO as _GPIO

    REAL_GPIO = True
    logger.info("RPi.GPIO loaded – running on real hardware")
except ImportError:
    REAL_GPIO = False
    logger.info("RPi.GPIO unavailable – using mock GPIO (simulation)")

    # ----- lightweight mock that satisfies every call site -----
    class _MockPWM:
        """Fake PWM channel."""

        def __init__(self, pin: int, freq: int):
            self._pin = pin
            self._duty = 0.0

        def start(self, duty: float) -> None:
            self._duty = duty

        def ChangeDutyCycle(self, duty: float) -> None:
            self._duty = duty

        def stop(self) -> None:
            self._duty = 0.0

    class _MockGPIO:
        """Drop-in replacement for RPi.GPIO when it is not available."""

        BCM = "BCM"
        BOARD = "BOARD"
        OUT = "OUT"
        IN = "IN"
        HIGH = 1
        LOW = 0
        PUD_UP = "PUD_UP"
        PUD_DOWN = "PUD_DOWN"

        @staticmethod
        def setmode(mode) -> None:
            pass

        @staticmethod
        def setwarnings(flag: bool) -> None:
            pass

        @staticmethod
        def setup(pin, mode, pull_up_down=None) -> None:
            pass

        @staticmethod
        def output(pin, state) -> None:
            pass

        @staticmethod
        def input(pin) -> int:
            """Simulation: sensors alternate; override via set_mock_input."""
            return _MockGPIO._mock_values.get(pin, 0)

        @staticmethod
        def PWM(pin: int, freq: int):
            return _MockPWM(pin, freq)

        @staticmethod
        def cleanup(channel=None) -> None:
            pass

        # --- helpers for simulation ---
        _mock_values: dict = {}

        @classmethod
        def set_mock_input(cls, pin: int, value: int) -> None:
            """Set a fixed return value for ``GPIO.input(pin)``."""
            cls._mock_values[pin] = value

    _GPIO = _MockGPIO()  # type: ignore[assignment]


# ── Public singleton ────────────────────────────────────────────────────────

GPIO = _GPIO  # every module does:  from hardware.gpio_manager import GPIO


class GPIOManager:
    """
    Central manager that tracks which pins are initialised so we can
    do a clean ``cleanup()`` on shutdown.
    """

    def __init__(self, simulation: bool = False):
        self.simulation = simulation or (not REAL_GPIO)
        self._initialised_pins: list[int] = []
        self._pwm_channels: dict[int, object] = {}
        logger.info(
            "GPIOManager created (simulation=%s, real_hw=%s)",
            self.simulation,
            REAL_GPIO,
        )

    # ---- setup helpers --------------------------------------------------

    def setup_output(self, pin: int) -> None:
        """Configure *pin* as an output."""
        GPIO.setup(pin, GPIO.OUT)
        self._initialised_pins.append(pin)
        logger.debug("Pin %d → OUTPUT", pin)

    def setup_input(self, pin: int, pull_up: bool = False) -> None:
        """Configure *pin* as an input with optional pull-up."""
        pud = GPIO.PUD_UP if pull_up else GPIO.PUD_DOWN
        GPIO.setup(pin, GPIO.IN, pull_up_down=pud)
        self._initialised_pins.append(pin)
        logger.debug("Pin %d → INPUT (pull_up=%s)", pin, pull_up)

    def create_pwm(self, pin: int, frequency: int) -> object:
        """Create and return a PWM object for *pin*."""
        pwm = GPIO.PWM(pin, frequency)
        self._pwm_channels[pin] = pwm
        logger.debug("PWM created on pin %d @ %d Hz", pin, frequency)
        return pwm

    # ---- read / write ---------------------------------------------------

    @staticmethod
    def write(pin: int, state: int) -> None:
        GPIO.output(pin, state)

    @staticmethod
    def read(pin: int) -> int:
        return GPIO.input(pin)

    # ---- cleanup --------------------------------------------------------

    def cleanup(self) -> None:
        """Stop all PWM channels and release GPIO resources."""
        for pin, pwm in self._pwm_channels.items():
            try:
                pwm.stop()  # type: ignore[union-attr]
            except Exception:
                pass
        self._pwm_channels.clear()

        try:
            GPIO.cleanup()
        except Exception:
            pass

        logger.info("GPIO cleanup complete (%d pins released)", len(self._initialised_pins))
        self._initialised_pins.clear()
