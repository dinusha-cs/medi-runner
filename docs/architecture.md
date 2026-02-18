# System Architecture

## Overview

The Medi Runner system follows a distributed architecture with four main components:

1. **Robot Controller API** (Raspberry Pi, FastAPI :8000) — REST API exposing movement, sensor, buzzer, mode, and camera endpoints. All GPIO pins are pre-wired as per the hardware appendix.
2. **ZeroClaw Agent** (Raspberry Pi, Python) — Autonomous-only line-following agent that reads the TCRT5000 5-channel IR array and Pi Camera V1.3 via the Robot Controller API, computes PID-based steering corrections, and posts movement commands back through the same API to follow the black line on the floor.
3. **Controller Backend** (Node.js :3001) — Manages WebSocket communication, missions, and data processing; bridges the frontend to the Robot Controller API.
4. **Controller Frontend** (Next.js :3000) — Manual control UI, real-time dashboard, live video streaming, mode switching. Connects **directly** to the Robot Controller API for movement commands and status, and to the Controller Backend for mission management and WebSocket events.

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
│  └──────────────▲──────────────────────▲───────────────────────┘   │
│                 │ HTTP (localhost)      │ HTTP (localhost)          │
│  ┌──────────────┴───────┐              │                           │
│  │   ZeroClaw Agent     │              │                           │
│  │   (Python, async)    │              │                           │
│  │                      │              │                           │
│  │  AUTONOMOUS MODE ONLY│              │                           │
│  │  • GET /sensors/ir   │              │                           │
│  │    → read IR S1-S5   │              │                           │
│  │  • Camera (future)   │              │                           │
│  │  • PID correction    │              │                           │
│  │  • POST /forward     │              │                           │
│  │  • POST /left|right  │              │                           │
│  │  • POST /stop        │              │                           │
│  └──────────────────────┘              │                           │
└────────────────────────────────────────┼───────────────────────────┘
                                         │
                          HTTP / REST     │
                 ┌───────────────────────┘
                 │
┌────────────────┴───────────────┐     ┌──────────────────────────┐
│  Controller Frontend           │ WS  │  Controller Backend      │
│  (Next.js :3000)               ├────►│  (Node.js :3001)         │
│                                │     │                          │
│  • Login (face recognition)    │     │  • WebSocket hub         │
│  • Mode switch (manual/auto)   │     │  • Mission management    │
│  • Manual virtual controller   │     │  • Real-time broadcast   │
│  • Real-time video stream      │     │  • Auth / validation     │
│  • Dashboard (IR, mode, speed) │     │  • Stream proxy          │
│  • 360° panoramic viewer       │     └──────────────────────────┘
│  • Mission prompt interface    │
│  • Mini-map path trace         │
│                                │─── HTTP ──► Robot Controller API
└────────────────────────────────┘          (direct REST calls)
```

### Connection Summary

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| **Controller Frontend** | Robot Controller API | HTTP REST | Movement commands (manual), status polling, mode switch, video stream |
| **Controller Frontend** | Controller Backend | WebSocket | Real-time events, mission updates, dashboard data |
| **Controller Backend** | Robot Controller API | HTTP REST / WS | Command relay, status aggregation |
| **ZeroClaw Agent** | Robot Controller API | HTTP REST | IR sensor reads, movement commands (**autonomous only**) |

### Operating Modes

| Mode | Who controls motors | Frontend | ZeroClaw Agent |
|------|---------------------|----------|----------------|
| **Manual** | Human via Frontend | Active — sends `POST /forward`, `/left`, `/right`, `/backward`, `/stop` | Paused — skips control loop (checks `GET /mode` and sleeps) |
| **Autonomous** | ZeroClaw Agent | Read-only dashboard + mode switch button | Active — reads `GET /sensors/ir` → PID → `POST /forward\|left\|right` at 20 Hz |

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

The central REST API that exposes all hardware capabilities. Every component (Frontend, Backend, ZeroClaw) communicates with the robot exclusively through this API.

```
robot-server/
├── api_server.py              # FastAPI REST API (movement, sensors, buzzer, mode, camera)
│                              #   - MoveRequest / BuzzerRequest / ModeRequest models
│                              #   - GPIO-driven IR reader (TCRT5000 5-ch)
│                              #   - Buzzer helper (GPIO 24)
│                              #   - CORS enabled for frontend access
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
├── controllers/               # Legacy / extended controllers
├── services/
│   ├── websocket_server.py    # WS bridge (backend ↔ robot)
│   ├── computer_vision.py     # Camera / sign detection / zone colour
│   └── mission_executor.py
├── tests/
│   ├── test_api.py            # 44 tests – API + motor controller
│   └── test_zeroclaw.py       # 25 tests – ZeroClaw agent + endpoints
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

### Controller Backend (Node.js :3001)

```javascript
controller-backend/
├── src/
│   ├── app.js                 # Express app configuration
│   ├── routes/
│   │   ├── robot.js          # Robot control endpoints (proxies to FastAPI)
│   │   ├── missions.js       # Mission management
│   │   └── streaming.js      # Video streaming routes
│   ├── services/
│   │   ├── robotCommService.js # HTTP client → Robot Controller API
│   │   ├── missionService.js  # Mission planning & execution
│   │   └── streamService.js   # Video stream proxy / relay
│   ├── models/
│   │   ├── Mission.js        # Mission data model
│   │   └── Robot.js          # Robot state model
│   └── middleware/
│       ├── auth.js           # JWT authentication
│       └── validation.js     # Request validation
├── config/
│   └── database.js           # Database configuration
└── package.json
```

**Key Responsibilities:**
- Proxies commands from frontend to Robot Controller API when needed
- WebSocket hub broadcasting real-time status to all connected frontends
- Mission planning, queueing, and execution orchestration
- User authentication (JWT) and authorization
- Video stream relay from Pi camera to browser clients

### Controller Frontend (Next.js :3000)

The frontend connects to **both** the Robot Controller API (direct REST for low-latency manual control) and the Controller Backend (WebSocket for real-time events and mission management).

```javascript
controller-frontend/
├── pages/
│   ├── index.js              # Dashboard homepage
│   ├── control.js            # Manual robot control
│   ├── missions.js           # Mission management
│   └── settings.js           # System configuration
├── src/
│   └── components/
│       ├── RobotControl/
│       │   ├── ManualControl.jsx  # Virtual joystick / directional pad
│       │   ├── StatusDisplay.jsx  # IR sensor readout, mode, speed
│       │   ├── CameraFeed.jsx     # Live MJPEG / WebRTC video stream
│       │   └── ModeSwitch.jsx     # Manual ↔ Autonomous toggle
│       ├── Mission/
│       │   ├── MissionPlanner.jsx # NL prompt → mission creation
│       │   ├── MissionStatus.jsx  # Active mission monitoring
│       │   └── MiniMap.jsx        # 2D graph-based path trace
│       ├── Dashboard/
│       │   ├── ZoneIndicator.jsx  # Current colour zone (Blue/Red/Green/Yellow)
│       │   ├── SensorPanel.jsx    # Real-time IR S1-S5 visualisation
│       │   └── PowerInfo.jsx      # Voltage, battery level
│       └── Common/
│           ├── Navigation.jsx     # App navigation
│           └── Layout.jsx         # Page layout wrapper
├── services/
│   ├── robotApi.js           # HTTP client → Robot Controller API (direct)
│   └── websocket.js          # WS client → Controller Backend
├── styles/
├── next.config.js
└── package.json
```

**Key Responsibilities:**
- Face-recognition login / enrollment with voice assistance
- Real-time robot control interface (virtual controller → direct API calls)
- Mode switching between manual and autonomous
- Live video streaming from Pi Camera
- 360° panoramic capture and viewer
- Dashboard with live IR sensor data, zone status, speed, power
- Natural-language mission prompt interface
- Mini-map path trace visualisation

## Communication Protocols

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

Diagnostics
  GET  /health                                                 → API health check
```

### WebSocket Messages (Controller Backend ↔ Frontend)

```json
{
  "type": "command",
  "action": "move",
  "data": {
    "direction": "forward",
    "speed": 50,
    "duration": 1000
  },
  "timestamp": 1640995200000
}

{
  "type": "status",
  "data": {
    "position": {"x": 10, "y": 5},
    "battery": 85,
    "sensors": [1, 0, 0, 1, 1],
    "mode": "autonomous",
    "zone": "blue"
  },
  "timestamp": 1640995201000
}

{
  "type": "mission",
  "action": "start",
  "data": {
    "id": "mission_001",
    "waypoints": [{"x": 100, "y": 200}],
    "tasks": ["deliver_medicine"]
  },
  "timestamp": 1640995202000
}
```

### Controller Backend REST Endpoints

```
Robot (proxied)
  GET    /api/robot/status        # Proxied to FastAPI /api/robot/status
  POST   /api/robot/command       # Parse & forward to FastAPI movement endpoints

Missions
  GET    /api/missions            # List all missions
  POST   /api/missions            # Create new mission (NL prompt parsed)
  GET    /api/missions/:id        # Get mission details
  PUT    /api/missions/:id        # Update mission
  DELETE /api/missions/:id        # Cancel mission

Streaming
  GET    /api/stream              # Video stream proxy from Pi camera

Auth
  POST   /api/auth/login          # Face-recognition authentication
  POST   /api/auth/enroll         # Enroll new face
```

## Data Flow

### Manual Mode
1. User opens Frontend → authenticates via face recognition
2. Frontend calls `POST /api/robot/mode {"mode": "manual"}` on Robot Controller API
3. User presses virtual controller → Frontend calls `POST /api/robot/forward` (direct REST)
4. Robot Controller API drives L298N motors via GPIO PWM
5. Frontend polls `GET /api/robot/status` and `GET /api/robot/sensors/ir` for dashboard
6. Live video streamed from Pi Camera → Frontend `<img>` / WebRTC

### Autonomous Mode
1. User (or ZeroClaw) calls `POST /api/robot/mode {"mode": "autonomous"}`
2. ZeroClaw Agent enters 20 Hz control loop
3. Each tick: `GET /sensors/ir` → PID → `POST /forward|left|right`
4. Frontend shows read-only dashboard; refreshes status via polling / WebSocket
5. Mode can be switched back to manual from Frontend at any time

### Mission Flow
1. User enters NL prompt on Frontend (e.g. "deliver X-ray from MRI to ICU")
2. Frontend sends prompt to Controller Backend via WebSocket
3. Backend parses prompt → creates ordered waypoint list
4. Backend orchestrates ZeroClaw + signboard detection to navigate
5. Progress broadcast to Frontend via WebSocket → Mini-map updates

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

- JWT-based authentication for API access
- WebSocket connection authorization
- Input validation and sanitization
- Rate limiting for robot commands
- Secure video streaming protocols

## Scalability Features

- Multi-robot support architecture
- Horizontal scaling for backend services
- Real-time data synchronization
- Mission queue management
- Load balancing for video streams

## Development Guidelines

- Use TypeScript for type safety
- Implement comprehensive error handling
- Follow RESTful API design principles
- Use WebSocket for real-time communication
- Implement proper logging and monitoring
- Write unit and integration tests
- Use Docker for consistent deployments
