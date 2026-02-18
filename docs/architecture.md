# System Architecture

## Overview

The Medi Runner system is a **Python-only** bare-metal architecture running on a Raspberry Pi 4. There are two main components:

1. **Robot Controller API** (FastAPI :8000) — REST API exposing movement, sensor, buzzer, mode, and camera endpoints. All GPIO pins are pre-wired as per the hardware appendix.
2. **ZeroClaw Agent** (Python, async httpx) — Autonomous-only line-following agent that reads the TCRT5000 5-channel IR array and Pi Camera V1.3 via the Robot Controller API, computes PID-based steering corrections, and posts movement commands back through the same API.

Both processes run directly on the Raspberry Pi — no Docker, no containers, no Node.js.

```
┌────────────────────────────────────────────────────────────────────┐
│                      Raspberry Pi 4 (8 GB)                         │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │            Robot Controller API  (FastAPI :8000)             │   │
│  │                                                             │   │
│  │  Movement       Sensors         Control        Diagnostics  │   │
│  │  POST /forward  GET /sensors/ir GET /mode      GET /status  │   │
│  │  POST /backward POST /buzzer   POST /mode      GET /health  │   │
│  │  POST /left                                                 │   │
│  │  POST /right                    Camera                      │   │
│  │  POST /stop                     GET /camera/snapshot        │   │
│  │                                 GET /camera/stream          │   │
│  │              ┌──────────────────────────────┐               │   │
│  │              │     GPIO / Hardware Layer     │               │   │
│  │              │  L298N  → ENA=20 IN1=23      │               │   │
│  │              │           IN2=22 IN3=27      │               │   │
│  │              │           IN4=17 ENB=16      │               │   │
│  │              │  IR S1-S5 → GPIO 5,6,13,19,26│               │   │
│  │              │  Buzzer   → GPIO 24          │               │   │
│  │              │  Camera   → CSI ribbon       │               │   │
│  │              └──────────────────────────────┘               │   │
│  └──────────────▲──────────────────────────────────────────────┘   │
│                 │ HTTP (localhost)                                  │
│  ┌──────────────┴───────┐                                          │
│  │   ZeroClaw Agent     │                                          │
│  │   (Python, async)    │                                          │
│  │                      │                                          │
│  │  AUTONOMOUS MODE ONLY│                                          │
│  │  • GET /sensors/ir   │                                          │
│  │    → read IR S1-S5   │                                          │
│  │  • Camera (future)   │                                          │
│  │  • PID correction    │                                          │
│  │  • POST /forward     │                                          │
│  │  • POST /left|right  │                                          │
│  │  • POST /stop        │                                          │
│  └──────────────────────┘                                          │
│                                                                    │
│  HTTP :8000 exposed to LAN (Wi-Fi)                                 │
│  Any HTTP client (browser, curl, Postman, custom frontend)         │
│  can consume the REST API from the network.                        │
└────────────────────────────────────────────────────────────────────┘
```

### Connection Summary

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| **ZeroClaw Agent** | Robot Controller API | HTTP REST | IR sensor reads, movement commands (**autonomous only**) |
| **Any HTTP Client** | Robot Controller API | HTTP REST | Movement commands, status polling, mode switch, camera stream |

### Operating Modes

| Mode | Who controls motors | ZeroClaw Agent |
|------|---------------------|----------------|
| **Manual** | External HTTP client sends `POST /forward`, `/left`, `/right`, `/backward`, `/stop` | Paused — skips control loop (checks `GET /mode` and sleeps) |
| **Autonomous** | ZeroClaw Agent | Active — reads `GET /sensors/ir` → PID → `POST /forward\|left\|right` at 20 Hz |

### ZeroClaw Agent — Autonomous Line-Following Flow

```
┌─────────────────────────────────────────────────────────┐
│  ZeroClaw Control Loop  (20 Hz — every 50 ms)           │
│                                                         │
│  1. GET /api/robot/mode                                 │
│     └─ if mode ≠ "autonomous" → stop motors, sleep, retry│
│                                                         │
│  2. GET /api/robot/sensors/ir                           │
│     └─ returns [S1, S2, S3, S4, S5]                    │
│        (0 = black line, 1 = white floor)                │
│                                                         │
│  3. compute_line_error(sensors)                         │
│     └─ weighted average → error ∈ [-2, +2]             │
│        None → line lost                                 │
│                                                         │
│  4. PID.update(error) → correction                      │
│     └─ Kp·e + Ki·∫e + Kd·de/dt                        │
│                                                         │
│  5. Map correction to movement command:                 │
│     |correction| < 0.3  → POST /forward  (base_speed)  │
│     |correction| < 1.0  → POST /left or /right (turn)  │
│     |correction| ≥ 1.0  → POST /left or /right (sharp) │
│                                                         │
│  6. Special cases:                                      │
│     • All white → line lost → creep forward / timeout   │
│     • All black → intersection → pause                  │
└─────────────────────────────────────────────────────────┘
```

## Component Architecture

### Robot Controller API (FastAPI — Raspberry Pi :8000)

The central REST API that exposes all hardware capabilities. Every component communicates with the robot exclusively through this API.

```
robot-server/
├── api_server.py              # FastAPI REST API (movement, sensors, buzzer, mode, camera)
│                              #   - MoveRequest / BuzzerRequest / ModeRequest models
│                              #   - GPIO-driven IR reader (TCRT5000 5-ch)
│                              #   - Buzzer helper (GPIO 24)
│                              #   - CORS enabled for cross-origin access
├── zeroclaw_agent.py          # ZeroClaw autonomous line-following agent
├── config.py                  # All GPIO pin maps, motor/sensor/CV settings
│                              #   - Motor: ENA=20 IN1=23 IN2=22 IN3=27 IN4=17 ENB=16
│                              #   - IR: S1=5 S2=6 S3=13 S4=19 S5=26
│                              #   - Buzzer: GPIO 24
│                              #   - Camera: CSI ribbon (640×480, 30 fps)
├── robot/
│   ├── motor_controller.py    # L298N motor driver (GPIO PWM via ENA/ENB)
│   ├── sensor_controller.py   # Sensor abstraction (IR, future ultrasonic)
│   └── navigation_controller.py
├── controllers/               # Extended controllers
├── services/
│   ├── computer_vision.py     # Camera / sign detection / zone colour
│   └── mission_executor.py
├── tests/
│   ├── test_api.py            # API + motor controller tests
│   └── test_zeroclaw.py       # ZeroClaw agent + endpoint tests
└── utils/
    └── logger.py
```

### ZeroClaw Agent (Python — runs on Raspberry Pi)

The ZeroClaw Agent is a **standalone Python process** that operates **only in autonomous mode**. It talks to hardware exclusively through the Robot Controller API — it never touches GPIO directly.

```
zeroclaw_agent.py
├── AgentConfig                # Dataclass: api_url, speeds, PID gains, timings
├── PID                        # Minimal PID controller (Kp, Ki, Kd)
└── ZeroClawAgent              # Main agent class
    ├── run()                  # Entry: set autonomous → start 20 Hz loop
    ├── _control_step()        # Read IR → PID → move command
    ├── compute_line_error()   # 5-sensor weighted average → error [-2, +2]
    ├── _direction_from_correction()  # Map PID output → forward/left/right
    ├── read_ir()              # GET /api/robot/sensors/ir → [S1..S5]
    ├── get_mode() / set_mode()# GET/POST /api/robot/mode
    ├── api_forward/left/right/backward/stop()  # POST /api/robot/{dir}
    ├── api_buzzer()           # POST /api/robot/buzzer
    └── shutdown()             # Stop motors → restore manual mode
```

**Lifecycle:**
1. Startup → `GET /health` (verify API is alive)
2. `POST /api/robot/mode {"mode": "autonomous"}`
3. **Control loop** (every 50 ms / 20 Hz):
   - `GET /api/robot/mode` → if not autonomous, pause
   - `GET /api/robot/sensors/ir` → read [S1, S2, S3, S4, S5]
   - `compute_line_error()` → weighted average (0 = line, 1 = floor)
   - `PID.update(error)` → correction value
   - Map correction → `POST /api/robot/forward|left|right` with speed
4. Shutdown → `POST /api/robot/stop` + `POST /api/robot/mode {"mode": "manual"}`

**IR Sensor Interpretation (TCRT5000 5-channel):**

| S1 (far-left) | S2 (left) | S3 (center) | S4 (right) | S5 (far-right) | Meaning | Action |
|:-:|:-:|:-:|:-:|:-:|---|---|
| 1 | 1 | 0 | 1 | 1 | Centered on line | Forward (base speed) |
| 1 | 0 | 0 | 1 | 1 | Slightly left | Gentle right correction |
| 1 | 1 | 0 | 0 | 1 | Slightly right | Gentle left correction |
| 0 | 0 | 1 | 1 | 1 | Far left | Sharp right turn |
| 1 | 1 | 1 | 0 | 0 | Far right | Sharp left turn |
| 0 | 0 | 0 | 0 | 0 | Intersection | Pause, then continue |
| 1 | 1 | 1 | 1 | 1 | Line lost | Creep forward / timeout-stop |

## Communication Protocol

### REST API (Robot Controller — FastAPI :8000)

All hardware interaction flows through a single REST API. Full reference: [docs/api-reference.md](api-reference.md)

```
Movement
  POST /api/robot/forward    { speed: 0-100, duration: 0+ }   → Move forward
  POST /api/robot/backward   { speed: 0-100, duration: 0+ }   → Move backward
  POST /api/robot/left       { speed: 0-100, duration: 0+ }   → Turn left
  POST /api/robot/right      { speed: 0-100, duration: 0+ }   → Turn right
  POST /api/robot/stop                                         → Stop all motors

Sensors
  GET  /api/robot/sensors/ir                                   → Read TCRT5000 [S1..S5]
  GET  /api/robot/status                                       → Motor speeds, position

Mode Control
  GET  /api/robot/mode                                         → Current mode
  POST /api/robot/mode       { mode: "manual"|"autonomous" }   → Switch mode

Peripherals
  POST /api/robot/buzzer     { times: 1-10, duration: 0.05-2 } → Beep buzzer

Camera
  GET  /api/robot/camera/stream                                → MJPEG video stream
  GET  /api/robot/camera/snapshot                              → Single JPEG frame

Diagnostics
  GET  /health                                                 → API health check
```

## Data Flow

### Manual Mode
1. External HTTP client calls `POST /api/robot/mode {"mode": "manual"}`
2. Client sends movement commands: `POST /api/robot/forward`, etc.
3. Robot Controller API drives L298N motors via GPIO PWM
4. Client polls `GET /api/robot/status` and `GET /api/robot/sensors/ir` for telemetry
5. Live video available at `GET /api/robot/camera/stream` (MJPEG)

### Autonomous Mode
1. ZeroClaw Agent (or external client) calls `POST /api/robot/mode {"mode": "autonomous"}`
2. ZeroClaw Agent enters 20 Hz control loop
3. Each tick: `GET /sensors/ir` → PID → `POST /forward|left|right`
4. External clients can monitor via polling `GET /status`, `GET /sensors/ir`
5. Mode can be switched back to manual at any time via `POST /mode`

## Hardware Pin Map (pre-wired)

All pins follow BCM numbering. Wiring matches `docs/medi-runner-guide.md` Appendix.

| Component | Function | BCM GPIO | Physical Pin |
|-----------|----------|----------|-------------|
| L298N | ENA (left speed PWM) | 20 | 38 |
| L298N | IN1 (left motor A) | 23 | 16 |
| L298N | IN2 (left motor B) | 22 | 15 |
| L298N | IN3 (right motor A) | 27 | 13 |
| L298N | IN4 (right motor B) | 17 | 11 |
| L298N | ENB (right speed PWM) | 16 | 36 |
| TCRT5000 | S1 — far left | 5 | 29 |
| TCRT5000 | S2 — left | 6 | 31 |
| TCRT5000 | S3 — center | 13 | 33 |
| TCRT5000 | S4 — right | 19 | 35 |
| TCRT5000 | S5 — far right | 26 | 37 |
| Buzzer | VCC (active, 5 V logic) | 24 | 18 |
| Camera | CSI ribbon | — | Camera slot |
| IR Array | 5 V power | — | Pin 4 (5 V) |
| IR Array / Buzzer | GND | — | Pin 6 (GND) |

## Security Considerations

- Input validation and sanitization on all API endpoints
- Rate limiting for robot commands to prevent hardware abuse
- CORS configured — restrict origins in production
- HTTPS recommended when exposing API outside local network

## Development Guidelines

- All backend code is **Python only** (FastAPI, asyncio, httpx)
- Install bare metal on Raspberry Pi — no Docker, no containers
- Implement comprehensive error handling
- Follow RESTful API design principles
- Use proper logging and monitoring (`utils/logger.py`)
- Write unit and integration tests (`pytest`)
- Use `systemd` services for production process management
