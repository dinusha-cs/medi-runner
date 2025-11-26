#!/usr/bin/env python3
"""
Quick Test Script for Optimized 5 IR Sensor Simulation
"""

import asyncio
import json
import time
from pathlib import Path

# Import the optimized simulator
from optimized_five_ir_simulation import OptimizedFiveIRSensorSimulator

async def main():
    """Run quick test"""
    
    print("🤖 Quick Test: Optimized 5 IR Sensor Robot Simulation")
    print("="*60)
    
    # Load test data
    test_file = Path("ir_sensor_5_test_data.json")
    if not test_file.exists():
        print(f"❌ Test data file not found: {test_file}")
        return
    
    try:
        with open(test_file, 'r') as f:
            test_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading test data: {e}")
        return
    
    # Create simulator
    simulator = OptimizedFiveIRSensorSimulator()
    
    try:
        # Get first scenario (straight_line)
        scenarios = test_data.get('test_scenarios', [])
        if not scenarios:
            print("❌ No scenarios found in test data")
            return
        
        # Run the straight line scenario
        print(f"🚀 Testing scenario: {scenarios[0]['name']}")
        result = await simulator.run_scenario(scenarios[0])
        
        # Generate report
        simulator.generate_summary_report([result])
        
        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = f"quick_test_log_{timestamp}.json"
        
        log_data = {
            'timestamp': timestamp,
            'scenario_tested': scenarios[0]['name'],
            'result': result,
            'sensor_config': simulator.sensor_config
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"\n📁 Test log saved to: {log_file}")
    
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        await simulator.sensor_controller.cleanup()
        await simulator.motor_controller.cleanup()
        await simulator.navigation_controller.cleanup()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())