we have connedcted follwing devies:
1. raspbery pi 4  B
2.  Motor Driver (L298N or similar)
3 . Motor Driver connected to two dc Motors
4. PI Cam V1.3 5MP
5. 5 IR Sensors for line following with bump sensor and proximity sensor

all these connected to GPIO ping as per below. 
GPIO Pin Configuration:
| Device               | GPIO Pin(s)        |
|----------------------|--------------------|
| Motor Driver IN1     | GPIO 17            |
| Motor Driver IN2     | GPIO 27            |
| Motor Driver IN3     | GPIO 22            |
| Motor Driver IN4     | GPIO 23            |
| PI Cam V1.3          | CSI Interface      |
| IR Sensor 1          | GPIO 5             |
| IR Sensor 2          | GPIO 6             |
| IR Sensor 3          | GPIO 13            |
| IR Sensor 4          | GPIO 19            |
| IR Sensor 5          | GPIO 26            |
| Bump Sensor          | GPIO 18            |
| Proximity Sensor     | GPIO 24            |
---------------------------------------------

application overview

architecture:
             ┌──────────────────────────────┐
             │     User's Browser (UI)      │
             │   Control Console (HTTP)     │
             │                              │
             │  - React components          │
             │  - Calls REST APIs           │
             │  - Opens WebSocket           │
             └─────────────┬────────────────┘
                           │  (HTTP: config, start/stop)
                           │  (WebSocket: commands, telemetry)
                           │
                     ┌─────┴──────────────────────┐
                     │   Python Robot Controller  │
                     │   (FastAPI / Flask / etc.) │
                     │                            │
                     │  REST endpoints:           │
                     │    - /api/start            │
                     │    - /api/stop             │
                     │    - /api/config           │
                     │                            │
                     │  WebSocket endpoint:       │
                     │    - /ws/control           │
                     │      ← joystick commands   │
                     │      → sensor updates      │
                     └─────┬──────────────────────┘
                           │
                           │  (local hardware I/O)
                           │
                  ┌────────┴────────┐
                  │   Robot HW      │
                  │  (motors, IMU,  │
                  │   encoders, etc)│
                  └─────────────────┘


UI Components:
1. Dashboard:
   - Real-time video feed from PI Cam V1.3
   - Sensor status indicators (IR sensors, bump sensor, proximity sensor)
   - Motor status (speed, direction)
   - Emergency stop button
2. Control Panel:
    - Joystick for manual control of the robot
    - Start/Stop buttons for autonomous mode
    - Configuration settings (speed, sensor thresholds PID parameters)
3. Logs & Telemetry:
   - Display recent actions and sensor readings


Backend Components:
1. REST API Endpoints:
   - /api/move: move left righ forward backward baseon header value
   - /api/start: Start autonomous mode
   - /api/stop: Stop autonomous mode
   - /api/config: Update configuration settings
   - /api/status: Get current status of the robot
   - /api/logs: Retrieve recent logs and telemetry data
   - /api/health: Check system health and diagnostics
   
2. WebSocket Endpoint:
    - /ws/control: Handle real-time commands from the UI and send sensor updates back
3. Hardware Interface Module:
   - Motor Control: Functions to set motor speeds and directions
    - Sensor Reading: Functions to read values from IR sensors, bump sensor, and proximity sensor
4. Autonomous Logic Module:
   - Line Following Algorithm: Logic to follow a line using IR sensor inputs
   - Obstacle Avoidance: Logic to respond to bump and proximity sensor inputs
5. Video Streaming Module:
   - Capture video from PI Cam V1.3 and stream to the UI
6. Configuration Management:
   - Load and save configuration settings (e.g., speed, sensor thresholds, PID parameters)

Technology Stack:
- Frontend: Any HTTP client (developed by separate team)
- Backend: Python (FastAPI or Flask), WebSocket
- Hardware Control: RPi.GPIO or gpiozero for GPIO interactions
- Video Streaming: OpenCV or PiCamera for video capture and streaming
- Deployment: Bare metal with systemd for service management



