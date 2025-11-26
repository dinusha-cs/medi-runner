"""
Navigation Controller for autonomous robot movement
Handles path planning, line following, and autonomous navigation modes.
"""

import asyncio
import time
import math
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from config import LINE_FOLLOWING, SAFETY
from utils.logger import setup_logger


class NavigationMode(Enum):
    """Navigation modes for the robot."""
    MANUAL = "manual"
    LINE_FOLLOWING = "line_following"
    AUTONOMOUS = "autonomous"
    MISSION = "mission"
    EMERGENCY_STOP = "emergency_stop"


class NavigationState(Enum):
    """States for autonomous navigation."""
    IDLE = "idle"
    MOVING = "moving"
    TURNING = "turning"
    SEARCHING = "searching"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"
    MISSION_PAUSED = "mission_paused"


class NavigationController:
    """
    High-level navigation controller that coordinates motor and sensor systems.
    """
    
    def __init__(self, motor_controller, sensor_controller):
        self.logger = setup_logger('NavigationController')
        
        # Component references
        self.motor = motor_controller
        self.sensors = sensor_controller
        
        # Navigation state
        self.mode = NavigationMode.MANUAL
        self.state = NavigationState.IDLE
        
        # Line following parameters
        self.base_speed = LINE_FOLLOWING['BASE_SPEED']
        self.turn_speed = LINE_FOLLOWING['TURN_SPEED']
        self.correction_factor = LINE_FOLLOWING['CORRECTION_FACTOR']
        
        # Navigation control
        self.navigation_task = None
        self.emergency_stop = False
        
        # Path tracking
        self.current_waypoint = None
        self.waypoint_queue = []
        self.position = {'x': 0, 'y': 0, 'heading': 0}  # Estimated position
        
        # Line following state
        self.line_lost_time = None
        self.last_line_position = 0
        
        # Statistics
        self.stats = {
            'distance_traveled': 0,
            'turns_completed': 0,
            'lines_followed': 0,
            'obstacles_avoided': 0
        }
    
    async def start(self):
        """
        Start the navigation controller.
        """
        self.logger.info("Navigation controller started")
        
        # Start navigation loop
        self.navigation_task = asyncio.create_task(self._navigation_loop())
    
    async def stop(self):
        """
        Stop the navigation controller.
        """
        if self.navigation_task:
            self.navigation_task.cancel()
            try:
                await self.navigation_task
            except asyncio.CancelledError:
                pass
        
        await self.set_mode(NavigationMode.MANUAL)
        self.logger.info("Navigation controller stopped")
    
    async def set_mode(self, mode: NavigationMode):
        """
        Set navigation mode.
        """
        if self.mode != mode:
            self.logger.info(f"Changing navigation mode: {self.mode.value} -> {mode.value}")
            
            # Stop current movement when changing modes
            await self.motor.stop_motors()
            
            self.mode = mode
            
            if mode == NavigationMode.EMERGENCY_STOP:
                self.emergency_stop = True
                self.state = NavigationState.IDLE
            else:
                self.emergency_stop = False
    
    async def _navigation_loop(self):
        """
        Main navigation control loop.
        """
        while True:
            try:
                if self.emergency_stop:
                    await self.motor.stop_motors()
                    self.state = NavigationState.IDLE
                    await asyncio.sleep(0.1)
                    continue
                
                if self.mode == NavigationMode.LINE_FOLLOWING:
                    await self._line_following_control()
                elif self.mode == NavigationMode.AUTONOMOUS:
                    await self._autonomous_control()
                elif self.mode == NavigationMode.MISSION:
                    await self._mission_control()
                
                await asyncio.sleep(0.05)  # 20Hz control loop
                
            except Exception as e:
                self.logger.error(f"Error in navigation loop: {e}")
                await self.set_mode(NavigationMode.EMERGENCY_STOP)
                await asyncio.sleep(1)
    
    async def _line_following_control(self):
        """
        Line following navigation logic.
        """
        try:
            # Get line position from sensors
            line_data = await self.sensors.get_line_position()
            
            if line_data['line_detected']:
                # Reset lost line timer
                self.line_lost_time = None
                self.last_line_position = line_data['position']
                
                if line_data['intersection']:
                    # Handle intersection
                    await self._handle_intersection()
                else:
                    # Follow the line
                    await self._follow_line(line_data)
                
                self.state = NavigationState.MOVING
                
            else:
                # Line lost - attempt recovery
                await self._handle_lost_line()
        
        except Exception as e:
            self.logger.error(f"Error in line following: {e}")
            await self.motor.stop_motors()
    
    async def _follow_line(self, line_data: Dict[str, Any]):
        """
        Follow detected line based on sensor data.
        """
        position = line_data['position']
        error = line_data['error']
        
        # Calculate steering adjustment
        steering = position * self.correction_factor
        
        # Determine movement based on line position
        if abs(position) < 0.2:  # On line
            await self.motor.move('forward', self.base_speed)
        elif position < -0.5:  # Line is to the left
            await self.motor.move('left', self.turn_speed)
        elif position > 0.5:   # Line is to the right
            await self.motor.move('right', self.turn_speed)
        else:  # Small corrections
            # Adjust motor speeds for gentle steering
            left_speed = self.base_speed - (steering * 20)
            right_speed = self.base_speed + (steering * 20)
            
            # Use the motor's line following method for precise control
            await self.motor.follow_line(line_data['sensors'], self.base_speed)
    
    async def _handle_intersection(self):
        """
        Handle intersection detection.
        """
        self.logger.info("Intersection detected")
        
        # Stop briefly at intersection
        await self.motor.stop_motors()
        await asyncio.sleep(LINE_FOLLOWING['INTERSECTION_DELAY'])
        
        # Continue forward through intersection (default behavior)
        # This could be enhanced to handle specific intersection rules
        await self.motor.move('forward', self.base_speed, 1.0)
        
        self.stats['turns_completed'] += 1
    
    async def _handle_lost_line(self):
        """
        Handle lost line recovery.
        """
        if self.line_lost_time is None:
            self.line_lost_time = time.time()
            self.logger.warning("Line lost - starting recovery")
        
        elapsed = time.time() - self.line_lost_time
        
        if elapsed < LINE_FOLLOWING['LOST_LINE_TIMEOUT']:
            # Search for line based on last known position
            if self.last_line_position < 0:
                # Line was to the left, turn left to find it
                await self.motor.move('left', self.turn_speed * 0.8)
            elif self.last_line_position > 0:
                # Line was to the right, turn right
                await self.motor.move('right', self.turn_speed * 0.8)
            else:
                # Unknown, try gentle forward movement
                await self.motor.move('forward', self.base_speed * 0.6)
            
            self.state = NavigationState.SEARCHING
        else:
            # Recovery timeout - stop and alert
            await self.motor.stop_motors()
            self.logger.error("Line recovery timeout - switching to manual mode")
            await self.set_mode(NavigationMode.MANUAL)
    
    async def _autonomous_control(self):
        """
        Autonomous navigation without line following.
        """
        # Check for obstacles
        obstacles = await self.sensors.detect_obstacles()
        
        if obstacles:
            await self._avoid_obstacles(obstacles)
        else:
            # Continue with planned movement
            if self.current_waypoint:
                await self._navigate_to_waypoint(self.current_waypoint)
            else:
                self.state = NavigationState.IDLE
    
    async def _mission_control(self):
        """
        Mission-based navigation control.
        """
        if self.waypoint_queue:
            if not self.current_waypoint:
                self.current_waypoint = self.waypoint_queue.pop(0)
                self.logger.info(f"Starting waypoint: {self.current_waypoint}")
            
            # Check if current waypoint is reached
            if await self._is_waypoint_reached(self.current_waypoint):
                self.logger.info(f"Waypoint reached: {self.current_waypoint}")
                self.current_waypoint = None
                
                if not self.waypoint_queue:
                    self.logger.info("Mission completed")
                    await self.set_mode(NavigationMode.MANUAL)
            else:
                await self._navigate_to_waypoint(self.current_waypoint)
        else:
            self.state = NavigationState.IDLE
    
    async def _avoid_obstacles(self, obstacles: List[Dict[str, Any]]):
        """
        Implement obstacle avoidance behavior.
        """
        self.logger.info(f"Avoiding {len(obstacles)} obstacles")
        
        # Simple obstacle avoidance - turn away from largest obstacle
        largest_obstacle = max(obstacles, key=lambda o: o['area'])
        
        # Determine avoidance direction based on obstacle position
        image_center = 320  # Assuming 640px width
        obstacle_center = largest_obstacle['center_x']
        
        if obstacle_center < image_center:
            # Obstacle on left, turn right
            await self.motor.move('right', self.turn_speed, 1.0)
        else:
            # Obstacle on right, turn left
            await self.motor.move('left', self.turn_speed, 1.0)
        
        self.state = NavigationState.OBSTACLE_AVOIDANCE
        self.stats['obstacles_avoided'] += 1
    
    async def _navigate_to_waypoint(self, waypoint: Dict[str, Any]):
        """
        Navigate to a specific waypoint.
        """
        target_x = waypoint.get('x', 0)
        target_y = waypoint.get('y', 0)
        
        # Calculate direction to waypoint
        dx = target_x - self.position['x']
        dy = target_y - self.position['y']
        
        # Calculate distance and angle
        distance = math.sqrt(dx*dx + dy*dy)
        target_angle = math.atan2(dy, dx)
        
        # Calculate turn needed
        angle_diff = target_angle - math.radians(self.position['heading'])
        
        # Normalize angle to [-π, π]
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        
        # Turn towards waypoint if needed
        if abs(angle_diff) > 0.1:  # 5.7 degrees tolerance
            turn_direction = 'right' if angle_diff > 0 else 'left'
            await self.motor.move(turn_direction, self.turn_speed, 0.5)
            self.state = NavigationState.TURNING
        else:
            # Move towards waypoint
            await self.motor.move('forward', self.base_speed)
            self.state = NavigationState.MOVING
    
    async def _is_waypoint_reached(self, waypoint: Dict[str, Any]) -> bool:
        """
        Check if the robot has reached the target waypoint.
        """
        # This is a simplified implementation
        # In practice, you'd use odometry or GPS for position tracking
        return False  # Placeholder
    
    async def add_waypoint(self, x: float, y: float, action: Optional[str] = None):
        """
        Add a waypoint to the navigation queue.
        """
        waypoint = {
            'x': x,
            'y': y,
            'action': action,
            'timestamp': time.time()
        }
        
        self.waypoint_queue.append(waypoint)
        self.logger.info(f"Added waypoint: {waypoint}")
    
    async def clear_waypoints(self):
        """
        Clear all waypoints and stop current navigation.
        """
        self.waypoint_queue.clear()
        self.current_waypoint = None
        await self.motor.stop_motors()
        self.logger.info("Waypoints cleared")
    
    async def emergency_stop(self):
        """
        Immediately stop all movement and enter emergency mode.
        """
        await self.set_mode(NavigationMode.EMERGENCY_STOP)
        self.logger.warning("EMERGENCY STOP activated")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current navigation status.
        """
        return {
            'mode': self.mode.value,
            'state': self.state.value,
            'position': self.position.copy(),
            'current_waypoint': self.current_waypoint,
            'waypoints_remaining': len(self.waypoint_queue),
            'emergency_stop': self.emergency_stop,
            'line_lost_time': self.line_lost_time,
            'stats': self.stats.copy(),
            'timestamp': time.time()
        }
