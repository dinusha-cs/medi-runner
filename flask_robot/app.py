"""
Flask Robot Server – REST API for the line-following robot.

Endpoints overview
------------------

**Mode**
    POST /api/mode                  – switch between manual / autonomous
    GET  /api/mode                  – get current mode

**Manual movement** (only in manual mode)
    POST /api/move                  – move in a direction (forward/backward/left/right/stop)
    POST /api/emergency-stop        – immediate halt (works in ANY mode)
    POST /api/speed                 – set default speed

**Autonomous (line-following)**
    POST /api/line-follow/start     – start autonomous line following
    POST /api/line-follow/stop      – stop line following
    GET  /api/line-follow/status    – PID & sensor status

**PID tuning**
    GET  /api/pid                   – current PID gains
    POST /api/pid                   – update PID gains
    POST /api/pid/reset             – zero PID state

**Sensors**
    GET  /api/sensors/ir            – raw + computed IR sensor data
    POST /api/sensors/ir/simulate   – set simulated IR readings (sim mode)

**Camera**
    GET  /api/camera/stream         – MJPEG live stream
    GET  /api/camera/snapshot       – single JPEG frame
    GET  /api/camera/status         – camera info

**Zone detection**
    GET  /api/zones/detect          – run zone detection on current frame
    GET  /api/zones/status          – detector config & last results

**Logging**
    GET  /api/logs                  – retrieve activity logs
    DELETE /api/logs                – clear in-memory logs
    GET  /api/logs/stats            – logging stats

**Errors**
    GET  /api/errors                – recent error records
    DELETE /api/errors              – clear error history

**System**
    GET  /api/status                – comprehensive robot status
    POST /api/shutdown              – graceful shutdown
"""

import logging
import signal
import time

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

# ── Local imports ────────────────────────────────────────────────────────
from config import (
    FLASK_HOST, FLASK_PORT, SIMULATION_MODE, DEBUG,
    GPIO_PINS, MOTOR, CAMERA, ZONE_COLOURS, ZONE_MIN_AREA,
    PID as PID_CFG, LOGGING as LOG_CFG,
)
from hardware.gpio_manager import GPIO, GPIOManager
from hardware.motor_driver import MotorDriver
from hardware.ir_sensor import IRSensorArray
from controllers.motor_controller import MotorController
from controllers.line_follower import LineFollower
from controllers.mode_manager import ModeManager, RobotMode
from vision.camera import Camera
from vision.zone_detector import ZoneDetector
from core.error_recovery import RecoveryManager
from core.activity_logger import ActivityLogger

# ── Logging bootstrap ────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_CFG["LEVEL"]),
    format=LOG_CFG["FORMAT"],
    datefmt=LOG_CFG.get("DATE_FORMAT"),
)
logger = logging.getLogger("FlaskRobotServer")

# =========================================================================
# Subsystem initialisation
# =========================================================================

# GPIO
gpio_manager = GPIOManager(simulation=SIMULATION_MODE)
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Motors
motor_driver = MotorDriver(pin_cfg=GPIO_PINS, gpio=gpio_manager, pwm_freq=MOTOR["PWM_FREQUENCY"])
motor_driver.initialise()
motor_ctrl = MotorController(motor_driver)

# IR sensors
ir_sensors = IRSensorArray(pin_cfg=GPIO_PINS, gpio=gpio_manager, simulation=SIMULATION_MODE)
ir_sensors.initialise()

# Line follower (autonomous)
activity = ActivityLogger()
recovery = RecoveryManager(emergency_stop_fn=lambda: motor_ctrl.emergency_stop())

def _on_line_follow_error(msg: str):
    """Callback when autonomous line-following fails irrecoverably."""
    recovery.record_error("line_follower", msg)
    activity.log("error", "line_follow_fail", msg, level="ERROR")

line_follower = LineFollower(motor_driver, ir_sensors, on_error=_on_line_follow_error)

# Mode manager
mode_mgr = ModeManager(motor_ctrl, line_follower)

# Camera
camera = Camera(config=CAMERA, simulation=SIMULATION_MODE)
camera.start()

# Zone detector
zone_detector = ZoneDetector(zone_colours=ZONE_COLOURS, min_area=ZONE_MIN_AREA)

# Watchdog health-checks
recovery.register_health_check("motor", lambda: motor_driver.is_initialised)
recovery.register_health_check("camera", lambda: camera._running)
recovery.start_watchdog()

# Record system start
_start_time = time.time()
activity.log("system", "startup", f"simulation={SIMULATION_MODE}")

# =========================================================================
# Flask app
# =========================================================================

app = Flask(__name__)
CORS(app)  # allow requests from any origin (web app)


# ── Helpers ──────────────────────────────────────────────────────────────

def _json_ok(data: dict = None, message: str = "ok", status: int = 200):
    """Standard success response."""
    payload = {"success": True, "message": message}
    if data:
        payload["data"] = data
    return jsonify(payload), status


def _json_error(message: str, status: int = 400):
    """Standard error response."""
    return jsonify({"success": False, "error": message}), status


# =========================================================================
# MODE endpoints
# =========================================================================

@app.route("/api/mode", methods=["GET"])
def get_mode():
    """Return the current operating mode."""
    return _json_ok(mode_mgr.get_status())


@app.route("/api/mode", methods=["POST"])
def set_mode():
    """
    Switch mode.

    JSON body::

        { "mode": "manual" | "autonomous", "base_speed": 50 }
    """
    body = request.get_json(silent=True) or {}
    mode_str = body.get("mode", "").lower()

    if mode_str not in ("manual", "autonomous"):
        return _json_error("'mode' must be 'manual' or 'autonomous'")

    target = RobotMode.MANUAL if mode_str == "manual" else RobotMode.AUTONOMOUS
    base_speed = body.get("base_speed")

    result = mode_mgr.set_mode(target, base_speed=base_speed)
    activity.log("mode", "switch", f"→ {mode_str}")
    return _json_ok(result, message=f"Mode set to {mode_str}")


# =========================================================================
# MANUAL MOVEMENT endpoints
# =========================================================================

@app.route("/api/move", methods=["POST"])
def move():
    """
    Move the robot (manual mode only).

    JSON body::

        { "direction": "forward"|"backward"|"left"|"right"|"stop",
          "speed": 60,
          "duration": 0 }
    """
    body = request.get_json(silent=True) or {}
    direction = body.get("direction", "").lower()
    speed = body.get("speed")
    duration = body.get("duration", 0)

    if not direction:
        return _json_error("'direction' is required")

    try:
        mode_mgr.require_manual()
    except RuntimeError as exc:
        return _json_error(str(exc), 409)

    try:
        result = motor_ctrl.move(direction, speed=speed, duration=duration)
        activity.log("motor", direction, f"speed={result['speed']}, dur={duration}")
        return _json_ok(result)
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:
        recovery.record_error("motor", str(exc), exc)
        return _json_error(f"Move failed: {exc}", 500)


@app.route("/api/emergency-stop", methods=["POST"])
def emergency_stop():
    """Immediate halt – works in ANY mode."""
    # Also stop line-follower if running
    if line_follower.is_running:
        line_follower.stop()
    result = motor_ctrl.emergency_stop()
    # Force mode to manual after e-stop
    mode_mgr.set_mode(RobotMode.MANUAL)
    activity.log("motor", "emergency_stop", "all motors halted", level="WARNING")
    return _json_ok(result, message="Emergency stop executed")


@app.route("/api/speed", methods=["POST"])
def set_speed():
    """
    Set default movement speed.

    JSON body::

        { "speed": 65 }
    """
    body = request.get_json(silent=True) or {}
    speed = body.get("speed")
    if speed is None:
        return _json_error("'speed' is required")

    result = motor_ctrl.set_speed(float(speed))
    activity.log("motor", "set_speed", f"speed={result['default_speed']}")
    return _json_ok(result)


# =========================================================================
# LINE-FOLLOWING endpoints
# =========================================================================

@app.route("/api/line-follow/start", methods=["POST"])
def line_follow_start():
    """
    Start autonomous line following.

    JSON body (optional)::

        { "base_speed": 50 }
    """
    body = request.get_json(silent=True) or {}
    base_speed = body.get("base_speed")

    # Auto-switch to autonomous mode
    mode_mgr.set_mode(RobotMode.AUTONOMOUS, base_speed=base_speed)
    activity.log("line_follow", "start", f"base_speed={base_speed}")
    return _json_ok(line_follower.get_status(), message="Line following started")


@app.route("/api/line-follow/stop", methods=["POST"])
def line_follow_stop():
    """Stop autonomous line following and switch to manual."""
    mode_mgr.set_mode(RobotMode.MANUAL)
    activity.log("line_follow", "stop", "switched to manual")
    return _json_ok(line_follower.get_status(), message="Line following stopped")


@app.route("/api/line-follow/status", methods=["GET"])
def line_follow_status():
    """Get line-follower and IR sensor status."""
    return _json_ok({
        "line_follower": line_follower.get_status(),
        "ir_sensors": ir_sensors.get_status(),
    })


# =========================================================================
# PID TUNING endpoints
# =========================================================================

@app.route("/api/pid", methods=["GET"])
def get_pid():
    """Return current PID gains."""
    return _json_ok(line_follower.get_pid_gains())


@app.route("/api/pid", methods=["POST"])
def set_pid():
    """
    Update PID gains.

    JSON body::

        { "kp": 25.0, "ki": 0.01, "kd": 15.0 }
    """
    body = request.get_json(silent=True) or {}
    gains = line_follower.set_pid_gains(
        kp=body.get("kp"),
        ki=body.get("ki"),
        kd=body.get("kd"),
    )
    activity.log("pid", "update", f"kp={gains['kp']} ki={gains['ki']} kd={gains['kd']}")
    return _json_ok(gains, message="PID gains updated")


@app.route("/api/pid/reset", methods=["POST"])
def reset_pid():
    """Zero accumulated PID integral and derivative state."""
    line_follower.reset_pid()
    activity.log("pid", "reset", "integral/derivative zeroed")
    return _json_ok(message="PID state reset")


# =========================================================================
# SENSOR endpoints
# =========================================================================

@app.route("/api/sensors/ir", methods=["GET"])
def get_ir_sensors():
    """Return raw IR readings plus computed error."""
    return _json_ok(ir_sensors.get_status())


@app.route("/api/sensors/ir/simulate", methods=["POST"])
def simulate_ir():
    """
    Set simulated IR sensor values (simulation mode only).

    JSON body::

        { "readings": [0, 0, 1, 0, 0] }
    """
    if not SIMULATION_MODE:
        return _json_error("Simulation endpoint only available in simulation mode", 403)

    body = request.get_json(silent=True) or {}
    readings = body.get("readings")
    if not readings or len(readings) != 5:
        return _json_error("'readings' must be a list of 5 integers (0 or 1)")

    ir_sensors.set_simulated_readings(readings)
    activity.log("sensors", "simulate_ir", f"readings={readings}")
    return _json_ok(ir_sensors.get_status(), message="Simulated IR values set")


# =========================================================================
# CAMERA endpoints
# =========================================================================

@app.route("/api/camera/stream")
def camera_stream():
    """MJPEG live video stream – embed in an <img> tag on the web app."""
    return Response(
        camera.generate_mjpeg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/api/camera/snapshot")
def camera_snapshot():
    """Return a single JPEG frame."""
    frame = camera.get_frame()
    if frame is None:
        return _json_error("No frame available", 503)
    return Response(frame, mimetype="image/jpeg")


@app.route("/api/camera/status")
def camera_status():
    """Camera information."""
    return _json_ok(camera.get_status())


# =========================================================================
# ZONE DETECTION endpoints
# =========================================================================

@app.route("/api/zones/detect", methods=["GET"])
def detect_zones():
    """
    Run colour-based zone detection on the current camera frame.

    Returns a list of detected zones with bounding boxes and confidence.
    """
    raw = camera.get_raw_frame()
    if raw is None:
        return _json_error("No camera frame available for detection", 503)

    detections = zone_detector.detect(raw)
    if detections:
        activity.log("zone", "detect", f"found {len(detections)}: {[d['zone'] for d in detections]}")
    return _json_ok({"detections": detections, "count": len(detections)})


@app.route("/api/zones/status", methods=["GET"])
def zone_status():
    """Zone detector configuration and last results."""
    return _json_ok(zone_detector.get_status())


# =========================================================================
# LOGGING endpoints
# =========================================================================

@app.route("/api/logs", methods=["GET"])
def get_logs():
    """
    Retrieve activity logs.

    Query params::

        ?limit=50        – max entries (default 50)
        &category=motor  – filter by category
        &level=ERROR     – filter by level
        &since=1700000000 – Unix timestamp
    """
    limit = request.args.get("limit", 50, type=int)
    category = request.args.get("category")
    level = request.args.get("level")
    since = request.args.get("since", type=float)

    logs = activity.get_logs(limit=limit, category=category, level=level, since=since)
    return _json_ok({"logs": logs, "count": len(logs)})


@app.route("/api/logs", methods=["DELETE"])
def clear_logs():
    """Clear the in-memory activity log buffer."""
    removed = activity.clear()
    return _json_ok({"removed": removed}, message="Activity logs cleared")


@app.route("/api/logs/stats", methods=["GET"])
def log_stats():
    """Logging statistics."""
    return _json_ok(activity.get_stats())


# =========================================================================
# ERROR endpoints
# =========================================================================

@app.route("/api/errors", methods=["GET"])
def get_errors():
    """
    Retrieve error records.

    Query params::

        ?limit=50
        &source=motor
    """
    limit = request.args.get("limit", 50, type=int)
    source = request.args.get("source")
    errors = recovery.get_errors(limit=limit, source=source)
    return _json_ok({"errors": errors, "count": len(errors)})


@app.route("/api/errors", methods=["DELETE"])
def clear_errors():
    """Clear all error records."""
    removed = recovery.clear_errors()
    return _json_ok({"removed": removed}, message="Error records cleared")


# =========================================================================
# SYSTEM endpoints
# =========================================================================

@app.route("/api/status", methods=["GET"])
def system_status():
    """Comprehensive robot status – mode, motors, sensors, camera, errors."""
    return _json_ok({
        "uptime": round(time.time() - _start_time, 1),
        "simulation": SIMULATION_MODE,
        "mode": mode_mgr.get_status(),
        "motors": motor_ctrl.get_status(),
        "ir_sensors": ir_sensors.get_status(),
        "line_follower": line_follower.get_status(),
        "camera": camera.get_status(),
        "zone_detector": zone_detector.get_status(),
        "recovery": recovery.get_status(),
        "logging": activity.get_stats(),
    })


@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    """Graceful shutdown – stop all subsystems and exit."""
    activity.log("system", "shutdown", "shutdown requested via API", level="WARNING")
    _cleanup()
    # Signal Flask to stop (works with Werkzeug dev server)
    func = request.environ.get("werkzeug.server.shutdown")
    if func:
        func()
    return _json_ok(message="Robot server shutting down")


# =========================================================================
# Cleanup
# =========================================================================

def _cleanup():
    """Stop all subsystems safely."""
    logger.info("Cleaning up all subsystems...")
    try:
        line_follower.stop()
    except Exception:
        pass
    try:
        motor_driver.stop()
    except Exception:
        pass
    try:
        camera.stop()
    except Exception:
        pass
    try:
        recovery.stop_watchdog()
    except Exception:
        pass
    try:
        gpio_manager.cleanup()
    except Exception:
        pass
    logger.info("Cleanup complete")


# Register signal handlers for clean shutdown
def _signal_handler(sig, frame):
    logger.info("Received signal %s – shutting down", sig)
    _cleanup()
    raise SystemExit(0)


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# =========================================================================
# Entry point
# =========================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  Line-Following Robot Flask Server")
    logger.info("  Host: %s:%d  Simulation: %s", FLASK_HOST, FLASK_PORT, SIMULATION_MODE)
    logger.info("=" * 60)
    try:
        app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=DEBUG,
            threaded=True,
            use_reloader=False,  # reloader conflicts with GPIO/threads
        )
    finally:
        _cleanup()
