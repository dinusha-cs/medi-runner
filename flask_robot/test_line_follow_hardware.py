#!/usr/bin/env python3
"""
test_line_follow_hardware.py
============================
Standalone test script for PID line-following on REAL hardware.

Run directly on the Raspberry Pi 4:

    python test_line_follow_hardware.py                 # default speed 45
    python test_line_follow_hardware.py --speed 55      # custom base speed
    python test_line_follow_hardware.py --tune           # interactive PID tuner
    python test_line_follow_hardware.py --sensor-only    # read sensors, no motors

What this script does
---------------------
1. Initialises GPIO for the 5-channel TCRT5000 IR array and L298N motors.
2. Runs an interactive sensor check so you can verify wiring.
3. Enters a PID line-following loop.
4. Prints real-time telemetry to the terminal.
5. Press Ctrl-C at any time → motors stop, GPIO cleaned up.

Wiring (must match config.py)
-----------------------------
    Raspberry Pi 4                       TCRT5000 IR Array
    ┌──────────────┐                  ┌─────────────────────┐
    │  5V  (pin 4) ├─── red ────────►│  VCC               │
    │  GND (pin 6) ├─── black ──────►│  GND               │
    │  GPIO5  (29) ├─── white ──────►│  S1  (far-left)    │
    │  GPIO6  (31) ├─── grey ───────►│  S2  (left)        │
    │  GPIO13 (33) ├─── yellow ─────►│  S3  (centre)      │
    │  GPIO19 (35) ├─── blue ───────►│  S4  (right)       │
    │  GPIO26 (37) ├─── brown ──────►│  S5  (far-right)   │
    └──────────────┘                  └─────────────────────┘

    Raspberry Pi 4                       L298N Motor Driver
    ┌──────────────┐                  ┌─────────────────────┐
    │  GPIO20 (38) ├─────────────────►│  ENA (left PWM)    │
    │  GPIO23 (16) ├─────────────────►│  IN1               │
    │  GPIO22 (15) ├─────────────────►│  IN2               │
    │  GPIO27 (13) ├─────────────────►│  IN3               │
    │  GPIO17 (11) ├─────────────────►│  IN4               │
    │  GPIO16 (36) ├─────────────────►│  ENB (right PWM)   │
    └──────────────┘                  └─────────────────────┘

PID Algorithm
-------------
    error = weighted_average(sensor_readings)
        weights = [-2, -1, 0, +1, +2] for S1..S5

    correction = Kp * error  +  Ki * ∫error·dt  +  Kd * d(error)/dt

    left_motor  = base_speed + correction
    right_motor = base_speed - correction

    Clamp both to [0, 100] (duty-cycle %).
"""

import argparse
import os
import signal
import sys
import time

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force REAL hardware mode regardless of env-var
os.environ["SIMULATION"] = "0"

from config import GPIO_PINS, MOTOR, PID as PID_CFG, LINE_FOLLOW as LF_CFG


# =========================================================================
# GPIO – import real RPi.GPIO (fails fast if not on a Pi)
# =========================================================================
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("=" * 60)
    print("  ERROR: RPi.GPIO not found.")
    print("  This script must run on a Raspberry Pi with real hardware.")
    print("=" * 60)
    sys.exit(1)


# =========================================================================
# Pin assignments (from config)
# =========================================================================
# IR sensors
IR_PINS = [
    GPIO_PINS["IR_SENSOR_1"],  # S1 far-left   (GPIO5)
    GPIO_PINS["IR_SENSOR_2"],  # S2 left        (GPIO6)
    GPIO_PINS["IR_SENSOR_3"],  # S3 centre      (GPIO13)
    GPIO_PINS["IR_SENSOR_4"],  # S4 right       (GPIO19)
    GPIO_PINS["IR_SENSOR_5"],  # S5 far-right   (GPIO26)
]
SENSOR_WEIGHTS = [-2, -1, 0, 1, 2]

# Motor driver
ENA = GPIO_PINS["MOTOR_ENA"]  # left PWM   (GPIO20)
IN1 = GPIO_PINS["MOTOR_IN1"]  # left dir   (GPIO23)
IN2 = GPIO_PINS["MOTOR_IN2"]  # left dir   (GPIO22)
ENB = GPIO_PINS["MOTOR_ENB"]  # right PWM  (GPIO16)
IN3 = GPIO_PINS["MOTOR_IN3"]  # right dir  (GPIO27)
IN4 = GPIO_PINS["MOTOR_IN4"]  # right dir  (GPIO17)

PWM_FREQ = MOTOR["PWM_FREQUENCY"]


# =========================================================================
# GPIO setup
# =========================================================================
def setup_gpio():
    """Initialise all GPIO pins and return (pwm_left, pwm_right)."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # IR sensor inputs
    for pin in IR_PINS:
        GPIO.setup(pin, GPIO.IN)

    # Motor outputs
    for pin in (IN1, IN2, IN3, IN4, ENA, ENB):
        GPIO.setup(pin, GPIO.OUT)

    # PWM channels
    pwm_left = GPIO.PWM(ENA, PWM_FREQ)
    pwm_right = GPIO.PWM(ENB, PWM_FREQ)
    pwm_left.start(0)
    pwm_right.start(0)

    print("[OK] GPIO initialised")
    return pwm_left, pwm_right


def cleanup_gpio(pwm_left, pwm_right):
    """Stop motors and release GPIO."""
    # Stop PWM
    pwm_left.ChangeDutyCycle(0)
    pwm_right.ChangeDutyCycle(0)
    pwm_left.stop()
    pwm_right.stop()

    # All direction pins LOW
    for pin in (IN1, IN2, IN3, IN4):
        GPIO.output(pin, GPIO.LOW)

    GPIO.cleanup()
    print("[OK] GPIO cleaned up – motors stopped")


# =========================================================================
# Motor helpers
# =========================================================================
def set_motors(pwm_left, pwm_right, left_speed: float, right_speed: float):
    """
    Drive both motors with independent speeds.

    Positive = forward, negative = backward.
    Values are clamped to [-100, 100].
    """
    left_speed = max(-100.0, min(100.0, left_speed))
    right_speed = max(-100.0, min(100.0, right_speed))

    # Left motor direction
    if left_speed >= 0:
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
    else:
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH)

    # Right motor direction
    if right_speed >= 0:
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)
    else:
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)

    pwm_left.ChangeDutyCycle(abs(left_speed))
    pwm_right.ChangeDutyCycle(abs(right_speed))


def stop_motors(pwm_left, pwm_right):
    """Immediately stop both motors."""
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    pwm_left.ChangeDutyCycle(0)
    pwm_right.ChangeDutyCycle(0)


# =========================================================================
# IR sensor reading
# =========================================================================
def read_ir_sensors() -> list:
    """Read all 5 IR sensors; returns [S1, S2, S3, S4, S5] (0 or 1)."""
    return [GPIO.input(pin) for pin in IR_PINS]


def compute_error(readings: list) -> tuple:
    """
    Compute weighted positional error from raw IR readings.

    Returns (error, on_line, all_black):
        error     – weighted average: -2.0 (far left) … +2.0 (far right)
        on_line   – True if at least one sensor detects the line
        all_black – True if all 5 sensors detect (intersection)
    """
    active = sum(readings)
    all_black = (active == 5)
    on_line = (active > 0)

    if not on_line:
        return 0.0, False, False

    weighted = sum(w * v for w, v in zip(SENSOR_WEIGHTS, readings))
    error = weighted / active
    return error, on_line, all_black


# =========================================================================
# PID controller
# =========================================================================
class PID:
    """
    Simple PID controller.

    correction = Kp × error + Ki × ∫error·dt + Kd × d(error)/dt

    The output is clamped to ±max_output to prevent motor over-drive.
    """

    def __init__(self, kp: float, ki: float, kd: float, max_output: float = 40.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_output = max_output

        # State
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = time.time()
        self._integral_limit = PID_CFG.get("INTEGRAL_LIMIT", 50.0)

    def reset(self):
        """Zero accumulated state."""
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = time.time()

    def compute(self, error: float) -> float:
        """Run one PID iteration and return the correction value."""
        now = time.time()
        dt = now - self._prev_time
        if dt <= 0:
            return 0.0

        # Proportional
        p = self.kp * error

        # Integral (with anti-windup clamp)
        self._integral += error * dt
        self._integral = max(-self._integral_limit, min(self._integral_limit, self._integral))
        i = self.ki * self._integral

        # Derivative
        d = self.kd * (error - self._prev_error) / dt

        self._prev_error = error
        self._prev_time = now

        output = p + i + d
        return max(-self.max_output, min(self.max_output, output))


# =========================================================================
# Sensor-only mode
# =========================================================================
def run_sensor_only():
    """Continuously read and display IR sensor values – no motor output."""
    print()
    print("=" * 60)
    print("  SENSOR-ONLY MODE")
    print("  Reading IR array – move the robot over the line")
    print("  Press Ctrl-C to exit")
    print("=" * 60)
    print()
    print("  S1(L2)  S2(L1)  S3(C)  S4(R1)  S5(R2)   Error   OnLine")
    print("  ------  ------  -----  ------  ------   -----   ------")

    try:
        while True:
            raw = read_ir_sensors()
            error, on_line, all_black = compute_error(raw)

            status = "ALL-BLACK" if all_black else ("ON-LINE" if on_line else "LOST")
            bar = _error_bar(error)

            print(
                f"\r  {raw[0]:^6}  {raw[1]:^6}  {raw[2]:^5}  {raw[3]:^6}  {raw[4]:^6}"
                f"   {error:+5.2f}   {status:<9} {bar}",
                end="", flush=True,
            )
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n\n[OK] Sensor-only mode ended")


def _error_bar(error: float, width: int = 21) -> str:
    """Render a visual bar: ◄ left ──── centre ──── right ►"""
    mid = width // 2
    pos = int(mid + error * (mid / 2.0))
    pos = max(0, min(width - 1, pos))
    bar = list("─" * width)
    bar[mid] = "│"
    bar[pos] = "●"
    return "[" + "".join(bar) + "]"


# =========================================================================
# Interactive PID tuner
# =========================================================================
def run_pid_tuner(pwm_left, pwm_right, base_speed: float):
    """
    Line-following with live PID gain adjustment.

    Keys (entered in the terminal):
        q         – quit
        p <val>   – set Kp
        i <val>   – set Ki
        d <val>   – set Kd
        s <val>   – set base speed
        r         – reset PID state
    """
    import threading

    pid = PID(
        kp=PID_CFG["KP"],
        ki=PID_CFG["KI"],
        kd=PID_CFG["KD"],
        max_output=PID_CFG["MAX_CORRECTION"],
    )

    running = True

    def input_loop():
        nonlocal running, base_speed
        print()
        print("PID tuner commands:  p <val> | i <val> | d <val> | s <speed> | r | q")
        while running:
            try:
                cmd = input("> ").strip().lower()
            except EOFError:
                break
            if cmd == "q":
                running = False
            elif cmd == "r":
                pid.reset()
                print(f"  PID reset.  Kp={pid.kp}  Ki={pid.ki}  Kd={pid.kd}")
            elif cmd.startswith("p "):
                pid.kp = float(cmd.split()[1])
                print(f"  Kp = {pid.kp}")
            elif cmd.startswith("i "):
                pid.ki = float(cmd.split()[1])
                print(f"  Ki = {pid.ki}")
            elif cmd.startswith("d "):
                pid.kd = float(cmd.split()[1])
                print(f"  Kd = {pid.kd}")
            elif cmd.startswith("s "):
                base_speed = float(cmd.split()[1])
                print(f"  base_speed = {base_speed}")
            else:
                print("  Unknown command. Use: p/i/d <val>, s <speed>, r, q")

    input_thread = threading.Thread(target=input_loop, daemon=True)
    input_thread.start()

    last_known_error = 0.0
    line_lost_since = None

    print()
    print("=" * 60)
    print("  PID TUNER – line following with live gain adjustment")
    print(f"  Kp={pid.kp}  Ki={pid.ki}  Kd={pid.kd}  speed={base_speed}")
    print("  Press Ctrl-C or type 'q' to stop")
    print("=" * 60)

    try:
        while running:
            raw = read_ir_sensors()
            error, on_line, all_black = compute_error(raw)

            if all_black:
                # Intersection – slow down, go straight
                set_motors(pwm_left, pwm_right, base_speed * 0.5, base_speed * 0.5)
                time.sleep(LF_CFG["ALL_BLACK_PAUSE"])
                continue

            if not on_line:
                # Line lost – search
                if line_lost_since is None:
                    line_lost_since = time.time()
                elapsed = time.time() - line_lost_since
                if elapsed > LF_CFG["LOST_LINE_TIMEOUT"]:
                    stop_motors(pwm_left, pwm_right)
                    print("\n  !! LINE LOST – motors stopped. Reposition robot.")
                    time.sleep(1.0)
                    line_lost_since = None
                    continue

                search_speed = LF_CFG["SEARCH_TURN_SPEED"]
                if last_known_error <= 0:
                    set_motors(pwm_left, pwm_right, -search_speed, search_speed)
                else:
                    set_motors(pwm_left, pwm_right, search_speed, -search_speed)
                time.sleep(LF_CFG["LOOP_INTERVAL"])
                continue
            else:
                line_lost_since = None

            # PID correction
            correction = pid.compute(error)
            left = base_speed + correction
            right = base_speed - correction
            set_motors(pwm_left, pwm_right, left, right)

            last_known_error = error
            time.sleep(LF_CFG["LOOP_INTERVAL"])

    except KeyboardInterrupt:
        pass
    finally:
        running = False
        stop_motors(pwm_left, pwm_right)
        print("\n[OK] PID tuner ended")


# =========================================================================
# Standard line-following
# =========================================================================
def run_line_follow(pwm_left, pwm_right, base_speed: float):
    """
    PID line-following main loop.

    Algorithm:
        1. Read 5 IR sensors → raw readings [0/1, 0/1, 0/1, 0/1, 0/1]
        2. Compute weighted error using weights [-2, -1, 0, +1, +2]
        3. Feed error into PID → correction value
        4. Set motor speeds: left = base + correction, right = base - correction
        5. Handle edge cases: line lost → search spin, intersection → slow pass
        6. Repeat at 50 Hz
    """
    pid = PID(
        kp=PID_CFG["KP"],
        ki=PID_CFG["KI"],
        kd=PID_CFG["KD"],
        max_output=PID_CFG["MAX_CORRECTION"],
    )

    last_known_error = 0.0
    line_lost_since = None
    loop_count = 0
    start_time = time.time()

    print()
    print("=" * 60)
    print("  LINE-FOLLOWING MODE (real hardware)")
    print(f"  Base speed : {base_speed}")
    print(f"  PID gains  : Kp={pid.kp}  Ki={pid.ki}  Kd={pid.kd}")
    print(f"  Loop rate  : {1.0 / LF_CFG['LOOP_INTERVAL']:.0f} Hz")
    print("  Press Ctrl-C to stop")
    print("=" * 60)
    print()
    print("  Sensors         Error   Correction  L-Motor  R-Motor  Status")
    print("  ───────         ─────   ──────────  ───────  ───────  ──────")

    try:
        while True:
            raw = read_ir_sensors()
            error, on_line, all_black = compute_error(raw)
            loop_count += 1

            # ── Intersection (all sensors on) ────────────────────────
            if all_black:
                set_motors(pwm_left, pwm_right, base_speed * 0.5, base_speed * 0.5)
                status = "INTERSECT"
                _print_telemetry(raw, error, 0.0, base_speed * 0.5, base_speed * 0.5, status)
                time.sleep(LF_CFG["ALL_BLACK_PAUSE"])
                pid.reset()  # prevent integral windup from pause
                continue

            # ── Line lost ────────────────────────────────────────────
            if not on_line:
                if line_lost_since is None:
                    line_lost_since = time.time()

                elapsed = time.time() - line_lost_since

                # Give up after timeout
                if elapsed > LF_CFG["LOST_LINE_TIMEOUT"]:
                    stop_motors(pwm_left, pwm_right)
                    status = "LOST-STOP"
                    _print_telemetry(raw, 0.0, 0.0, 0.0, 0.0, status)
                    print(f"\n  !! Line lost for {elapsed:.1f}s – motors stopped. Reposition and press Enter...")
                    try:
                        input()
                    except EOFError:
                        break
                    line_lost_since = None
                    pid.reset()
                    continue

                # Search: spin toward last known error direction
                search = LF_CFG["SEARCH_TURN_SPEED"]
                if last_known_error <= 0:
                    left_s, right_s = -search, search
                else:
                    left_s, right_s = search, -search

                set_motors(pwm_left, pwm_right, left_s, right_s)
                status = f"SEARCH {elapsed:.1f}s"
                _print_telemetry(raw, last_known_error, 0.0, left_s, right_s, status)
                time.sleep(LF_CFG["LOOP_INTERVAL"])
                continue
            else:
                line_lost_since = None

            # ── PID correction ───────────────────────────────────────
            correction = pid.compute(error)
            left_speed = base_speed + correction
            right_speed = base_speed - correction

            set_motors(pwm_left, pwm_right, left_speed, right_speed)
            last_known_error = error

            status = "TRACKING"
            _print_telemetry(raw, error, correction, left_speed, right_speed, status)

            time.sleep(LF_CFG["LOOP_INTERVAL"])

    except KeyboardInterrupt:
        pass
    finally:
        stop_motors(pwm_left, pwm_right)
        elapsed = time.time() - start_time
        hz = loop_count / elapsed if elapsed > 0 else 0
        print(f"\n\n[OK] Line following ended – {loop_count} loops in {elapsed:.1f}s ({hz:.1f} Hz)")


def _print_telemetry(raw, error, correction, left, right, status):
    """Single-line telemetry output (overwrites current line)."""
    sensors_str = "".join("█" if v else "░" for v in raw)
    print(
        f"\r  [{sensors_str}]  {error:+5.2f}     {correction:+6.2f}"
        f"      {left:5.1f}    {right:5.1f}    {status:<12}",
        end="", flush=True,
    )


# =========================================================================
# Motor self-test
# =========================================================================
def run_motor_test(pwm_left, pwm_right):
    """Quick motor sanity check – each direction for 1 second."""
    print()
    print("=" * 60)
    print("  MOTOR SELF-TEST")
    print("  Each direction runs for 1 second at low speed")
    print("=" * 60)

    tests = [
        ("Forward",  40,  40),
        ("Backward", -40, -40),
        ("Left",     -35,  35),
        ("Right",     35, -35),
    ]

    for name, left, right in tests:
        print(f"  {name:10s} ... ", end="", flush=True)
        set_motors(pwm_left, pwm_right, left, right)
        time.sleep(1.0)
        stop_motors(pwm_left, pwm_right)
        print("OK")
        time.sleep(0.5)

    print("\n[OK] Motor test complete")


# =========================================================================
# Main
# =========================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Test PID line-following on REAL Raspberry Pi hardware",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_line_follow_hardware.py                  # basic line follow
  python test_line_follow_hardware.py --speed 55       # faster
  python test_line_follow_hardware.py --sensor-only    # IR sensors only
  python test_line_follow_hardware.py --tune           # interactive PID tuner
  python test_line_follow_hardware.py --motor-test     # test motor wiring
        """,
    )
    parser.add_argument("--speed", type=float, default=45.0, help="Base motor speed (0-100, default 45)")
    parser.add_argument("--sensor-only", action="store_true", help="Only read IR sensors (no motor output)")
    parser.add_argument("--tune", action="store_true", help="Interactive PID tuning mode")
    parser.add_argument("--motor-test", action="store_true", help="Quick motor direction self-test")
    parser.add_argument("--kp", type=float, default=None, help="Override Kp gain")
    parser.add_argument("--ki", type=float, default=None, help="Override Ki gain")
    parser.add_argument("--kd", type=float, default=None, help="Override Kd gain")
    args = parser.parse_args()

    # Override PID gains if provided
    if args.kp is not None:
        PID_CFG["KP"] = args.kp
    if args.ki is not None:
        PID_CFG["KI"] = args.ki
    if args.kd is not None:
        PID_CFG["KD"] = args.kd

    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     LINE-FOLLOWING HARDWARE TEST                          ║")
    print("║     Raspberry Pi 4 + TCRT5000 IR + L298N Motors          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # --- Sensor-only mode doesn't need motor GPIO ---
    if args.sensor_only:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in IR_PINS:
            GPIO.setup(pin, GPIO.IN)
        print("[OK] IR sensor pins initialised")
        try:
            run_sensor_only()
        finally:
            GPIO.cleanup()
            print("[OK] GPIO cleaned up")
        return

    # --- Full GPIO setup (sensors + motors) ---
    pwm_left, pwm_right = setup_gpio()

    # Graceful Ctrl-C handler
    def signal_handler(sig, frame):
        print("\n\n  Caught Ctrl-C – stopping motors...")
        stop_motors(pwm_left, pwm_right)
        cleanup_gpio(pwm_left, pwm_right)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # --- Quick wiring check ---
        print("\n  Quick sensor check (place robot on/off line):")
        for _ in range(5):
            raw = read_ir_sensors()
            error, on_line, _ = compute_error(raw)
            bar = _error_bar(error)
            print(f"    Sensors: {raw}  Error: {error:+5.2f}  {bar}")
            time.sleep(0.3)

        if args.motor_test:
            run_motor_test(pwm_left, pwm_right)
        elif args.tune:
            run_pid_tuner(pwm_left, pwm_right, args.speed)
        else:
            run_line_follow(pwm_left, pwm_right, args.speed)

    except Exception as exc:
        print(f"\n\n  !! FATAL ERROR: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_gpio(pwm_left, pwm_right)


if __name__ == "__main__":
    main()
