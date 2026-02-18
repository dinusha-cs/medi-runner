# Medi-Runner Robot Controller API Reference

> **Base URL:** `http://<raspberry-pi-ip>:8000`
>
> **Framework:** FastAPI (Python 3.11+)
>
> **Source:** `robot-server/api_server.py`

---

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Common Response Format](#common-response-format)
- [Endpoints](#endpoints)
  - [Movement](#movement)
    - [POST /api/robot/forward](#post-apirobotforward)
    - [POST /api/robot/backward](#post-apirobotbackward)
    - [POST /api/robot/left](#post-apirobotleft)
    - [POST /api/robot/right](#post-apirobotright)
    - [POST /api/robot/stop](#post-apirobotstop)
  - [Sensors](#sensors)
    - [GET /api/robot/sensors/ir](#get-apirobotsensorsir)
  - [Status](#status)
    - [GET /api/robot/status](#get-apirobotstatus)
  - [Mode Control](#mode-control)
    - [GET /api/robot/mode](#get-apirobotmode)
    - [POST /api/robot/mode](#post-apirobotmode)
  - [Peripherals](#peripherals)
    - [POST /api/robot/buzzer](#post-apirobotbuzzer)
  - [Diagnostics](#diagnostics)
    - [GET /health](#get-health)
- [Request / Response Models](#request--response-models)
- [Error Handling](#error-handling)
- [Hardware Pin Reference](#hardware-pin-reference)
- [ZeroClaw Agent API Usage](#zeroclaw-agent-api-usage)
- [Frontend Integration Guide](#frontend-integration-guide)

---

## Overview

The Robot Controller API is the **single point of access** to all robot hardware. Every component in the Medi-Runner system communicates with the robot exclusively through this REST API:

| Consumer | Mode | Typical Calls |
|----------|------|---------------|
| **Controller Frontend** (Next.js) | Manual | `POST /forward`, `POST /stop`, `GET /status`, `GET /sensors/ir`, `POST /mode` |
| **ZeroClaw Agent** (Python) | Autonomous | `GET /sensors/ir`, `POST /forward\|left\|right`, `GET /mode`, `POST /mode` |
| **Controller Backend** (Node.js) | Both | `GET /status`, `GET /mode` (status aggregation) |

CORS is enabled for all origins to allow direct browser-to-API calls from the frontend.

---

## Authentication

Currently **open** (no auth token required). All endpoints accept unauthenticated requests. Authentication is handled at the Controller Backend / Frontend layer.

---

## Common Response Format

All endpoints return a unified `RobotResponse` JSON object:

```json
{
  "success": true,
  "action": "forward",
  "message": "Moving forward at 50% speed",
  "data": { ... },
  "timestamp": 1740000000.123
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | `boolean` | Whether the operation succeeded |
| `action` | `string` | Name of the action performed |
| `message` | `string` | Human-readable status message |
| `data` | `object \| null` | Action-specific payload |
| `timestamp` | `float` | Unix epoch timestamp (seconds) |

---

## Endpoints

### Movement

All movement endpoints accept an optional JSON body. If no body is provided, defaults apply.

---

#### POST /api/robot/forward

Move the robot forward.

**Request Body** (optional):

```json
{
  "speed": 50,
  "duration": 0
}
```

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `speed` | `int` | `50` | 0–100 | Motor speed percentage |
| `duration` | `float` | `0` | ≥ 0 | Duration in seconds. `0` = continuous until next command |

**Response:**

```json
{
  "success": true,
  "action": "forward",
  "message": "Moving forward at 50% speed",
  "data": {
    "direction": "forward",
    "speed": 50,
    "left_speed": 50,
    "right_speed": 50
  },
  "timestamp": 1740000000.123
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/api/robot/forward \
  -H "Content-Type: application/json" \
  -d '{"speed": 60, "duration": 2}'
```

---

#### POST /api/robot/backward

Move the robot backward.

**Request Body** (optional):

```json
{
  "speed": 50,
  "duration": 0
}
```

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `speed` | `int` | `50` | 0–100 | Motor speed percentage |
| `duration` | `float` | `0` | ≥ 0 | Duration in seconds. `0` = continuous |

**Response:**

```json
{
  "success": true,
  "action": "backward",
  "message": "Moving backward at 50% speed",
  "data": {
    "direction": "backward",
    "speed": 50,
    "left_speed": 50,
    "right_speed": 50
  },
  "timestamp": 1740000000.456
}
```

---

#### POST /api/robot/left

Turn the robot left (left motor backward, right motor forward).

**Request Body** (optional):

```json
{
  "speed": 50,
  "duration": 0
}
```

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `speed` | `int` | `50` | 0–100 | Turn speed percentage |
| `duration` | `float` | `0` | ≥ 0 | Duration in seconds |

**Response:**

```json
{
  "success": true,
  "action": "left",
  "message": "Turning left at 50% speed",
  "data": {
    "direction": "left",
    "speed": 50,
    "left_speed": -50,
    "right_speed": 50
  },
  "timestamp": 1740000000.789
}
```

---

#### POST /api/robot/right

Turn the robot right (left motor forward, right motor backward).

**Request Body** (optional):

```json
{
  "speed": 50,
  "duration": 0
}
```

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `speed` | `int` | `50` | 0–100 | Turn speed percentage |
| `duration` | `float` | `0` | ≥ 0 | Duration in seconds |

**Response:**

```json
{
  "success": true,
  "action": "right",
  "message": "Turning right at 50% speed",
  "data": {
    "direction": "right",
    "speed": 50,
    "left_speed": 50,
    "right_speed": -50
  },
  "timestamp": 1740000001.012
}
```

---

#### POST /api/robot/stop

Immediately stop all motor movement.

**Request Body:** None

**Response:**

```json
{
  "success": true,
  "action": "stop",
  "message": "Robot stopped",
  "data": {
    "left_speed": 0,
    "right_speed": 0
  },
  "timestamp": 1740000001.345
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/api/robot/stop
```

---

### Sensors

#### GET /api/robot/sensors/ir

Read the TCRT5000 5-channel IR sensor array. This is the primary input for autonomous line following.

**Request:** No parameters.

**Response:**

```json
{
  "success": true,
  "action": "ir_sensor",
  "message": "IR sensor array read",
  "data": {
    "sensors": [1, 1, 0, 1, 1],
    "labels": ["S1_far_left", "S2_left", "S3_center", "S4_right", "S5_far_right"],
    "pins": [5, 6, 13, 19, 26]
  },
  "timestamp": 1740000001.678
}
```

**Sensor Value Convention:**

| Value | Meaning | Surface |
|-------|---------|---------|
| `0` | Line detected | Black line |
| `1` | No line | White floor |

**Sensor Positions (front of robot, left to right):**

```
     Front of Robot
  ┌───────────────────┐
  │ S1  S2  S3  S4  S5│
  │ (5) (6) (13)(19)(26)│  ← GPIO pins
  └───────────────────┘
     IR Array (TCRT5000)
```

| Sensor | Label | GPIO | Position |
|--------|-------|------|----------|
| S1 | `S1_far_left` | 5 | Far left |
| S2 | `S2_left` | 6 | Left |
| S3 | `S3_center` | 13 | Center |
| S4 | `S4_right` | 19 | Right |
| S5 | `S5_far_right` | 26 | Far right |

**Common Patterns:**

| S1 | S2 | S3 | S4 | S5 | Interpretation |
|:--:|:--:|:--:|:--:|:--:|----------------|
| 1 | 1 | 0 | 1 | 1 | Centered — go forward |
| 1 | 0 | 0 | 1 | 1 | Slightly left of center — correct right |
| 1 | 1 | 0 | 0 | 1 | Slightly right of center — correct left |
| 0 | 0 | 1 | 1 | 1 | Line far left — sharp right |
| 1 | 1 | 1 | 0 | 0 | Line far right — sharp left |
| 0 | 0 | 0 | 0 | 0 | Intersection (all black) — pause |
| 1 | 1 | 1 | 1 | 1 | Line lost (all white) — search / stop |

**Example:**

```bash
curl http://localhost:8000/api/robot/sensors/ir
```

---

### Status

#### GET /api/robot/status

Get current robot status including motor state, speeds, and position data.

**Request:** No parameters.

**Response:**

```json
{
  "success": true,
  "action": "status",
  "message": "Robot status retrieved",
  "data": {
    "is_moving": true,
    "direction": "forward",
    "left_speed": 50,
    "right_speed": 50,
    "position": { "x": 0, "y": 0, "heading": 0 },
    "uptime": 123.45
  },
  "timestamp": 1740000002.000
}
```

**Example:**

```bash
curl http://localhost:8000/api/robot/status
```

---

### Mode Control

The robot supports two operating modes. Mode switching is the mechanism that ensures **only one controller** (human or ZeroClaw) drives the motors at any time.

#### GET /api/robot/mode

Get the current operating mode.

**Response:**

```json
{
  "success": true,
  "action": "mode",
  "message": "Current mode: manual",
  "data": {
    "mode": "manual"
  },
  "timestamp": 1740000002.500
}
```

---

#### POST /api/robot/mode

Switch between manual and autonomous mode.

**Request Body (required):**

```json
{
  "mode": "autonomous"
}
```

| Field | Type | Allowed Values | Description |
|-------|------|---------------|-------------|
| `mode` | `string` | `"manual"` or `"autonomous"` | Target operating mode |

**Response:**

```json
{
  "success": true,
  "action": "mode",
  "message": "Mode changed from manual to autonomous",
  "data": {
    "mode": "autonomous",
    "previous": "manual"
  },
  "timestamp": 1740000003.000
}
```

**Mode Behaviour:**

| Mode | Frontend | ZeroClaw Agent |
|------|----------|----------------|
| `manual` | Can send movement commands | Pauses control loop (polls mode, sleeps) |
| `autonomous` | Read-only dashboard; can switch mode back | Active — reads IR, runs PID, sends movement commands |

**Example:**

```bash
# Switch to autonomous
curl -X POST http://localhost:8000/api/robot/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "autonomous"}'

# Switch back to manual
curl -X POST http://localhost:8000/api/robot/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "manual"}'
```

---

### Peripherals

#### POST /api/robot/buzzer

Activate the 5 V active buzzer on GPIO 24.

**Request Body** (optional):

```json
{
  "times": 1,
  "duration": 0.3
}
```

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `times` | `int` | `1` | 1–10 | Number of beeps |
| `duration` | `float` | `0.3` | 0.05–2.0 | Duration of each beep in seconds |

**Response:**

```json
{
  "success": true,
  "action": "buzzer",
  "message": "Buzzer activated 1 time(s)",
  "data": {
    "times": 1,
    "duration": 0.3,
    "pin": 24
  },
  "timestamp": 1740000003.500
}
```

**Zone Detection Beep Patterns (Stage 3):**

| Zone Colour | Beeps | Meaning |
|-------------|-------|---------|
| Blue | 1 | Imaging / diagnostics |
| Red | 2 | Emergency / critical zone |
| Green | 3 | General area |
| Yellow | 4 | Caution / transitions |
| Destination reached | 5 | Target unit found |

**Example:**

```bash
# Single beep
curl -X POST http://localhost:8000/api/robot/buzzer

# Emergency zone — 2 quick beeps
curl -X POST http://localhost:8000/api/robot/buzzer \
  -H "Content-Type: application/json" \
  -d '{"times": 2, "duration": 0.15}'
```

---

### Diagnostics

#### GET /health

Simple health-check endpoint to verify the API is running.

**Response:**

```json
{
  "status": "ok",
  "simulation_mode": false,
  "timestamp": 1740000004.000
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Always `"ok"` if the server is running |
| `simulation_mode` | `boolean` | `true` if running without real GPIO hardware |
| `timestamp` | `float` | Unix epoch timestamp |

**Example:**

```bash
curl http://localhost:8000/health
```

---

## Request / Response Models

### MoveRequest

```python
class MoveRequest(BaseModel):
    speed: int = Field(default=50, ge=0, le=100)
    duration: float = Field(default=0, ge=0)
```

### BuzzerRequest

```python
class BuzzerRequest(BaseModel):
    times: int = Field(default=1, ge=1, le=10)
    duration: float = Field(default=0.3, ge=0.05, le=2.0)
```

### ModeRequest

```python
class ModeRequest(BaseModel):
    mode: str = Field(..., pattern="^(manual|autonomous)$")
```

### RobotResponse

```python
class RobotResponse(BaseModel):
    success: bool
    action: str
    message: str
    data: Optional[dict] = None
    timestamp: float
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| `200` | Success | All successful operations |
| `422` | Validation Error | Invalid request body (e.g., speed > 100, bad mode string) |
| `503` | Service Unavailable | Motor controller not initialised |
| `500` | Internal Server Error | Unexpected failure |

### Validation Error Response (422)

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "speed"],
      "msg": "Input should be less than or equal to 100",
      "input": 150
    }
  ]
}
```

### Motor Not Ready (503)

```json
{
  "detail": "Motor controller not initialised"
}
```

---

## Hardware Pin Reference

All GPIO pins use BCM numbering. Wiring follows `docs/medi-runner-guide.md` Appendix.

### Motor Driver (L298N)

```
Raspberry Pi          L298N Motor Controller
─────────────         ─────────────────────
GPIO 20  [pin 38] ──► ENA  (Left motor PWM speed)
GPIO 23  [pin 16] ──► IN1  (Left motor direction A)
GPIO 22  [pin 15] ──► IN2  (Left motor direction B)
GPIO 27  [pin 13] ──► IN3  (Right motor direction A)
GPIO 17  [pin 11] ──► IN4  (Right motor direction B)
GPIO 16  [pin 36] ──► ENB  (Right motor PWM speed)
```

**Motor Direction Logic:**

| IN1 | IN2 | Left Motor |
|:---:|:---:|------------|
| HIGH | LOW | Forward |
| LOW | HIGH | Backward |
| LOW | LOW | Stop |

| IN3 | IN4 | Right Motor |
|:---:|:---:|-------------|
| HIGH | LOW | Forward |
| LOW | HIGH | Backward |
| LOW | LOW | Stop |

### IR Sensor Array (TCRT5000 5-channel)

```
Raspberry Pi          TCRT5000 IR Array
─────────────         ─────────────────
5V   [pin  4] ──► VCC
GND  [pin  6] ──► GND
GPIO  5 [pin 29] ──► S1  (far left)
GPIO  6 [pin 31] ──► S2  (left)
GPIO 13 [pin 33] ──► S3  (center)
GPIO 19 [pin 35] ──► S4  (right)
GPIO 26 [pin 37] ──► S5  (far right)
```

### Buzzer (5 V Active)

```
Raspberry Pi          Buzzer
─────────────         ──────
GND  [pin  6] ──► GND
GPIO 24 [pin 18] ──► VCC
```

### Camera (Pi Camera V1.3 5MP)

```
Camera slot ──► CSI ribbon cable ──► Camera module
```

Camera settings (from `config.py`):
- Resolution: 640 × 480
- FPS: 30
- Rotation: 0°

---

## ZeroClaw Agent API Usage

The ZeroClaw Agent is the autonomous line-following controller. It operates **only** when `mode == "autonomous"` and communicates with hardware exclusively through this API.

### Startup Sequence

```
1. GET  /health                         → verify API is alive
2. POST /api/robot/mode {"mode":"autonomous"} → claim control
3. Loop (20 Hz):
   a. GET  /api/robot/mode              → skip if not autonomous
   b. GET  /api/robot/sensors/ir        → read [S1..S5]
   c. compute PID correction from sensor error
   d. POST /api/robot/forward|left|right → move
4. Shutdown:
   a. POST /api/robot/stop              → halt motors
   b. POST /api/robot/mode {"mode":"manual"} → release control
```

### PID Line-Following Algorithm

```
                  IR Sensors [S1..S5]
                         │
                         ▼
              ┌─────────────────────┐
              │ compute_line_error()│
              │                     │
              │ weights: [-2,-1,0,1,2]│
              │ active = 1 - sensor │
              │ error = Σ(w·a) / Σa │
              │ range: [-2, +2]     │
              └─────────┬───────────┘
                        │ error
                        ▼
              ┌─────────────────────┐
              │     PID.update()    │
              │                     │
              │ P = Kp × error      │
              │ I = Ki × ∫error·dt  │
              │ D = Kd × d(error)/dt│
              │ output = P + I + D  │
              └─────────┬───────────┘
                        │ correction
                        ▼
              ┌─────────────────────┐
              │  Direction Mapping  │
              │                     │
              │ |c| < 0.3 → forward │
              │ |c| < 1.0 → gentle  │
              │     left or right   │
              │ |c| ≥ 1.0 → sharp   │
              │     left or right   │
              └─────────┬───────────┘
                        │
                        ▼
              POST /api/robot/{direction}
```

### Agent Configuration Defaults

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_url` | `http://localhost:8000` | Robot Controller API base URL |
| `base_speed` | `50` | Forward speed (0–100) |
| `turn_speed` | `40` | Gentle turn speed |
| `sharp_turn_speed` | `30` | Sharp turn speed |
| `loop_interval` | `0.05` | Control loop period (50 ms = 20 Hz) |
| `lost_line_timeout` | `2.0` | Seconds before stopping when line lost |
| `intersection_pause` | `0.8` | Pause at all-black intersection |
| `kp` | `1.0` | PID proportional gain |
| `ki` | `0.0` | PID integral gain |
| `kd` | `0.0` | PID derivative gain |

### CLI Usage

```bash
# Default settings
python zeroclaw_agent.py

# Custom API URL and speed
python zeroclaw_agent.py --url http://192.168.1.100:8000 --speed 55

# With PID tuning
python zeroclaw_agent.py --kp 1.2 --ki 0.01 --kd 0.3
```

---

## Frontend Integration Guide

### Direct API Calls (Manual Mode)

The Controller Frontend connects **directly** to the Robot Controller API for low-latency manual control.

```javascript
// services/robotApi.js

const ROBOT_API = process.env.NEXT_PUBLIC_ROBOT_API || 'http://localhost:8000';

// Movement commands
export async function moveForward(speed = 50) {
  const res = await fetch(`${ROBOT_API}/api/robot/forward`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speed }),
  });
  return res.json();
}

export async function stopRobot() {
  const res = await fetch(`${ROBOT_API}/api/robot/stop`, { method: 'POST' });
  return res.json();
}

// Mode switching
export async function setMode(mode) {
  const res = await fetch(`${ROBOT_API}/api/robot/mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
  return res.json();
}

export async function getMode() {
  const res = await fetch(`${ROBOT_API}/api/robot/mode`);
  return res.json();
}

// Sensor polling (for dashboard)
export async function getIRSensors() {
  const res = await fetch(`${ROBOT_API}/api/robot/sensors/ir`);
  return res.json();
}

export async function getStatus() {
  const res = await fetch(`${ROBOT_API}/api/robot/status`);
  return res.json();
}

// Buzzer
export async function buzzer(times = 1, duration = 0.3) {
  const res = await fetch(`${ROBOT_API}/api/robot/buzzer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ times, duration }),
  });
  return res.json();
}
```

### Polling Pattern (Dashboard)

```javascript
// Poll IR sensors and status every 200ms for dashboard
useEffect(() => {
  const interval = setInterval(async () => {
    const [irData, statusData] = await Promise.all([
      getIRSensors(),
      getStatus(),
    ]);
    setSensors(irData.data.sensors);
    setRobotStatus(statusData.data);
  }, 200);

  return () => clearInterval(interval);
}, []);
```

---

## Running the API Server

```bash
cd robot-server

# Install dependencies
pip install -r requirements.txt

# Start the API server (with hot-reload)
python api_server.py

# Server runs at http://0.0.0.0:8000
# Swagger docs at http://0.0.0.0:8000/docs
# ReDoc at http://0.0.0.0:8000/redoc
```

### Simulation Mode

Set `SIMULATION_MODE = True` in `config.py` to run without real GPIO hardware. IR sensors return random patterns and motor commands are logged but not executed.

---

## OpenAPI / Swagger

FastAPI auto-generates interactive API documentation:

- **Swagger UI:** `http://<host>:8000/docs`
- **ReDoc:** `http://<host>:8000/redoc`
- **OpenAPI JSON:** `http://<host>:8000/openapi.json`
