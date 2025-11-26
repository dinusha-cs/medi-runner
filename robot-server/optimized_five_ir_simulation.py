#!/usr/bin/env python3
"""
Optimized 5 IR Sensor Robot Simulation with Improved Algorithm
Enhanced for better line following and obstacle detection accuracy
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Import robot modules
from robot.sensor_controller import SensorController
from robot.motor_controller import MotorController
from robot.navigation_controller import NavigationController

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OptimizedFiveIRSensorSimulator:
    """Enhanced 5 IR Sensor Simulator with improved algorithms"""
    
    def __init__(self):
        self.sensor_controller = SensorController()
        self.motor_controller = MotorController()
        self.navigation_controller = NavigationController()
        
        # Enhanced sensor configuration
        self.sensor_config = {
            'ir_thresholds': {
                'line_detected': 400,      # Higher threshold for better line detection
                'obstacle_close': 700,     # Medium proximity
                'obstacle_very_close': 600, # Very close obstacle
                'safe_distance': 900       # Safe operating distance
            },
            'bump_threshold': 1,           # Bump sensor trigger
            'proximity_thresholds': {
                'collision_imminent': 25,  # Immediate collision risk
                'very_close': 50,          # Very close obstacle
                'close': 100,              # Close obstacle
                'safe': 200                # Safe distance
            },
            'weighted_position': {
                'ir1_weight': -2.0,        # Far left
                'ir2_weight': -1.0,        # Left
                'ir3_weight': 0.0,         # Center
                'ir4_weight': 1.0,         # Right
                'ir5_weight': 2.0          # Far right
            }
        }
        
        # Action tracking
        self.action_counts = {}
        self.total_steps = 0
        self.correct_actions = 0
        
    async def analyze_sensor_data(self, data: Dict[str, Any]) -> str:
        """Enhanced sensor data analysis with improved algorithms"""
        
        # Extract sensor values
        ir1 = data.get('ir1', 0)
        ir2 = data.get('ir2', 0)
        ir3 = data.get('ir3', 0)
        ir4 = data.get('ir4', 0)
        ir5 = data.get('ir5', 0)
        bump = data.get('bump', 0)
        proximity = data.get('proximity', 999)
        
        # Safety checks first (highest priority)
        if bump == 1:
            return "collision_detected"
            
        if proximity <= self.sensor_config['proximity_thresholds']['collision_imminent']:
            return "emergency_stop"
            
        if proximity <= self.sensor_config['proximity_thresholds']['very_close']:
            return "reverse_from_obstacle"
            
        # Enhanced line detection algorithm
        line_threshold = self.sensor_config['ir_thresholds']['line_detected']
        
        # Count sensors detecting line
        line_sensors = []
        if ir1 >= line_threshold:
            line_sensors.append(('ir1', ir1, -2.0))
        if ir2 >= line_threshold:
            line_sensors.append(('ir2', ir2, -1.0))
        if ir3 >= line_threshold:
            line_sensors.append(('ir3', ir3, 0.0))
        if ir4 >= line_threshold:
            line_sensors.append(('ir4', ir4, 1.0))
        if ir5 >= line_threshold:
            line_sensors.append(('ir5', ir5, 2.0))
        
        # If multiple sensors detect line, calculate weighted position
        if len(line_sensors) >= 3:
            # Wide line detected - use weighted average for direction
            total_weight = 0
            total_intensity = 0
            
            for sensor_name, intensity, weight in line_sensors:
                # Normalize intensity (higher IR values = stronger line signal)
                normalized_intensity = min(intensity / 1000.0, 1.0)
                total_weight += weight * normalized_intensity
                total_intensity += normalized_intensity
            
            if total_intensity > 0:
                position = total_weight / total_intensity
                
                # Enhanced direction determination
                if position < -0.3:
                    return "wide_line_slight_left"
                elif position > 0.3:
                    return "wide_line_slight_right"
                else:
                    return "wide_line_forward"
            else:
                return "wide_line_forward"
                
        elif len(line_sensors) >= 1:
            # Standard line following
            center_sensors = [s for s in line_sensors if s[0] in ['ir2', 'ir3', 'ir4']]
            
            if center_sensors:
                # Calculate position based on center sensors
                total_weight = sum(s[2] * s[1] for s in center_sensors)
                total_intensity = sum(s[1] for s in center_sensors)
                
                if total_intensity > 0:
                    position = total_weight / total_intensity
                    
                    if position < -0.5:
                        return "turn_left"
                    elif position > 0.5:
                        return "turn_right"
                    else:
                        return "forward"
            
            # Edge sensors only
            if ir1 >= line_threshold and ir2 < line_threshold:
                return "sharp_left"
            if ir5 >= line_threshold and ir4 < line_threshold:
                return "sharp_right"
        
        # Obstacle detection (when no line is detected)
        obstacle_threshold = self.sensor_config['ir_thresholds']['obstacle_close']
        
        max_ir = max(ir1, ir2, ir3, ir4, ir5)
        if max_ir >= obstacle_threshold:
            if proximity <= self.sensor_config['proximity_thresholds']['close']:
                return "obstacle_very_close"
            else:
                return "obstacle_detected"
        
        # Enhanced safe distance check
        if proximity >= self.sensor_config['proximity_thresholds']['safe']:
            # Check if we're backing away from obstacle
            if any(ir >= 500 for ir in [ir1, ir2, ir3, ir4, ir5]):
                return "ready_to_continue"
            else:
                return "safe_distance"
        
        # Default forward movement
        return "forward"
    
    async def execute_action(self, action: str) -> None:
        """Execute the determined action"""
        
        # Track actions
        self.action_counts[action] = self.action_counts.get(action, 0) + 1
        
        try:
            if action in ["collision_detected", "emergency_stop"]:
                await self.motor_controller.emergency_stop()
            elif action == "reverse_from_obstacle":
                await self.motor_controller.move_backward(speed=50, duration=0.1)
            elif action in ["turn_left", "wide_line_slight_left"]:
                await self.navigation_controller.turn_left(duration=0.05)
            elif action in ["turn_right", "wide_line_slight_right"]:
                await self.navigation_controller.turn_right(duration=0.05)
            elif action == "sharp_left":
                await self.navigation_controller.turn_left(duration=0.1)
            elif action == "sharp_right":
                await self.navigation_controller.turn_right(duration=0.1)
            elif action == "obstacle_very_close":
                await self.motor_controller.stop()
            elif action == "obstacle_detected":
                await self.motor_controller.move_forward(speed=30, duration=0.05)
            elif action in ["backing_away", "reverse_from_obstacle"]:
                await self.motor_controller.move_backward(speed=40, duration=0.1)
            else:  # forward, wide_line_forward, safe_distance, ready_to_continue
                await self.motor_controller.move_forward(speed=100, duration=0.1)
                
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
    
    async def run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test scenario with enhanced tracking"""
        
        scenario_name = scenario['name']
        duration = scenario['duration']
        readings = scenario['sensor_readings']
        
        logger.info(f"🚀 Starting scenario: {scenario_name}")
        logger.info(f"📋 Loaded scenario: {scenario_name}")
        logger.info(f"📝 Description: {scenario['description']}")
        logger.info(f"⏱️ Duration: {duration} seconds")
        
        start_time = time.time()
        step = 0
        correct = 0
        scenario_action_counts = {}
        obstacle_detections = 0
        collision_detections = 0
        
        while time.time() - start_time < duration and step < len(readings):
            current_time = time.time() - start_time
            reading = readings[step % len(readings)]
            
            # Analyze sensor data
            analyzed_action = await self.analyze_sensor_data(reading)
            expected_action = reading.get('expected_action', 'unknown')
            
            # Count specific events
            if 'obstacle' in analyzed_action:
                obstacle_detections += 1
            if 'collision' in analyzed_action:
                collision_detections += 1
            
            # Track actions for this scenario
            scenario_action_counts[analyzed_action] = scenario_action_counts.get(analyzed_action, 0) + 1
            
            # Check accuracy
            is_correct = analyzed_action == expected_action
            if is_correct:
                correct += 1
            
            # Execute action
            await self.execute_action(analyzed_action)
            
            # Display progress
            status_icon = "✅" if is_correct else "❌"
            sensor_display = f"IR1:{reading['ir1']} IR2:{reading['ir2']} IR3:{reading['ir3']} IR4:{reading['ir4']} IR5:{reading['ir5']}"
            safety_display = f"B:{reading['bump']} P:{reading.get('proximity', 999):3d}"
            
            print(f"\r[{current_time:.1f}s] {sensor_display} | {safety_display} | Expected: {expected_action:20s} | Analyzed: {analyzed_action:20s} {status_icon}", end="", flush=True)
            
            step += 1
            await asyncio.sleep(0.01)  # Small delay for realistic timing
        
        print(f"\n🏁 Scenario '{scenario_name}' completed in {duration} seconds")
        
        # Calculate accuracy
        accuracy = (correct / step * 100) if step > 0 else 0
        
        # Display scenario summary
        print(f"\n📊 Scenario Summary for '{scenario_name}':")
        print(f"   Total Steps: {step}")
        print(f"   Correct Actions: {correct}")
        print(f"   Accuracy: {accuracy:.1f}%")
        print(f"   Obstacle Detections: {obstacle_detections}")
        print(f"   Collision Detections: {collision_detections}")
        print(f"   Action Distribution:")
        for action, count in sorted(scenario_action_counts.items()):
            print(f"     {action}: {count} times")
        
        return {
            'name': scenario_name,
            'steps': step,
            'correct': correct,
            'accuracy': accuracy,
            'obstacle_detections': obstacle_detections,
            'collision_detections': collision_detections,
            'actions': scenario_action_counts
        }
    
    async def run_all_scenarios(self, test_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all scenarios from test data"""
        
        results = []
        scenarios = test_data.get('test_scenarios', [])
        
        print(f"🎯 Running {len(scenarios)} test scenarios with optimized algorithms\n")
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"{'='*60}")
            print(f"📍 Scenario {i}/{len(scenarios)}: {scenario['name']}")
            print(f"{'='*60}")
            
            result = await self.run_scenario(scenario)
            results.append(result)
            
            print(f"\n{'-'*60}")
            
            # Short break between scenarios
            if i < len(scenarios):
                print(f"\n⏳ Preparing next scenario...")
                await asyncio.sleep(1)
        
        return results
    
    def generate_summary_report(self, results: List[Dict[str, Any]]) -> None:
        """Generate comprehensive summary report"""
        
        print(f"\n{'='*80}")
        print(f"📋 OPTIMIZED 5 IR SENSOR SIMULATION SUMMARY REPORT")
        print(f"{'='*80}")
        
        total_steps = sum(r['steps'] for r in results)
        total_correct = sum(r['correct'] for r in results)
        overall_accuracy = (total_correct / total_steps * 100) if total_steps > 0 else 0
        
        print(f"\n🎯 Overall Performance:")
        print(f"   Total Scenarios: {len(results)}")
        print(f"   Total Steps: {total_steps}")
        print(f"   Total Correct: {total_correct}")
        print(f"   Overall Accuracy: {overall_accuracy:.1f}%")
        
        print(f"\n📊 Scenario Breakdown:")
        for result in results:
            print(f"   {result['name']:25s} - {result['accuracy']:5.1f}% ({result['correct']}/{result['steps']})")
        
        # Best and worst performing scenarios
        if results:
            best = max(results, key=lambda x: x['accuracy'])
            worst = min(results, key=lambda x: x['accuracy'])
            
            print(f"\n🏆 Best Performance: {best['name']} ({best['accuracy']:.1f}%)")
            print(f"📉 Needs Improvement: {worst['name']} ({worst['accuracy']:.1f}%)")
        
        print(f"\n{'='*80}")

async def main():
    """Main simulation runner"""
    
    # Load test data
    test_file = Path("ir_sensor_5_test_data.json")
    if not test_file.exists():
        print(f"❌ Test data file not found: {test_file}")
        print("   Please run the 5 IR sensor demo first to generate test data")
        return
    
    try:
        with open(test_file, 'r') as f:
            test_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading test data: {e}")
        return
    
    # Create and run simulator
    simulator = OptimizedFiveIRSensorSimulator()
    
    try:
        # Run quick test or all scenarios
        print("🤖 Optimized 5 IR Sensor Robot Simulation")
        print("==========================================")
        print("Select mode:")
        print("0: Quick test (straight_line scenario)")
        print("1: All scenarios")
        
        try:
            choice = input("Enter your choice (0/1): ").strip()
        except EOFError:
            choice = "0"  # Default to quick test
        
        if choice == "0":
            # Quick test with first scenario
            scenarios = test_data.get('test_scenarios', [])
            if scenarios:
                print(f"🚀 Running quick test with scenario: {scenarios[0]['name']}")
                result = await simulator.run_scenario(scenarios[0])
                results = [result]  # Make it a list for consistency
                simulator.generate_summary_report([result])
            else:
                print("❌ No scenarios found in test data")
                return
        else:
            # Run all scenarios
            results = await simulator.run_all_scenarios(test_data)
            simulator.generate_summary_report(results)
        
        # Save log option
        try:
            save_log = input("\n💾 Save simulation log? (y/n): ").strip().lower()
        except EOFError:
            save_log = "y"  # Auto save in batch mode
            
        if save_log == 'y':
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            log_file = f"optimized_simulation_log_{timestamp}.json"
            
            # Use results from the simulation
            final_results = results if 'results' in locals() else []
            total_steps = sum(r['steps'] for r in final_results) if final_results else 0
            total_correct = sum(r['correct'] for r in final_results) if final_results else 0
            overall_accuracy = (total_correct / total_steps * 100) if total_steps > 0 else 0
            
            log_data = {
                'timestamp': timestamp,
                'sensor_config': simulator.sensor_config,
                'results': final_results,
                'summary': {
                    'total_steps': total_steps,
                    'total_correct': total_correct,
                    'overall_accuracy': overall_accuracy
                }
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            print(f"📁 Simulation log saved to: {log_file}")
    
    except KeyboardInterrupt:
        print("\n⚠️ Simulation interrupted by user")
    except Exception as e:
        print(f"\n❌ Simulation error: {e}")
    finally:
        # Cleanup
        print("\n🧹 Cleaning up Optimized 5 IR Sensor Simulator...")
        await simulator.sensor_controller.cleanup()
        await simulator.motor_controller.cleanup()
        await simulator.navigation_controller.cleanup()
        logger.info("✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())