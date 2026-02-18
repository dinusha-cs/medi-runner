#!/usr/bin/env python3
"""
Medi Runner Robot REST API Server
Exposes HTTP endpoints for robot movement control.

Hardware:
    - Raspberry Pi 4 (8GB)
    - L298N Motor Driver
    - TCRT5000 IR Array
    - LM2596 Buck Converter
    - 5V Active Buzzer (GPIO 24)
    - Camera V1.3 5MP
    - Power pack (2x 8650 batteries)

Endpoints:
    POST /api/robot/forward   - Move forward
    POST /api/robot/backward  - Move backward
    POST /api/robot/left      - Turn left
    POST /api/robot/right     - Turn right
    POST /api/robot/stop      - Stop movement
    GET  /api/robot/status    - Get robot status
    POST /api/robot/buzzer    - Activate buzzer
    GET  /api/robot/voltage   - Get Raspberry Pi input voltage
    GET  /api/robot/sensors/ir - Read IR sensor array
    GET  /api/robot/mode      - Get current mode
    POST /api/robot/mode      - Switch mode (manual/autonomous)
    GET  /api/robot/camera/stream    - Live MJPEG video stream
    GET  /api/robot/camera/snapshot  - Single JPEG capture
    POST /api/robot/camera/panoramic - Capture 360° panoramic photo
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add current directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    SIMULATION_MODE, GPIO_PINS, MOTOR_SETTINGS, LOGGING as LOG_CFG,
    CAMERA_RESOLUTION, CAMERA_FPS, CAMERA_ROTATION,
)
from robot.motor_controller import MotorController
from robot.sensor_controller import SensorController

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, LOG_CFG.get("LEVEL", "INFO")),
    format=LOG_CFG.get("FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
)
logger = logging.getLogger("APIServer")

# ---------------------------------------------------------------------------
# GPIO buzzer helper (thin wrapper – keeps motor controller focused on motors)
# ---------------------------------------------------------------------------
try:
    import RPi.GPIO as GPIO
except ImportError:
    # Mock for dev / test environments
    class _MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        HIGH = 1
        LOW = 0

        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode): pass
        @staticmethod
        def output(pin, state): pass
        @staticmethod
        def cleanup(pin=None): pass

    GPIO = _MockGPIO()

BUZZER_PIN = GPIO_PINS.get("BUZZER", 24)


async def _buzz(times: int = 1, duration: float = 0.3):
    """Activate the buzzer *times* times."""
    if not SIMULATION_MODE:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)
    for i in range(times):
        if not SIMULATION_MODE:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
        logger.debug(f"BUZZ {i + 1}/{times}")
        await asyncio.sleep(duration)
        if not SIMULATION_MODE:
            GPIO.output(BUZZER_PIN, GPIO.LOW)
        if i < times - 1:
            await asyncio.sleep(duration)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class MoveRequest(BaseModel):
    speed: int = Field(default=50, ge=0, le=100, description="Speed percentage 0-100")
    duration: float = Field(default=0, ge=0, description="Duration in seconds (0 = continuous)")


class BuzzerRequest(BaseModel):
    times: int = Field(default=1, ge=1, le=10, description="Number of beeps")
    duration: float = Field(default=0.3, ge=0.05, le=2.0, description="Beep duration in seconds")


class ModeRequest(BaseModel):
    mode: str = Field(..., pattern="^(manual|autonomous)$", description="'manual' or 'autonomous'")


class RobotResponse(BaseModel):
    success: bool
    action: str
    message: str
    data: Optional[dict] = None
    timestamp: float


# ---------------------------------------------------------------------------
# Application lifespan – initialise & tear-down the motor controller
# ---------------------------------------------------------------------------
motor: Optional[MotorController] = None
sensors: Optional[SensorController] = None
robot_mode: str = "manual"  # "manual" | "autonomous"


# ---------------------------------------------------------------------------
# IR sensor direct GPIO reader (TCRT5000 – digital, 0 = line, 1 = floor)
# ---------------------------------------------------------------------------
IR_PINS = [
    GPIO_PINS.get("IR_SENSOR_1", 5),
    GPIO_PINS.get("IR_SENSOR_2", 6),
    GPIO_PINS.get("IR_SENSOR_3", 13),
    GPIO_PINS.get("IR_SENSOR_4", 19),
    GPIO_PINS.get("IR_SENSOR_5", 26),
]

try:
    import RPi.GPIO as _GPIO_IR
except ImportError:
    _GPIO_IR = GPIO  # use the mock already defined above

_ir_initialized = False


def _ensure_ir_gpio():
    global _ir_initialized
    if _ir_initialized or SIMULATION_MODE:
        return
    _GPIO_IR.setwarnings(False)
    _GPIO_IR.setmode(_GPIO_IR.BCM)
    for pin in IR_PINS:
        _GPIO_IR.setup(pin, _GPIO_IR.IN if hasattr(_GPIO_IR, "IN") else _GPIO_IR.OUT)
    _ir_initialized = True


def read_ir_sensors() -> list[int]:
    """Return 5-element list [S1..S5]. 0 = black line, 1 = white floor."""
    if SIMULATION_MODE:
        import random
        # Simulate robot roughly on the line
        patterns = [
            [1, 1, 0, 1, 1],
            [1, 0, 0, 1, 1],
            [1, 1, 0, 0, 1],
            [0, 0, 1, 1, 1],
            [1, 1, 1, 0, 0],
        ]
        return random.choice(patterns)
    _ensure_ir_gpio()
    return [_GPIO_IR.input(pin) for pin in IR_PINS]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global motor, sensors
    motor = MotorController(simulation_mode=SIMULATION_MODE)
    sensors = SensorController(simulation_mode=SIMULATION_MODE)
    await motor.initialize()
    await sensors.initialize()
    logger.info(
        f"Robot API started – simulation={SIMULATION_MODE}, "
        f"motor pins IN1={GPIO_PINS['MOTOR_IN1']}, IN2={GPIO_PINS['MOTOR_IN2']}, "
        f"IN3={GPIO_PINS['MOTOR_IN3']}, IN4={GPIO_PINS['MOTOR_IN4']}, "
        f"ENA={GPIO_PINS['MOTOR_ENA']}, ENB={GPIO_PINS['MOTOR_ENB']}, "
        f"IR={IR_PINS}, buzzer={BUZZER_PIN}"
    )
    yield
    await motor.cleanup()
    await sensors.cleanup()
    logger.info("Robot API shut down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Medi-Runner Robot Controller API",
    description="REST API for controlling the Medi-Runner robot movement, buzzer, and status.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _response(success: bool, action: str, message: str, data: dict | None = None) -> RobotResponse:
    return RobotResponse(
        success=success,
        action=action,
        message=message,
        data=data,
        timestamp=time.time(),
    )


def _get_motor() -> MotorController:
    if motor is None or not motor.is_initialized:
        raise HTTPException(status_code=503, detail="Motor controller not initialised")
    return motor


# ---------------------------------------------------------------------------
# Movement endpoints
# ---------------------------------------------------------------------------
@app.post("/api/robot/forward", response_model=RobotResponse)
async def move_forward(req: MoveRequest = MoveRequest()):
    """Move the robot forward."""
    m = _get_motor()
    result = await m.move("forward", req.speed, req.duration)
    return _response(True, "forward", f"Moving forward at {req.speed}% speed", result)


@app.post("/api/robot/backward", response_model=RobotResponse)
async def move_backward(req: MoveRequest = MoveRequest()):
    """Move the robot backward."""
    m = _get_motor()
    result = await m.move("backward", req.speed, req.duration)
    return _response(True, "backward", f"Moving backward at {req.speed}% speed", result)


@app.post("/api/robot/left", response_model=RobotResponse)
async def move_left(req: MoveRequest = MoveRequest()):
    """Turn the robot left."""
    m = _get_motor()
    result = await m.move("left", req.speed, req.duration)
    return _response(True, "left", f"Turning left at {req.speed}% speed", result)


@app.post("/api/robot/right", response_model=RobotResponse)
async def move_right(req: MoveRequest = MoveRequest()):
    """Turn the robot right."""
    m = _get_motor()
    result = await m.move("right", req.speed, req.duration)
    return _response(True, "right", f"Turning right at {req.speed}% speed", result)


@app.post("/api/robot/stop", response_model=RobotResponse)
async def stop_robot():
    """Stop all robot movement."""
    m = _get_motor()
    result = await m.stop()
    return _response(True, "stop", "Robot stopped", result)


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------
@app.get("/api/robot/status", response_model=RobotResponse)
async def get_status():
    """Get current robot status including motor speeds, position, and diagnostics."""
    m = _get_motor()
    status = await m.get_status()
    return _response(True, "status", "Robot status retrieved", status)


# ---------------------------------------------------------------------------
# Buzzer endpoint
# ---------------------------------------------------------------------------
@app.post("/api/robot/buzzer", response_model=RobotResponse)
async def activate_buzzer(req: BuzzerRequest = BuzzerRequest()):
    """Activate the buzzer (GPIO 24)."""
    await _buzz(req.times, req.duration)
    return _response(
        True,
        "buzzer",
        f"Buzzer activated {req.times} time(s)",
        {"times": req.times, "duration": req.duration, "pin": BUZZER_PIN},
    )


# ---------------------------------------------------------------------------
# IR Sensor endpoint
# ---------------------------------------------------------------------------
@app.get("/api/robot/sensors/ir", response_model=RobotResponse)
async def get_ir_sensors():
    """Read the 5-channel TCRT5000 IR array.  0 = black line, 1 = white floor."""
    readings = read_ir_sensors()
    return _response(
        True,
        "ir_sensor",
        "IR sensor array read",
        {
            "sensors": readings,
            "labels": ["S1_far_left", "S2_left", "S3_center", "S4_right", "S5_far_right"],
            "pins": IR_PINS,
        },
    )


# ---------------------------------------------------------------------------
# Voltage endpoint – Raspberry Pi supply voltage
# ---------------------------------------------------------------------------
@app.get("/api/robot/voltage", response_model=RobotResponse)
async def get_voltage():
    """
    Read current Raspberry Pi input voltage.

    Uses ``vcgencmd measure_volts core`` and ``/sys/class/thermal/thermal_zone0/temp``
    to report supply voltage and CPU temperature.
    """
    import subprocess

    voltage = None
    cpu_temp = None
    throttled = None

    if SIMULATION_MODE:
        voltage = 5.1
        cpu_temp = 42.0
        throttled = "0x0"
    else:
        try:
            raw = subprocess.check_output(
                ["vcgencmd", "measure_volts", "core"], timeout=2
            ).decode().strip()                             # e.g. "volt=1.3500V"
            voltage = float(raw.split("=")[1].rstrip("V"))
        except Exception as exc:
            logger.warning(f"vcgencmd voltage read failed: {exc}")

        try:
            raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
            cpu_temp = int(raw) / 1000.0                   # millidegrees → °C
        except Exception as exc:
            logger.warning(f"CPU temp read failed: {exc}")

        try:
            raw = subprocess.check_output(
                ["vcgencmd", "get_throttled"], timeout=2
            ).decode().strip()                             # e.g. "throttled=0x0"
            throttled = raw.split("=")[1]
        except Exception:
            pass

    return _response(True, "voltage", "Raspberry Pi voltage info", {
        "core_voltage_v": voltage,
        "cpu_temp_c": cpu_temp,
        "throttled": throttled,
    })


# ---------------------------------------------------------------------------
# Mode endpoint (manual / autonomous)
# ---------------------------------------------------------------------------
@app.get("/api/robot/mode", response_model=RobotResponse)
async def get_mode():
    """Get the current robot operating mode."""
    return _response(True, "mode", f"Current mode: {robot_mode}", {"mode": robot_mode})


@app.post("/api/robot/mode", response_model=RobotResponse)
async def set_mode(req: ModeRequest):
    """Switch between manual and autonomous mode."""
    global robot_mode
    old = robot_mode
    robot_mode = req.mode
    logger.info(f"Mode changed: {old} -> {robot_mode}")
    return _response(
        True,
        "mode",
        f"Mode changed from {old} to {robot_mode}",
        {"mode": robot_mode, "previous": old},
    )


# ---------------------------------------------------------------------------
# Camera streaming (MJPEG)
# ---------------------------------------------------------------------------
# MJPEG is the simplest and most compatible way to stream video to a browser.
# The frontend connects directly via <img src="http://PI:8000/api/robot/camera/stream" />
# No WebSocket relay needed – browser-native, low-latency on local network.
# ---------------------------------------------------------------------------

from fastapi.responses import StreamingResponse, Response

# Try to import picamera2 (Raspberry Pi OS Bookworm) or fallback to legacy picamera
_camera = None
_camera_lock = asyncio.Lock()


def _init_camera():
    """Lazy-init the Pi camera. Returns a capture-callable or None."""
    global _camera
    if _camera is not None:
        return _camera

    if SIMULATION_MODE:
        # Return a dummy JPEG generator for dev/test
        import io
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            Image = None

        class _SimCamera:
            """Generate a placeholder JPEG frame with a timestamp."""
            def capture_frame(self) -> bytes:
                if Image is None:
                    # Minimal 1×1 black JPEG if Pillow not installed
                    return (
                        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00'
                        b'\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06'
                        b'\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r'
                        b'\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f'
                        b'\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f'
                        b"'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01"
                        b'\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01'
                        b'\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00'
                        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff'
                        b'\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03'
                        b'\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04'
                        b'\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1'
                        b'\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17'
                        b'\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghij'
                        b'stuvwxyz\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb'
                        b'R\xa8\xa0\x02\x80\x0f\xff\xd9'
                    )
                w, h = CAMERA_RESOLUTION
                img = Image.new("RGB", (w, h), (30, 30, 40))
                draw = ImageDraw.Draw(img)
                txt = f"SIMULATION  {time.strftime('%H:%M:%S')}"
                draw.text((w // 2 - 80, h // 2 - 10), txt, fill=(0, 255, 100))
                draw.rectangle([0, 0, w - 1, h - 1], outline=(0, 255, 100))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=70)
                return buf.getvalue()

        _camera = _SimCamera()
        return _camera

    # --- Real hardware ---
    try:
        from picamera2 import Picamera2
        cam = Picamera2()
        cam_config = cam.create_video_configuration(
            main={"size": CAMERA_RESOLUTION, "format": "RGB888"}
        )
        cam.configure(cam_config)
        cam.start()

        import io

        class _PiCamera2Wrapper:
            def capture_frame(self) -> bytes:
                import io as _io
                buf = _io.BytesIO()
                cam.capture_file(buf, format="jpeg")
                return buf.getvalue()

        _camera = _PiCamera2Wrapper()
        logger.info("Pi Camera initialised (picamera2)")
        return _camera

    except ImportError:
        pass

    try:
        import picamera

        class _LegacyPiCamera:
            def __init__(self):
                self.cam = picamera.PiCamera()
                self.cam.resolution = CAMERA_RESOLUTION
                self.cam.framerate = CAMERA_FPS
                self.cam.rotation = CAMERA_ROTATION

            def capture_frame(self) -> bytes:
                import io as _io
                buf = _io.BytesIO()
                self.cam.capture(buf, format="jpeg", use_video_port=True)
                return buf.getvalue()

        _camera = _LegacyPiCamera()
        logger.info("Pi Camera initialised (legacy picamera)")
        return _camera

    except ImportError:
        logger.warning("No camera library available – camera endpoints disabled")
        return None


async def _mjpeg_generator():
    """Yield JPEG frames as multipart/x-mixed-replace boundaries."""
    cam = _init_camera()
    if cam is None:
        return
    fps = CAMERA_FPS
    interval = 1.0 / fps
    while True:
        try:
            frame = cam.capture_frame()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(frame)).encode() + b"\r\n"
                b"\r\n" + frame + b"\r\n"
            )
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error(f"MJPEG frame error: {e}")
            await asyncio.sleep(0.5)


@app.get("/api/robot/camera/stream")
async def camera_stream():
    """
    Live MJPEG video stream from Pi Camera V1.3.

    Usage in browser / frontend:
        <img src="http://<pi-ip>:8000/api/robot/camera/stream" />

    This is the recommended way to display the live feed – works in all
    browsers, no JavaScript needed, ~100 ms latency on local WiFi.
    """
    cam = _init_camera()
    if cam is None:
        raise HTTPException(status_code=503, detail="Camera not available")
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/robot/camera/snapshot")
async def camera_snapshot():
    """
    Capture a single JPEG snapshot from the Pi Camera.

    Returns the raw JPEG image (Content-Type: image/jpeg).
    Useful for the 360° panoramic capture (take multiple snapshots while
    rotating) or for debugging.
    """
    cam = _init_camera()
    if cam is None:
        raise HTTPException(status_code=503, detail="Camera not available")
    frame = cam.capture_frame()
    return Response(content=frame, media_type="image/jpeg")


# ---------------------------------------------------------------------------
# 360° Panoramic photo capture
# ---------------------------------------------------------------------------
class PanoramicRequest(BaseModel):
    """Parameters for 360° panoramic capture."""
    steps: int = 12           # number of snapshots (360/steps = degrees per step)
    turn_speed: int = 40      # motor speed while turning
    turn_duration: float = 0.3  # seconds to turn between shots
    settle_delay: float = 0.2   # seconds to wait after turn before capture


@app.post("/api/robot/camera/panoramic", response_model=RobotResponse)
async def camera_panoramic(req: PanoramicRequest = PanoramicRequest()):
    """
    Capture a 360° panoramic set of images.

    The robot rotates in place, capturing a snapshot at each step.
    Returns a list of base64-encoded JPEG images that the frontend can
    stitch into a panorama.

    **Process:** turn right → pause → capture → repeat ``steps`` times.
    """
    import base64

    cam = _init_camera()
    if cam is None:
        raise HTTPException(status_code=503, detail="Camera not available")

    m = _get_motor()
    frames: list[dict] = []
    degrees_per_step = 360.0 / req.steps

    for i in range(req.steps):
        # Turn the robot one step
        if i > 0:
            await m.move("right", req.turn_speed, req.turn_duration)
            await asyncio.sleep(req.settle_delay)

        # Capture snapshot
        jpeg = cam.capture_frame()
        frames.append({
            "index": i,
            "angle_deg": round(i * degrees_per_step, 1),
            "jpeg_b64": base64.b64encode(jpeg).decode(),
        })

    return _response(True, "panoramic", f"Captured {req.steps} frames for 360° panorama", {
        "steps": req.steps,
        "degrees_per_step": degrees_per_step,
        "frames": frames,
    })


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "simulation_mode": SIMULATION_MODE, "timestamp": time.time()}


# ---------------------------------------------------------------------------
# Run with uvicorn when executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
