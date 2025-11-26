#!/usr/bin/env python3
"""
Simple Robot Demo
Shows robot behavior with IR sensor data in an easy-to-understand format
"""

import json
import time
import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_robot_demo():
    """Show a simple demonstration of robot behavior"""
    
    # Load test data
    with open('ir_sensor_test_data.json', 'r') as f:
        test_data = json.load(f)
    
    clear_screen()
    print("🤖 MEDI-RUNNER ROBOT IR SENSOR DEMONSTRATION")
    print("=" * 60)
    print()
    print("This demo shows how the robot responds to different")
    print("IR sensor readings while following a line.")
    print()
    print("IR Sensor Layout:")
    print("   [LEFT]  [CENTER]  [RIGHT]")
    print("     📡      📡       📡")
    print("        \\     |      /")
    print("         \\    |     /")
    print("          \\   |    /")
    print("           \\  |   /")
    print("            \\ |  /")
    print("             \\| /")
    print("              🤖")
    print()
    print("Higher sensor values = stronger line detection")
    print("Lower sensor values = weaker/no line detection")
    print()
    
    input("Press Enter to start the demonstration...")
    
    # Demo different scenarios
    scenarios_to_demo = [
        ('straight_line', 3),  # Show first 3 steps
        ('left_turn', 4),      # Show first 4 steps  
        ('right_turn', 4),     # Show first 4 steps
        ('lost_line', 5)       # Show first 5 steps
    ]
    
    for scenario_name, steps_to_show in scenarios_to_demo:
        scenario = test_data['test_scenarios'][scenario_name]
        
        clear_screen()
        print(f"🎬 SCENARIO: {scenario_name.replace('_', ' ').upper()}")
        print("=" * 60)
        print(f"Description: {scenario['description']}")
        print()
        
        for i in range(min(steps_to_show, len(scenario['sensor_data']))):
            step = scenario['sensor_data'][i]
            
            print(f"⏱️  Time: {step['timestamp']:.1f}s")
            print()
            
            # Show sensor readings visually
            left_val = step['left']
            center_val = step['center'] 
            right_val = step['right']
            
            # Create visual bars
            max_val = 1000
            bar_length = 20
            
            left_bar = "█" * int((left_val / max_val) * bar_length)
            left_bar += "░" * (bar_length - len(left_bar))
            
            center_bar = "█" * int((center_val / max_val) * bar_length)
            center_bar += "░" * (bar_length - len(center_bar))
            
            right_bar = "█" * int((right_val / max_val) * bar_length)
            right_bar += "░" * (bar_length - len(right_bar))
            
            print("📊 Sensor Readings:")
            print(f"   LEFT:   [{left_bar}] {left_val:4d}")
            print(f"   CENTER: [{center_bar}] {center_val:4d}")
            print(f"   RIGHT:  [{right_bar}] {right_val:4d}")
            print()
            
            # Show what the robot should do
            action = step['action']
            action_desc = {
                'forward': '⬆️  Move straight forward',
                'slight_left_correction': '↖️  Turn slightly left',
                'slight_right_correction': '↗️  Turn slightly right',
                'sharp_left': '⬅️  Turn sharp left',
                'sharp_right': '➡️  Turn sharp right',
                'prepare_left_turn': '🔄 Preparing for left turn',
                'initiate_left_turn': '⤴️  Starting left turn',
                'executing_left_turn': '↺  Executing left turn',
                'deep_left_turn': '↺  Deep left turn',
                'completing_left_turn': '↻  Completing left turn',
                'prepare_right_turn': '🔄 Preparing for right turn',
                'initiate_right_turn': '⤵️  Starting right turn',
                'executing_right_turn': '↻  Executing right turn',
                'deep_right_turn': '↻  Deep right turn',
                'completing_right_turn': '↺  Completing right turn',
                'line_lost': '❓ Lost the line - searching',
                'stop': '🛑 Stop',
                'intersection_detected': '✖️  Intersection detected'
            }
            
            desc = action_desc.get(action, f"🤖 {action}")
            print(f"🎯 Robot Action: {desc}")
            
            # Show motor action if available
            if action in test_data['action_mapping']:
                motor_info = test_data['action_mapping'][action]
                left_motor = motor_info['left_motor']
                right_motor = motor_info['right_motor']
                
                print()
                print("🎛️  Motor Control:")
                
                if left_motor > 0:
                    left_arrow = "🟢" + "▶" * (left_motor // 20)
                elif left_motor < 0:
                    left_arrow = "🔴" + "◀" * (abs(left_motor) // 20)
                else:
                    left_arrow = "⏸️"
                
                if right_motor > 0:
                    right_arrow = "🟢" + "▶" * (right_motor // 20)
                elif right_motor < 0:
                    right_arrow = "🔴" + "◀" * (abs(right_motor) // 20)
                else:
                    right_arrow = "⏸️"
                
                print(f"   Left Motor:  {left_motor:4d}% {left_arrow}")
                print(f"   Right Motor: {right_motor:4d}% {right_arrow}")
            
            print()
            print("-" * 60)
            
            if i < steps_to_show - 1:
                input("Press Enter to see next step...")
        
        print()
        print(f"✅ End of {scenario_name.replace('_', ' ')} demonstration")
        print()
        input("Press Enter to continue to next scenario...")
    
    # Final summary
    clear_screen()
    print("🎓 DEMONSTRATION COMPLETE!")
    print("=" * 60)
    print()
    print("What you learned:")
    print()
    print("1. 📡 IR sensors detect the line strength")
    print("   • High values (800+) = strong line detection")
    print("   • Medium values (400-800) = moderate line")
    print("   • Low values (<400) = weak/no line")
    print()
    print("2. 🧠 Robot makes decisions based on sensor patterns:")
    print("   • Center high + sides low = go forward")
    print("   • Left high + center low = turn right toward center")
    print("   • Right high + center low = turn left toward center")
    print("   • All sensors low = line lost, search for it")
    print()
    print("3. 🎛️  Motors control robot movement:")
    print("   • Equal speeds = straight movement")
    print("   • Different speeds = turning")
    print("   • Negative speeds = reverse movement")
    print()
    print("Next Steps:")
    print("• Run 'python ir_sensor_simulation.py' for detailed testing")
    print("• Run 'python visual_simulation.py' for visual representation")
    print("• Run 'python comprehensive_test.py' for full analysis")
    print()
    print("🤖 Ready to test with real hardware!")

if __name__ == "__main__":
    try:
        show_robot_demo()
    except FileNotFoundError:
        print("❌ Error: ir_sensor_test_data.json not found")
        print("Please make sure you're in the correct directory")
    except KeyboardInterrupt:
        print("\\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")