#!/usr/bin/env python3
"""
5 IR Sensor + Bump + Proximity Sensor Test Simulator
Tests robot behavior with 5 IR sensors, 1 bump sensor, and 1 proximity sensor
"""

import asyncio
import json
import logging
import time
import sys
import os
from pathlib import Path
from datetime import datetime

# Add current directory to path for local imports
sys.path.append(str(Path(__file__).parent))

# Set up basic configuration for simulation
SIMULATION_MODE = True
DEBUG = True
LOGGING = {
    'LEVEL': 'INFO',
    'FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}

from robot.sensor_controller import SensorController
from robot.motor_controller import MotorController
from robot.navigation_controller import NavigationController

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING.get('LEVEL', 'INFO')),
    format=LOGGING.get('FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)

logger = logging.getLogger(__name__)

class FiveIRSensorSimulator:
    """Enhanced robot simulator for 5 IR sensors + bump + proximity"""
    
    def __init__(self, test_data_file="ir_sensor_5_test_data.json"):
        self.test_data_file = test_data_file
        self.test_data = None
        self.current_scenario = None
        self.current_step = 0
        self.scenario_start_time = 0
        
        # Initialize controllers in simulation mode
        self.sensor_controller = SensorController(simulation_mode=True)
        self.motor_controller = MotorController(simulation_mode=True)
        self.navigation_controller = NavigationController(simulation_mode=True)
        
        # Robot state
        self.robot_state = {
            "position": {"x": 0, "y": 0, "angle": 0},
            "speed": {"left": 0, "right": 0},
            "current_action": "stopped",
            "line_following_active": False,
            "scenario_name": None,
            "obstacle_detected": False,
            "collision_detected": False
        }
        
        self.simulation_log = []
        
    async def initialize(self):
        """Initialize the simulation"""
        logger.info("🤖 Initializing 5 IR Sensor Test Simulator...")
        
        # Load test data
        try:
            with open(self.test_data_file, 'r') as f:
                self.test_data = json.load(f)
            logger.info(f"✅ Loaded test data from {self.test_data_file}")
        except FileNotFoundError:
            logger.error(f"❌ Test data file not found: {self.test_data_file}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in test data file: {e}")
            return False
        
        # Initialize robot controllers
        await self.sensor_controller.initialize()
        await self.motor_controller.initialize()
        await self.navigation_controller.initialize()
        
        logger.info("✅ 5 IR Sensor Test Simulator initialized successfully!")
        return True
    
    async def cleanup(self):
        """Cleanup simulation resources"""
        logger.info("🧹 Cleaning up 5 IR Sensor Test Simulator...")
        
        await self.sensor_controller.cleanup()
        await self.motor_controller.cleanup()
        await self.navigation_controller.cleanup()
        
        logger.info("✅ Cleanup complete")
    
    def load_scenario(self, scenario_name):
        """Load a specific test scenario"""
        if scenario_name not in self.test_data["test_scenarios"]:
            available = list(self.test_data["test_scenarios"].keys())
            raise ValueError(f"Scenario '{scenario_name}' not found. Available: {available}")
        
        self.current_scenario = self.test_data["test_scenarios"][scenario_name]
        self.robot_state["scenario_name"] = scenario_name
        self.current_step = 0
        self.scenario_start_time = time.time()
        
        logger.info(f"📋 Loaded scenario: {scenario_name}")
        logger.info(f"📝 Description: {self.current_scenario['description']}")
        logger.info(f"⏱️ Duration: {self.current_scenario['duration']} seconds")
    
    def get_current_sensor_data(self):
        """Get sensor data for current time in scenario"""
        if not self.current_scenario:
            return {"ir1": 150, "ir2": 200, "ir3": 200, "ir4": 200, "ir5": 150, "bump": 0, "proximity": 250}
        
        elapsed_time = time.time() - self.scenario_start_time
        sensor_data_points = self.current_scenario["sensor_data"]
        
        # Find the appropriate data point based on elapsed time
        for i, data_point in enumerate(sensor_data_points):
            if elapsed_time <= data_point["timestamp"]:
                return {
                    "ir1": data_point["ir1"],
                    "ir2": data_point["ir2"], 
                    "ir3": data_point["ir3"],
                    "ir4": data_point["ir4"],
                    "ir5": data_point["ir5"],
                    "bump": data_point["bump"],
                    "proximity": data_point["proximity"],
                    "action": data_point["action"],
                    "timestamp": data_point["timestamp"]
                }
        
        # If we've passed all data points, return the last one
        if sensor_data_points:
            last_point = sensor_data_points[-1]
            return {
                "ir1": last_point["ir1"],
                "ir2": last_point["ir2"],
                "ir3": last_point["ir3"],
                "ir4": last_point["ir4"],
                "ir5": last_point["ir5"],
                "bump": last_point["bump"],
                "proximity": last_point["proximity"],
                "action": last_point["action"],
                "timestamp": elapsed_time
            }
        
        return {"ir1": 150, "ir2": 200, "ir3": 200, "ir4": 200, "ir5": 150, "bump": 0, "proximity": 250, "action": "stopped"}
    
    def analyze_sensor_data(self, sensor_data):
        """Analyze 5 IR sensor + bump + proximity data and determine robot action"""
        ir1, ir2, ir3, ir4, ir5 = sensor_data["ir1"], sensor_data["ir2"], sensor_data["ir3"], sensor_data["ir4"], sensor_data["ir5"]
        bump = sensor_data["bump"]
        proximity = sensor_data["proximity"]
        
        thresholds = self.test_data["sensor_thresholds"]
        
        # Priority 1: Check for collision (bump sensor)
        if bump == 1:
            return "collision_detected"
        
        # Priority 2: Check for very close obstacle (proximity sensor)
        if proximity < thresholds["proximity_collision_imminent"]:
            return "emergency_stop"
        elif proximity < thresholds["proximity_obstacle_very_close"]:
            return "obstacle_very_close"
        elif proximity < thresholds["proximity_obstacle_close"]:
            return "obstacle_detected"
        
        # Priority 3: Line following with 5 IR sensors
        
        # Calculate sensor statistics
        ir_values = [ir1, ir2, ir3, ir4, ir5]
        ir_sum = sum(ir_values)
        ir_avg = ir_sum / 5
        
        # Check for line loss (all sensors low)
        if all(val < thresholds["ir_lost_line_threshold"] for val in ir_values):
            return "line_lost"
        
        # Check for intersection (multiple sensors high)
        high_sensors = sum(1 for val in ir_values if val > thresholds["ir_intersection_threshold"])
        if high_sensors >= 4:
            return "intersection_detected"
        elif high_sensors >= 3:
            return "approaching_intersection"
        
        # Check for wide line detection (multiple consecutive sensors high)
        if (ir1 > thresholds["ir_line_detected"] and 
            ir2 > thresholds["ir_strong_line"] and 
            ir3 > thresholds["ir_very_strong_line"] and 
            ir4 > thresholds["ir_strong_line"] and 
            ir5 > thresholds["ir_line_detected"]):
            
            # Wide line - use weighted average for position
            weighted_pos = (ir1*(-2) + ir2*(-1) + ir3*0 + ir4*1 + ir5*2) / ir_sum
            
            if weighted_pos < -0.3:
                return "wide_line_slight_right"
            elif weighted_pos > 0.3:
                return "wide_line_slight_left"
            else:
                return "wide_line_forward"
        
        # Standard line following logic
        
        # Center sensor dominant - good line tracking
        if ir3 > thresholds["ir_strong_line"]:
            # Calculate weighted position using all 5 sensors
            weighted_pos = (ir1*(-2) + ir2*(-1) + ir3*0 + ir4*1 + ir5*2) / ir_sum
            
            if weighted_pos < -0.5:
                return "slight_right_correction"
            elif weighted_pos > 0.5:
                return "slight_left_correction"
            else:
                return "forward"
        
        # Check for line on left side (sensors 1, 2)
        elif (ir1 > thresholds["ir_line_detected"] or ir2 > thresholds["ir_line_detected"]) and ir3 < thresholds["ir_line_detected"]:
            if ir1 > thresholds["ir_strong_line"]:
                return "sharp_right"
            else:
                return "slight_right_correction"
        
        # Check for line on right side (sensors 4, 5)
        elif (ir4 > thresholds["ir_line_detected"] or ir5 > thresholds["ir_line_detected"]) and ir3 < thresholds["ir_line_detected"]:
            if ir5 > thresholds["ir_strong_line"]:
                return "sharp_left"
            else:
                return "slight_left_correction"
        
        # Check for moderate line detection in center
        elif ir3 > thresholds["ir_line_detected"]:
            # Use sensor differences for fine adjustments
            left_bias = (ir1 + ir2) - (ir4 + ir5)
            
            if left_bias > 100:
                return "slight_right_correction"
            elif left_bias < -100:
                return "slight_left_correction"
            else:
                return "forward"
        
        # No clear line detected
        else:
            return "search_pattern"
    
    async def execute_action(self, action, sensor_data):
        """Execute robot action based on analysis"""
        action_mapping = self.test_data["action_mapping"]
        
        # Update robot state based on sensor data
        self.robot_state["obstacle_detected"] = sensor_data.get("proximity", 250) < 100
        self.robot_state["collision_detected"] = sensor_data.get("bump", 0) == 1
        
        if action in action_mapping:
            motor_cmd = action_mapping[action]
            left_speed = motor_cmd["left_motor"]
            right_speed = motor_cmd["right_motor"]
            
            # Update robot state
            self.robot_state["speed"]["left"] = left_speed
            self.robot_state["speed"]["right"] = right_speed
            self.robot_state["current_action"] = action
            
            # Simulate motor command
            if action in ["emergency_stop", "collision_detected"]:
                await self.motor_controller.emergency_stop()
            elif action == "reverse_from_obstacle":
                await self.motor_controller.move("backward", 50, 0.5)
            elif action.startswith("search"):
                direction = "left" if "left" in action else "right"
                await self.motor_controller.move(direction, 30, 0.3)
            elif action.startswith("obstacle_avoidance"):
                direction = "left" if "left" in action else "right"
                await self.motor_controller.move(direction, 60, 0.2)
            else:
                # Calculate movement based on motor speeds
                avg_speed = (abs(left_speed) + abs(right_speed)) / 2
                if left_speed == right_speed and left_speed > 0:
                    await self.motor_controller.move("forward", avg_speed, 0.1)
                elif left_speed > right_speed:
                    await self.motor_controller.move("left", avg_speed * 0.8, 0.1)
                elif right_speed > left_speed:
                    await self.motor_controller.move("right", avg_speed * 0.8, 0.1)
        
        # Log the action
        log_entry = {
            "timestamp": time.time() - self.scenario_start_time,
            "scenario": self.robot_state["scenario_name"],
            "sensor_data": sensor_data,
            "analyzed_action": action,
            "expected_action": sensor_data.get("action", "unknown"),
            "motor_speeds": {"left": self.robot_state["speed"]["left"], 
                           "right": self.robot_state["speed"]["right"]},
            "match": action == sensor_data.get("action", "unknown"),
            "obstacle_detected": self.robot_state["obstacle_detected"],
            "collision_detected": self.robot_state["collision_detected"]
        }
        
        self.simulation_log.append(log_entry)
    
    async def run_scenario(self, scenario_name, real_time=True):
        """Run a specific scenario"""
        logger.info(f"🚀 Starting scenario: {scenario_name}")
        
        self.load_scenario(scenario_name)
        scenario_duration = self.current_scenario["duration"]
        
        start_time = time.time()
        
        while (time.time() - start_time) < scenario_duration:
            # Get current sensor data from scenario
            current_sensor_data = self.get_current_sensor_data()
            
            # Analyze sensor data
            analyzed_action = self.analyze_sensor_data(current_sensor_data)
            
            # Execute the action
            await self.execute_action(analyzed_action, current_sensor_data)
            
            # Print real-time status with 5 IR sensors
            elapsed = time.time() - start_time
            expected_action = current_sensor_data.get("action", "unknown")
            match = "✅" if analyzed_action == expected_action else "❌"
            
            ir_display = f"IR1:{current_sensor_data['ir1']:3d} IR2:{current_sensor_data['ir2']:3d} IR3:{current_sensor_data['ir3']:3d} IR4:{current_sensor_data['ir4']:3d} IR5:{current_sensor_data['ir5']:3d}"
            other_sensors = f"B:{current_sensor_data['bump']} P:{current_sensor_data['proximity']:3d}"
            
            print(f"\\r[{elapsed:.1f}s] {ir_display} | {other_sensors} | "
                  f"Expected: {expected_action:20s} | Analyzed: {analyzed_action:20s} {match}", 
                  end="", flush=True)
            
            # Wait for next update
            if real_time:
                await asyncio.sleep(0.1)  # 10Hz update rate
            else:
                await asyncio.sleep(0.01)  # Fast simulation
        
        print(f"\\n🏁 Scenario '{scenario_name}' completed in {scenario_duration} seconds")
        
        # Print summary
        self.print_scenario_summary()
    
    def print_scenario_summary(self):
        """Print summary of the completed scenario"""
        if not self.simulation_log:
            return
        
        scenario_logs = [log for log in self.simulation_log 
                        if log["scenario"] == self.robot_state["scenario_name"]]
        
        total_steps = len(scenario_logs)
        correct_actions = sum(1 for log in scenario_logs if log["match"])
        accuracy = (correct_actions / total_steps * 100) if total_steps > 0 else 0
        
        # Count safety events
        obstacle_detections = sum(1 for log in scenario_logs if log["obstacle_detected"])
        collision_detections = sum(1 for log in scenario_logs if log["collision_detected"])
        
        print(f"\\n📊 Scenario Summary for '{self.robot_state['scenario_name']}':")
        print(f"   Total Steps: {total_steps}")
        print(f"   Correct Actions: {correct_actions}")
        print(f"   Accuracy: {accuracy:.1f}%")
        print(f"   Obstacle Detections: {obstacle_detections}")
        print(f"   Collision Detections: {collision_detections}")
        
        # Show action distribution
        actions = {}
        for log in scenario_logs:
            action = log["analyzed_action"]
            actions[action] = actions.get(action, 0) + 1
        
        print(f"   Action Distribution:")
        for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"     {action}: {count} times")


async def main():
    """Main simulation function"""
    print("🤖 5 IR Sensor + Bump + Proximity Test Simulation")
    print("=" * 60)
    print("Hardware Configuration:")
    print("• 5 IR Sensors (IR1-IR5) for line detection")
    print("• 1 Bump Sensor for collision detection")  
    print("• 1 Proximity Sensor for obstacle detection")
    print("=" * 60)
    
    simulator = FiveIRSensorSimulator()
    
    if not await simulator.initialize():
        print("❌ Failed to initialize simulator")
        return
    
    try:
        # List available scenarios
        scenarios = list(simulator.test_data["test_scenarios"].keys())
        print(f"\\n📋 Available test scenarios ({len(scenarios)}):")
        for i, scenario in enumerate(scenarios, 1):
            description = simulator.test_data["test_scenarios"][scenario]["description"]
            print(f"   {i}. {scenario}: {description}")
        
        print(f"\\n🎮 Choose an option:")
        print(f"   0. Run all scenarios")
        for i, scenario in enumerate(scenarios, 1):
            print(f"   {i}. Run '{scenario}' scenario")
        print(f"   q. Quit")
        
        choice = input("\\nEnter your choice: ").strip().lower()
        
        if choice == 'q':
            print("👋 Goodbye!")
            return
        elif choice == '0':
            # Run all scenarios
            for scenario in scenarios:
                await simulator.run_scenario(scenario, real_time=False)
                print("\\n" + "-"*60)
        else:
            try:
                scenario_idx = int(choice) - 1
                if 0 <= scenario_idx < len(scenarios):
                    scenario_name = scenarios[scenario_idx]
                    await simulator.run_scenario(scenario_name, real_time=True)
                else:
                    print("❌ Invalid choice")
                    return
            except ValueError:
                print("❌ Invalid choice")
                return
        
        # Save log
        save_log = input("\\n💾 Save simulation log? (y/n): ").strip().lower()
        if save_log == 'y':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"5ir_simulation_log_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump({
                    "simulation_metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "sensor_configuration": "5 IR + 1 Bump + 1 Proximity",
                        "test_data_file": simulator.test_data_file,
                        "total_steps": len(simulator.simulation_log)
                    },
                    "simulation_log": simulator.simulation_log
                }, f, indent=2)
            
            print(f"💾 Simulation log saved to {filename}")
    
    except KeyboardInterrupt:
        print("\\n\\n🛑 Simulation interrupted by user")
    
    finally:
        await simulator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())