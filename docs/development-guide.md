# Development Guide

## Quick Start

### Prerequisites

**Development Environment:**
- Node.js v18+ with npm/pnpm
- Python 3.9+ with pip
- Git for version control
- VS Code or preferred IDE

**Raspberry Pi Setup:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install python3-pip python3-venv
pip3 install opencv-python RPi.GPIO asyncio websockets

# Enable camera and GPIO
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable
# Navigate to: Interface Options → GPIO → Enable
```

**Development Machine:**
```bash
# Install Node.js (use nvm recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# Install pnpm
npm install -g pnpm

# Clone project
git clone <repository-url>
cd medi-runner
```

### Project Setup

1. **Install Dependencies**
```bash
# Root package.json for scripts
npm install

# Install all project dependencies
npm run install:all

# Or install individually
cd robot-server && pip3 install -r requirements.txt
cd ../controller-backend && pnpm install
cd ../controller-front-end && pnpm install
```

2. **Environment Configuration**
```bash
# Copy environment templates
cp controller-backend/.env.example controller-backend/.env
cp controller-front-end/.env.local.example controller-front-end/.env.local

# Configure robot server
cp robot-server/config.example.py robot-server/config.py
```

3. **Database Setup**
```bash
# Initialize database (SQLite for development)
cd controller-backend
npm run db:init
npm run db:migrate
```

## Development Workflow

### Starting Development Servers

**Option 1: All services together**
```bash
npm run dev
```

**Option 2: Individual services**
```bash
# Terminal 1: Robot server (on Raspberry Pi)
cd robot-server
python3 main.py

# Terminal 2: Backend API
cd controller-backend
npm run dev

# Terminal 3: Frontend
cd controller-front-end
npm run dev
```

### Development URLs
- Frontend: http://localhost:3000
- Backend API: http://localhost:3001
- Robot Server: ws://raspberrypi.local:8765

## Project Structure Deep Dive

### Robot Server (Python)

```python
# robot-server/main.py
import asyncio
from controllers import MotorController, SensorController
from services import WebSocketClient, ComputerVision

class RobotServer:
    def __init__(self):
        self.motor = MotorController()
        self.sensors = SensorController()
        self.vision = ComputerVision()
        self.websocket = WebSocketClient()
    
    async def start(self):
        """Start robot server with all subsystems"""
        await asyncio.gather(
            self.motor.start(),
            self.sensors.start(),
            self.vision.start(),
            self.websocket.connect()
        )

if __name__ == "__main__":
    robot = RobotServer()
    asyncio.run(robot.start())
```

**Key Classes:**

```python
# controllers/motor_controller.py
class MotorController:
    def __init__(self):
        # GPIO pin setup for L298N
        self.pins = {
            'in1': 17, 'in2': 27, 'in3': 22, 'in4': 23,
            'ena': 24, 'enb': 25
        }
    
    def move_forward(self, speed=50):
        """Move robot forward with specified speed (0-100)"""
        pass
    
    def turn_left(self, angle=90):
        """Turn robot left by specified angle"""
        pass
    
    def follow_line(self, sensor_data):
        """Line following algorithm"""
        pass

# controllers/sensor_controller.py
class SensorController:
    def __init__(self):
        self.ir_pins = [6, 12, 13, 19, 16]
        self.camera = None
    
    def read_ir_sensors(self):
        """Read IR sensor array, return [0,1,0,1,1] format"""
        return [GPIO.input(pin) for pin in self.ir_pins]
    
    def capture_image(self):
        """Capture image from Pi camera"""
        pass

# services/computer_vision.py
class ComputerVision:
    def __init__(self):
        self.camera = cv2.VideoCapture(0)
    
    def detect_signs(self, image):
        """Detect and interpret hospital signs"""
        pass
    
    def detect_obstacles(self, image):
        """Detect obstacles in path"""
        pass
```

### Controller Backend (Node.js)

```javascript
// controller-backend/src/app.js
const express = require('express');
const WebSocket = require('ws');
const cors = require('cors');

const app = express();
const server = require('http').createServer(app);
const wss = new WebSocket.Server({ server });

// Middleware
app.use(cors());
app.use(express.json());
app.use('/api/auth', require('./routes/auth'));
app.use('/api/robot', require('./routes/robot'));
app.use('/api/missions', require('./routes/missions'));

// WebSocket connection handling
wss.on('connection', (ws) => {
    console.log('Client connected');
    
    ws.on('message', async (message) => {
        const data = JSON.parse(message);
        await handleRobotCommand(data);
    });
});

server.listen(3001, () => {
    console.log('Server running on port 3001');
});
```

**Key Services:**

```javascript
// services/robotCommService.js
class RobotCommunicationService {
    constructor() {
        this.robotWs = null;
        this.clientWs = new Set();
    }
    
    connectToRobot(robotUrl) {
        this.robotWs = new WebSocket(robotUrl);
        this.robotWs.on('message', this.handleRobotMessage.bind(this));
    }
    
    sendCommand(command) {
        if (this.robotWs?.readyState === WebSocket.OPEN) {
            this.robotWs.send(JSON.stringify(command));
        }
    }
    
    handleRobotMessage(message) {
        // Broadcast robot status to all clients
        this.clientWs.forEach(ws => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(message);
            }
        });
    }
}

// services/missionService.js
class MissionService {
    async createMission(missionData) {
        // Validate mission parameters
        // Save to database
        // Send to robot for execution
    }
    
    async getMissionStatus(missionId) {
        // Query mission progress
        // Return current status
    }
    
    async cancelMission(missionId) {
        // Stop mission execution
        // Update database
        // Notify robot
    }
}
```

### Controller Frontend (Next.js)

```jsx
// controller-front-end/pages/control.js
import { useState, useEffect } from 'react';
import WebSocketService from '../services/websocket';
import RobotControl from '../components/RobotControl';
import CameraFeed from '../components/CameraFeed';
import StatusDisplay from '../components/StatusDisplay';

export default function ControlPage() {
    const [robotStatus, setRobotStatus] = useState({});
    const [wsService] = useState(() => new WebSocketService());
    
    useEffect(() => {
        wsService.connect();
        wsService.onMessage = (data) => {
            if (data.type === 'status') {
                setRobotStatus(data.data);
            }
        };
        
        return () => wsService.disconnect();
    }, []);
    
    const sendCommand = (command) => {
        wsService.send({
            type: 'command',
            ...command,
            timestamp: Date.now()
        });
    };
    
    return (
        <div className="grid grid-cols-2 gap-4 p-4">
            <div>
                <RobotControl onCommand={sendCommand} />
                <StatusDisplay status={robotStatus} />
            </div>
            <div>
                <CameraFeed robotStatus={robotStatus} />
            </div>
        </div>
    );
}
```

**Key Components:**

```jsx
// components/RobotControl/ManualControl.jsx
import { useState } from 'react';

export default function ManualControl({ onCommand }) {
    const [mode, setMode] = useState('manual'); // 'manual' | 'autonomous'
    const [speed, setSpeed] = useState(50);
    
    const handleMovement = (direction) => {
        onCommand({
            action: 'move',
            data: { direction, speed }
        });
    };
    
    const toggleMode = () => {
        const newMode = mode === 'manual' ? 'autonomous' : 'manual';
        setMode(newMode);
        onCommand({
            action: 'set_mode',
            data: { mode: newMode }
        });
    };
    
    return (
        <div className="p-4 border rounded">
            <div className="mb-4">
                <button
                    onClick={toggleMode}
                    className={`px-4 py-2 rounded ${
                        mode === 'autonomous' ? 'bg-green-500' : 'bg-blue-500'
                    } text-white`}
                >
                    {mode.toUpperCase()} MODE
                </button>
            </div>
            
            {mode === 'manual' && (
                <div className="grid grid-cols-3 gap-2">
                    <div></div>
                    <button onClick={() => handleMovement('forward')}>↑</button>
                    <div></div>
                    <button onClick={() => handleMovement('left')}>←</button>
                    <button onClick={() => handleMovement('stop')}>⏹</button>
                    <button onClick={() => handleMovement('right')}>→</button>
                    <div></div>
                    <button onClick={() => handleMovement('backward')}>↓</button>
                    <div></div>
                </div>
            )}
            
            <div className="mt-4">
                <label>Speed: {speed}%</label>
                <input
                    type="range"
                    min="10"
                    max="100"
                    value={speed}
                    onChange={(e) => setSpeed(e.target.value)}
                    className="w-full"
                />
            </div>
        </div>
    );
}
```

## Testing Strategy

### Unit Testing

```python
# tests/test_motor_controller.py
import unittest
from unittest.mock import Mock, patch
from controllers.motor_controller import MotorController

class TestMotorController(unittest.TestCase):
    def setUp(self):
        self.motor = MotorController()
    
    @patch('RPi.GPIO.output')
    def test_move_forward(self, mock_gpio):
        self.motor.move_forward(speed=50)
        # Assert GPIO calls
        mock_gpio.assert_called()
    
    def test_line_following_algorithm(self):
        # Test with different sensor inputs
        result = self.motor.follow_line([0, 0, 1, 0, 0])
        self.assertEqual(result, 'straight')
```

```javascript
// tests/robotCommService.test.js
const RobotCommunicationService = require('../src/services/robotCommService');
const WebSocket = require('ws');

describe('RobotCommunicationService', () => {
    let service;
    
    beforeEach(() => {
        service = new RobotCommunicationService();
    });
    
    test('should send command to robot', () => {
        const mockWs = { send: jest.fn(), readyState: WebSocket.OPEN };
        service.robotWs = mockWs;
        
        service.sendCommand({ action: 'move', direction: 'forward' });
        
        expect(mockWs.send).toHaveBeenCalledWith(
            JSON.stringify({ action: 'move', direction: 'forward' })
        );
    });
});
```

### Integration Testing

```javascript
// tests/integration/robot-api.test.js
const request = require('supertest');
const app = require('../src/app');

describe('Robot API Integration', () => {
    test('POST /api/robot/command should send command', async () => {
        const response = await request(app)
            .post('/api/robot/command')
            .send({
                action: 'move',
                direction: 'forward',
                speed: 50
            });
        
        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('success', true);
    });
});
```

## Debugging

### Logging Configuration

```python
# robot-server/utils/logger.py
import logging

def setup_logger(name, level=logging.INFO):
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    
    return logger
```

```javascript
// controller-backend/src/utils/logger.js
const winston = require('winston');

const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({ filename: 'error.log', level: 'error' }),
        new winston.transports.File({ filename: 'combined.log' })
    ]
});

if (process.env.NODE_ENV !== 'production') {
    logger.add(new winston.transports.Console({
        format: winston.format.simple()
    }));
}

module.exports = logger;
```

### Common Issues & Solutions

**Robot Server Issues:**
- GPIO permissions: `sudo usermod -a -G gpio $USER`
- Camera not detected: `sudo raspi-config` → Enable camera
- WebSocket connection failed: Check firewall and network settings

**Backend API Issues:**
- Port already in use: `lsof -ti:3001 | xargs kill -9`
- Database connection: Check database status and credentials
- CORS errors: Verify CORS configuration

**Frontend Issues:**
- WebSocket connection: Check backend server status
- Build errors: Clear `.next` directory and rebuild
- Environment variables: Verify `.env.local` configuration

## Deployment

### Production Build

```bash
# Build frontend for production
cd controller-front-end
npm run build

# Prepare robot server for deployment
cd robot-server
pip3 freeze > requirements.txt

# Backend production setup
cd controller-backend
npm run build
```

### Docker Deployment

```dockerfile
# Dockerfile.backend
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3001
CMD ["npm", "start"]
```

```dockerfile
# Dockerfile.frontend
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/out /usr/share/nginx/html
EXPOSE 80
```

### Environment Variables

```bash
# controller-backend/.env
NODE_ENV=production
PORT=3001
DB_URL=postgresql://user:pass@localhost:5432/medi_runner
ROBOT_WS_URL=ws://raspberrypi.local:8765
JWT_SECRET=your-secret-key

# controller-front-end/.env.local
NEXT_PUBLIC_API_URL=http://localhost:3001
NEXT_PUBLIC_WS_URL=ws://localhost:3001

# robot-server/config.py
WS_HOST = '0.0.0.0'
WS_PORT = 8765
CAMERA_RESOLUTION = (640, 480)
CAMERA_FPS = 30
DEBUG = False
```

This development guide provides the foundation for building and maintaining the Medi Runner robot system. Follow the conventions and patterns established here to ensure consistency and maintainability across the project.
