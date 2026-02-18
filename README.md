# Medi Runner Challenge 2025

## Project Overview

The Medi Runner Challenge is a robotics and software development competition where teams build an autonomous medical delivery robot capable of navigating hospital corridors, interpreting signs, and functioning as a smart medical assistant.

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  Raspberry Pi 4 (8 GB)                         │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Robot Controller API  (FastAPI :8000)             │  │
│  │                                                          │  │
│  │  POST /forward   GET /sensors/ir   GET /mode             │  │
│  │  POST /backward  POST /buzzer      POST /mode            │  │
│  │  POST /left      GET /status       GET /camera/stream    │  │
│  │  POST /right     GET /health       GET /camera/snapshot  │  │
│  │  POST /stop                                              │  │
│  │               ┌────────────────────┐                     │  │
│  │               │  GPIO / Hardware   │                     │  │
│  │               │  L298N, IR, Buzzer │                     │  │
│  │               │  Pi Camera (CSI)   │                     │  │
│  │               └────────────────────┘                     │  │
│  └──────────────▲───────────────────────────────────────────┘  │
│                 │ HTTP (localhost)                              │
│  ┌──────────────┴───────┐                                      │
│  │   ZeroClaw Agent     │  Autonomous line-following (PID)     │
│  │   (Python, httpx)    │  Only active in autonomous mode      │
│  └──────────────────────┘                                      │
│                                                                │
│  HTTP :8000 exposed on LAN — any client can consume the API    │
└────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
medi-runner/
├── docs/                      # Documentation
│   ├── architecture.md        # System architecture
│   ├── api-reference.md       # Full API reference
│   ├── development-guide.md   # Setup & development guide
│   └── medi-runner-guide.md   # Competition guide
├── robot-server/              # Python robot controller (FastAPI)
│   ├── api_server.py          # REST API server (:8000)
│   ├── zeroclaw_agent.py      # ZeroClaw autonomous agent
│   ├── config.py              # GPIO pins & settings
│   ├── requirements.txt       # Python dependencies
│   ├── robot/                 # Motor & sensor controllers
│   ├── services/              # Computer vision, missions
│   ├── tests/                 # pytest test suite
│   └── utils/                 # Logging utilities
├── hardware/                  # Hardware specs and diagrams
└── env/                       # Python virtual environment
```

## Technology Stack

### Hardware
- **Brain**: Raspberry Pi 4 Model B (8 GB)
- **Motors**: 2× DC Motors with L298N Driver
- **Sensors**: TCRT5000 5-channel IR Array (line following)
- **Camera**: Pi Camera V1.3 5MP (CSI ribbon)
- **Power**: 2× 8650 batteries with LM2596 buck converter
- **Audio**: 5V Active Buzzer (GPIO 24)

### Software
- **Language**: Python 3.11+ (all components)
- **API Framework**: FastAPI with Uvicorn
- **Autonomous Agent**: ZeroClaw (async httpx, PID controller)
- **Computer Vision**: OpenCV, picamera2
- **GPIO**: RPi.GPIO
- **Deployment**: Bare metal with systemd services

## Quick Start

### 1. Raspberry Pi Setup
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev libopencv-dev

# Enable camera and GPIO
sudo raspi-config
```

### 2. Install Dependencies
```bash
cd robot-server
python3 -m venv ../env
source ../env/bin/activate
pip install -r requirements.txt
cp config.example.py config.py
```

### 3. Start the API Server
```bash
python api_server.py
# Runs at http://0.0.0.0:8000
# Swagger docs at http://0.0.0.0:8000/docs
```

### 4. Start ZeroClaw Agent (autonomous mode)
```bash
# In a separate terminal
python zeroclaw_agent.py
```

### 5. Simulation Mode
Set `SIMULATION_MODE = True` in `config.py` to develop without real hardware.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/robot/forward` | Move forward |
| POST | `/api/robot/backward` | Move backward |
| POST | `/api/robot/left` | Turn left |
| POST | `/api/robot/right` | Turn right |
| POST | `/api/robot/stop` | Stop all motors |
| GET | `/api/robot/sensors/ir` | Read IR sensor array |
| GET | `/api/robot/status` | Get robot status |
| GET | `/api/robot/mode` | Get current mode |
| POST | `/api/robot/mode` | Switch mode (manual/autonomous) |
| POST | `/api/robot/buzzer` | Activate buzzer |
| GET | `/api/robot/camera/stream` | MJPEG video stream |
| GET | `/api/robot/camera/snapshot` | Single JPEG frame |
| GET | `/health` | Health check |

Full API reference: [docs/api-reference.md](docs/api-reference.md)

## Documentation

- [System Architecture](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Development Guide](docs/development-guide.md)
- [Hardware Specifications](hardware/specifications.md)

## GPIO Pin Map (BCM)

| Component | Pins |
|-----------|------|
| L298N Motor Driver | ENA=20, IN1=23, IN2=22, IN3=27, IN4=17, ENB=16 |
| TCRT5000 IR Array | S1=5, S2=6, S3=13, S4=19, S5=26 |
| Buzzer | GPIO 24 |
| Camera | CSI ribbon |
