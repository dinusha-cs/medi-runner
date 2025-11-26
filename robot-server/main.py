#!/usr/bin/env python3
"""
Medi Runner Robot Server
Main application entry point for the robot control system.
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

# Add current directory to path for local imports
sys.path.append(str(Path(__file__).parent))

try:
    from config import *
except ImportError:
    print("Error: config.py not found. Please copy config.example.py to config.py and configure it.")
    sys.exit(1)

# Import our actual robot controllers
from robot.motor_controller import MotorController
from robot.sensor_controller import SensorController
from robot.navigation_controller import NavigationController
from websocket_server import WebSocketServer

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING.get('LEVEL', 'INFO')),
    format=LOGGING.get('FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)

class RobotServer:
    """
    Main robot server class that coordinates all subsystems.
    """
    
    def __init__(self):
        self.logger = logging.getLogger('RobotServer')
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Initialize subsystems
        try:
            self.motor_controller = MotorController(simulation_mode=SIMULATION_MODE)
            self.sensor_controller = SensorController(simulation_mode=SIMULATION_MODE)
            self.navigation_controller = NavigationController(simulation_mode=SIMULATION_MODE)
            
            self.websocket_server = WebSocketServer(
                host=WS_HOST,
                port=WS_PORT,
                robot_instance=self
            )
            
            self.logger.info("🤖 Robot subsystems initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize robot subsystems: {e}")
            raise
    
    async def execute_command(self, command_data):
        """Execute robot command from WebSocket or API"""
        try:
            action = command_data.get('action', '')
            self.logger.info(f"📤 Executing command: {action}")
            
            if action == 'move':
                direction = command_data.get('direction', 'forward')
                speed = command_data.get('speed', 50)
                duration = command_data.get('duration', 0)
                
                result = await self.motor_controller.move(direction, speed, duration)
                return {"success": True, "result": result}
                
            elif action == 'stop':
                result = await self.motor_controller.stop()
                return {"success": True, "result": result}
                
            elif action == 'emergency_stop':
                result = await self.motor_controller.emergency_stop()
                return {"success": True, "result": "Emergency stop executed"}
                
            elif action == 'navigate_to':
                target = command_data.get('target', {})
                result = await self.navigation_controller.navigate_to(target)
                return {"success": True, "result": result}
                
            elif action == 'get_sensors':
                result = await self.sensor_controller.get_all_sensor_data()
                return {"success": True, "result": result}
                
            elif action == 'get_status':
                result = await self.get_status()
                return {"success": True, "result": result}
                
            elif action == 'set_pid_values':
                kp = command_data.get('kp')
                ki = command_data.get('ki')
                kd = command_data.get('kd')
                result = await self.motor_controller.set_pid_values(kp=kp, ki=ki, kd=kd)
                return {"success": True, "result": result}
                
            elif action == 'get_pid_values':
                result = await self.motor_controller.get_pid_values()
                return {"success": True, "result": result}
                
            elif action == 'reset_pid':
                result = await self.motor_controller.reset_pid()
                return {"success": True, "result": result}
                
            elif action == 'start_line_following':
                base_speed = command_data.get('base_speed', 50)
                result = await self.motor_controller.start_line_following(base_speed)
                return {"success": True, "result": result}
                
            elif action == 'stop_line_following':
                result = await self.motor_controller.stop_line_following()
                return {"success": True, "result": result}
                
            else:
                return {"success": False, "message": f"Unknown action: {action}"}
                
        except Exception as e:
            self.logger.error(f"❌ Command execution failed: {e}")
            return {"success": False, "message": str(e)}
    
    async def get_status(self):
        """Get comprehensive robot status"""
        try:
            motor_status = await self.motor_controller.get_status()
            sensor_data = await self.sensor_controller.get_all_sensor_data()
            navigation_status = await self.navigation_controller.get_status()
            
            return {
                "robot_id": SIMULATION.get('ROBOT_ID', 'robot-001'),
                "robot_name": SIMULATION.get('ROBOT_NAME', 'MediBot'),
                "timestamp": time.time(),
                "status": "online",
                "motor": motor_status,
                "sensors": sensor_data,
                "navigation": navigation_status,
                "simulation_mode": SIMULATION_MODE,
                "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0
            }
        except Exception as e:
            self.logger.error(f"❌ Error getting status: {e}")
            return {"status": "error", "message": str(e), "timestamp": time.time()}
    
    async def start(self):
        """
        Start the robot server and all subsystems.
        """
        try:
            self.logger.info("🚀 Starting Medi Runner Robot Server...")
            self.start_time = time.time()
            self.running = True
            
            # Initialize all subsystems
            await self.motor_controller.initialize()
            await self.sensor_controller.initialize()
            await self.navigation_controller.initialize()
            
            # Start WebSocket server
            await self.websocket_server.start_server()
            
            self.logger.info("✅ All subsystems started successfully")
            self.logger.info(f"🌐 WebSocket server running on ws://{WS_HOST}:{WS_PORT}")
            self.logger.info(f"🤖 Robot: {SIMULATION.get('ROBOT_NAME', 'MediBot')} (Simulation: {SIMULATION_MODE})")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            self.logger.info("🛑 Robot server stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error in robot server: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """
        Clean up resources and stop all subsystems.
        """
        self.logger.info("🧹 Cleaning up robot server...")
        self.running = False
        
        try:
            # Stop all subsystems
            if hasattr(self, 'motor_controller'):
                await self.motor_controller.cleanup()
            if hasattr(self, 'sensor_controller'):
                await self.sensor_controller.cleanup()
            if hasattr(self, 'navigation_controller'):
                await self.navigation_controller.cleanup()
            if hasattr(self, 'websocket_server'):
                await self.websocket_server.stop_server()
            
            self.logger.info("✅ Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"❌ Error during cleanup: {e}")
    
    def signal_handler(self, sig, frame):
        """
        Handle shutdown signals.
        """
        self.logger.info(f"📡 Received signal {sig}, shutting down...")
        self.shutdown_event.set()


async def main():
    """
    Main entry point.
    """
    # Setup logging
    logger = logging.getLogger('Main')
    
    try:
        # Create robot server instance
        robot_server = RobotServer()
        
        # Setup signal handlers
        def signal_handler(sig, frame):
            logger.info(f"📡 Received signal {sig}")
            robot_server.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run the server
        logger.info("🏁 Starting Medi Runner Robot Challenge 2025")
        await robot_server.start()
        
    except KeyboardInterrupt:
        logger.info("⌨️ Received keyboard interrupt")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("👋 Robot server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
