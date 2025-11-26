"""
Simple WebSocket Test Client
Test communication with robot server and control system.
"""

import asyncio
import json
import websockets
import time
import sys


async def test_robot_connection():
    """
    Test WebSocket connection to robot server.
    """
    robot_uri = "ws://localhost:8765"
    
    try:
        print(f"🤖 Connecting to robot at {robot_uri}...")
        
        async with websockets.connect(robot_uri) as websocket:
            print("✅ Connected to robot server!")
            
            # Listen for welcome message
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 Welcome: {welcome_data}")
            
            # Test commands
            test_commands = [
                {
                    'type': 'command',
                    'data': {
                        'action': 'move',
                        'direction': 'forward',
                        'speed': 50,
                        'duration': 2
                    },
                    'id': f'test_cmd_{int(time.time())}'
                },
                {
                    'type': 'command',
                    'data': {
                        'action': 'move',
                        'direction': 'right',
                        'speed': 40,
                        'duration': 1
                    },
                    'id': f'test_cmd_{int(time.time())}_2'
                },
                {
                    'type': 'command',
                    'data': {
                        'action': 'stop'
                    },
                    'id': f'test_cmd_{int(time.time())}_3'
                }
            ]
            
            # Create task to listen for messages
            async def listen_for_messages():
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        print(f"📥 Received: {data['type']}")
                        if data.get('type') == 'status':
                            print(f"   🤖 Position: ({data['data']['motor'].get('position', {}).get('x', 0):.1f}, {data['data']['motor'].get('position', {}).get('y', 0):.1f})")
                            print(f"   🔋 Battery: {data['data']['sensors'].get('battery_level', 0)}%")
                        elif data.get('type') == 'ack':
                            print(f"   ✅ Command acknowledged: {data.get('message_id')}")
                    except websockets.exceptions.ConnectionClosed:
                        print("🔌 Connection closed")
                        break
                    except Exception as e:
                        print(f"❌ Error receiving message: {e}")
            
            # Start listening task
            listen_task = asyncio.create_task(listen_for_messages())
            
            # Send test commands
            for i, cmd in enumerate(test_commands):
                print(f"\n📤 Sending command {i+1}: {cmd['data']['action']}")
                await websocket.send(json.dumps(cmd))
                await asyncio.sleep(3)  # Wait between commands
            
            print("\n⏳ Waiting for more status updates...")
            await asyncio.sleep(10)
            
            # Cancel listening task
            listen_task.cancel()
            
    except ConnectionRefusedError:
        print("❌ Could not connect to robot server. Is it running?")
        print("   Start with: python robot-server/main.py")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_control_backend():
    """
    Test WebSocket connection to control backend.
    """
    backend_uri = "ws://localhost:3001"
    
    try:
        print(f"🎮 Connecting to control backend at {backend_uri}...")
        
        async with websockets.connect(backend_uri) as websocket:
            print("✅ Connected to control backend!")
            
            # Send robot registration
            robot_data = {
                'type': 'robot_update',
                'data': {
                    'id': 'robot-sim-001',
                    'name': 'MediBot Simulator',
                    'status': 'connected',
                    'position': {'x': 5.2, 'y': 3.1, 'rotation': 45},
                    'battery': {
                        'level': 85,
                        'voltage': 12.4,
                        'charging': False
                    },
                    'sensors': {
                        'lidar': {'status': 'active', 'value': 'scanning'},
                        'camera': {'status': 'active', 'value': 'streaming'},
                        'ultrasonic': {'status': 'active', 'value': 25.6, 'unit': 'cm'},
                        'imu': {'status': 'active', 'value': {'acceleration': {'x': 0.1, 'y': 0.2, 'z': 9.8}}},
                        'gps': {'status': 'active', 'value': {'latitude': 59.3293, 'longitude': 18.0686}}
                    },
                    'actuators': {
                        'wheels': [
                            {'id': 'left', 'speed': 0, 'direction': 'stop'},
                            {'id': 'right', 'speed': 0, 'direction': 'stop'}
                        ],
                        'gripper': {'position': 50, 'force': 0, 'hasObject': False, 'status': 'idle'}
                    },
                    'mission': None,
                    'lastUpdate': time.time()
                }
            }
            
            await websocket.send(json.dumps(robot_data))
            print("📤 Sent robot registration")
            
            # Listen for commands
            async def listen_for_commands():
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        print(f"📥 Command received: {data}")
                        
                        # Send acknowledgment
                        ack = {
                            'type': 'command',
                            'data': {
                                'id': data.get('id'),
                                'acknowledged': True,
                                'completed': True,
                                'error': None
                            }
                        }
                        await websocket.send(json.dumps(ack))
                        
                    except websockets.exceptions.ConnectionClosed:
                        print("🔌 Connection to backend closed")
                        break
                    except Exception as e:
                        print(f"❌ Error: {e}")
            
            # Start listening
            listen_task = asyncio.create_task(listen_for_commands())
            
            # Send periodic status updates
            for i in range(10):
                await asyncio.sleep(2)
                
                # Update robot position
                robot_data['data']['position']['x'] += 0.5
                robot_data['data']['battery']['level'] -= 1
                robot_data['data']['lastUpdate'] = time.time()
                
                await websocket.send(json.dumps(robot_data))
                print(f"📊 Status update {i+1} sent")
            
            listen_task.cancel()
            
    except ConnectionRefusedError:
        print("❌ Could not connect to control backend. Is it running?")
        print("   Start with: npm run dev (in controller-backend)")
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """
    Main test function.
    """
    print("🧪 Medi Runner Robot Communication Test")
    print("=====================================")
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        test_type = 'robot'
    
    if test_type == 'robot':
        await test_robot_connection()
    elif test_type == 'backend':
        await test_control_backend()
    elif test_type == 'both':
        print("🔄 Testing robot connection...")
        await test_robot_connection()
        print("\n" + "="*50)
        print("🔄 Testing backend connection...")
        await test_control_backend()
    else:
        print("Usage: python test_robot.py [robot|backend|both]")
        print("  robot  - Test robot server connection")
        print("  backend - Test control backend connection")
        print("  both   - Test both connections")


if __name__ == "__main__":
    asyncio.run(main())