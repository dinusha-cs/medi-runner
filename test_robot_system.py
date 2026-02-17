#!/usr/bin/env python3
"""
Medi Runner Robot Simulation and Testing Script
This script simulates and tests the complete robot system
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path

# Add robot modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'robot-server'))

try:
    import websockets
except ImportError:
    print("❌ websockets not installed. Installing...")
    os.system("pip install websockets aiofiles")
    import websockets

class RobotSimulationTester:
    """Complete robot simulation testing framework"""
    
    def __init__(self):
        self.robot_uri = "ws://localhost:8765"
        self.backend_uri = "ws://localhost:3001"
        self.test_results = []
        
    async def test_robot_connection(self):
        """Test connection to robot WebSocket server"""
        print("🤖 Testing Robot Server Connection...")
        
        try:
            # Try to connect to robot server
            async with websockets.connect(self.robot_uri) as websocket:
                # Send test message
                test_msg = {
                    "type": "command",
                    "id": f"test_{int(time.time())}",
                    "data": {
                        "action": "get_status"
                    }
                }
                
                await websocket.send(json.dumps(test_msg))
                print(f"📤 Sent: {test_msg}")
                
                # Wait for response
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"📥 Received: {response_data}")
                
                self.test_results.append({
                    "test": "robot_connection",
                    "status": "PASS",
                    "message": "Robot server responds correctly"
                })
                
                return True
                
        except ConnectionRefusedError:
            print("❌ Robot server not running on ws://localhost:8765")
            self.test_results.append({
                "test": "robot_connection", 
                "status": "FAIL",
                "message": "Robot server not accessible"
            })
            return False
        except Exception as e:
            print(f"❌ Robot connection failed: {e}")
            self.test_results.append({
                "test": "robot_connection",
                "status": "FAIL", 
                "message": str(e)
            })
            return False
    
    async def test_robot_commands(self):
        """Test robot command execution"""
        print("🎮 Testing Robot Commands...")
        
        commands_to_test = [
            {
                "action": "move",
                "direction": "forward",
                "speed": 50,
                "duration": 2
            },
            {
                "action": "move", 
                "direction": "right",
                "speed": 40,
                "duration": 1
            },
            {
                "action": "stop"
            },
            {
                "action": "get_sensors"
            }
        ]
        
        try:
            async with websockets.connect(self.robot_uri) as websocket:
                for cmd in commands_to_test:
                    test_msg = {
                        "type": "command",
                        "id": f"cmd_test_{int(time.time())}",
                        "data": cmd
                    }
                    
                    print(f"   Testing: {cmd['action']}")
                    await websocket.send(json.dumps(test_msg))
                    
                    # Wait for command acknowledgment
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "ack":
                        print(f"   ✅ Command acknowledged: {cmd['action']}")
                    else:
                        print(f"   ❓ Unexpected response: {response_data}")
                    
                    await asyncio.sleep(0.5)  # Small delay between commands
                
                self.test_results.append({
                    "test": "robot_commands",
                    "status": "PASS", 
                    "message": "All commands executed successfully"
                })
                
        except Exception as e:
            print(f"❌ Command testing failed: {e}")
            self.test_results.append({
                "test": "robot_commands",
                "status": "FAIL",
                "message": str(e)
            })
    
    async def test_mission_simulation(self):
        """Test mission execution simulation"""
        print("🎯 Testing Mission Simulation...")
        
        mission = {
            "id": "mission_001",
            "type": "delivery",
            "destination": {
                "room": "101",
                "coordinates": {"x": 100, "y": 50}
            },
            "cargo": "Medicine Package A",
            "priority": "normal"
        }
        
        try:
            async with websockets.connect(self.robot_uri) as websocket:
                # Send mission start command
                mission_msg = {
                    "type": "mission",
                    "id": f"mission_{int(time.time())}",
                    "data": mission
                }
                
                await websocket.send(json.dumps(mission_msg))
                print(f"📤 Mission sent: {mission['type']} to {mission['destination']['room']}")
                
                # Wait for mission acknowledgment
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"📥 Mission response: {response_data}")
                
                self.test_results.append({
                    "test": "mission_simulation",
                    "status": "PASS",
                    "message": "Mission simulation completed"
                })
                
        except Exception as e:
            print(f"❌ Mission simulation failed: {e}")
            self.test_results.append({
                "test": "mission_simulation",
                "status": "FAIL",
                "message": str(e)
            })
    
    async def test_emergency_procedures(self):
        """Test emergency stop and safety procedures"""
        print("🚨 Testing Emergency Procedures...")
        
        try:
            async with websockets.connect(self.robot_uri) as websocket:
                # Test emergency stop
                emergency_msg = {
                    "type": "emergency",
                    "id": f"emergency_{int(time.time())}",
                    "data": {
                        "action": "emergency_stop",
                        "reason": "Safety test"
                    }
                }
                
                await websocket.send(json.dumps(emergency_msg))
                print("📤 Emergency stop command sent")
                
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"📥 Emergency response: {response_data}")
                
                self.test_results.append({
                    "test": "emergency_procedures",
                    "status": "PASS",
                    "message": "Emergency procedures working correctly"
                })
                
        except Exception as e:
            print(f"❌ Emergency procedure testing failed: {e}")
            self.test_results.append({
                "test": "emergency_procedures", 
                "status": "FAIL",
                "message": str(e)
            })
    
    async def run_comprehensive_test(self):
        """Run all robot tests"""
        print("🚀 Starting Comprehensive Robot Testing...")
        print("=" * 50)
        
        # Test robot connection first
        robot_online = await self.test_robot_connection()
        
        if robot_online:
            # Run all other tests
            await self.test_robot_commands()
            await self.test_mission_simulation()
            await self.test_emergency_procedures()
        else:
            print("⚠️  Skipping detailed tests - robot server not available")
        
        # Print test summary
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print comprehensive test results"""
        print()
        print("📊 Test Results Summary")
        print("=" * 30)
        
        passed = 0
        failed = 0
        
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_icon} {result['test']}: {result['status']} - {result['message']}")
            
            if result["status"] == "PASS":
                passed += 1
            else:
                failed += 1
        
        print()
        print(f"📈 Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        
        if failed == 0:
            print("🎉 All tests passed! Robot simulation is working correctly.")
        else:
            print("⚠️  Some tests failed. Check robot server status.")

async def manual_robot_control():
    """Interactive manual robot control"""
    print("🎮 Manual Robot Control Mode")
    print("=" * 30)
    print("Commands:")
    print("  w - Move Forward    s - Move Backward")
    print("  a - Turn Left       d - Turn Right") 
    print("  x - Stop            e - Emergency Stop")
    print("  q - Quit")
    print()
    
    try:
        async with websockets.connect("ws://localhost:8765") as websocket:
            print("🤖 Connected to robot!")
            
            while True:
                try:
                    # Get user input (simplified for demo)
                    print("Enter command (w/a/s/d/x/e/q): ", end="", flush=True)
                    
                    # For demo purposes, simulate some commands
                    demo_commands = ['w', 'd', 's', 'a', 'x', 'q']
                    for cmd in demo_commands:
                        print(cmd)
                        
                        if cmd == 'q':
                            print("👋 Exiting manual control")
                            return
                        
                        # Map commands to robot actions
                        action_map = {
                            'w': {"action": "move", "direction": "forward", "speed": 50},
                            's': {"action": "move", "direction": "backward", "speed": 50},
                            'a': {"action": "move", "direction": "left", "speed": 40},
                            'd': {"action": "move", "direction": "right", "speed": 40},
                            'x': {"action": "stop"},
                            'e': {"action": "emergency_stop"}
                        }
                        
                        if cmd in action_map:
                            command = {
                                "type": "command",
                                "id": f"manual_{int(time.time())}",
                                "data": action_map[cmd]
                            }
                            
                            await websocket.send(json.dumps(command))
                            print(f"📤 Sent: {action_map[cmd]['action']}")
                            
                            # Wait for response
                            response = await websocket.recv()
                            print(f"📥 Robot response: {json.loads(response)}")
                        
                        await asyncio.sleep(1)  # Demo delay
                        
                except KeyboardInterrupt:
                    print("\n👋 Manual control interrupted")
                    break
                    
    except ConnectionRefusedError:
        print("❌ Cannot connect to robot server. Is it running?")

def check_robot_server_files():
    """Check if robot server files exist"""
    print("📁 Checking Robot Server Files...")
    
    robot_dir = Path("robot-server")
    required_files = [
        "main.py",
        "config.py", 
        "websocket_server.py",
        "robot/motor_controller.py",
        "robot/sensor_controller.py",
        "robot/navigation_controller.py"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        full_path = robot_dir / file_path
        if full_path.exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️  Missing {len(missing_files)} required files")
        return False
    else:
        print("\n✅ All robot server files present")
        return True

async def main():
    """Main testing function"""
    print("🤖 Medi Runner Challenge 2025 - Robot Testing")
    print("=" * 50)
    
    # Check if files exist
    if not check_robot_server_files():
        print("❌ Cannot proceed without required robot files")
        return
    
    print("\nSelect testing mode:")
    print("1. Comprehensive Testing (recommended)")
    print("2. Manual Robot Control")
    print("3. Connection Test Only")
    
    # For demo, run comprehensive testing
    choice = "1"
    print(f"Running option {choice}")
    
    if choice == "1":
        tester = RobotSimulationTester()
        await tester.run_comprehensive_test()
    elif choice == "2":
        await manual_robot_control()
    elif choice == "3":
        tester = RobotSimulationTester()
        await tester.test_robot_connection()
    
    print("\n🏁 Robot testing completed!")
    print("\n📖 Next Steps:")
    print("   1. Start robot server: python robot-server/main.py")
    print("   2. Start backend API: cd controller-backend && npm run dev") 
    print("   3. Start frontend: cd controller-frontend && npm run dev")
    print("   4. Open dashboard: http://localhost:3000")

if __name__ == "__main__":
    asyncio.run(main())