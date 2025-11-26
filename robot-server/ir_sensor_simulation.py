#!/usr/bin/env python3
"""
Enhanced IR Sensor Simulation Test Script
Tests robot behavior with predefined IR sensor data scenarios
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

class IRSensorTestSimulator:
    """Enhanced robot simulator for testing IR sensor scenarios"""
    
    def __init__(self, test_data_file="ir_sensor_test_data.json"):
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
            "scenario_name": None
        }
        
        self.simulation_log = []
        
    async def initialize(self):
        """Initialize the simulation"""
        logger.info("🤖 Initializing IR Sensor Test Simulator...")
        
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
        
        logger.info("✅ IR Sensor Test Simulator initialized successfully!")
        return True
    
    async def cleanup(self):
        """Cleanup simulation resources"""
        logger.info("🧹 Cleaning up IR Sensor Test Simulator...")
        
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
        """Get IR sensor data for current time in scenario"""
        if not self.current_scenario:
            return {"left": 200, "center": 200, "right": 200}
        
        elapsed_time = time.time() - self.scenario_start_time
        sensor_data_points = self.current_scenario["sensor_data"]
        
        # Find the appropriate data point based on elapsed time
        for i, data_point in enumerate(sensor_data_points):
            if elapsed_time <= data_point["timestamp"]:
                return {
                    "left": data_point["left"],
                    "center": data_point["center"], 
                    "right": data_point["right"],
                    "action": data_point["action"],
                    "timestamp": data_point["timestamp"]
                }
        
        # If we've passed all data points, return the last one
        if sensor_data_points:
            last_point = sensor_data_points[-1]
            return {
                "left": last_point["left"],
                "center": last_point["center"],
                "right": last_point["right"],
                "action": last_point["action"],
                "timestamp": elapsed_time
            }
        
        return {"left": 200, "center": 200, "right": 200, "action": "stopped"}
    
    def analyze_sensor_data(self, sensor_data):
        """Analyze IR sensor data and determine robot action"""
        left = sensor_data["left"]
        center = sensor_data["center"]
        right = sensor_data["right"]
        
        thresholds = self.test_data["sensor_thresholds"]
        
        # Calculate sensor differences for more precise detection
        left_center_diff = left - center
        right_center_diff = right - center
        left_right_diff = abs(left - right)
        
        # Check for line loss first
        if all(val < thresholds["lost_line_threshold"] for val in [left, center, right]):
            return "line_lost"
        
        # Check for intersection (all sensors high)
        if (left > thresholds["intersection_threshold"] and 
            center > thresholds["intersection_threshold"] and 
            right > thresholds["intersection_threshold"]):
            return "intersection_detected"
        
        # Check for strong line in center
        if center > thresholds["strong_line"]:
            # Line is strong in center, check for corrections
            if left > thresholds["line_detected"] and right < thresholds["line_detected"]:
                # Left sensor sees line, need to turn right to center
                return "slight_right_correction" 
            elif right > thresholds["line_detected"] and left < thresholds["line_detected"]:
                # Right sensor sees line, need to turn left to center
                return "slight_left_correction"
            elif left_right_diff > 50:  # Significant difference between left and right
                if left > right:
                    return "slight_right_correction"
                else:
                    return "slight_left_correction"
            else:
                return "forward"
        
        # Check for moderate line in center
        elif center > thresholds["line_detected"]:
            if left_center_diff > 100:  # Left much higher than center
                return "slight_right_correction"
            elif right_center_diff > 100:  # Right much higher than center
                return "slight_left_correction"
            elif left_right_diff > 100:
                if left > right:
                    return "slight_right_correction"
                else:
                    return "slight_left_correction"
            else:
                return "forward"
        
        # Line mostly on left side
        elif left > thresholds["line_detected"] and center < thresholds["line_detected"]:
            if left > thresholds["strong_line"]:
                return "sharp_right"
            else:
                return "slight_right_correction"
        
        # Line mostly on right side  
        elif right > thresholds["line_detected"] and center < thresholds["line_detected"]:
            if right > thresholds["strong_line"]:
                return "sharp_left"
            else:
                return "slight_left_correction"
        
        # No clear line detected
        else:
            return "search_pattern"
    
    async def execute_action(self, action, sensor_data):
        """Execute robot action based on analysis"""
        action_mapping = self.test_data["action_mapping"]
        
        if action in action_mapping:
            motor_cmd = action_mapping[action]
            left_speed = motor_cmd["left_motor"]
            right_speed = motor_cmd["right_motor"]
            
            # Update robot state
            self.robot_state["speed"]["left"] = left_speed
            self.robot_state["speed"]["right"] = right_speed
            self.robot_state["current_action"] = action
            
            # Simulate motor command
            if action == "stop":
                await self.motor_controller.stop()
            elif action.startswith("search"):
                # Implement search pattern
                direction = "left" if "left" in action else "right"
                await self.motor_controller.move(direction, 30, 0.5)
            else:
                # Calculate movement direction and speed
                avg_speed = (abs(left_speed) + abs(right_speed)) / 2
                if left_speed == right_speed and left_speed > 0:
                    await self.motor_controller.move("forward", avg_speed, 0.1)
                elif left_speed > right_speed:
                    await self.motor_controller.move("left", avg_speed, 0.1)
                elif right_speed > left_speed:
                    await self.motor_controller.move("right", avg_speed, 0.1)
        
        # Log the action
        log_entry = {
            "timestamp": time.time() - self.scenario_start_time,
            "scenario": self.robot_state["scenario_name"],
            "sensor_data": sensor_data,
            "analyzed_action": action,
            "expected_action": sensor_data.get("action", "unknown"),
            "motor_speeds": {"left": self.robot_state["speed"]["left"], 
                           "right": self.robot_state["speed"]["right"]},
            "match": action == sensor_data.get("action", "unknown")
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
            
            # Print real-time status
            elapsed = time.time() - start_time
            expected_action = current_sensor_data.get("action", "unknown")
            match = "✅" if analyzed_action == expected_action else "❌"
            
            print(f"\\r[{elapsed:.1f}s] IR: L{current_sensor_data['left']:3d} "
                  f"C{current_sensor_data['center']:3d} R{current_sensor_data['right']:3d} | "
                  f"Expected: {expected_action:20s} | Analyzed: {analyzed_action:20s} {match}", 
                  end="", flush=True)
            
            # Wait for next update (or run at full speed if real_time=False)
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
        
        print(f"\\n📊 Scenario Summary for '{self.robot_state['scenario_name']}':")
        print(f"   Total Steps: {total_steps}")
        print(f"   Correct Actions: {correct_actions}")
        print(f"   Accuracy: {accuracy:.1f}%")
        
        # Show action distribution
        actions = {}
        for log in scenario_logs:
            action = log["analyzed_action"]
            actions[action] = actions.get(action, 0) + 1
        
        print(f"   Action Distribution:")
        for action, count in sorted(actions.items()):
            print(f"     {action}: {count} times")
    
    async def run_all_scenarios(self, real_time=True):
        """Run all available test scenarios"""
        scenarios = list(self.test_data["test_scenarios"].keys())
        
        logger.info(f"🎯 Running all {len(scenarios)} scenarios...")
        
        for i, scenario_name in enumerate(scenarios):
            print(f"\\n{'='*60}")
            print(f"Scenario {i+1}/{len(scenarios)}: {scenario_name}")
            print(f"{'='*60}")
            
            await self.run_scenario(scenario_name, real_time)
            
            if i < len(scenarios) - 1:  # Not the last scenario
                print(f"\\n⏸️ Pausing 2 seconds before next scenario...")
                await asyncio.sleep(2)
        
        print(f"\\n🎉 All scenarios completed!")
        self.print_overall_summary()
    
    def print_overall_summary(self):
        """Print overall simulation summary"""
        if not self.simulation_log:
            return
        
        total_steps = len(self.simulation_log)
        correct_actions = sum(1 for log in self.simulation_log if log["match"])
        overall_accuracy = (correct_actions / total_steps * 100) if total_steps > 0 else 0
        
        print(f"\\n📈 Overall Simulation Summary:")
        print(f"   Total Steps Across All Scenarios: {total_steps}")
        print(f"   Correct Actions: {correct_actions}")
        print(f"   Overall Accuracy: {overall_accuracy:.1f}%")
        
        # Accuracy per scenario
        scenarios = {}
        for log in self.simulation_log:
            scenario = log["scenario"]
            if scenario not in scenarios:
                scenarios[scenario] = {"total": 0, "correct": 0}
            scenarios[scenario]["total"] += 1
            if log["match"]:
                scenarios[scenario]["correct"] += 1
        
        print(f"\\n   Per-Scenario Accuracy:")
        for scenario, stats in scenarios.items():
            accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"     {scenario}: {accuracy:.1f}% ({stats['correct']}/{stats['total']})")
    
    def save_simulation_log(self, filename=None):
        """Save simulation log to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"simulation_log_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "simulation_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "test_data_file": self.test_data_file,
                    "total_steps": len(self.simulation_log)
                },
                "simulation_log": self.simulation_log
            }, f, indent=2)
        
        logger.info(f"💾 Simulation log saved to {filename}")


async def main():
    """Main simulation function"""
    print("🤖 IR Sensor Test Simulation")
    print("=" * 50)
    
    simulator = IRSensorTestSimulator()
    
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
            await simulator.run_all_scenarios(real_time=True)
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
            simulator.save_simulation_log()
    
    except KeyboardInterrupt:
        print("\\n\\n🛑 Simulation interrupted by user")
    
    finally:
        await simulator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())