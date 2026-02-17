# Hardware Specifications

## Component Overview

### Raspberry Pi 4 Model B (Robot Brain)

**Specifications:**
- CPU: Quad-core ARM Cortex-A72 @ 1.5GHz
- RAM: 4GB LPDDR4
- Storage: 32GB microSD card (minimum)
- GPIO: 40-pin header
- Camera: CSI connector for Pi Camera
- Power: 5V/3A via USB-C or GPIO

**GPIO Pin Assignment:**
```
Pin 2  (5V)     → Motor Driver VCC
Pin 4  (5V)     → Sensor Array VCC
Pin 6  (GND)    → Common Ground
Pin 11 (GPIO17) → Motor Driver IN1
Pin 13 (GPIO27) → Motor Driver IN2
Pin 15 (GPIO22) → Motor Driver IN3
Pin 16 (GPIO23) → Motor Driver IN4
Pin 18 (GPIO24) → Motor Driver ENA (PWM)
Pin 22 (GPIO25) → Motor Driver ENB (PWM)
Pin 29 (GPIO5)  → Buzzer Signal
Pin 31 (GPIO6)  → IR Sensor 1
Pin 32 (GPIO12) → IR Sensor 2
Pin 33 (GPIO13) → IR Sensor 3
Pin 35 (GPIO19) → IR Sensor 4
Pin 36 (GPIO16) → IR Sensor 5
```

### Motor Driver (L298N)

**Specifications:**
- Dual H-Bridge motor driver
- Operating Voltage: 5V-35V
- Logic Voltage: 5V
- Output Current: Up to 2A per channel
- PWM Support: Yes

**Connections:**
```
VCC     → 5V from Pi or external
GND     → Common Ground
IN1/IN2 → Left Motor Control
IN3/IN4 → Right Motor Control
ENA/ENB → PWM Speed Control
OUT1/OUT2 → Left Motor
OUT3/OUT4 → Right Motor
```

**Control Logic:**
```python
# Forward
IN1 = HIGH, IN2 = LOW, IN3 = HIGH, IN4 = LOW
# Backward
IN1 = LOW, IN2 = HIGH, IN3 = LOW, IN4 = HIGH
# Turn Left
IN1 = LOW, IN2 = HIGH, IN3 = HIGH, IN4 = LOW
# Turn Right
IN1 = HIGH, IN2 = LOW, IN3 = LOW, IN4 = HIGH
# Stop
IN1 = LOW, IN2 = LOW, IN3 = LOW, IN4 = LOW
```

### DC Motors + Robot Chassis

**Motor Specifications:**
- Type: DC Geared Motors
- Voltage: 3V-6V
- RPM: 200-300 (with gear reduction)
- Torque: High due to gear reduction
- Encoder: Optional (for precise positioning)

**Chassis Features:**
- 4-wheel design with rear-wheel drive
- Acrylic or aluminum frame
- Battery compartment
- Mounting points for Pi and sensors
- Cable management system

### IR Line Following Sensor Array

**Specifications:**
- Number of Sensors: 5-sensor array
- Detection Range: 1-3cm
- Output: Digital (HIGH/LOW)
- Operating Voltage: 3.3V-5V
- Response Time: <1ms

**Sensor Layout:**
```
[S1] [S2] [S3] [S4] [S5]
  ←     ←  Center →    →
Far   Near       Near  Far
Left  Left       Right Right
```

**Reading Interpretation:**
```python
# Line Following Logic
[0,0,1,0,0] → Go Straight
[0,1,1,0,0] → Slight Left
[1,1,0,0,0] → Turn Left
[0,0,1,1,0] → Slight Right
[0,0,0,1,1] → Turn Right
[1,1,1,1,1] → Intersection/Stop
[0,0,0,0,0] → Lost Line
```

### Pi Camera Module v1.3

**Specifications:**
- Sensor: 5MP OmniVision OV5647
- Resolution: 2592×1944 static, 1080p30 video
- Interface: 15-pin MIPI CSI-2
- Lens: Fixed focus, f/2.9
- Field of View: 54°×41°

**Mounting:**
- Front-facing for navigation
- Adjustable angle bracket
- Cable length: 15cm (extendable)

### Power System

**Battery Pack:**
- Type: 2x 18650 Li-ion batteries
- Voltage: 7.4V nominal
- Capacity: 2500mAh minimum
- Protection: Built-in BMS

**DC-DC Converter (LM2596):**
- Input: 7-35V
- Output: 5V @ 3A (adjustable)
- Efficiency: >85%
- Features: Overcurrent protection

**Power Distribution:**
```
Battery → Switch → LM2596 → 5V Rail
                     ├── Raspberry Pi (USB-C)
                     ├── Motor Driver VCC
                     └── Sensor Array VCC
```

### Additional Components

**3V Active Buzzer:**
- Operating Voltage: 3-5V
- Sound Level: 85dB
- Frequency: 2300Hz ±500Hz
- Usage: Status alerts, collision warnings

**Jumper Wires & Breadboard:**
- Male-to-Female jumpers for Pi connections
- Male-to-Male for breadboard connections
- Half-size breadboard for prototyping
- Resistors: 220Ω, 1kΩ, 10kΩ

## Wiring Diagram

```
┌─────────────────┐
│  Raspberry Pi   │
│                 │
│  GPIO Pins      │
└─────┬───────────┘
      │
      ├─── 5V ─────┬─── Motor Driver VCC
      │            └─── Sensor Array VCC
      │
      ├─── GND ────┬─── Motor Driver GND
      │            ├─── Sensor Array GND
      │            └─── Buzzer GND
      │
      ├─── GPIO17 ── Motor Driver IN1
      ├─── GPIO27 ── Motor Driver IN2
      ├─── GPIO22 ── Motor Driver IN3
      ├─── GPIO23 ── Motor Driver IN4
      ├─── GPIO24 ── Motor Driver ENA
      ├─── GPIO25 ── Motor Driver ENB
      │
      ├─── GPIO5  ── Buzzer Signal
      │
      ├─── GPIO6  ── IR Sensor 1
      ├─── GPIO12 ── IR Sensor 2
      ├─── GPIO13 ── IR Sensor 3
      ├─── GPIO19 ── IR Sensor 4
      └─── GPIO16 ── IR Sensor 5

┌─────────────────┐    ┌─────────────────┐
│  Left Motor     │    │  Right Motor    │
└─────────────────┘    └─────────────────┘
         ▲                       ▲
         │                       │
┌─────────────────────────────────────────┐
│           L298N Motor Driver            │
└─────────────────────────────────────────┘
```

## Assembly Instructions

1. **Chassis Preparation**
   - Assemble robot chassis according to kit instructions
   - Mount motors and wheels
   - Install battery compartment

2. **Power System Setup**
   - Connect batteries to LM2596 input
   - Adjust output to 5V using potentiometer
   - Install power switch and USB port
   - Test voltage levels

3. **Raspberry Pi Installation**
   - Mount Pi on chassis using standoffs
   - Connect power via USB-C or GPIO
   - Install camera module
   - Insert programmed SD card

4. **Motor Driver Connection**
   - Mount L298N on chassis
   - Connect power and control signals
   - Connect motors to outputs
   - Test motor rotation

5. **Sensor Integration**
   - Mount IR sensor array at front
   - Connect sensor outputs to GPIO pins
   - Install buzzer for audio feedback
   - Test sensor readings

6. **Final Testing**
   - Power on system
   - Verify all connections
   - Test basic movements
   - Calibrate sensors

## Troubleshooting

**Common Issues:**
- Motor not rotating: Check power connections and driver wiring
- Sensors not responding: Verify GPIO pin assignments
- Camera not detected: Check CSI cable connection
- Power issues: Measure voltage levels at each component
- Erratic behavior: Check for loose connections

**Safety Precautions:**
- Always disconnect power when making connections
- Use proper voltage levels for each component
- Avoid short circuits
- Handle components with anti-static precautions
- Test connections before applying full power
