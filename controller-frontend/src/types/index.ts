// Types for the Medi Runner Challenge 2025 Frontend Dashboard

export interface RobotState {
  id: string;
  name: string;
  status: 'connected' | 'disconnected' | 'error';
  position: {
    x: number;
    y: number;
    z: number;
    rotation: number;
  };
  battery: {
    level: number;
    voltage: number;
    charging: boolean;
  };
  sensors: {
    lidar: SensorData;
    camera: SensorData;
    ultrasonic: SensorData[];
    imu: IMUData;
    gps: GPSData;
  };
  actuators: {
    wheels: WheelData[];
    gripper: GripperData;
    arm: ArmData;
  };
  mission: Mission | null;
  lastUpdate: string;
}

export interface SensorData {
  status: 'active' | 'inactive' | 'error';
  value: number | string | object;
  timestamp: string;
  unit?: string;
}

export interface IMUData extends SensorData {
  value: {
    acceleration: { x: number; y: number; z: number };
    gyroscope: { x: number; y: number; z: number };
    magnetometer: { x: number; y: number; z: number };
    orientation: { roll: number; pitch: number; yaw: number };
  };
}

export interface GPSData extends SensorData {
  value: {
    latitude: number;
    longitude: number;
    altitude: number;
    accuracy: number;
    satellites: number;
  };
}

export interface WheelData {
  id: string;
  speed: number; // RPM
  direction: 'forward' | 'backward' | 'stop';
  power: number; // 0-100%
  encoder: number;
}

export interface GripperData {
  position: number; // 0-100% (0 = closed, 100 = open)
  force: number; // 0-100%
  hasObject: boolean;
  status: 'moving' | 'idle' | 'error';
}

export interface ArmData {
  joints: ArmJoint[];
  endEffector: {
    x: number;
    y: number;
    z: number;
  };
  status: 'moving' | 'idle' | 'error';
}

export interface ArmJoint {
  id: string;
  angle: number; // degrees
  targetAngle: number;
  speed: number; // degrees/second
  torque: number;
}

export interface Mission {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'paused';
  progress: number; // 0-100%
  steps: MissionStep[];
  currentStep: number;
  startTime?: string;
  endTime?: string;
  estimatedDuration: number; // seconds
}

export interface MissionStep {
  id: string;
  name: string;
  type: 'move' | 'pickup' | 'drop' | 'scan' | 'wait' | 'custom';
  description: string;
  parameters: Record<string, any>;
  status: 'pending' | 'active' | 'completed' | 'failed';
  duration: number; // seconds
}

export interface Command {
  id: string;
  type: 'move' | 'rotate' | 'stop' | 'pickup' | 'drop' | 'scan' | 'mission' | 'emergency';
  parameters: Record<string, any>;
  timestamp: string;
  acknowledged: boolean;
  completed: boolean;
  error?: string;
}

export interface CameraFeed {
  id: string;
  name: string;
  url: string;
  status: 'active' | 'inactive' | 'error';
  resolution: { width: number; height: number };
  fps: number;
  latency: number; // milliseconds
}

export interface SystemStatus {
  uptime: number; // seconds
  cpuUsage: number; // 0-100%
  memoryUsage: number; // 0-100%
  networkLatency: number; // milliseconds
  connectedRobots: number;
  activeMissions: number;
  lastHeartbeat: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  source: 'robot' | 'system' | 'mission' | 'user';
  robotId?: string;
  message: string;
  details?: Record<string, any>;
}

export interface WebSocketMessage {
  type: 'robot_update' | 'mission_update' | 'command' | 'log' | 'system_status' | 'camera_frame';
  data: any;
  timestamp: string;
  id?: string;
}

// UI State types
export interface DashboardState {
  selectedRobotId: string | null;
  selectedMissionId: string | null;
  showLogs: boolean;
  showCameras: boolean;
  emergencyMode: boolean;
  connectionStatus: 'connected' | 'connecting' | 'disconnected';
}

// Props types for components
export interface ControlPanelProps {
  robot: RobotState;
  onCommand: (command: Omit<Command, 'id' | 'timestamp' | 'acknowledged' | 'completed'>) => void;
  disabled?: boolean;
}

export interface MissionManagerProps {
  missions: Mission[];
  robots: RobotState[];
  onStartMission: (missionId: string, robotId: string) => void;
  onStopMission: (missionId: string) => void;
  onCreateMission: (mission: Omit<Mission, 'id' | 'status' | 'progress' | 'currentStep'>) => void;
}

export interface SensorDisplayProps {
  sensors: RobotState['sensors'];
  compact?: boolean;
}

export interface CameraViewProps {
  feeds: CameraFeed[];
  selectedFeedId?: string;
  onSelectFeed?: (feedId: string) => void;
}

export interface LogViewerProps {
  logs: LogEntry[];
  maxEntries?: number;
  filter?: {
    level?: LogEntry['level'][];
    source?: LogEntry['source'][];
    robotId?: string;
  };
}