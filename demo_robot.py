#!/usr/bin/env python3
"""
Quick Robot Simulation Demo
Shows the robot components working in simulation mode
"""

import asyncio
import sys
import os
from pathlib import Path

# Add robot modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'robot-server'))

from robot.motor_controller import MotorController
from robot.sensor_controller import SensorController
from robot.navigation_controller import NavigationController

async def demo_motors():
    """Demo motor controller simulation"""
    print("🔧 Motor Controller Demo")
    print("=" * 25)
    
    motor = MotorController(simulation_mode=True)
    await motor.initialize()
    
    print("Moving forward for 2 seconds...")
    result = await motor.move("forward", 60, 2)
    print(f"✅ Result: {result}")
    
    print("Turning right for 1 second...")
    result = await motor.move("right", 50, 1)
    print(f"✅ Result: {result}")
    
    print("Stopping robot...")
    result = await motor.stop()
    print(f"✅ Result: {result}")
    
    status = await motor.get_status()
    print(f"📊 Final Status: {status}")
    
    await motor.cleanup()
    print()

async def demo_sensors():
    """Demo sensor controller simulation"""
    print("🔬 Sensor Controller Demo")
    print("=" * 25)
    
    sensor = SensorController(simulation_mode=True)
    await sensor.initialize()
    
    print("Reading all sensors...")
    all_data = await sensor.get_all_sensor_data()
    print(f"📊 All Sensors: {all_data}")
    
    print("Reading individual sensors...")
    distance = await sensor.get_ultrasonic_distance()
    print(f"📏 Distance: {distance} cm")
    
    line = await sensor.get_line_sensor()
    print(f"📏 Line Sensors: {line}")
    
    battery = await sensor.get_battery_status()
    print(f"🔋 Battery: {battery}")
    
    await sensor.cleanup()
    print()

async def demo_navigation():
    """Demo navigation controller simulation"""
    print("🗺️ Navigation Controller Demo")
    print("=" * 30)
    
    nav = NavigationController(simulation_mode=True)
    await nav.initialize()
    
    print("Getting current position...")
    pos = await nav.get_current_position()
    print(f"📍 Current Position: {pos}")
    
    print("Navigating to Room 101...")
    target = {"x": 100, "y": 50, "angle": 45}
    result = await nav.navigate_to(target)
    print(f"🎯 Navigation Result: {result}")
    
    print("Final position...")
    final_pos = await nav.get_current_position()
    print(f"📍 Final Position: {final_pos}")
    
    status = await nav.get_status()
    print(f"📊 Navigation Status: {status}")
    
    await nav.cleanup()
    print()

async def demo_full_integration():
    """Demo complete robot integration"""
    print("🤖 Complete Robot Integration Demo")
    print("=" * 35)
    
    # Initialize all controllers
    motor = MotorController(simulation_mode=True)
    sensor = SensorController(simulation_mode=True)
    nav = NavigationController(simulation_mode=True)
    
    await motor.initialize()
    await sensor.initialize()
    await nav.initialize()
    
    print("🚀 All systems initialized!")
    
    # Simulate a delivery mission
    print("\n🎯 Mission: Medicine Delivery to Room 101")
    print("Step 1: Check sensors and position...")
    
    initial_pos = await nav.get_current_position()
    battery = await sensor.get_battery_status()
    distance = await sensor.get_ultrasonic_distance()
    
    print(f"   📍 Position: {initial_pos}")
    print(f"   🔋 Battery: {battery['percentage']}%")
    print(f"   📏 Clear path: {distance} cm")
    
    print("\nStep 2: Navigate to pharmacy...")
    pharmacy_target = {"x": 50, "y": 80, "room": "pharmacy"}
    nav_result = await nav.navigate_to(pharmacy_target)
    print(f"   ✅ Navigation: {nav_result['status']}")
    
    print("\nStep 3: Simulate medicine pickup...")
    await motor.move("forward", 30, 1)  # Approach pickup point
    await asyncio.sleep(1)  # Simulate pickup
    await motor.move("backward", 30, 1)  # Back away
    print("   📦 Medicine picked up!")
    
    print("\nStep 4: Navigate to Room 101...")
    room_target = {"x": 150, "y": 60, "room": "101"}
    nav_result = await nav.navigate_to(room_target)
    print(f"   ✅ Delivery navigation: {nav_result['status']}")
    
    print("\nStep 5: Medicine delivery...")
    await motor.move("forward", 25, 2)  # Approach delivery point
    await asyncio.sleep(1)  # Simulate delivery
    print("   🏥 Medicine delivered successfully!")
    
    print("\nStep 6: Return to base...")
    base_target = {"x": 0, "y": 0, "room": "base"}
    nav_result = await nav.navigate_to(base_target)
    print(f"   🏠 Return: {nav_result['status']}")
    
    # Final status
    final_pos = await nav.get_current_position()
    final_battery = await sensor.get_battery_status()
    motor_status = await motor.get_status()
    
    print(f"\n📊 Mission Complete!")
    print(f"   Final Position: {final_pos}")
    print(f"   Battery Remaining: {final_battery['percentage']}%")
    print(f"   Motor Status: {motor_status['motors']['is_moving']}")
    
    # Cleanup
    await motor.cleanup()
    await sensor.cleanup()
    await nav.cleanup()
    
    print("\n🎉 Robot simulation demo completed successfully!")

async def main():
    """Run all demonstrations"""
    print("🤖 Medi Runner Challenge 2025 - Robot Simulation Demo")
    print("=" * 55)
    print("This demo shows the robot controllers working in simulation mode")
    print("without requiring physical hardware or WebSocket connections.")
    print()
    
    try:
        await demo_motors()
        await demo_sensors()
        await demo_navigation()
        await demo_full_integration()
        
        print("✨ All demonstrations completed successfully!")
        print()
        print("🔧 What was demonstrated:")
        print("   ✅ Motor control with movement simulation")
        print("   ✅ Sensor readings with realistic data")
        print("   ✅ Navigation with path planning")
        print("   ✅ Complete mission execution flow")
        print("   ✅ Position tracking and status monitoring")
        print()
        print("🚀 Your robot simulation is ready for:")
        print("   • WebSocket integration testing")
        print("   • Frontend dashboard connection")
        print("   • Backend API integration")
        print("   • Mission planning and execution")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())