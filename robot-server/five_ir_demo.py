#!/usr/bin/env python3
"""
5 IR Sensor Visual Demonstration
Shows how 5 IR sensors + bump + proximity sensors work together
"""

import json
import time
import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def create_sensor_bar(value, max_value=1000, bar_length=15):
    """Create a visual bar representation of sensor value"""
    filled = int((value / max_value) * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    return f"[{bar}] {value:4d}"

def show_sensor_layout():
    """Show the 5 IR sensor layout"""
    print("🔬 5 IR SENSOR ARRAY LAYOUT")
    print("=" * 50)
    print()
    print("        IR1    IR2    IR3    IR4    IR5")
    print("         📡     📡     📡     📡     📡")
    print("       (Far   (Left) (Center)(Right)(Far")
    print("        Left)                        Right)")
    print("         |      |      |      |      |")
    print("          \\     |      |      |     /")
    print("           \\    |      |      |    /")
    print("            \\   |      |      |   /")
    print("             \\  |      |      |  /")
    print("              \\ |      |      | /")
    print("               \\|      |      |/")
    print("                \\      |      /")
    print("                 \\     |     /")
    print("                  \\    |    /")
    print("                   \\   |   /")
    print("                    \\  |  /")
    print("                     \\ | /")
    print("                      \\|/")
    print("                      🤖")
    print("                   ROBOT")
    print()
    print("🚧 BUMP SENSOR: Physical collision detection")
    print("📏 PROXIMITY: Distance measurement (2-400cm)")
    print()
    input("Press Enter to continue...")

def demonstrate_sensor_scenario(scenario_name, scenario_data, steps_to_show=5):
    """Demonstrate a specific scenario with visual feedback"""
    
    clear_screen()
    print(f"🎬 SCENARIO DEMO: {scenario_name.replace('_', ' ').upper()}")
    print("=" * 70)
    print(f"Description: {scenario_data['description']}")
    print()
    
    for i in range(min(steps_to_show, len(scenario_data['sensor_data']))):
        step = scenario_data['sensor_data'][i]
        
        print(f"⏱️  Time: {step['timestamp']:.1f}s")
        print()
        
        # Show 5 IR sensor readings
        ir_sensors = ['ir1', 'ir2', 'ir3', 'ir4', 'ir5']
        ir_labels = ['Far Left', 'Left', 'Center', 'Right', 'Far Right']
        
        print("📊 IR Sensor Readings:")
        for j, (sensor, label) in enumerate(zip(ir_sensors, ir_labels)):
            value = step[sensor]
            bar = create_sensor_bar(value)
            status = "🟢 STRONG" if value > 600 else "🟡 MEDIUM" if value > 400 else "🔴 WEAK"
            print(f"   {label:10} ({sensor.upper()}): {bar} {status}")
        
        print()
        
        # Show other sensors
        bump_status = "🚨 COLLISION!" if step['bump'] == 1 else "✅ Clear"
        proximity_status = "🚨 OBSTACLE!" if step['proximity'] < 50 else "⚠️ Close" if step['proximity'] < 100 else "✅ Clear"
        
        print("🛡️  Safety Sensors:")
        print(f"   Bump Sensor:      {bump_status}")
        print(f"   Proximity Sensor: [{create_sensor_bar(400-step['proximity'], 400, 10)}] {step['proximity']}cm {proximity_status}")
        print()
        
        # Visualize sensor pattern
        print("🎯 Sensor Pattern Visualization:")
        
        # Create visual representation
        sensor_chars = []
        for sensor in ir_sensors:
            value = step[sensor]
            if value > 800:
                sensor_chars.append("██")
            elif value > 600:
                sensor_chars.append("▓▓")
            elif value > 400:
                sensor_chars.append("░░")
            else:
                sensor_chars.append("  ")
        
        print(f"   Line Pattern: [{sensor_chars[0]}][{sensor_chars[1]}][{sensor_chars[2]}][{sensor_chars[3]}][{sensor_chars[4]}]")
        print(f"   Sensor Names:  IR1   IR2   IR3   IR4   IR5")
        print()
        
        # Show expected action
        action = step['action']
        action_icons = {
            'forward': '⬆️  Move Forward',
            'slight_left_correction': '↖️  Slight Left',
            'slight_right_correction': '↗️  Slight Right',
            'sharp_left': '⬅️  Sharp Left',
            'sharp_right': '➡️  Sharp Right',
            'emergency_stop': '🛑 EMERGENCY STOP',
            'collision_detected': '💥 COLLISION!',
            'obstacle_detected': '🚧 Obstacle Detected',
            'line_lost': '❓ Line Lost',
            'intersection_detected': '✖️  Intersection',
            'wide_line_forward': '⬆️  Wide Line Forward',
            'wide_line_slight_left': '↖️  Wide Line Left',
            'wide_line_slight_right': '↗️  Wide Line Right'
        }
        
        action_desc = action_icons.get(action, f"🤖 {action}")
        print(f"🎯 Robot Action: {action_desc}")
        
        # Calculate and show line position estimate
        ir_values = [step[sensor] for sensor in ir_sensors]
        if sum(ir_values) > 0:
            # Weighted average position (-2 to +2, where 0 is center)
            weighted_pos = sum(val * (i - 2) for i, val in enumerate(ir_values)) / sum(ir_values)
            
            position_bar = ""
            for pos in range(-20, 21):  # -2.0 to +2.0 in 0.1 increments
                if abs(pos/10 - weighted_pos) < 0.2:
                    position_bar += "🤖"
                elif abs(pos/10) < 0.1:  # Center marker
                    position_bar += "|"
                else:
                    position_bar += "·"
            
            print(f"📍 Line Position: {position_bar}")
            print(f"    Position Value: {weighted_pos:.2f} (negative=left, positive=right)")
        
        print()
        print("-" * 70)
        
        if i < steps_to_show - 1:
            input("Press Enter to see next step...")

def show_sensor_comparison():
    """Show comparison between different sensor configurations"""
    clear_screen()
    print("📊 SENSOR CONFIGURATION COMPARISON")
    print("=" * 60)
    print()
    
    print("🔄 3-Sensor vs 5-Sensor Configuration:")
    print()
    
    print("3-Sensor Array (Basic):")
    print("   [LEFT] [CENTER] [RIGHT]")
    print("     📡      📡      📡")
    print("   ✅ Simple logic")
    print("   ❌ Limited precision")
    print("   ❌ Poor curve handling")
    print()
    
    print("5-Sensor Array (Advanced):")
    print("   [IR1] [IR2] [IR3] [IR4] [IR5]")
    print("    📡    📡    📡    📡    📡")
    print("   ✅ High precision")
    print("   ✅ Better curve handling") 
    print("   ✅ Wide line detection")
    print("   ✅ Smoother corrections")
    print()
    
    print("Additional Sensors:")
    print("   🚧 Bump Sensor:")
    print("      • Physical collision detection")
    print("      • Emergency stop capability")
    print("      • Prevents damage")
    print()
    print("   📏 Proximity Sensor:")
    print("      • Distance measurement")
    print("      • Obstacle avoidance")
    print("      • Predictive collision prevention")
    print()
    
    input("Press Enter to continue...")

def main():
    """Main demonstration function"""
    try:
        # Load test data
        with open('ir_sensor_5_test_data.json', 'r') as f:
            test_data = json.load(f)
        
        clear_screen()
        print("🤖 5 IR SENSOR + SAFETY SENSORS DEMONSTRATION")
        print("=" * 60)
        print()
        print("This demonstration shows how your robot's sensor")
        print("configuration works with:")
        print("• 5 IR Sensors for precise line following")
        print("• 1 Bump Sensor for collision detection") 
        print("• 1 Proximity Sensor for obstacle avoidance")
        print()
        
        input("Press Enter to start the demonstration...")
        
        # Show sensor layout
        show_sensor_layout()
        
        # Show sensor comparison
        show_sensor_comparison()
        
        # Demo key scenarios
        key_scenarios = [
            ('straight_line', 4),
            ('left_turn', 4), 
            ('obstacle_detection', 5),
            ('bump_collision', 4),
            ('wide_line_detection', 4)
        ]
        
        for scenario_name, steps in key_scenarios:
            if scenario_name in test_data['test_scenarios']:
                scenario = test_data['test_scenarios'][scenario_name]
                demonstrate_sensor_scenario(scenario_name, scenario, steps)
                
                print()
                print(f"✅ End of {scenario_name.replace('_', ' ')} demonstration")
                print()
                continue_demo = input("Continue to next scenario? (y/n): ").strip().lower()
                if continue_demo != 'y':
                    break
        
        # Final summary
        clear_screen()
        print("🎓 DEMONSTRATION COMPLETE!")
        print("=" * 60)
        print()
        print("🔑 Key Learnings:")
        print()
        print("1. 📡 5 IR Sensors provide:")
        print("   • Precise line position detection")
        print("   • Smooth steering corrections") 
        print("   • Better handling of curves and intersections")
        print("   • Wide line detection capabilities")
        print()
        print("2. 🛡️  Safety Sensors ensure:")
        print("   • Collision prevention (proximity)")
        print("   • Impact detection (bump)")
        print("   • Emergency stop capabilities")
        print("   • Obstacle avoidance")
        print()
        print("3. 🧠 Smart Algorithm Features:")
        print("   • Weighted position calculation")
        print("   • Multi-sensor decision making")
        print("   • Priority-based safety responses")
        print("   • Context-aware navigation")
        print()
        print("🚀 Your robot is ready for:")
        print("• Hospital corridor navigation")
        print("• Medication delivery missions")
        print("• Safe autonomous operation")
        print("• Complex path following")
        print()
        print("Next Steps:")
        print("• Run 'python five_ir_simulation.py' for testing")
        print("• Calibrate sensor thresholds with real hardware")
        print("• Test in actual hospital environment")
        
    except FileNotFoundError:
        print("❌ Error: ir_sensor_5_test_data.json not found")
        print("Please make sure you're in the correct directory")
    except KeyboardInterrupt:
        print("\\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()