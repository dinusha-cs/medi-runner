# System Architecture

## Overview

The Medi Runner system follows a distributed architecture with four main components:

1. **Robot Controller API** (Raspberry Pi, FastAPI) - REST API exposing movement, sensor, buzzer, and mode endpoints
2. **ZeroClaw Agent** (Raspberry Pi, Python) - Autonomous line-following agent that reads IR sensors and camera, sends movement commands via the API
3. **Controller Backend** (Node.js) - Manages communication, missions, and data processing
4. **Controller Frontend** (Next.js) - Manual control UI, dashboard, video streaming

```
┌──────────────────┐         ┌─────────────────────────┐
│  Controller       │  HTTP   │  Robot Controller API    │
│  Frontend (Next.js)├───────►│  (FastAPI :8000)         │
│  - Manual control │         │                         │
│  - Dashboard      │         │  POST /api/robot/forward│
│  - Video stream   │         │  POST /api/robot/left   │
│  - Mode switch    │         │  POST /api/robot/right  │
└──────────────────┘         │  POST /api/robot/backward│
                              │  POST /api/robot/stop   │
┌──────────────────┐         │  GET  /api/robot/status  │
│  ZeroClaw Agent   │  HTTP   │  GET  /api/robot/sensors/ir│
│  (Python)         ├───────►│  POST /api/robot/buzzer  │
│                   │         │  GET  /api/robot/mode    │
│  AUTONOMOUS ONLY  │         │  POST /api/robot/mode    │
│  - Reads IR array │         │                         │
│  - Reads camera   │         │  ┌──────────────────┐   │
│  - PID control    │         │  │ GPIO / Hardware   │   │
│  - Line following │         │  │ L298N motors      │   │
└──────────────────┘         │  │ TCRT5000 IR (5ch) │   │
                              │  │ Pi Camera V1.3    │   │
┌──────────────────┐  WS     │  │ Buzzer GPIO24     │   │
│ Controller Backend├───────►│  └──────────────────┘   │
│ (Node.js :3001)   │         └─────────────────────────┘
└──────────────────┘
```

### Operating Modes

| Mode | Who controls | Frontend | ZeroClaw |
|------|-------------|----------|----------|
| **Manual** | Human via Frontend | Active – sends movement commands | Paused – skips control loop |
| **Autonomous** | ZeroClaw Agent | Read-only dashboard + mode switch | Active – reads IR, drives motors |

## Component Architecture

### Robot Controller API (FastAPI – Raspberry Pi)

```python
robot-server/
├── api_server.py              # FastAPI REST API (movement, sensors, buzzer, mode)
├── zeroclaw_agent.py          # ZeroClaw autonomous line-following agent
├── config.py                  # GPIO pins, motor/sensor settings
├── robot/
│   ├── motor_controller.py    # L298N motor driver (GPIO PWM)
│   ├── sensor_controller.py   # Sensor abstraction
│   └── navigation_controller.py
├── controllers/               # Legacy controllers
├── services/
│   ├── websocket_server.py    # WS bridge (backend ↔ robot)
│   ├── computer_vision.py     # Camera / sign detection
│   └── mission_executor.py
├── tests/
│   ├── test_api.py            # 44 tests – API + motor controller
│   └── test_zeroclaw.py       # 25 tests – ZeroClaw agent + new endpoints
└── utils/
    └── logger.py
```

**REST API Endpoints:**

```
POST /api/robot/forward      Move forward  { speed, duration }
POST /api/robot/backward     Move backward { speed, duration }
POST /api/robot/left         Turn left     { speed, duration }
POST /api/robot/right        Turn right    { speed, duration }
POST /api/robot/stop         Stop motors
GET  /api/robot/status       Motor status, position, encoders
GET  /api/robot/sensors/ir   Read TCRT5000 5-ch IR array [S1..S5]
GET  /api/robot/mode         Get current mode (manual|autonomous)
POST /api/robot/mode         Set mode      { mode }
POST /api/robot/buzzer       Beep buzzer   { times, duration }
GET  /health                 Health check
```

### ZeroClaw Agent (Python – runs on Raspberry Pi)

```
zeroclaw_agent.py
├── ZeroClawAgent              # Main agent class
│   ├── run()                  # Entry – sets autonomous, starts loop
│   ├── _control_step()        # Read IR → PID → move command
│   ├── compute_line_error()   # 5-sensor → error in [-2, +2]
│   ├── read_ir()              # GET /api/robot/sensors/ir
│   ├── api_forward/left/…()   # POST /api/robot/{direction}
│   └── shutdown()             # Stop motors, restore manual mode
├── PID                        # Lightweight PID controller
└── AgentConfig                # Tuneable params (speed, PID gains)
```

**Behaviour:**
1. On start → calls `POST /api/robot/mode { "autonomous" }`
2. Every 50 ms (20 Hz):
   - `GET /api/robot/mode` → skip if not autonomous
   - `GET /api/robot/sensors/ir` → read [S1..S5]
   - Compute weighted line error (0 = line, 1 = floor)
   - PID correction → pick direction + speed
   - `POST /api/robot/{forward|left|right}` → move
3. On shutdown → `POST /api/robot/stop` + `POST /api/robot/mode { "manual" }`

### Controller Backend (Node.js)

```javascript
controller-backend/
├── src/
│   ├── app.js                 # Express app configuration
│   ├── routes/
│   │   ├── robot.js          # Robot control endpoints
│   │   ├── missions.js       # Mission management
│   │   └── streaming.js      # Video streaming routes
│   ├── services/
│   │   ├── robotCommService.js # Robot communication
│   │   ├── missionService.js  # Mission planning
│   │   └── streamService.js   # Video stream management
│   ├── models/
│   │   ├── Mission.js        # Mission data model
│   │   └── Robot.js          # Robot state model
│   └── middleware/
│       ├── auth.js           # Authentication middleware
│       └── validation.js     # Request validation
├── config/
│   └── database.js           # Database configuration
└── package.json
```

**Key Responsibilities:**
- WebSocket communication with robot
- Mission planning and management
- User authentication and authorization
- Real-time data streaming
- API endpoints for frontend

### Controller Frontend (Next.js)

```javascript
controller-front-end/
├── pages/
│   ├── index.js              # Dashboard homepage
│   ├── control.js            # Manual robot control
│   ├── missions.js           # Mission management
│   └── settings.js           # System configuration
├── components/
│   ├── RobotControl/
│   │   ├── ManualControl.jsx # Joystick and manual controls
│   │   ├── StatusDisplay.jsx # Robot status indicators
│   │   └── CameraFeed.jsx    # Live video stream
│   ├── Mission/
│   │   ├── MissionPlanner.jsx # Mission creation interface
│   │   └── MissionStatus.jsx  # Active mission monitoring
│   └── Common/
│       ├── Navigation.jsx     # App navigation
│       └── Layout.jsx        # Page layout wrapper
├── services/
│   ├── api.js               # Backend API client
│   └── websocket.js         # WebSocket connection
├── styles/
└── next.config.js
```

**Key Responsibilities:**
- Real-time robot control interface
- Mission planning and monitoring
- Live video streaming display
- System configuration and settings
- User authentication and team management

## Communication Protocols

### WebSocket Messages

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
    "mode": "autonomous"
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

### REST API Endpoints

```
GET    /api/robot/status        # Get current robot status
POST   /api/robot/command       # Send command to robot
GET    /api/missions            # List all missions
POST   /api/missions            # Create new mission
GET    /api/missions/:id        # Get mission details
PUT    /api/missions/:id        # Update mission
DELETE /api/missions/:id        # Cancel mission
GET    /api/stream              # Video stream endpoint
POST   /api/auth/login          # User authentication
```

## Data Flow

1. **User Interaction**: Frontend sends commands via WebSocket
2. **Command Processing**: Backend validates and forwards to robot
3. **Robot Execution**: Robot processes commands and sends status updates
4. **Real-time Updates**: Status changes broadcast to all connected clients
5. **Mission Execution**: Autonomous missions run independently with progress updates

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
