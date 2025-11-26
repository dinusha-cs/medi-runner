#!/usr/bin/env python3
"""
Working 5 IR Sensor Robot Simulation - Simplified Version
"""

import asyncio
import time
from typing import Dict, Any

# Import robot modules
from robot.sensor_controller import SensorController
from robot.motor_controller import MotorController
from robot.navigation_controller import NavigationController

class WorkingFiveIRSimulator:
    """Working 5 IR Sensor Simulator"""
    
    def __init__(self):
        self.sensor_controller = SensorController()
        self.motor_controller = MotorController()
        self.navigation_controller = NavigationController()
    
    async def analyze_sensors(self, ir1, ir2, ir3, ir4, ir5, bump, proximity):
        """Analyze sensor data and determine action"""
        
        # Safety first
        if bump == 1:
            return "COLLISION_DETECTED"
        
        if proximity < 30:
            return "EMERGENCY_STOP"
        
        if proximity < 60:
            return "OBSTACLE_VERY_CLOSE"
        
        # Line following logic - center sensor is primary
        if ir3 > 700:  # Strong center line detection
            # Check for corrections needed
            left_strength = (ir1 + ir2) / 2
            right_strength = (ir4 + ir5) / 2
            
            if left_strength > right_strength + 50:
                return "SLIGHT_LEFT_CORRECTION"
            elif right_strength > left_strength + 50:
                return "SLIGHT_RIGHT_CORRECTION"
            else:
                return "FORWARD"
        
        # Turn detection
        if ir1 > 400 or ir2 > 400:  # Left turn
            return "LEFT_TURN"
        
        if ir4 > 400 or ir5 > 400:  # Right turn
            return "RIGHT_TURN"
        
        # Obstacle detection
        max_ir = max(ir1, ir2, ir3, ir4, ir5)
        if max_ir > 600:
            return "OBSTACLE_DETECTED"
        
        return "FORWARD"
    
    async def execute_action(self, action):
        """Execute the determined action"""
        
        if action == "COLLISION_DETECTED" or action == "EMERGENCY_STOP":
            await self.motor_controller.emergency_stop()
        elif action == "OBSTACLE_VERY_CLOSE":
            await self.motor_controller.move("backward", speed=50, duration=0.1)
        elif action == "LEFT_TURN" or action == "SLIGHT_LEFT_CORRECTION":
            await self.motor_controller.move("left", speed=60, duration=0.1)
        elif action == "RIGHT_TURN" or action == "SLIGHT_RIGHT_CORRECTION":
            await self.motor_controller.move("right", speed=60, duration=0.1)
        elif action == "OBSTACLE_DETECTED":
            await self.motor_controller.move("forward", speed=30, duration=0.1)
        else:  # FORWARD
            await self.motor_controller.move("forward", speed=100, duration=0.1)
    
    async def run_test(self):
        """Run a comprehensive test simulation"""
        
        print("🤖 5 IR Sensor Robot Simulation Test")
        print("=" * 50)
        
        # Initialize controllers
        print("🔧 Initializing controllers...")
        await self.sensor_controller.initialize()
        await self.motor_controller.initialize()
        await self.navigation_controller.initialize()
        
        # Test scenarios with sensor readings
        test_cases = [
            # Straight line following
            {"name": "Straight Line", "ir1": 150, "ir2": 200, "ir3": 800, "ir4": 200, "ir5": 150, "bump": 0, "proximity": 250},
            {"name": "Left Correction", "ir1": 130, "ir2": 180, "ir3": 820, "ir4": 220, "ir5": 160, "bump": 0, "proximity": 240},
            {"name": "Right Correction", "ir1": 160, "ir2": 210, "ir3": 810, "ir4": 190, "ir5": 140, "bump": 0, "proximity": 260},
            
            # Turn scenarios
            {"name": "Left Turn", "ir1": 450, "ir2": 500, "ir3": 600, "ir4": 100, "ir5": 50, "bump": 0, "proximity": 230},
            {"name": "Right Turn", "ir1": 50, "ir2": 100, "ir3": 600, "ir4": 500, "ir5": 450, "bump": 0, "proximity": 230},
            
            # Obstacle scenarios
            {"name": "Obstacle Ahead", "ir1": 150, "ir2": 200, "ir3": 650, "ir4": 200, "ir5": 150, "bump": 0, "proximity": 80},
            {"name": "Very Close Obstacle", "ir1": 150, "ir2": 200, "ir3": 700, "ir4": 200, "ir5": 150, "bump": 0, "proximity": 40},
            
            # Safety scenarios
            {"name": "Collision", "ir1": 150, "ir2": 200, "ir3": 800, "ir4": 200, "ir5": 150, "bump": 1, "proximity": 20},
            {"name": "Emergency", "ir1": 150, "ir2": 200, "ir3": 800, "ir4": 200, "ir5": 150, "bump": 0, "proximity": 15},
        ]
        
        total_tests = len(test_cases)
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n📍 Test {i}/{total_tests}: {test['name']}")
            print(f"   Sensors: IR1:{test['ir1']} IR2:{test['ir2']} IR3:{test['ir3']} IR4:{test['ir4']} IR5:{test['ir5']}")
            print(f"   Safety: Bump:{test['bump']} Proximity:{test['proximity']}cm")
            
            # Analyze sensors
            action = await self.analyze_sensors(
                test['ir1'], test['ir2'], test['ir3'], test['ir4'], test['ir5'], 
                test['bump'], test['proximity']
            )
            
            print(f"   → Action: {action}")
            
            # Execute action
            await self.execute_action(action)
            
            # Small delay for demonstration
            await asyncio.sleep(0.3)
        
        print(f"\n✅ Completed {total_tests} test scenarios")
        
        # Real-time demonstration
        print(f"\n🔄 Running 10-second real-time simulation...")
        
        start_time = time.time()
        step = 0
        
        while time.time() - start_time < 10:
            # Simulate varying sensor readings (straight line with minor variations)
            base_time = time.time() - start_time
            
            # Generate realistic sensor readings
            ir1 = 150 + int(10 * (0.5 - (step % 20) / 40))
            ir2 = 200 + int(15 * (0.5 - (step % 15) / 30))
            ir3 = 820 + int(20 * (0.5 - (step % 10) / 20))
            ir4 = 200 + int(15 * (0.5 - (step % 12) / 24))
            ir5 = 150 + int(10 * (0.5 - (step % 18) / 36))
            
            bump = 0
            proximity = 250 + int(30 * (0.5 - (step % 8) / 16))
            
            # Analyze and execute
            action = await self.analyze_sensors(ir1, ir2, ir3, ir4, ir5, bump, proximity)
            await self.execute_action(action)
            
            # Display real-time data
            print(f"\r[{base_time:.1f}s] IR1:{ir1:3d} IR2:{ir2:3d} IR3:{ir3:3d} IR4:{ir4:3d} IR5:{ir5:3d} | B:{bump} P:{proximity:3d} | {action:20s}", end="", flush=True)
            
            step += 1
            await asyncio.sleep(0.1)
        
        print(f"\n\n🏁 Real-time simulation completed ({step} steps)")

async def main():
    """Main function"""
    
    simulator = WorkingFiveIRSimulator()
    
    try:
        await simulator.run_test()
    
    except KeyboardInterrupt:
        print("\n⚠️ Simulation interrupted by user")
    except Exception as e:
        print(f"\n❌ Simulation error: {e}")
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        await simulator.sensor_controller.cleanup()
        await simulator.motor_controller.cleanup()
        await simulator.navigation_controller.cleanup()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())