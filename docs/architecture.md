# System Architecture

## Overview

The Medi Runner system follows a distributed architecture with three main components:

1. **Robot Server** (Raspberry Pi) - Controls hardware and autonomous behaviors
2. **Controller Backend** (Node.js) - Manages communication and data processing
3. **Controller Frontend** (Next.js) - Provides user interface and mission control

## Component Architecture

### Robot Server (Raspberry Pi)

```python
robot_server/
├── main.py                 # Main application entry
├── controllers/
│   ├── motor_controller.py # Motor control and movement
│   ├── sensor_controller.py # IR sensors and camera
│   └── navigation_controller.py # Path planning and following
├── services/
│   ├── websocket_client.py # Communication with backend
│   ├── computer_vision.py  # Image processing and recognition
│   └── mission_executor.py # Task execution logic
├── config/
│   ├── hardware_config.py  # GPIO pins and hardware settings
│   └── ai_config.py       # CV and AI model configurations
└── utils/
    ├── logger.py          # Logging utilities
    └── helpers.py         # Common helper functions
```

**Key Responsibilities:**
- Hardware control (motors, sensors, camera)
- Real-time navigation and obstacle avoidance
- Computer vision processing
- Mission execution and status reporting

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
