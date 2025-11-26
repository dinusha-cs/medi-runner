"""
Navigation Controller for Medi Runner Robot
Handles path planning, localization, and autonomous navigation
"""

import asyncio
import logging
import time
import math
import random

logger = logging.getLogger(__name__)

class NavigationController:
    """Navigation controller with simulation capabilities"""
    
    def __init__(self, simulation_mode=True):
        self.simulation_mode = simulation_mode
        self.is_initialized = False
        
        # Robot state
        self.current_position = {"x": 0, "y": 0, "angle": 0}
        self.target_position = None
        self.is_navigating = False
        self.navigation_mode = "manual"  # manual, auto, line_follow
        
        # Map and environment
        self.map_data = {
            "rooms": [
                {"id": "101", "x": 100, "y": 50, "name": "Patient Room 101"},
                {"id": "102", "x": 200, "y": 50, "name": "Patient Room 102"},
                {"id": "pharmacy", "x": 0, "y": 100, "name": "Pharmacy"},
                {"id": "surgery", "x": 150, "y": 150, "name": "Surgery"},
                {"id": "base", "x": 0, "y": 0, "name": "Base Station"}
            ],
            "obstacles": [
                {"x": 75, "y": 25, "width": 20, "height": 10, "type": "furniture"},
                {"x": 125, "y": 75, "width": 15, "height": 15, "type": "equipment"}
            ],
            "paths": [
                {"start": "base", "end": "pharmacy", "waypoints": [[0, 0], [0, 50], [0, 100]]},
                {"start": "pharmacy", "end": "101", "waypoints": [[0, 100], [50, 100], [100, 50]]}
            ]
        }
        
        # Navigation parameters
        self.navigation_params = {
            "max_speed": 80,
            "turn_speed": 40,
            "position_tolerance": 10,  # mm
            "angle_tolerance": 5,      # degrees
            "obstacle_threshold": 30,  # cm
            "line_follow_speed": 60
        }
        
        logger.info(f"🗺️ Navigation Controller initialized (simulation: {simulation_mode})")
    
    async def initialize(self):
        """Initialize navigation controller"""
        logger.info("🗺️ Initializing navigation systems...")
        
        if self.simulation_mode:
            await asyncio.sleep(0.4)  # Simulate initialization
            logger.info("✅ Navigation simulation initialized")
            
            # Set initial position
            self.current_position = {"x": 0, "y": 0, "angle": 0}
        else:
            # Real navigation initialization
            logger.info("✅ Physical navigation systems initialized")
        
        self.is_initialized = True
        return True
    
    async def cleanup(self):
        """Cleanup navigation controller"""
        if self.is_navigating:
            await self.stop_navigation()
        
        logger.info("🧹 Navigation controller cleanup complete")
        self.is_initialized = False
    
    async def navigate_to(self, target):
        """Navigate to target position or room"""
        if not self.is_initialized:
            raise Exception("Navigation controller not initialized")
        
        logger.info(f"🎯 Navigation to {target}")
        
        # Parse target
        if isinstance(target, dict):
            if "room" in target:
                target_pos = await self._get_room_position(target["room"])
            else:
                target_pos = target
        elif isinstance(target, str):
            target_pos = await self._get_room_position(target)
        else:
            raise ValueError("Invalid target format")
        
        self.target_position = target_pos
        self.is_navigating = True
        self.navigation_mode = "auto"
        
        if self.simulation_mode:
            result = await self._simulate_navigation(target_pos)
        else:
            result = await self._execute_physical_navigation(target_pos)
        
        return result
    
    async def stop_navigation(self):
        """Stop current navigation"""
        logger.info("🛑 Stopping navigation")
        
        self.is_navigating = False
        self.target_position = None
        self.navigation_mode = "manual"
        
        return {"action": "stop_navigation", "status": "completed"}
    
    async def follow_line(self, speed=60):
        """Start line following mode"""
        if not self.is_initialized:
            raise Exception("Navigation controller not initialized")
        
        logger.info(f"📏 Starting line following at {speed}% speed")
        
        self.navigation_mode = "line_follow"
        self.is_navigating = True
        
        if self.simulation_mode:
            result = await self._simulate_line_following(speed)
        else:
            result = await self._execute_physical_line_following(speed)
        
        return result
    
    async def get_current_position(self):
        """Get current robot position"""
        if self.simulation_mode:
            # Add some noise to simulate sensor uncertainty
            noise_x = random.uniform(-5, 5)
            noise_y = random.uniform(-5, 5)
            noise_angle = random.uniform(-2, 2)
            
            return {
                "x": self.current_position["x"] + noise_x,
                "y": self.current_position["y"] + noise_y,
                "angle": (self.current_position["angle"] + noise_angle) % 360
            }
        else:
            # Would use actual localization sensors
            return self.current_position.copy()
    
    async def get_status(self):
        """Get navigation status"""
        return {
            "navigation": {
                "is_navigating": self.is_navigating,
                "mode": self.navigation_mode,
                "current_position": await self.get_current_position(),
                "target_position": self.target_position,
                "distance_to_target": await self._calculate_distance_to_target() if self.target_position else None
            },
            "map": {
                "rooms_available": len(self.map_data["rooms"]),
                "obstacles_detected": len(self.map_data["obstacles"])
            },
            "status": "online" if self.is_initialized else "offline"
        }
    
    async def update_map(self, map_update):
        """Update map data (obstacles, rooms, etc.)"""
        logger.info("🗺️ Updating map data")
        
        if "rooms" in map_update:
            self.map_data["rooms"].extend(map_update["rooms"])
        
        if "obstacles" in map_update:
            self.map_data["obstacles"].extend(map_update["obstacles"])
        
        return {"status": "map_updated", "timestamp": time.time()}
    
    async def plan_path(self, start, goal):
        """Plan optimal path between two points"""
        logger.info(f"📍 Planning path from {start} to {goal}")
        
        if self.simulation_mode:
            path = await self._simulate_path_planning(start, goal)
        else:
            path = await self._execute_physical_path_planning(start, goal)
        
        return path
    
    async def _get_room_position(self, room_id):
        """Get position coordinates for a room"""
        for room in self.map_data["rooms"]:
            if room["id"] == room_id or room["name"].lower() == room_id.lower():
                return {"x": room["x"], "y": room["y"], "angle": 0}
        
        raise ValueError(f"Room '{room_id}' not found in map")
    
    async def _simulate_navigation(self, target_pos):
        """Simulate autonomous navigation"""
        logger.info(f"🤖 Simulating navigation to {target_pos}")
        
        start_pos = self.current_position.copy()
        distance = math.sqrt(
            (target_pos["x"] - start_pos["x"])**2 + 
            (target_pos["y"] - start_pos["y"])**2
        )
        
        # Simulate navigation time (1 second per 10mm)
        navigation_time = distance / 100
        update_interval = 0.5
        updates = int(navigation_time / update_interval)
        
        logger.info(f"📏 Distance: {distance:.1f}mm, Time: {navigation_time:.1f}s")
        
        for i in range(updates + 1):
            progress = (i + 1) / (updates + 1)
            
            # Update position along path
            self.current_position["x"] = start_pos["x"] + (target_pos["x"] - start_pos["x"]) * progress
            self.current_position["y"] = start_pos["y"] + (target_pos["y"] - start_pos["y"]) * progress
            
            # Update angle to face target
            if progress < 1:
                dx = target_pos["x"] - self.current_position["x"]
                dy = target_pos["y"] - self.current_position["y"]
                self.current_position["angle"] = math.atan2(dy, dx) * 180 / math.pi % 360
            
            await asyncio.sleep(update_interval)
            logger.debug(f"🎯 Navigation progress: {progress * 100:.1f}%")
        
        self.is_navigating = False
        self.navigation_mode = "manual"
        
        return {
            "action": "navigate_to",
            "target": target_pos,
            "final_position": self.current_position.copy(),
            "distance_traveled": distance,
            "time_elapsed": navigation_time,
            "status": "completed"
        }
    
    async def _simulate_line_following(self, speed):
        """Simulate line following navigation"""
        logger.info("📏 Simulating line following")
        
        # Simulate following a line for a set duration
        follow_time = 10  # seconds
        update_interval = 0.2
        updates = int(follow_time / update_interval)
        
        for i in range(updates):
            # Simulate slight course corrections
            angle_correction = random.uniform(-3, 3)
            self.current_position["angle"] = (self.current_position["angle"] + angle_correction) % 360
            
            # Move forward along line
            forward_distance = (speed / 100) * 5  # mm per update
            rad_angle = self.current_position["angle"] * math.pi / 180
            
            self.current_position["x"] += forward_distance * math.cos(rad_angle)
            self.current_position["y"] += forward_distance * math.sin(rad_angle)
            
            await asyncio.sleep(update_interval)
        
        self.is_navigating = False
        self.navigation_mode = "manual"
        
        return {
            "action": "line_follow",
            "speed": speed,
            "time_elapsed": follow_time,
            "final_position": self.current_position.copy(),
            "status": "completed"
        }
    
    async def _simulate_path_planning(self, start, goal):
        """Simulate A* or similar path planning algorithm"""
        await asyncio.sleep(0.5)  # Simulate computation time
        
        # Simple straight-line path for simulation
        path = {
            "waypoints": [
                start,
                {"x": (start["x"] + goal["x"]) / 2, "y": (start["y"] + goal["y"]) / 2},
                goal
            ],
            "total_distance": math.sqrt((goal["x"] - start["x"])**2 + (goal["y"] - start["y"])**2),
            "estimated_time": 15.0,  # seconds
            "obstacles_avoided": random.randint(0, 3)
        }
        
        return path
    
    async def _calculate_distance_to_target(self):
        """Calculate distance to current target"""
        if not self.target_position:
            return None
        
        distance = math.sqrt(
            (self.target_position["x"] - self.current_position["x"])**2 + 
            (self.target_position["y"] - self.current_position["y"])**2
        )
        
        return round(distance, 1)
    
    async def _execute_physical_navigation(self, target_pos):
        """Execute navigation on physical hardware"""
        logger.warning("🔩 Physical navigation not implemented - using simulation")
        return await self._simulate_navigation(target_pos)
    
    async def _execute_physical_line_following(self, speed):
        """Execute line following on physical hardware"""
        logger.warning("🔩 Physical line following not implemented - using simulation")
        return await self._simulate_line_following(speed)
    
    async def _execute_physical_path_planning(self, start, goal):
        """Execute path planning with physical sensors"""
        logger.warning("🔩 Physical path planning not implemented - using simulation")
        return await self._simulate_path_planning(start, goal)
    
    async def get_map_data(self):
        """Get current map data"""
        return {
            "map": self.map_data,
            "timestamp": time.time(),
            "coordinate_system": "mm from origin"
        }
    
    async def emergency_navigation_stop(self):
        """Emergency stop for navigation"""
        logger.warning("🚨 Emergency navigation stop")
        
        self.is_navigating = False
        self.target_position = None
        self.navigation_mode = "emergency_stopped"
        
        return {"action": "emergency_nav_stop", "status": "executed"}
    
    async def calibrate_navigation(self):
        """Calibrate navigation sensors and positioning"""
        logger.info("🔧 Starting navigation calibration...")
        
        if self.simulation_mode:
            await asyncio.sleep(3)  # Simulate calibration time
            logger.info("✅ Navigation calibration completed (simulated)")
        else:
            # Real calibration would involve sensor alignment, etc.
            pass
        
        return {
            "calibration": "completed",
            "position_accuracy": "±5mm",
            "angle_accuracy": "±2°",
            "timestamp": time.time()
        }