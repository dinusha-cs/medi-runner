import asyncio
import logging
from robot.motor_controller import MotorController
from robot.sensor_controller import SensorController
from robot.navigation_controller import NavigationController

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RobotSimulator:
    """Complete robot simulation for testing"""
    
    def __init__(self):
        self.motor = MotorController()
        self.sensor = SensorController()
        self.navigation = NavigationController()
        self.is_running = False
        
    async def start_simulation(self):
        """Start the robot simulation"""
        logger.info("🤖 Starting Robot Simulation...")
        
        # Initialize all controllers
        await self.motor.initialize()
        await self.sensor.initialize()
        await self.navigation.initialize()
        
        self.is_running = True
        logger.info("✅ Robot simulation started successfully!")
        
    async def stop_simulation(self):
        """Stop the robot simulation"""
        logger.info("🛑 Stopping Robot Simulation...")
        
        self.is_running = False
        
        # Cleanup all controllers
        await self.motor.cleanup()
        await self.sensor.cleanup()
        await self.navigation.cleanup()
        
        logger.info("✅ Robot simulation stopped")
        
    async def get_status(self):
        """Get comprehensive robot status"""
        if not self.is_running:
            return {"status": "offline", "message": "Robot simulation not running"}
            
        try:
            motor_status = await self.motor.get_status()
            sensor_data = await self.sensor.get_all_sensor_data()
            navigation_status = await self.navigation.get_status()
            
            return {
                "status": "online",
                "timestamp": asyncio.get_event_loop().time(),
                "motor": motor_status,
                "sensors": sensor_data,
                "navigation": navigation_status,
                "simulation_mode": True
            }
        except Exception as e:
            logger.error(f"❌ Error getting status: {e}")
            return {"status": "error", "message": str(e)}
    
    async def execute_command(self, command):
        """Execute robot command"""
        if not self.is_running:
            return {"success": False, "message": "Robot simulation not running"}
            
        try:
            action = command.get("action", "")
            
            if action == "move":
                direction = command.get("direction", "forward")
                speed = command.get("speed", 50)
                duration = command.get("duration", 0)
                
                result = await self.motor.move(direction, speed, duration)
                return {"success": True, "result": result}
                
            elif action == "stop":
                result = await self.motor.stop()
                return {"success": True, "result": result}
                
            elif action == "emergency_stop":
                result = await self.motor.emergency_stop()
                return {"success": True, "result": "Emergency stop executed"}
                
            elif action == "navigate_to":
                target = command.get("target", {})
                result = await self.navigation.navigate_to(target)
                return {"success": True, "result": result}
                
            elif action == "get_sensors":
                result = await self.sensor.get_all_sensor_data()
                return {"success": True, "result": result}
                
            else:
                return {"success": False, "message": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"❌ Command execution failed: {e}")
            return {"success": False, "message": str(e)}

# Simulation test functions
async def test_motor_simulation():
    """Test motor controller simulation"""
    print("🔧 Testing Motor Controller Simulation...")
    
    motor = MotorController()
    await motor.initialize()
    
    # Test movements
    print("   Testing forward movement...")
    await motor.move("forward", 50, 2)
    
    print("   Testing turn right...")
    await motor.move("right", 40, 1)
    
    print("   Testing stop...")
    await motor.stop()
    
    status = await motor.get_status()
    print(f"   Motor Status: {status}")
    
    await motor.cleanup()
    print("✅ Motor simulation test complete")

async def test_sensor_simulation():
    """Test sensor controller simulation"""
    print("🔬 Testing Sensor Controller Simulation...")
    
    sensor = SensorController()
    await sensor.initialize()
    
    # Test sensor readings
    ultrasonic = await sensor.get_ultrasonic_distance()
    print(f"   Ultrasonic Distance: {ultrasonic} cm")
    
    line = await sensor.get_line_sensor()
    print(f"   Line Sensor: {line}")
    
    imu = await sensor.get_imu_data()
    print(f"   IMU Data: {imu}")
    
    all_sensors = await sensor.get_all_sensor_data()
    print(f"   All Sensors: {all_sensors}")
    
    await sensor.cleanup()
    print("✅ Sensor simulation test complete")

async def test_navigation_simulation():
    """Test navigation controller simulation"""
    print("🗺️  Testing Navigation Controller Simulation...")
    
    nav = NavigationController()
    await nav.initialize()
    
    # Test navigation
    target = {"x": 100, "y": 50, "angle": 45}
    result = await nav.navigate_to(target)
    print(f"   Navigation result: {result}")
    
    position = await nav.get_current_position()
    print(f"   Current position: {position}")
    
    status = await nav.get_status()
    print(f"   Navigation status: {status}")
    
    await nav.cleanup()
    print("✅ Navigation simulation test complete")

async def test_full_robot_simulation():
    """Test complete robot simulation"""
    print("🤖 Testing Complete Robot Simulation...")
    
    robot = RobotSimulator()
    
    # Start simulation
    await robot.start_simulation()
    
    # Test commands
    print("   Testing movement command...")
    cmd_result = await robot.execute_command({
        "action": "move",
        "direction": "forward", 
        "speed": 60,
        "duration": 3
    })
    print(f"   Command result: {cmd_result}")
    
    # Get status
    print("   Getting robot status...")
    status = await robot.get_status()
    print(f"   Robot status: {status}")
    
    # Test navigation
    print("   Testing navigation command...")
    nav_result = await robot.execute_command({
        "action": "navigate_to",
        "target": {"x": 200, "y": 100, "angle": 90}
    })
    print(f"   Navigation result: {nav_result}")
    
    # Test emergency stop
    print("   Testing emergency stop...")
    stop_result = await robot.execute_command({"action": "emergency_stop"})
    print(f"   Emergency stop result: {stop_result}")
    
    # Stop simulation
    await robot.stop_simulation()
    print("✅ Full robot simulation test complete")

async def main():
    """Main simulation test runner"""
    print("🚀 Medi Runner Robot Simulation Tests")
    print("=====================================")
    
    try:
        # Test individual components
        await test_motor_simulation()
        print()
        
        await test_sensor_simulation()
        print()
        
        await test_navigation_simulation()
        print()
        
        # Test full integration
        await test_full_robot_simulation()
        print()
        
        print("🎉 All simulation tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Simulation test failed: {e}")
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())