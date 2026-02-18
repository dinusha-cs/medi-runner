# Medi Runner Challenge 2025 — Implementation Plan (Development + Deployment + Testing)

## 0) High-Level Plan Overview
We will build an integrated system with two parallel workstreams:
- **Robotics Workstream (on Pi):** motor control, sensors, autonomy, camera stream, robot API — all Python
- **Frontend Workstream:** Developed by a separate team; consumes the REST API

We will ship in increments:
- Stage 1 = "Bring-up + controllable + visible"
- Stage 2 = "Autonomous corridor navigation + dual-mode"
- Stage 3 = "Perception + decision logic + mission behaviors"
- Stage 4 = "Innovation extension + polish + demo reliability"

---

## 1) Development Plan (By Stage)

### Stage 1 — Hardware + Base Software Bring-up
**Goal:** A working robot platform + controllable API.

#### Robotics (Pi)
1. **OS + base setup**
   - Raspberry Pi Desktop OS
   - Enable SSH (local), enable camera, update packages
2. **GPIO + motor control**
   - Map L298N: IN1/IN2 = left direction, IN3/IN4 = right direction
   - ENA/ENB = PWM speed control
   - Implement basic movement: forward, backward, stop, left, right, turn-in-place
3. **Safety**
   - Watchdog timer: stop motors if no command within N ms
   - Clean shutdown handling (stop motors on exit)
4. **Robot API (minimum)**
   - FastAPI REST endpoints for drive commands
   - Telemetry `/status` (mode, last_cmd_time, speed)

**Stage 1 Exit Proof**
- Robot can be driven via REST API (curl, Postman, or any HTTP client)
- Robot stops safely on disconnect/timeout
- API responds at http://<pi-ip>:8000/health

---

### Stage 2 — Corridor Navigation + Dual Mode
**Goal:** Reliable line following + stable turns + switch between manual and autonomous.

#### Robotics (Pi)
1. **IR sensor array integration**
   - Read each sensor channel (TCRT5000 5-ch)
   - Normalize values and derive line position estimate
2. **Line following controller (ZeroClaw Agent)**
   - Weighted error approach (PID: Kp, Ki, Kd)
   - Convert error → differential speed (left_speed/right_speed)
3. **Recovery logic**
   - If line lost: slow down, search in last-known direction, then widen search
4. **Mode manager**
   - Modes: manual / autonomous
   - Transition rules: manual overrides; autonomous resumes only when toggled
5. **Telemetry expansion**
   - Publish sensor readings summary (line_error, line_detected)
   - Current mode + commanded speeds

**Stage 2 Exit Proof**
- Robot follows line smoothly on track
- Can switch to manual instantly and regain control via API
- Stable turning behavior (no violent oscillations)

---

### Stage 3 — Hospital Intelligence (Zones + Signs + Behaviors)
**Goal:** Use camera to capture sign images, send them to OpenAI Vision API for interpretation, and execute mission logic based on the AI response.

#### Robotics (Pi)
1. **Camera capture**
   - Provide frames to streaming + sign-detection inference pipeline
   - On sign detection trigger (proximity sensor, periodic scan, or operator snapshot), capture a high-quality still frame of the sign
2. **OpenAI Vision-based sign recognition pipeline**
   - When a sign is detected in the camera feed:
     1. Capture the sign image (crop/enhance if possible)
     2. Send the image to the OpenAI Vision API (`gpt-4o`) with predefined action definitions:
        - `TURN_LEFT` — "Turn left at the next junction"
        - `TURN_RIGHT` — "Turn right at the next junction"
        - `STOP` — "Stop the robot immediately"
        - `FORWARD` — "Continue moving forward"
        - `BACKWARD` — "Reverse the robot"
        - `ZONE_<name>` — "You have entered zone <name>"
     3. OpenAI responds with the best-matching action key + confidence score
     4. Robot executes the matched action (e.g., turn left, stop, enter zone)
   - **Fallback:** If OpenAI confidence is below threshold (default 70%), robot pauses and requests operator confirmation
3. **OpenAI API key management**
   - API key configured in `config.py` or environment variable
4. **Behavior state machine**
   - States: `NAVIGATING` → `SIGN_DETECTED` → `CAPTURING_IMAGE` → `WAITING_FOR_AI` → `AI_DECISION_RECEIVED` → `EXECUTING_ACTION` → `NAVIGATING`
   - Error states: `AI_TIMEOUT`, `LOW_CONFIDENCE`, `AI_ERROR` (falls back to safe stop)
5. **Mission protocol**
   - Robot accepts a mission (e.g., "Deliver to Ward B")
   - Robot reports events (zone entered, sign read, AI decision made, confidence score)

**Stage 3 Exit Proof**
- Robot captures a sign image, sends it to OpenAI, and receives a correct action
- Robot executes the AI-determined action (e.g., turns left when sign shows left arrow)
- Low-confidence results trigger safe behavior
- All results logged

---

### Stage 4 — Open Innovation Round
**Goal:** Add a meaningful "wow" feature tied to medical domain value.

Pick ONE strong innovation and make it reliable:
- Medication delivery audit log (time, zones, confirmation beep)
- "Nurse call" mode: robot navigates to a beacon/marker when requested
- Dynamic obstacle pause: stop when obstacle detected (if sensor available) + resume
- Voice prompts via buzzer confirmations
- Smart batching: multi-stop route with simple optimization

**Stage 4 Exit Proof**
- Feature is demoable end-to-end in under 60 seconds
- Clear story: "why it helps in a hospital"
- Does not break Stage 2/3 stability

---

## 2) Deployment Plan

### On Raspberry Pi (Robot) — Bare Metal

**Project structure:**
```
/home/pi/medi-runner/
├── robot-server/
│   ├── api_server.py          # FastAPI REST API (:8000)
│   ├── zeroclaw_agent.py      # ZeroClaw autonomous agent
│   ├── config.py              # All settings
│   ├── requirements.txt       # Python dependencies
│   ├── robot/                 # Motor & sensor controllers
│   ├── services/              # CV, missions
│   ├── tests/                 # pytest suite
│   └── utils/                 # Logging
└── env/                       # Python virtual environment
```

**Startup — systemd services:**
```bash
# /etc/systemd/system/medi-runner-api.service
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

```bash
# /etc/systemd/system/medi-runner-zeroclaw.service
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

**Network:**
- Hostname: NeuroNex-Navi
- Wi-Fi Network: Cleint-5F / Password: Welcome123()*
- API port: 8000

**Safety defaults:**
- Motors STOP on service stop
- Motors STOP if watchdog triggers
- Motors STOP if mode transitions to ERROR

**Configuration:**
- All settings in `config.py` (GPIO pins, speeds, PID gains, camera, simulation mode)
- Environment variables can override if needed

**Release discipline:**
- Tag stable milestones: `stage1-stable`, `stage2-stable`, etc.
- Keep a "last known good" branch for demo fallback

---

## 3) Development Readiness Plan (Team Devices + SSH + Dependencies)

### 3.1 Team Device Allocation (6 Members → 3 Workstations)

| Device | Role | Purpose | Team Members |
|--------|------|---------|-------------|
| **Device 1 — API Testing & Integration** | Integration Tester + QA | Test API endpoints, verify streaming, validate sensor data | Member 1 (primary), Member 2 (backup) |
| **Device 2 — Platform & Configuration** | Platform / DevOps Engineer | OS maintenance, system config, network setup, Pi camera & GPIO config, log monitoring | Member 3 (primary), Member 4 (backup) |
| **Device 3 — Robot Controller Deployment** | Robot Software Engineer | Deploy and debug Python robot-server, manage systemd services, run integration tests | Member 5 (primary), Member 6 (backup) |

### 3.2 SSH Key Setup (All 3 Devices → Robot Pi)

> **Robot hostname:** `NeuroNex-Navi`
> **Robot user:** `pi` (or your configured username)
> **Robot IP:** Discover with `ping NeuroNex-Navi.local` or check router DHCP leases
> **Wi-Fi Network:** Cleint-5F / Password: Welcome123()*

#### Step 1 — Generate SSH key pair (run on each developer device)

**Windows (PowerShell):**
```powershell
ssh-keygen -t ed25519 -C "device1-testing@medirunner"
```

**Linux / macOS:**
```bash
ssh-keygen -t ed25519 -C "device1-testing@medirunner"
```

#### Step 2 — Copy public key to the Robot Pi

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub pi@<PI_IP>
```

#### Step 3 — Verify passwordless SSH

```bash
ssh pi@<PI_IP>
hostname   # Should print: NeuroNex-Navi
```

#### Step 4 — (Optional) Configure SSH alias

Add to `~/.ssh/config`:
```
Host robot
    HostName <PI_IP>
    User pi
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
```

### 3.3 Raspberry Pi OS Update & Base Configuration

```bash
# 1. Update OS
sudo apt update && sudo apt full-upgrade -y

# 2. Set hostname
sudo hostnamectl set-hostname NeuroNex-Navi
echo "127.0.1.1  NeuroNex-Navi" | sudo tee -a /etc/hosts

# 3. Enable required interfaces
sudo raspi-config nonint do_ssh 0
sudo raspi-config nonint do_camera 0
sudo raspi-config nonint do_i2c 0

# 4. Configure Wi-Fi
sudo nmcli dev wifi connect "Cleint-5F" password "Welcome123()*"

# 5. Set timezone
sudo timedatectl set-timezone Asia/Colombo

# 6. Reboot
sudo reboot
```

### 3.4 Install Dependencies on Raspberry Pi

#### Python environment (Robot Server)
```bash
# Install Python 3.11+ and system libraries
sudo apt install -y python3 python3-pip python3-venv python3-dev \
  libopencv-dev python3-opencv libatlas-base-dev

# Create virtual environment
cd /home/pi/medi-runner
python3 -m venv env
source env/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r robot-server/requirements.txt
```

#### Additional system tools
```bash
sudo apt install -y git htop tmux vim curl wget jq screen rsync \
  python3-rpi.gpio python3-gpiozero pigpio python3-pigpio

# Start pigpio daemon (for hardware PWM)
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

### 3.5 Environment Configuration

All configuration is in `robot-server/config.py`:
```python
# config.py
SIMULATION_MODE = False

# Motor GPIO Pins (BCM)
MOTOR_ENA = 20
MOTOR_IN1 = 23
MOTOR_IN2 = 22
MOTOR_IN3 = 27
MOTOR_IN4 = 17
MOTOR_ENB = 16

# IR Sensors (BCM)
IR_SENSOR_PINS = [5, 6, 13, 19, 26]

# Buzzer
BUZZER_PIN = 24

# Camera
CAMERA_RESOLUTION = (640, 480)
CAMERA_FPS = 30
CAMERA_ROTATION = 0
```

### 3.6 Per-Device Workflow After Setup

| Device | After SSH + deps are ready... |
|--------|-------------------------------|
| **Device 1 — Testing** | `ssh robot`, test with `curl http://localhost:8000/health`, verify camera stream at `http://<PI_IP>:8000/api/robot/camera/stream`, run `pytest` |
| **Device 2 — Platform** | `ssh robot`, monitor with `htop`, check `journalctl -u medi-runner-api -f`, manage config, restart services |
| **Device 3 — Deployment** | `ssh robot`, deploy with `git pull`, `source env/bin/activate`, run `python api_server.py`, verify motor + sensor responses |

### 3.7 Quick Verification Checklist (Day 1)

```bash
# API health check
ssh robot "curl -s http://localhost:8000/health"

# System info
ssh robot "cat /proc/cpuinfo | grep Model"
ssh robot "vcgencmd measure_temp"
ssh robot "df -h /"
ssh robot "free -m"
ssh robot "python3 -c 'import RPi.GPIO; print(\"GPIO OK\")'"

# Python modules
ssh robot "cd /home/pi/medi-runner && source env/bin/activate && python -c 'import cv2; print(cv2.__version__)'"
ssh robot "cd /home/pi/medi-runner && source env/bin/activate && python -c 'import fastapi; print(\"FastAPI OK\")'"
```

---

## 4) Test Plan (By Stage + Cross-Cutting)

### General Test Principles
- Test the **full pipeline early**: HTTP client → API → motors
- Always keep a **STOP** test available
- Validate in realistic lighting and surface conditions (IR sensors + camera are sensitive)

---

### Stage 1 Tests
**Electronics**
- Verify common ground between Pi, motor driver, and power system
- Confirm motor direction mapping (left/right not swapped)
- Verify buck converter output stable at 5V under load

**Software**
- API responds reliably at http://<pi-ip>:8000
- Movement commands work as expected (curl + Swagger)
- Watchdog stops motors on command loss

**Acceptance**
- Drive forward/back/left/right/stop repeatedly with no hangs

---

### Stage 2 Tests
**Line Following**
- Straight segments: robot stays centered
- Curves: robot turns smoothly without overshoot
- Speed sweep: test low/medium/high PWM for stability

**Recovery**
- Force off-line drift: robot finds line again within a bounded time
- Confirm no runaway behavior (always bounded speed)

**Mode Switching**
- Switch autonomous→manual: control is immediate
- Switch manual→autonomous: autonomy resumes only on explicit toggle

**Acceptance**
- Robot completes a representative corridor loop with minimal intervention

---

### Stage 3 Tests
**OpenAI Sign Recognition**
- Capture sign image under different lighting angles and distances; verify OpenAI returns correct action
- Repeatability: same sign image sent 5 times yields consistent action + confidence ≥ threshold
- Test all predefined actions: `TURN_LEFT`, `TURN_RIGHT`, `STOP`, `FORWARD`, `BACKWARD`, and at least one `ZONE_<name>`
- Verify low-confidence responses correctly trigger safe behavior
- Test OpenAI API timeout handling: simulate slow/no response → robot enters safe stop
- Test with invalid/missing API key → clear error, robot does not crash

**Behavior**
- Correct response to at least 3 sign types
- Full state machine flow: `SIGN_DETECTED` → `CAPTURING_IMAGE` → `WAITING_FOR_AI` → `AI_DECISION_RECEIVED` → `EXECUTING_ACTION`
- Error handling: if sign not detected or AI fails, fallback behavior (safe stop) triggers

**Acceptance**
- One end-to-end mission demo with visible AI decision evidence
- Robot correctly interprets at least 3 different signs in a single run

---

### Stage 4 Tests
**Innovation Feature**
- Test feature end-to-end 10 times without reboot
- Ensure it does not degrade Stage 2 navigation
- Add a kill-switch / disable toggle

**Acceptance**
- Reliable 60-second showcase demo + clear value statement

---

## 5) Integration Checklist (Always-On)
- ✅ Pinout finalized and documented
- ✅ One API contract everyone follows (REST endpoints + schemas)
- ✅ Logging: timestamps, mode changes, sensor summary, error codes
- ✅ "Demo mode" procedure written:
  1) Power on robot
  2) Confirm API health
  3) Confirm camera stream
  4) Test manual control via API
  5) Toggle autonomous
  6) Run mission
  7) Show innovation feature

---

## 6) Risk Register (Common Pitfalls + Mitigations)
- **Power instability / brownouts** → check buck converter, separate motor power if possible, reduce peak PWM
- **Motor noise resets Pi** → ensure grounds, add capacitance if available, reduce sudden acceleration
- **IR sensors inconsistent** → calibrate thresholds, add filtering, test surface contrast
- **Latency in teleop** → keep REST payloads small, prioritize STOP
- **Camera lag** → lower resolution/framerate, MJPEG is lightweight
- **OpenAI API latency** → cache recent sign results, set request timeout (default 10s), robot pauses safely while waiting
- **OpenAI API cost** → debounce sign capture (min 5s between calls), log usage, set daily call limit
- **OpenAI API downtime** → fallback to safe stop; robot does not crash

---

## 7) Definition of Done (Competition-Ready)
- Robot is controllable at all times, with safe STOP
- Stage 2 autonomy is stable and repeatable
- Stage 3 intelligence is demonstrable: robot captures sign images, sends to OpenAI Vision, receives and executes correct actions
- Stage 4 innovation is clear, reliable, and doesn't break the base system
- All backend code is Python, running bare metal on Raspberry Pi
