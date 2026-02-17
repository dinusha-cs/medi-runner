import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { 
  RobotState, 
  Mission, 
  SystemStatus, 
  LogEntry, 
  CameraFeed, 
  DashboardState, 
  Command,
  WebSocketMessage
} from '@/types';

interface AppState {
  // Connection state
  connectionStatus: 'connected' | 'connecting' | 'disconnected';
  lastHeartbeat: Date | null;
  
  // Robot data
  robots: Record<string, RobotState>;
  selectedRobotId: string | null;
  
  // Mission data
  missions: Record<string, Mission>;
  selectedMissionId: string | null;
  
  // System data
  systemStatus: SystemStatus | null;
  logs: LogEntry[];
  cameraFeeds: Record<string, CameraFeed>;
  
  // UI state
  dashboardState: DashboardState;
  
  // Commands
  pendingCommands: Command[];
  commandHistory: Command[];
  
  // Actions
  setConnectionStatus: (status: 'connected' | 'connecting' | 'disconnected') => void;
  updateHeartbeat: () => void;
  
  // Robot actions
  updateRobot: (robot: RobotState) => void;
  removeRobot: (robotId: string) => void;
  selectRobot: (robotId: string | null) => void;
  
  // Mission actions
  updateMission: (mission: Mission) => void;
  removeMission: (missionId: string) => void;
  selectMission: (missionId: string | null) => void;
  
  // System actions
  updateSystemStatus: (status: SystemStatus) => void;
  addLog: (log: LogEntry) => void;
  clearLogs: () => void;
  
  // Camera actions
  updateCameraFeed: (feed: CameraFeed) => void;
  removeCameraFeed: (feedId: string) => void;
  
  // Command actions
  addCommand: (command: Omit<Command, 'id' | 'timestamp' | 'acknowledged' | 'completed'>) => void;
  acknowledgeCommand: (commandId: string) => void;
  completeCommand: (commandId: string, error?: string) => void;
  
  // Dashboard actions
  toggleEmergencyMode: () => void;
  setShowLogs: (show: boolean) => void;
  setShowCameras: (show: boolean) => void;
  
  // WebSocket message handler
  handleWebSocketMessage: (message: WebSocketMessage) => void;
}

export const useAppStore = create<AppState>()(
  devtools(
    (set, get) => ({
      // Initial state
      connectionStatus: 'disconnected',
      lastHeartbeat: null,
      robots: {},
      selectedRobotId: null,
      missions: {},
      selectedMissionId: null,
      systemStatus: null,
      logs: [],
      cameraFeeds: {},
      dashboardState: {
        selectedRobotId: null,
        selectedMissionId: null,
        showLogs: false,
        showCameras: true,
        emergencyMode: false,
        connectionStatus: 'disconnected',
      },
      pendingCommands: [],
      commandHistory: [],
      
      // Connection actions
      setConnectionStatus: (status) => 
        set((state) => ({
          connectionStatus: status,
          dashboardState: { ...state.dashboardState, connectionStatus: status },
        })),
      
      updateHeartbeat: () =>
        set({ lastHeartbeat: new Date() }),
      
      // Robot actions
      updateRobot: (robot) =>
        set((state) => ({
          robots: { ...state.robots, [robot.id]: robot },
        })),
      
      removeRobot: (robotId) =>
        set((state) => {
          const { [robotId]: removed, ...remaining } = state.robots;
          return {
            robots: remaining,
            selectedRobotId: state.selectedRobotId === robotId ? null : state.selectedRobotId,
          };
        }),
      
      selectRobot: (robotId) =>
        set((state) => ({
          selectedRobotId: robotId,
          dashboardState: { ...state.dashboardState, selectedRobotId: robotId },
        })),
      
      // Mission actions
      updateMission: (mission) =>
        set((state) => ({
          missions: { ...state.missions, [mission.id]: mission },
        })),
      
      removeMission: (missionId) =>
        set((state) => {
          const { [missionId]: removed, ...remaining } = state.missions;
          return {
            missions: remaining,
            selectedMissionId: state.selectedMissionId === missionId ? null : state.selectedMissionId,
          };
        }),
      
      selectMission: (missionId) =>
        set((state) => ({
          selectedMissionId: missionId,
          dashboardState: { ...state.dashboardState, selectedMissionId: missionId },
        })),
      
      // System actions
      updateSystemStatus: (status) =>
        set({ systemStatus: status }),
      
      addLog: (log) =>
        set((state) => ({
          logs: [log, ...state.logs].slice(0, 1000), // Keep last 1000 logs
        })),
      
      clearLogs: () =>
        set({ logs: [] }),
      
      // Camera actions
      updateCameraFeed: (feed) =>
        set((state) => ({
          cameraFeeds: { ...state.cameraFeeds, [feed.id]: feed },
        })),
      
      removeCameraFeed: (feedId) =>
        set((state) => {
          const { [feedId]: removed, ...remaining } = state.cameraFeeds;
          return { cameraFeeds: remaining };
        }),
      
      // Command actions
      addCommand: (commandData) => {
        const command: Command = {
          ...commandData,
          id: `cmd_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date().toISOString(),
          acknowledged: false,
          completed: false,
        };
        
        set((state) => ({
          pendingCommands: [...state.pendingCommands, command],
        }));
        
        return command;
      },
      
      acknowledgeCommand: (commandId) =>
        set((state) => ({
          pendingCommands: state.pendingCommands.map((cmd) =>
            cmd.id === commandId ? { ...cmd, acknowledged: true } : cmd
          ),
        })),
      
      completeCommand: (commandId, error) =>
        set((state) => {
          const command = state.pendingCommands.find((cmd) => cmd.id === commandId);
          if (!command) return state;
          
          const completedCommand = {
            ...command,
            completed: true,
            error,
          };
          
          return {
            pendingCommands: state.pendingCommands.filter((cmd) => cmd.id !== commandId),
            commandHistory: [completedCommand, ...state.commandHistory].slice(0, 100),
          };
        }),
      
      // Dashboard actions
      toggleEmergencyMode: () =>
        set((state) => ({
          dashboardState: {
            ...state.dashboardState,
            emergencyMode: !state.dashboardState.emergencyMode,
          },
        })),
      
      setShowLogs: (show) =>
        set((state) => ({
          dashboardState: { ...state.dashboardState, showLogs: show },
        })),
      
      setShowCameras: (show) =>
        set((state) => ({
          dashboardState: { ...state.dashboardState, showCameras: show },
        })),
      
      // WebSocket message handler
      handleWebSocketMessage: (message) => {
        const { type, data } = message;
        const state = get();
        
        switch (type) {
          case 'robot_update':
            state.updateRobot(data as RobotState);
            break;
            
          case 'mission_update':
            state.updateMission(data as Mission);
            break;
            
          case 'system_status':
            state.updateSystemStatus(data as SystemStatus);
            break;
            
          case 'log':
            state.addLog(data as LogEntry);
            break;
            
          case 'camera_frame':
            // Handle camera frame updates if needed
            break;
            
          case 'command':
            if (data.acknowledged) {
              state.acknowledgeCommand(data.id);
            }
            if (data.completed) {
              state.completeCommand(data.id, data.error);
            }
            break;
            
          default:
            console.warn('Unknown WebSocket message type:', type);
        }
      },
    }),
    {
      name: 'medi-runner-app-store',
    }
  )
);

// Selectors for better performance
export const useRobots = () => useAppStore((state) => Object.values(state.robots));
export const useSelectedRobot = () => {
  const robots = useAppStore((state) => state.robots);
  const selectedId = useAppStore((state) => state.selectedRobotId);
  return selectedId ? robots[selectedId] : null;
};

export const useMissions = () => useAppStore((state) => Object.values(state.missions));
export const useSelectedMission = () => {
  const missions = useAppStore((state) => state.missions);
  const selectedId = useAppStore((state) => state.selectedMissionId);
  return selectedId ? missions[selectedId] : null;
};

export const useCameraFeeds = () => useAppStore((state) => Object.values(state.cameraFeeds));
export const useConnectionStatus = () => useAppStore((state) => state.connectionStatus);
export const useEmergencyMode = () => useAppStore((state) => state.dashboardState.emergencyMode);