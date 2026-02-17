<<<<<<< HEAD
# Medi Runner Challenge 2025 🚀

## Project Overview

The Medi Runner Challenge is a comprehensive robotics and software development competition where teams build an autonomous medical delivery robot capable of navigating hospital corridors, interpreting signs, and functioning as a smart medical assistant.

## Challenge Structure

The competition consists of 4 progressive stages:

### Stage 1: Robot Birth & Foundation
- **Robotics Track**: Hardware assembly, component integration, basic motor control
- **Software Track**: User authentication, team enrollment, control console setup
- **Outcome**: Functional robot with operational control interface

### Stage 2: Navigation & Control
- **Robotics Track**: Line following, stable turning, sensor integration
- **Software Track**: Next.js control console, tele-driving vs autonomous mode switching
- **Outcome**: Robot capable of corridor navigation with remote/auto control

### Stage 3: Intelligence & Recognition
- **Robotics Track**: Advanced sensor integration, hospital zone recognition
- **Software Track**: Sign interpretation, AI-powered decision making, real-time streaming
- **Outcome**: Smart robot that understands hospital environments

### Stage 4: Innovation Challenge
- **Open Track**: Creative extensions, medical domain improvements, advanced features
- **Outcome**: Production-ready medical delivery system concept

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Robot Server   │◄──►│ Controller API  │◄──►│ Frontend UI     │
│ (Raspberry Pi)  │    │ (Backend)       │    │ (Next.js)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Hardware      │    │   WebSocket/    │    │   Real-time     │
│   Components    │    │   HTTP APIs     │    │   Dashboard     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         ▼                                              ▼
┌─────────────────┐                          ┌─────────────────┐
│   Simulation    │                          │   3D Viewer     │
│   Tools         │                          │   (Three.js)    │
└─────────────────┘                          └─────────────────┘
```

## Project Structure

```
medi-runner/
├── docs/                      # Documentation and design specs
├── robot-server/              # Raspberry Pi robot controller
├── controller-backend/        # Node.js/Express API server
├── controller-front-end/      # Next.js dashboard
├── hardware/                  # Hardware specs and diagrams
├── tests/                     # Integration and unit tests
└── deployment/               # Docker and deployment configs
```

## Technology Stack

### Hardware
- **Brain**: Raspberry Pi 4 Model B
- **Motors**: DC Motors with L298N Driver
- **Sensors**: IR Line Following Array, Pi Camera v1.3
- **Power**: Dual battery pack with LM2596 converter
- **Audio**: 3V Active Buzzer
- **Chassis**: Pre-assembled robot car kit

### Software
- **Robot Controller**: Python (asyncio, OpenCV, GPIO)
- **Backend API**: Node.js/Express with WebSocket support
- **Frontend**: Next.js with real-time streaming
- **Communication**: WebSocket, HTTP REST APIs
- **AI/ML**: Computer Vision, Sign Recognition
- **Database**: SQLite/PostgreSQL for mission data
- **Simulation**: Python/pygame 2D, Three.js 3D, Webots support

## Team Roles

### 🎯 Innovation Lead
- Strategic planning and vision
- Cross-track coordination
- Innovation challenge leadership
- Performance optimization

### 🤖 Pilot (Robotics Track Lead)
- Hardware assembly and integration
- Sensor programming and calibration
- Autonomous navigation algorithms
- Motor control and power management

### 💻 Co-Pilot (Software Track Lead)
- Control console development
- Real-time communication systems
- AI integration and computer vision
- User interface and experience

### 👥 Sub-team Members
- Specialized task execution
- Pair programming support
- Testing and debugging
- Documentation and demos

## Development Phases

### Phase 1: Foundation (Stage 1)
1. **Hardware Setup**
   - Component assembly and wiring
   - GPIO configuration and testing
   - Basic motor control implementation

2. **Software Foundation**
   - Project structure initialization
   - Authentication system
   - Basic control interface

### Phase 2: Navigation (Stage 2)
1. **Autonomous Navigation**
   - Line following algorithm
   - Sensor data processing
   - Movement control logic

2. **Control Systems**
   - Real-time dashboard
   - Manual/auto mode switching
   - Live camera streaming

### Phase 3: Intelligence (Stage 3)
1. **Computer Vision**
   - Sign recognition system
   - Hospital zone mapping
   - Object detection and avoidance

2. **Smart Behaviors**
   - Decision making algorithms
   - Mission planning system
   - Emergency protocols

### Phase 4: Innovation (Stage 4)
1. **Creative Extensions**
   - Advanced AI features
   - Medical domain integrations
   - Performance optimizations

## Quick Start Guide

1. **Prerequisites Setup**
   ```bash
   # Raspberry Pi preparation
   sudo apt update && sudo apt upgrade
   pip install opencv-python RPi.GPIO asyncio
   
   # Development environment
   node --version  # v18+
   npm install -g pnpm
   ```

2. **Project Installation**
   ```bash
   git clone <repository>
   cd medi-runner
   
   # Install all dependencies
   npm run install:all
   ```

3. **Development**
   ```bash
   # Start all services
   npm run dev
   
   # Or start individually
   npm run dev:robot      # Robot server
   npm run dev:backend    # API backend
   npm run dev:frontend   # Next.js UI
   ```

4. **Robot Simulation**
   ```bash
   # 2D Hospital Simulation (pygame)
   python hospital_simulation.py
   
   # 3D Web Viewer (Three.js)
   # Open robot_3d_viewer.html in browser
   
   # Component Testing
   python demo_robot.py
   
   # WebSocket Testing
   python test_robot_system.py
   ```

## Competition Strategy

### Time Management
- **25% Hardware Assembly & Integration**
- **35% Core Navigation & Control**
- **25% Intelligence & Computer Vision**
- **15% Innovation & Polish**

### Success Metrics
- ✅ Robot responds to commands
- ✅ Autonomous line following
- ✅ Real-time video streaming
- ✅ Sign recognition accuracy
- ✅ Innovation feature completeness

## Resources & References

- [Raspberry Pi GPIO Documentation](https://pinout.xyz/)
- [OpenCV Computer Vision](https://docs.opencv.org/4.x/)
- [Next.js Documentation](https://nextjs.org/docs)
- [L298N Motor Driver Guide](hardware/motor-driver-guide.md)
- [Competition Rules & Scoring](docs/competition-rules.md)

---

**🏆 Ready to build the future of medical robotics? Let's make it happen!**
=======
initial commit
>>>>>>> 50c1c59d56f03a32fabb976e9d07910eac598c3f
