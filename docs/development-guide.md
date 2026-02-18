# Development Guide

## Quick Start

### Prerequisites

**Raspberry Pi Setup (bare metal):**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and system dependencies
sudo apt install -y python3-pip python3-venv python3-dev libopencv-dev

# Enable camera and GPIO
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable
# Navigate to: Interface Options → GPIO → Enable

# Reboot after enabling
sudo reboot
```

**Development Machine (optional — for remote editing):**
- VS Code with Remote-SSH extension
- Python 3.9+ (for linting / local tests with SIMULATION_MODE)

### Project Setup

1. **Clone and install dependencies**
```bash
git clone <repository-url>
cd medi-runner/robot-server

# Create virtual environment (recommended)
python3 -m venv ../env
source ../env/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

2. **Configure the robot**
```bash
# Copy and edit config
cp config.example.py config.py
nano config.py
```

Key settings in `config.py`:
```python
# Set True when developing without real hardware
SIMULATION_MODE = False

# GPIO pins (BCM numbering) — match your wiring
MOTOR_ENA = 20
MOTOR_IN1 = 23
MOTOR_IN2 = 22
MOTOR_IN3 = 27
MOTOR_IN4 = 17
MOTOR_ENB = 16

IR_SENSOR_PINS = [5, 6, 13, 19, 26]
BUZZER_PIN = 24

# Camera
CAMERA_RESOLUTION = (640, 480)
CAMERA_FPS = 30
CAMERA_ROTATION = 0
```

## Development Workflow

### Starting the API Server

```bash
cd robot-server
source ../env/bin/activate

# Start the Robot Controller API (FastAPI on :8000)
python api_server.py

# Server runs at http://0.0.0.0:8000
# Swagger UI at http://0.0.0.0:8000/docs
# ReDoc at http://0.0.0.0:8000/redoc
```

### Starting the ZeroClaw Agent

In a separate terminal (while the API server is running):

```bash
cd robot-server
source ../env/bin/activate

# Default settings
python zeroclaw_agent.py

# Custom API URL (e.g. if running remotely)
python zeroclaw_agent.py --url http://192.168.1.100:8000

# With PID tuning
python zeroclaw_agent.py --kp 1.2 --ki 0.01 --kd 0.3 --speed 55
```

### Development URLs
- Robot Controller API: `http://<pi-ip>:8000`
- Swagger Docs: `http://<pi-ip>:8000/docs`
- MJPEG Camera Stream: `http://<pi-ip>:8000/api/robot/camera/stream`

### Simulation Mode

Set `SIMULATION_MODE = True` in `config.py` to develop without real hardware:
- IR sensors return random patterns
- Motor commands are logged but not executed
- Camera returns generated dummy frames

## Project Structure

```
robot-server/
├── api_server.py              # FastAPI REST API — main entry point
├── zeroclaw_agent.py          # ZeroClaw autonomous agent (PID line-following)
├── config.py                  # All settings: GPIO pins, motor, camera, CV
├── config.example.py          # Template config
├── requirements.txt           # Python dependencies
├── robot/
│   ├── motor_controller.py    # L298N motor driver (GPIO PWM)
│   ├── sensor_controller.py   # IR sensor abstraction
│   └── navigation_controller.py
├── controllers/               # Extended controllers
├── services/
│   ├── computer_vision.py     # Camera / sign detection
│   └── mission_executor.py    # Mission planning
├── tests/
│   ├── test_api.py            # API + motor tests
│   └── test_zeroclaw.py       # ZeroClaw agent tests
└── utils/
    └── logger.py              # Logging utility
```

### Key Classes

```python
# api_server.py — FastAPI application
# Endpoints: /api/robot/forward, /backward, /left, /right, /stop
#            /api/robot/sensors/ir, /api/robot/status
#            /api/robot/mode (GET/POST), /api/robot/buzzer
#            /api/robot/camera/stream, /api/robot/camera/snapshot
#            /health

# zeroclaw_agent.py — Autonomous controller
class AgentConfig:    # Dataclass: api_url, speeds, PID gains, timings
class PID:            # Minimal PID controller (Kp, Ki, Kd)
class ZeroClawAgent:  # Main agent
    # run()           → entry point: set autonomous, start loop
    # _control_step() → read IR → PID → move command
    # compute_line_error() → 5-sensor weighted average → error [-2, +2]
    # read_ir()       → GET /api/robot/sensors/ir
    # shutdown()      → stop motors, restore manual mode
```

## Testing

### Running Tests

```bash
cd robot-server
source ../env/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v
pytest tests/test_zeroclaw.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing
```

### Writing Tests

```python
# tests/test_api.py
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Import with simulation mode
import config
config.SIMULATION_MODE = True

from api_server import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_move_forward():
    response = client.post("/api/robot/forward", json={"speed": 50})
    assert response.status_code == 200

def test_get_ir_sensors():
    response = client.get("/api/robot/sensors/ir")
    assert response.status_code == 200
    data = response.json()
    assert "sensors" in data["data"]

def test_mode_switch():
    # Set autonomous
    response = client.post("/api/robot/mode", json={"mode": "autonomous"})
    assert response.status_code == 200

    # Verify
    response = client.get("/api/robot/mode")
    assert response.json()["data"]["mode"] == "autonomous"

    # Set back to manual
    response = client.post("/api/robot/mode", json={"mode": "manual"})
    assert response.status_code == 200
```

### Quick API Test with curl

```bash
# Health check
curl http://localhost:8000/health

# Move forward
curl -X POST http://localhost:8000/api/robot/forward \
  -H "Content-Type: application/json" \
  -d '{"speed": 50}'

# Read IR sensors
curl http://localhost:8000/api/robot/sensors/ir

# Switch to autonomous mode
curl -X POST http://localhost:8000/api/robot/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "autonomous"}'

# Beep buzzer
curl -X POST http://localhost:8000/api/robot/buzzer \
  -H "Content-Type: application/json" \
  -d '{"times": 2, "duration": 0.3}'

# Camera snapshot
curl http://localhost:8000/api/robot/camera/snapshot --output snapshot.jpg
```

## Debugging

### Logging

```python
# utils/logger.py
import logging

def setup_logger(name, level=logging.INFO):
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger
```

Enable debug logging:
```bash
# Run with debug output
python api_server.py  # FastAPI shows request logs by default

# ZeroClaw verbose logging
python zeroclaw_agent.py --kp 1.0 2>&1 | tee zeroclaw.log
```

### Common Issues & Solutions

**GPIO Permission Errors:**
```bash
sudo usermod -a -G gpio $USER
# Log out and back in, or:
newgrp gpio
```

**Camera Not Detected:**
```bash
# Check camera is enabled
sudo raspi-config  # Interface Options → Camera → Enable
# Verify camera
vcgencmd get_camera
# Should show: supported=1 detected=1

# For Bookworm (libcamera):
libcamera-hello --list-cameras
```

**Port Already in Use:**
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

**IR Sensors Reading All-High:**
- Verify wiring: S1-S5 → GPIO 5, 6, 13, 19, 26
- Check sensor height (3-8mm above surface)
- Test with `curl http://localhost:8000/api/robot/sensors/ir`

## Deployment (Bare Metal)

### systemd Service — API Server

Create `/etc/systemd/system/medi-runner-api.service`:
```ini
[Unit]
Description=Medi Runner Robot Controller API
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/medi-runner/robot-server
Environment=PATH=/home/pi/medi-runner/env/bin:/usr/bin
ExecStart=/home/pi/medi-runner/env/bin/python api_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### systemd Service — ZeroClaw Agent

Create `/etc/systemd/system/medi-runner-zeroclaw.service`:
```ini
[Unit]
Description=Medi Runner ZeroClaw Agent
After=medi-runner-api.service
Requires=medi-runner-api.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/medi-runner/robot-server
Environment=PATH=/home/pi/medi-runner/env/bin:/usr/bin
ExecStart=/home/pi/medi-runner/env/bin/python zeroclaw_agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable medi-runner-api medi-runner-zeroclaw
sudo systemctl start medi-runner-api

# Start ZeroClaw only when you want autonomous mode
sudo systemctl start medi-runner-zeroclaw

# Check status
sudo systemctl status medi-runner-api
sudo systemctl status medi-runner-zeroclaw

# View logs
journalctl -u medi-runner-api -f
journalctl -u medi-runner-zeroclaw -f
```

### Environment Variables

```bash
# robot-server/config.py — all configuration in one Python file
SIMULATION_MODE = False
CAMERA_RESOLUTION = (640, 480)
CAMERA_FPS = 30
DEBUG = False
```

---

This development guide covers the Python-only bare-metal setup for the Medi Runner robot. All services run directly on the Raspberry Pi without Docker or containers.
