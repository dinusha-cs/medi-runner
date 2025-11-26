"""
Mission Executor Service
Handles mission planning, execution, and monitoring.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from enum import Enum

from config import MISSION, SAFETY
from utils.logger import setup_logger


class MissionState(Enum):
    """Mission execution states."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionType(Enum):
    """Types of missions the robot can perform."""
    DELIVERY = "delivery"
    PATROL = "patrol"
    INSPECTION = "inspection"
    EMERGENCY = "emergency"
    CUSTOM = "custom"


class MissionExecutor:
    """
    Executes missions and coordinates with navigation and vision systems.
    """
    
    def __init__(self, navigation_controller, computer_vision):
        self.logger = setup_logger('MissionExecutor')
        
        # Component references
        self.navigation = navigation_controller
        self.vision = computer_vision
        
        # Mission state
        self.state = MissionState.IDLE
        self.current_mission = None
        self.mission_queue = []
        
        # Mission execution
        self.execution_task = None
        self.start_time = None
        self.pause_time = None
        
        # Mission history
        self.completed_missions = []
        self.max_history = 50
        
        # Statistics
        self.stats = {
            'missions_completed': 0,
            'missions_failed': 0,
            'total_execution_time': 0,
            'average_mission_time': 0,
            'success_rate': 0
        }
    
    async def start(self):
        """
        Start the mission executor service.
        """
        self.logger.info("Mission executor service started")
    
    async def stop(self):
        """
        Stop the mission executor and cancel current mission.
        """
        if self.execution_task:
            await self.cancel_mission()
        
        self.logger.info("Mission executor service stopped")
    
    async def start_mission(self, mission_data: Dict[str, Any]) -> bool:
        """
        Start a new mission.
        
        Args:
            mission_data: Mission configuration and parameters
            
        Returns:
            True if mission started successfully, False otherwise
        """
        try:
            # Validate mission data
            if not self._validate_mission(mission_data):
                return False
            
            # Cancel current mission if running
            if self.state in [MissionState.EXECUTING, MissionState.PLANNING]:
                await self.cancel_mission()
            
            # Prepare mission
            mission = self._prepare_mission(mission_data)
            self.current_mission = mission
            
            self.logger.info(f"Starting mission: {mission['id']}")
            
            # Start execution
            self.state = MissionState.PLANNING
            self.start_time = time.time()
            self.pause_time = None
            
            self.execution_task = asyncio.create_task(self._execute_mission(mission))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting mission: {e}")
            self.state = MissionState.FAILED
            return False
    
    async def pause_mission(self) -> bool:
        """
        Pause the current mission.
        """
        if self.state == MissionState.EXECUTING:
            self.state = MissionState.PAUSED
            self.pause_time = time.time()
            
            # Stop robot movement
            await self.navigation.emergency_stop()
            
            self.logger.info("Mission paused")
            return True
        
        return False
    
    async def resume_mission(self) -> bool:
        """
        Resume a paused mission.
        """
        if self.state == MissionState.PAUSED:
            self.state = MissionState.EXECUTING
            
            # Calculate pause duration
            if self.pause_time:
                pause_duration = time.time() - self.pause_time
                self.logger.info(f"Resuming mission after {pause_duration:.2f} seconds")
                self.pause_time = None
            
            return True
        
        return False
    
    async def cancel_mission(self) -> bool:
        """
        Cancel the current mission.
        """
        if self.state in [MissionState.EXECUTING, MissionState.PLANNING, MissionState.PAUSED]:
            self.state = MissionState.CANCELLED
            
            # Stop execution task
            if self.execution_task:
                self.execution_task.cancel()
                try:
                    await self.execution_task
                except asyncio.CancelledError:
                    pass
                self.execution_task = None
            
            # Stop robot
            await self.navigation.emergency_stop()
            
            # Record cancelled mission
            if self.current_mission:
                self._record_mission_completion(MissionState.CANCELLED)
            
            self.logger.info("Mission cancelled")
            return True
        
        return False
    
    def _validate_mission(self, mission_data: Dict[str, Any]) -> bool:
        """
        Validate mission data before execution.
        """
        try:
            # Required fields
            required_fields = ['type', 'waypoints']
            for field in required_fields:
                if field not in mission_data:
                    self.logger.error(f"Missing required field: {field}")
                    return False
            
            # Validate mission type
            try:
                MissionType(mission_data['type'])
            except ValueError:
                self.logger.error(f"Invalid mission type: {mission_data['type']}")
                return False
            
            # Validate waypoints
            waypoints = mission_data['waypoints']
            if not isinstance(waypoints, list) or len(waypoints) == 0:
                self.logger.error("Waypoints must be a non-empty list")
                return False
            
            if len(waypoints) > MISSION['MAX_WAYPOINTS']:
                self.logger.error(f"Too many waypoints: {len(waypoints)} > {MISSION['MAX_WAYPOINTS']}")
                return False
            
            # Validate each waypoint
            for i, waypoint in enumerate(waypoints):
                if not isinstance(waypoint, dict):
                    self.logger.error(f"Waypoint {i} must be a dictionary")
                    return False
                
                if 'x' not in waypoint or 'y' not in waypoint:
                    self.logger.error(f"Waypoint {i} missing coordinates")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating mission: {e}")
            return False
    
    def _prepare_mission(self, mission_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare mission for execution.
        """
        mission = {
            'id': mission_data.get('id', f"mission_{int(time.time())}"),
            'type': mission_data['type'],
            'waypoints': mission_data['waypoints'],
            'tasks': mission_data.get('tasks', []),
            'parameters': mission_data.get('parameters', {}),
            'priority': mission_data.get('priority', 'normal'),
            'timeout': mission_data.get('timeout', MISSION['MAX_MISSION_TIME']),
            'created_time': time.time(),
            'start_time': None,
            'estimated_duration': self._estimate_mission_duration(mission_data),
            'current_waypoint_index': 0,
            'completed_waypoints': [],
            'status': 'prepared'
        }
        
        return mission
    
    def _estimate_mission_duration(self, mission_data: Dict[str, Any]) -> float:
        """
        Estimate mission completion time.
        """
        # Simple estimation based on number of waypoints
        base_time = 30  # seconds per waypoint
        waypoint_count = len(mission_data['waypoints'])
        
        # Add time for tasks
        task_time = len(mission_data.get('tasks', [])) * 15
        
        return base_time * waypoint_count + task_time
    
    async def _execute_mission(self, mission: Dict[str, Any]):
        """
        Execute the mission.
        """
        try:
            self.logger.info(f"Executing mission {mission['id']}")
            
            mission['start_time'] = time.time()
            self.state = MissionState.EXECUTING
            
            # Execute waypoints
            for i, waypoint in enumerate(mission['waypoints']):
                if self.state != MissionState.EXECUTING:
                    break
                
                mission['current_waypoint_index'] = i
                
                self.logger.info(f"Navigating to waypoint {i}: {waypoint}")
                
                # Navigate to waypoint
                success = await self._navigate_to_waypoint(waypoint)
                
                if not success:
                    raise Exception(f"Failed to reach waypoint {i}")
                
                # Execute waypoint tasks
                await self._execute_waypoint_tasks(waypoint, mission)
                
                mission['completed_waypoints'].append(waypoint)
                
                # Check timeout
                elapsed = time.time() - mission['start_time']
                if elapsed > mission['timeout']:
                    raise Exception("Mission timeout")
            
            # Mission completed successfully
            if self.state == MissionState.EXECUTING:
                self.state = MissionState.COMPLETED
                self.logger.info(f"Mission {mission['id']} completed successfully")
                self._record_mission_completion(MissionState.COMPLETED)
        
        except asyncio.CancelledError:
            self.logger.info("Mission execution cancelled")
        except Exception as e:
            self.logger.error(f"Mission execution failed: {e}")
            self.state = MissionState.FAILED
            self._record_mission_completion(MissionState.FAILED)
        finally:
            self.execution_task = None
    
    async def _navigate_to_waypoint(self, waypoint: Dict[str, Any]) -> bool:
        """
        Navigate to a specific waypoint.
        """
        try:
            # Set navigation mode based on waypoint type
            if 'navigation_mode' in waypoint:
                mode = waypoint['navigation_mode']
                if mode == 'line_following':
                    await self.navigation.set_mode(NavigationMode.LINE_FOLLOWING)
                elif mode == 'autonomous':
                    await self.navigation.set_mode(NavigationMode.AUTONOMOUS)
            
            # Add waypoint to navigation queue
            await self.navigation.add_waypoint(
                waypoint['x'], 
                waypoint['y'], 
                waypoint.get('action')
            )
            
            # Wait for waypoint to be reached (simplified)
            timeout = waypoint.get('timeout', 60)  # 60 second timeout per waypoint
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.state != MissionState.EXECUTING:
                    return False
                
                nav_status = await self.navigation.get_status()
                
                # Check if waypoint is reached (simplified check)
                if nav_status['waypoints_remaining'] == 0:
                    return True
                
                await asyncio.sleep(1)
            
            self.logger.warning(f"Timeout reaching waypoint: {waypoint}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error navigating to waypoint: {e}")
            return False
    
    async def _execute_waypoint_tasks(self, waypoint: Dict[str, Any], mission: Dict[str, Any]):
        """
        Execute tasks at a waypoint.
        """
        tasks = waypoint.get('tasks', [])
        
        for task in tasks:
            if self.state != MissionState.EXECUTING:
                break
            
            await self._execute_task(task, waypoint, mission)
            
            # Pause at waypoint
            pause_duration = waypoint.get('pause_duration', MISSION['PAUSE_DURATION'])
            await asyncio.sleep(pause_duration)
    
    async def _execute_task(self, task: Dict[str, Any], waypoint: Dict[str, Any], mission: Dict[str, Any]):
        """
        Execute a specific task.
        """
        task_type = task.get('type', 'unknown')
        
        self.logger.info(f"Executing task: {task_type}")
        
        try:
            if task_type == 'delivery':
                await self._handle_delivery_task(task, waypoint)
            elif task_type == 'inspection':
                await self._handle_inspection_task(task, waypoint)
            elif task_type == 'wait':
                wait_time = task.get('duration', 5)
                await asyncio.sleep(wait_time)
            elif task_type == 'scan':
                await self._handle_scan_task(task, waypoint)
            else:
                self.logger.warning(f"Unknown task type: {task_type}")
        
        except Exception as e:
            self.logger.error(f"Error executing task {task_type}: {e}")
    
    async def _handle_delivery_task(self, task: Dict[str, Any], waypoint: Dict[str, Any]):
        """
        Handle delivery task (placeholder implementation).
        """
        self.logger.info("Simulating delivery task")
        await asyncio.sleep(2)  # Simulate delivery time
    
    async def _handle_inspection_task(self, task: Dict[str, Any], waypoint: Dict[str, Any]):
        """
        Handle inspection task using computer vision.
        """
        self.logger.info("Performing inspection")
        
        # Capture image for inspection
        frame = await self._capture_inspection_image()
        if frame is not None:
            # Process image for signs or anomalies
            results = await self.vision.process_frame(frame)
            
            # Log inspection results
            self.logger.info(f"Inspection results: {len(results.get('signs', []))} signs detected")
    
    async def _handle_scan_task(self, task: Dict[str, Any], waypoint: Dict[str, Any]):
        """
        Handle environment scanning task.
        """
        self.logger.info("Scanning environment")
        
        # Rotate robot to scan 360 degrees
        for angle in [90, 90, 90, 90]:  # Four 90-degree turns
            if self.state != MissionState.EXECUTING:
                break
            
            await self.navigation.motor.turn_by_angle(angle)
            await asyncio.sleep(1)  # Pause to capture data
    
    async def _capture_inspection_image(self):
        """
        Capture image for inspection (placeholder).
        """
        # This would interface with the camera
        return None
    
    def _record_mission_completion(self, final_state: MissionState):
        """
        Record mission completion statistics.
        """
        if not self.current_mission:
            return
        
        mission = self.current_mission
        completion_time = time.time()
        
        # Calculate execution time
        if mission.get('start_time'):
            execution_time = completion_time - mission['start_time']
        else:
            execution_time = 0
        
        # Update statistics
        if final_state == MissionState.COMPLETED:
            self.stats['missions_completed'] += 1
        else:
            self.stats['missions_failed'] += 1
        
        self.stats['total_execution_time'] += execution_time
        
        total_missions = self.stats['missions_completed'] + self.stats['missions_failed']
        if total_missions > 0:
            self.stats['average_mission_time'] = self.stats['total_execution_time'] / total_missions
            self.stats['success_rate'] = self.stats['missions_completed'] / total_missions
        
        # Add to history
        mission_record = {
            **mission,
            'final_state': final_state.value,
            'completion_time': completion_time,
            'execution_time': execution_time
        }
        
        self.completed_missions.append(mission_record)
        
        # Limit history size
        if len(self.completed_missions) > self.max_history:
            self.completed_missions.pop(0)
        
        self.current_mission = None
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current mission executor status.
        """
        status = {
            'state': self.state.value,
            'stats': self.stats.copy(),
            'mission_queue_size': len(self.mission_queue),
            'history_size': len(self.completed_missions),
            'timestamp': time.time()
        }
        
        if self.current_mission:
            mission = self.current_mission
            elapsed = time.time() - (mission.get('start_time') or time.time())
            
            status['current_mission'] = {
                'id': mission['id'],
                'type': mission['type'],
                'progress': mission['current_waypoint_index'] / len(mission['waypoints']),
                'elapsed_time': elapsed,
                'estimated_remaining': max(0, mission['estimated_duration'] - elapsed),
                'current_waypoint': mission['current_waypoint_index'],
                'total_waypoints': len(mission['waypoints'])
            }
        
        return status