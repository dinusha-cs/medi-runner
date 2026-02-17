# Medi Runner Challenge 2025 — Implementation Plan (Development + Deployment + Testing)

## 0) High-Level Plan Overview
We will build an integrated system with two parallel workstreams:
- **Robotics Workstream (on Pi):** motor control, sensors, autonomy, camera stream, robot API
- **Console Workstream (Next.js):** UI, teleop, stream viewer, autonomy toggle, mission control, AI insights

We will ship in increments:
- Stage 1 = “Bring-up + controllable + visible”
- Stage 2 = “Autonomous corridor navigation + dual-mode”
- Stage 3 = “Perception + decision logic + mission behaviors”
- Stage 4 = “Innovation extension + polish + demo reliability”

---

## 1) Development Plan (By Stage)

### Stage 1 — Hardware + Base Software Bring-up
**Goal:** A working robot platform + basic console onboarding.

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
   - HTTP `/cmd` (or WebSocket) to send drive commands
   - Telemetry `/status` (mode, last_cmd_time, speed)

#### Console (Next.js)
1. **Project skeleton**
   - Next.js app with pages: Login/Enrollment, Control Dashboard
2. **Basic auth/enrollment**
   - Lightweight user login (can be local only)
3. **Teleop controls UI**
   - Buttons + keyboard mapping (W/A/S/D)
4. **Connect to Robot API**
   - Send commands, show connection status and last response time

**Stage 1 Exit Proof**
- Robot can be driven from console
- Robot stops safely on disconnect/timeout
- Team members can login/enroll and operate

---

### Stage 2 — Corridor Navigation + Dual Mode
**Goal:** Reliable line following + stable turns + switch between TELEOP and AUTO.

#### Robotics (Pi)
1. **IR sensor array integration**
   - Read each sensor channel
   - Normalize values and derive line position estimate
2. **Line following controller**
   - Simple weighted error approach (left-to-right weights)
   - Convert error -> differential speed (left_speed/right_speed)
3. **Recovery logic**
   - If line lost: slow down, search in last-known direction, then widen search
4. **Mode manager**
   - Modes: TELEOP / AUTO
   - Transition rules: teleop overrides; auto resumes only when toggled
5. **Telemetry expansion**
   - Publish sensor readings summary (line_error, line_detected)
   - Current mode + commanded speeds

#### Console (Next.js)
1. **Mode toggle**
   - TELEOP <-> AUTO switch with clear visual status
2. **Autonomy dashboard**
   - Show line_detected, line_error, current speed
3. **Operator ergonomics**
   - Big STOP button always visible
   - Connection loss indicator

**Stage 2 Exit Proof**
- Robot follows line smoothly on track
- Can switch to teleop instantly and regain control
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
     2. Send a request to the **controller-backend** `POST /api/sign-recognition` endpoint containing:
        - The captured image (base64-encoded)
        - A set of **predefined action definitions**:
          - `TURN_LEFT` — "Turn left at the next junction"
          - `TURN_RIGHT` — "Turn right at the next junction"
          - `STOP` — "Stop the robot immediately"
          - `FORWARD` — "Continue moving forward"
          - `BACKWARD` — "Reverse the robot"
          - `ZONE_<name>` — "You have entered zone <name>" (dynamic, e.g., `ZONE_WARD_A`)
     3. The backend forwards the image + definitions to the **OpenAI Vision API** (`gpt-4o` model) with a prompt asking: *"Analyze this hospital corridor sign image. Which of the following predefined actions best matches the instruction shown on this sign? Return the action key and your confidence level."*
     4. OpenAI responds with the best-matching action key + confidence score
     5. The backend returns the result to the robot server
     6. The robot executes the matched action (e.g., turn left, stop, enter zone)
   - **Fallback:** If OpenAI confidence is below a configurable threshold (default 70%), the robot pauses and requests operator confirmation via the console
3. **OpenAI API key management**
   - The OpenAI API key is configured in the **controller-backend `.env`** file as `OPENAI_API_KEY`
   - On first startup (or via an admin settings page), the key is **persisted to the database** (`settings` table, key: `openai_api_key`, value: encrypted)
   - At runtime the backend reads the key from the database; falls back to `.env` if not found in DB
   - The console provides an **admin UI** to view/update the stored API key
4. **Behavior state machine**
   - States: `NAVIGATING` → `SIGN_DETECTED` → `CAPTURING_IMAGE` → `WAITING_FOR_AI` → `AI_DECISION_RECEIVED` → `EXECUTING_ACTION` → `NAVIGATING`
   - Error states: `AI_TIMEOUT`, `LOW_CONFIDENCE` (triggers operator confirmation), `AI_ERROR` (falls back to safe stop)
5. **Mission protocol**
   - Robot accepts a mission (e.g., "Deliver to Ward B")
   - Robot reports events (zone entered, sign read, AI decision made, confidence score)
   - All AI sign-recognition results are **logged to the database** with: timestamp, image reference, prompt sent, action returned, confidence, whether operator override occurred

#### Controller Backend (Node.js)
1. **Sign recognition endpoint** — `POST /api/sign-recognition`
   - Accepts: `{ image: <base64>, context?: <string> }`
   - Internally calls OpenAI Chat Completions API with vision capability (`gpt-4o`)
   - Sends the image + predefined action definitions as a structured prompt
   - Returns: `{ action: "TURN_LEFT", confidence: 0.92, reasoning: "Sign shows left arrow with text 'Ward A'" }`
2. **API key management endpoints**
   - `GET /api/settings/openai-key` — returns masked key status (configured / not configured)
   - `PUT /api/settings/openai-key` — updates the key in the database (admin only)
3. **Sign recognition history** — `GET /api/sign-recognition/history`
   - Returns paginated log of all sign recognition events with images, decisions, and outcomes
4. **Database schema additions**
   - `settings` table: `{ key: string, value: string (encrypted), updated_at: timestamp }`
   - `sign_recognition_log` table: `{ id, timestamp, image_path, prompt_sent, action_returned, confidence, operator_override, mission_id }`

#### Console (Next.js)
1. **Streaming UI**
   - Live feed panel + **"Capture Sign" button** for manual sign capture
   - Overlay showing detected sign region (bounding box if available)
2. **Mission control**
   - Select mission destination (zone)
   - Show mission progress timeline with AI decision events highlighted
3. **AI interaction panel**
   - Real-time display of sign recognition results: captured image, AI response (action + confidence + reasoning)
   - Operator **confirm / override** controls when confidence is below threshold
   - Log of all AI decisions with filtering and search
4. **Admin settings page**
   - Configure / update OpenAI API key (stored to database via backend)
   - Set confidence threshold for auto-execution vs. operator confirmation
   - View API usage stats (calls made, average confidence, override rate)

**Stage 3 Exit Proof**
- Robot captures a sign image, sends it to OpenAI via the backend, and receives a correct action
- Robot executes the AI-determined action (e.g., turns left when sign shows left arrow)
- Low-confidence results trigger operator confirmation in the console
- OpenAI API key is configurable via `.env` and persisted in the database
- Console shows video feed + AI decisions + mission state + sign recognition history

---

### Stage 4 — Open Innovation Round
**Goal:** Add a meaningful “wow” feature tied to medical domain value.

Pick ONE strong innovation and make it reliable:
- Medication delivery audit log (time, zones, confirmation beep)
- “Nurse call” mode: robot navigates to a beacon/marker when requested
- Dynamic obstacle pause: stop when obstacle detected (if sensor available) + resume
- Voice prompts via console (text-to-speech) + buzzer confirmations
- Smart batching: multi-stop route with simple optimization
- Remote assist: operator can take over instantly from console with auto-pausing

**Stage 4 Exit Proof**
- Feature is demoable end-to-end in under 60 seconds
- Clear story: “why it helps in a hospital”
- Does not break Stage 2/3 stability

---

## 2) Deployment Plan

### On Raspberry Pi (Robot)
**Recommended structure**
- `/opt/medirunner/robot/`
  - `motor_service.py`
  - `sensor_service.py`
  - `autonomy_service.py`
  - `camera_service.py`
  - `robot_api.py`
  - `config.yaml`

**Startup**
- Use `systemd` services for:
  - `robot-api.service`
  - `robot-camera.service` (optional)
- Ensure services auto-restart on crash

**Network**
- Assign stable hostname : NeuroNex-Navi
- Prefer local Wi-Fi Network
    credentials : 
        Wifi network - Cleint-5F
        Password - Welcome123()*

- Expose:
  - API por : 8000
  - Stream port :8080

**Safety defaults**
- Motors STOP on service stop
- Motors STOP if watchdog triggers
- Motors STOP if mode transitions to ERROR

### Next.js Control Console
**Run modes**
- Dev: `npm run dev` for rapid iteration
- Demo: `npm run build && npm start` for stability

**Configuration**
- Environment variables:
  - `ROBOT_API_URL`
  - `ROBOT_STREAM_URL`
  - `OPENAI_API_KEY` — OpenAI API key for Vision-based sign recognition (also persisted to database on first use)
  - `OPENAI_MODEL` — Model to use for sign recognition (default: `gpt-4o`)
  - `SIGN_CONFIDENCE_THRESHOLD` — Minimum confidence (0-1) for auto-execution (default: `0.7`)

**Release discipline**
- Tag stable milestones:
  - `stage1-stable`, `stage2-stable`, etc.
- Keep a “last known good” branch for demo fallback

---

## 3) Test Plan (By Stage + Cross-Cutting)

### General Test Principles
- Test the **full pipeline early**: UI -> API -> motors
- Always keep a **STOP** test available
- Validate in realistic lighting and surface conditions (IR sensors + camera are sensitive)

---

### Stage 1 Tests
**Electronics**
- Verify common ground between Pi, motor driver, and power system
- Confirm motor direction mapping (left/right not swapped)
- Verify buck converter output stable at 5V under load

**Software**
- API responds reliably
- Teleop commands move robot as expected
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
- Switch AUTO->TELEOP: control is immediate
- Switch TELEOP->AUTO: autonomy resumes only on explicit toggle

**Acceptance**
- Robot completes a representative corridor loop with minimal intervention

---

### Stage 3 Tests
**OpenAI Sign Recognition**
- Capture sign image under different lighting angles and distances; verify OpenAI returns correct action
- Repeatability: same sign image sent 5 times yields consistent action + confidence ≥ threshold
- Test all predefined actions: `TURN_LEFT`, `TURN_RIGHT`, `STOP`, `FORWARD`, `BACKWARD`, and at least one `ZONE_<name>`
- Verify low-confidence responses (e.g., blurry/partial sign) correctly trigger operator confirmation flow
- Test OpenAI API timeout handling: simulate slow/no response → robot enters safe stop
- Test with invalid/missing API key → backend returns clear error, robot does not crash

**API Key Management**
- Verify `.env` key is read on startup and persisted to database
- Verify admin UI can update the key and subsequent sign recognition uses the new key
- Verify masked key status endpoint does not leak the full key

**Behavior**
- Correct response to at least 3 sign types (e.g., LEFT arrow, RIGHT arrow, Zone name)
- Full state machine flow: `SIGN_DETECTED` → `CAPTURING_IMAGE` → `WAITING_FOR_AI` → `AI_DECISION_RECEIVED` → `EXECUTING_ACTION`
- Mission state transitions and AI decisions logged correctly to database
- Error handling: if sign not detected or AI fails, fallback behavior (safe stop + operator alert) triggers

**Sign Recognition History**
- Verify all recognition events are logged with image, prompt, action, confidence, and operator override status
- Verify history endpoint returns paginated results correctly

**Acceptance**
- One end-to-end mission demo: "Go to Zone X" with visible AI decision evidence in console
- Robot correctly interprets at least 3 different signs using OpenAI Vision in a single run

---

### Stage 4 Tests
**Innovation Feature**
- Test feature end-to-end 10 times without reboot
- Ensure it does not degrade Stage 2 navigation
- Add a kill-switch / disable toggle in console

**Acceptance**
- Reliable 60-second showcase demo + clear value statement

---

## 4) Integration Checklist (Always-On)
- ✅ Pinout finalized and documented
- ✅ One API contract everyone follows (command + telemetry)
- ✅ Logging: timestamps, mode changes, sensor summary, error codes
- ✅ “Demo mode” procedure written:
  1) Power on robot
  2) Confirm stream
  3) Confirm teleop
  4) Toggle auto
  5) Run mission
  6) Show innovation feature

---

## 5) Risk Register (Common Pitfalls + Mitigations)
- **Power instability / brownouts** → check buck converter, separate motor power if possible, reduce peak PWM
- **Motor noise resets Pi** → ensure grounds, add capacitance if available, reduce sudden acceleration
- **IR sensors inconsistent** → calibrate thresholds, add filtering, test surface contrast
- **Latency in teleop** → prefer WebSocket, keep payload small, prioritize STOP
- **Camera lag** → lower resolution/framerate, choose simpler streaming method
- **OpenAI API latency** → cache recent sign results, set request timeout (default 10s), robot pauses safely while waiting
- **OpenAI API cost** → debounce sign capture (min 5s between calls), log usage, set daily call limit in admin settings
- **OpenAI API key leak** → store encrypted in database, never log the full key, mask in admin UI
- **OpenAI API downtime** → fallback to operator manual decision via console; robot enters safe stop

---

## 6) Definition of Done (Competition-Ready)
- Robot is controllable at all times, with safe STOP
- Stage 2 autonomy is stable and repeatable
- Stage 3 intelligence is demonstrable: robot captures sign images, sends to OpenAI Vision, receives and executes correct actions, with full audit trail in database
- Stage 4 innovation is clear, reliable, and doesn’t break the base system
