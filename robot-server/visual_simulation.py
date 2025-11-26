#!/usr/bin/env python3
"""
IR Sensor Visual Simulator
Creates a visual representation of robot movement based on IR sensor data
"""

import json
import time
import os
import sys
from datetime import datetime

class IRSensorVisualizer:
    """Visual representation of IR sensor simulation"""
    
    def __init__(self, test_data_file="ir_sensor_test_data.json"):
        self.test_data_file = test_data_file
        self.test_data = None
        
        # Load test data
        with open(test_data_file, 'r') as f:
            self.test_data = json.load(f)
        
        # Robot visualization parameters
        self.robot_width = 7
        self.path_width = 40
        self.display_height = 10
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def create_sensor_bar(self, value, max_value=1000, bar_length=20):
        """Create a visual bar representation of sensor value"""
        filled = int((value / max_value) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        return f"[{bar}] {value:4d}"
    
    def get_robot_position(self, left_val, center_val, right_val):
        """Calculate robot position based on sensor values"""
        # Normalize sensor values
        total = left_val + center_val + right_val
        if total == 0:
            return self.path_width // 2
        
        # Weighted position calculation
        left_weight = left_val / total
        center_weight = center_val / total  
        right_weight = right_val / total
        
        # Position from 0 (far left) to path_width (far right)
        position = (left_weight * 0 + center_weight * (self.path_width // 2) + 
                   right_weight * self.path_width)
        
        return int(position)
    
    def visualize_scenario_step(self, scenario_data, step_index):
        """Visualize a single step of the scenario"""
        if step_index >= len(scenario_data["sensor_data"]):
            return False
        
        step = scenario_data["sensor_data"][step_index]
        
        # Clear screen and show header
        self.clear_screen()
        print("🤖 IR Sensor Visual Simulation")
        print("=" * 60)
        print(f"Scenario: {scenario_data['description']}")
        print(f"Time: {step['timestamp']:.1f}s | Action: {step['action']}")
        print("-" * 60)
        
        # Show sensor readings
        print("\\n📊 Sensor Readings:")
        print(f"Left:   {self.create_sensor_bar(step['left'])}")
        print(f"Center: {self.create_sensor_bar(step['center'])}")
        print(f"Right:  {self.create_sensor_bar(step['right'])}")
        
        # Show visual path and robot
        print("\\n🛣️  Path Visualization:")
        
        # Create the path representation
        robot_pos = self.get_robot_position(step['left'], step['center'], step['right'])
        
        # Top border
        print("  " + "█" * (self.path_width + 2))
        
        # Path with robot
        for i in range(self.display_height):
            line = "  █"
            
            for j in range(self.path_width):
                if i == self.display_height // 2:  # Robot row
                    if abs(j - robot_pos) < self.robot_width // 2:
                        line += "🤖"[0] if j == robot_pos else "▓"
                    else:
                        # Show line if center sensor is high
                        if step['center'] > 400 and abs(j - self.path_width // 2) < 2:
                            line += "█"
                        else:
                            line += " "
                else:
                    # Show line path
                    if abs(j - self.path_width // 2) < 2:
                        if step['center'] > 400:
                            line += "█"
                        elif step['left'] > 400 and j < self.path_width // 3:
                            line += "█"  
                        elif step['right'] > 400 and j > 2 * self.path_width // 3:
                            line += "█"
                        else:
                            line += "░"
                    else:
                        line += " "
            
            line += "█"
            print(line)
        
        # Bottom border
        print("  " + "█" * (self.path_width + 2))
        
        # Show action and motor speeds
        action_mapping = self.test_data.get("action_mapping", {})
        if step['action'] in action_mapping:
            motor_info = action_mapping[step['action']]
            print(f"\\n🎛️  Motor Control:")
            print(f"   Left Motor:  {motor_info['left_motor']:4d}% {'█' * (abs(motor_info['left_motor']) // 10)}")
            print(f"   Right Motor: {motor_info['right_motor']:4d}% {'█' * (abs(motor_info['right_motor']) // 10)}")
            print(f"   Description: {motor_info['description']}")
        
        print("\\n⏯️  Press Enter to continue, 'q' to quit...")
        return True
    
    def run_scenario_visualization(self, scenario_name):
        """Run visualization for a specific scenario"""
        if scenario_name not in self.test_data["test_scenarios"]:
            print(f"❌ Scenario '{scenario_name}' not found")
            return
        
        scenario = self.test_data["test_scenarios"][scenario_name]
        
        print(f"🎬 Starting visualization: {scenario_name}")
        print(f"📝 {scenario['description']}")
        input("Press Enter to start...")
        
        for i in range(len(scenario["sensor_data"])):
            if not self.visualize_scenario_step(scenario, i):
                break
            
            # Wait for user input
            user_input = input().strip().lower()
            if user_input == 'q':
                print("👋 Visualization stopped")
                break
            elif user_input == 'a':  # Auto mode
                print("🔄 Running in auto mode...")
                time.sleep(1)
                while i < len(scenario["sensor_data"]) - 1:
                    i += 1
                    if not self.visualize_scenario_step(scenario, i):
                        break
                    time.sleep(0.8)  # Auto advance every 0.8 seconds
                break
        
        print("\\n🏁 Scenario visualization completed!")
    
    def show_scenario_menu(self):
        """Show menu of available scenarios"""
        scenarios = list(self.test_data["test_scenarios"].keys())
        
        print("🎮 Available Scenarios:")
        print("-" * 40)
        
        for i, scenario_name in enumerate(scenarios, 1):
            description = self.test_data["test_scenarios"][scenario_name]["description"]
            print(f"{i:2d}. {scenario_name}")
            print(f"    {description}")
            print()
        
        print("Choose a scenario (1-{}) or 'q' to quit:".format(len(scenarios)))
        
        while True:
            choice = input("Enter choice: ").strip().lower()
            
            if choice == 'q':
                return None
            
            try:
                scenario_idx = int(choice) - 1
                if 0 <= scenario_idx < len(scenarios):
                    return scenarios[scenario_idx]
                else:
                    print(f"❌ Invalid choice. Please enter 1-{len(scenarios)} or 'q'")
            except ValueError:
                print("❌ Invalid input. Please enter a number or 'q'")


def main():
    """Main visualization function"""
    try:
        visualizer = IRSensorVisualizer()
        
        print("🎨 IR Sensor Visual Simulator")
        print("=" * 40)
        print("This tool provides a visual representation")
        print("of how the robot responds to IR sensor data.")
        print()
        
        while True:
            scenario_name = visualizer.show_scenario_menu()
            
            if scenario_name is None:
                print("👋 Goodbye!")
                break
            
            visualizer.run_scenario_visualization(scenario_name)
            
            print("\\n" + "=" * 40)
            continue_choice = input("Run another scenario? (y/n): ").strip().lower()
            if continue_choice != 'y':
                print("👋 Thanks for using IR Sensor Visual Simulator!")
                break
    
    except FileNotFoundError:
        print("❌ Test data file not found. Please ensure 'ir_sensor_test_data.json' exists.")
    except KeyboardInterrupt:
        print("\\n\\n👋 Simulation interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()