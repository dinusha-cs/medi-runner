# Medi-Runner Challenge 2026 -- Complete Guide & Evaluation

------------------------------------------------------------------------

# Additional Information -- Stage 3

## Zone Identification (Color Detection)

-   Use colored plastic pieces and T-shaped stands for practice.
-   Demonstrate color detection using the main arena zig-zag path.

## Hospital Direction Boards (Signboard Detection)

-   Three directional signboards + one department board.
-   Signboards placed near decision points.
-   Robot must detect board → interpret arrow → turn at next junction.

Example: - ICU → - ICU ← - ICU ↑

------------------------------------------------------------------------

# Marks & Penalties

## Grand Total: 360 Points

## Technical Evaluations -- 180 Points

### Stage 1 -- 55 Points

-   Robotics -- 20
-   Software -- 35

### Stage 2 -- 60 Points

-   Robotics -- 30
-   Software -- 30

### Stage 3 -- 65 Points

-   Robotics -- 25
-   Software -- 40

## Final Demonstration -- 180 Points

-   Stage Outputs -- 90
-   Innovative Extension -- 90

------------------------------------------------------------------------

# Stage 1 -- Birth of the Medi-Runner

## Robotics Track

### Assemble Robot

-   Build chassis, wheels, motors
-   Ignore default switch placement
-   Use provided power supply

### Connect Components

-   Power supply
-   Motor controller
-   Raspberry Pi (USB power only)
-   Camera module
-   IR array

### Demonstration Sequence

-   2 sec forward → stop
-   Turn right → stop
-   Turn left → stop
-   Snapshot
-   Reverse → stop

------------------------------------------------------------------------

## Software Track

-   Next.js app
-   Face enrollment
-   Face authentication
-   Voice-assisted login
-   Futuristic UI/UX

------------------------------------------------------------------------

# Stage 2 -- Corridor Navigation

## Robotics

-   Calibrate 5-way IR sensor
-   Follow:
    -   Straight
    -   Curves
    -   Circular
    -   Rectangular
    -   Zig-zag
-   Complete full main arena lap

## Software

-   Auto/manual toggle
-   Real-time video
-   Virtual controller
-   360° scan + viewer

------------------------------------------------------------------------

# Stage 3 -- Understanding Signs & Zones

## Robotics

### Zone Detection

  Color    Meaning     Beeps
  -------- ----------- -------
  Blue     Imaging     1
  Red      Emergency   2
  Green    General     3
  Yellow   Caution     4

### Signboard Detection

Robot must: - Read text - Interpret arrow - Navigate - Beep at
destination

Destination indication: - 5 consecutive beeps

------------------------------------------------------------------------

## Software

### Dashboard

Display real-time: - Zone - Mode - Voltage - Speed

### Prompt-Based Navigation

Example: "I want to deliver XYZ from X-ray to MRI."

Robot must: - Navigate pickup → 1 beep - Navigate destination → 2 beeps

### Mini Map

-   2D logical path trace
-   Zones visited
-   Stops and beeps

------------------------------------------------------------------------

# Stage 4 -- Innovative Extension

Open-ended extension stage.

Final 10-minute presentation must include: - Face recognition - Auto &
Manual modes - Live video + tele-drive - 360° capture - Dashboard -
Prompt navigation - Innovative extension demo

------------------------------------------------------------------------

# Appendix -- Hardware

-   Raspberry Pi 4 (8GB)
-   TCRT5000 IR Array
-   L298N Motor Driver
-   LM2596 Buck Converter
-   5V Active Buzzer
-   Camera V1.3 5MP
-   Power Pack (2x 8650 batteries)
