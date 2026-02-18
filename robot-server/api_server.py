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
    SIMULATION_MODE, GPIO_PINS, MOTOR_SETTINGS, LOGGING as LOG_CFG
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
