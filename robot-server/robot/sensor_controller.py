"""
Sensor Controller for Medi Runner Robot
Handles ultrasonic, line following, IMU, and other sensors
"""

import asyncio
import logging
import time
import random
import math

logger = logging.getLogger(__name__)

class SensorController:
    """Sensor controller with simulation capabilities"""
    
    def __init__(self, simulation_mode=True):
        self.simulation_mode = simulation_mode
        self.is_initialized = False
        
        # Sensor data cache
        self.sensor_data = {
            "ultrasonic": {"distance": 0, "timestamp": 0},
            "line_sensor": {"left": 0, "center": 0, "right": 0, "timestamp": 0},
            "imu": {"accel": {"x": 0, "y": 0, "z": 0}, "gyro": {"x": 0, "y": 0, "z": 0}, "timestamp": 0},
            "temperature": {"value": 0, "timestamp": 0},
            "battery": {"voltage": 0, "percentage": 0, "timestamp": 0}
        }
        
        # Simulation parameters
        self.environment = {
            "obstacles": [
                {"x": 150, "y": 50, "radius": 20},  # Simulated obstacles
                {"x": -100, "y": 75, "radius": 15}
            ],
            "line_path": {"width": 50, "offset": 0},  # Line following path
            "room_temp": 22.0,
            "battery_drain_rate": 0.1  # % per minute
        }
        
        logger.info(f"🔬 Sensor Controller initialized (simulation: {simulation_mode})")
    
    async def initialize(self):
        """Initialize all sensors"""
        logger.info("🔬 Initializing sensor systems...")
        
        if self.simulation_mode:
            await asyncio.sleep(0.3)  # Simulate initialization
            logger.info("✅ Sensor simulation initialized")
            
            # Initialize simulated sensor data
            await self._initialize_simulated_sensors()
        else:
            # Real sensor initialization
            logger.info("✅ Physical sensors initialized")
        
        self.is_initialized = True
        return True
    
    async def cleanup(self):
        """Cleanup sensor controller"""
        logger.info("🧹 Sensor controller cleanup complete")
        self.is_initialized = False
    
    async def get_ultrasonic_distance(self):
        """Get distance from ultrasonic sensor"""
        if not self.is_initialized:
            raise Exception("Sensor controller not initialized")
        
        if self.simulation_mode:
            distance = await self._simulate_ultrasonic()
        else:
            distance = await self._read_physical_ultrasonic()
        
        self.sensor_data["ultrasonic"] = {
            "distance": distance,
            "timestamp": time.time()
        }
        
        return distance
    
    async def get_line_sensor(self):
        """Get line sensor readings (left, center, right)"""
        if not self.is_initialized:
            raise Exception("Sensor controller not initialized")
        
        if self.simulation_mode:
            readings = await self._simulate_line_sensor()
        else:
            readings = await self._read_physical_line_sensor()
        
        self.sensor_data["line_sensor"] = {
            **readings,
            "timestamp": time.time()
        }
        
        return readings
    
    async def get_imu_data(self):
        """Get IMU (accelerometer + gyroscope) data"""
        if not self.is_initialized:
            raise Exception("Sensor controller not initialized")
        
        if self.simulation_mode:
            imu_data = await self._simulate_imu()
        else:
            imu_data = await self._read_physical_imu()
        
        self.sensor_data["imu"] = {
            **imu_data,
            "timestamp": time.time()
        }
        
        return imu_data
    
    async def get_temperature(self):
        """Get temperature sensor reading"""
        if not self.is_initialized:
            raise Exception("Sensor controller not initialized")
        
        if self.simulation_mode:
            temp = await self._simulate_temperature()
        else:
            temp = await self._read_physical_temperature()
        
        self.sensor_data["temperature"] = {
            "value": temp,
            "timestamp": time.time()
        }
        
        return temp
    
    async def get_battery_status(self):
        """Get battery voltage and percentage"""
        if not self.is_initialized:
            raise Exception("Sensor controller not initialized")
        
        if self.simulation_mode:
            battery = await self._simulate_battery()
        else:
            battery = await self._read_physical_battery()
        
        self.sensor_data["battery"] = {
            **battery,
            "timestamp": time.time()
        }
        
        return battery
    
    async def get_all_sensor_data(self):
        """Get readings from all sensors"""
        logger.debug("📊 Reading all sensors...")
        
        try:
            # Read all sensors concurrently
            tasks = [
                self.get_ultrasonic_distance(),
                self.get_line_sensor(),
                self.get_imu_data(),
                self.get_temperature(),
                self.get_battery_status()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Package results
            all_data = {
                "ultrasonic": {"distance": results[0] if not isinstance(results[0], Exception) else None},
                "line_sensor": results[1] if not isinstance(results[1], Exception) else None,
                "imu": results[2] if not isinstance(results[2], Exception) else None,
                "temperature": {"celsius": results[3] if not isinstance(results[3], Exception) else None},
                "battery": results[4] if not isinstance(results[4], Exception) else None,
                "timestamp": time.time()
            }
            
            return all_data
            
        except Exception as e:
            logger.error(f"❌ Error reading sensors: {e}")
            return {"error": str(e), "timestamp": time.time()}
    
    async def _initialize_simulated_sensors(self):
        """Initialize simulated sensor baseline values"""
        # Set initial simulated values
        self.sensor_data["battery"]["percentage"] = 85.0
        self.sensor_data["temperature"]["value"] = 22.5
        logger.debug("🔧 Simulated sensors baseline set")
    
    async def _simulate_ultrasonic(self):
        """Simulate ultrasonic distance sensor"""
        # Base distance with some variation
        base_distance = 200  # cm
        
        # Add some realistic noise
        noise = random.uniform(-10, 10)
        distance = max(5, base_distance + noise)  # Min 5cm
        
        # Simulate obstacles occasionally
        if random.random() < 0.1:  # 10% chance of obstacle
            distance = random.uniform(10, 50)
        
        await asyncio.sleep(0.05)  # Simulate sensor delay
        return round(distance, 1)
    
    async def _simulate_line_sensor(self):
        """Simulate line following sensor array"""
        # Simulate line detection with some wandering
        line_offset = random.uniform(-20, 20)  # Line position offset
        
        # Calculate sensor activation based on line position
        sensors = {
            "left": max(0, min(1023, 512 + line_offset * 10)),
            "center": max(0, min(1023, 512 - abs(line_offset) * 5)),
            "right": max(0, min(1023, 512 - line_offset * 10))
        }
        
        # Add some noise
        for sensor in sensors:
            sensors[sensor] += random.randint(-50, 50)
            sensors[sensor] = max(0, min(1023, sensors[sensor]))
        
        await asyncio.sleep(0.02)  # Simulate sensor delay
        return sensors
    
    async def _simulate_imu(self):
        """Simulate IMU (accelerometer and gyroscope)"""
        # Simulate slight movement and gravity
        accel = {
            "x": random.uniform(-0.5, 0.5),  # Lateral acceleration
            "y": random.uniform(-0.5, 0.5),  # Forward acceleration  
            "z": 9.81 + random.uniform(-0.2, 0.2)  # Gravity + noise
        }
        
        gyro = {
            "x": random.uniform(-2, 2),  # Roll rate
            "y": random.uniform(-2, 2),  # Pitch rate
            "z": random.uniform(-5, 5)   # Yaw rate
        }
        
        await asyncio.sleep(0.01)  # Simulate sensor delay
        return {"accel": accel, "gyro": gyro}
    
    async def _simulate_temperature(self):
        """Simulate temperature sensor"""
        base_temp = self.environment["room_temp"]
        
        # Add some variation due to electronics heating
        variation = random.uniform(-2, 5)
        temp = base_temp + variation
        
        await asyncio.sleep(0.1)  # Simulate sensor delay
        return round(temp, 1)
    
    async def _simulate_battery(self):
        """Simulate battery monitoring"""
        # Gradually decrease battery over time
        current_time = time.time()
        
        # Simulate battery drain
        if "last_battery_update" not in self.__dict__:
            self.last_battery_update = current_time
            self.simulated_battery_percentage = 85.0
        
        time_diff = current_time - self.last_battery_update
        drain = self.environment["battery_drain_rate"] * (time_diff / 60)
        
        self.simulated_battery_percentage = max(0, self.simulated_battery_percentage - drain)
        self.last_battery_update = current_time
        
        # Convert percentage to voltage (simplified)
        voltage = 11.0 + (self.simulated_battery_percentage / 100.0) * 1.6
        
        await asyncio.sleep(0.05)  # Simulate sensor delay
        return {
            "voltage": round(voltage, 2),
            "percentage": round(self.simulated_battery_percentage, 1)
        }
    
    async def _read_physical_ultrasonic(self):
        """Read physical ultrasonic sensor"""
        # This would interface with actual hardware
        logger.warning("🔩 Physical ultrasonic not implemented - using simulation")
        return await self._simulate_ultrasonic()
    
    async def _read_physical_line_sensor(self):
        """Read physical line sensor"""
        # This would interface with actual hardware
        logger.warning("🔩 Physical line sensor not implemented - using simulation")
        return await self._simulate_line_sensor()
    
    async def _read_physical_imu(self):
        """Read physical IMU"""
        # This would interface with actual hardware  
        logger.warning("🔩 Physical IMU not implemented - using simulation")
        return await self._simulate_imu()
    
    async def _read_physical_temperature(self):
        """Read physical temperature sensor"""
        # This would interface with actual hardware
        logger.warning("🔩 Physical temperature sensor not implemented - using simulation")
        return await self._simulate_temperature()
    
    async def _read_physical_battery(self):
        """Read physical battery monitoring"""
        # This would interface with actual hardware
        logger.warning("🔩 Physical battery monitoring not implemented - using simulation")
        return await self._simulate_battery()
    
    async def calibrate_sensors(self):
        """Calibrate all sensors"""
        logger.info("🔧 Starting sensor calibration...")
        
        if self.simulation_mode:
            await asyncio.sleep(2)  # Simulate calibration time
            logger.info("✅ Sensor calibration completed (simulated)")
        else:
            # Real calibration procedures
            pass
        
        return {
            "calibration": "completed",
            "sensors": ["ultrasonic", "line_sensor", "imu", "temperature", "battery"],
            "timestamp": time.time()
        }
    
    async def get_sensor_diagnostics(self):
        """Get detailed sensor diagnostics"""
        diagnostics = {
            "controller": {
                "initialized": self.is_initialized,
                "simulation_mode": self.simulation_mode,
                "timestamp": time.time()
            },
            "sensors": {}
        }
        
        # Check each sensor
        for sensor_name in ["ultrasonic", "line_sensor", "imu", "temperature", "battery"]:
            try:
                last_reading = self.sensor_data.get(sensor_name, {})
                age = time.time() - last_reading.get("timestamp", 0)
                
                diagnostics["sensors"][sensor_name] = {
                    "status": "operational" if age < 10 else "stale",
                    "last_reading_age": round(age, 1),
                    "data_available": bool(last_reading)
                }
            except Exception as e:
                diagnostics["sensors"][sensor_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return diagnostics
    
    async def set_environment_parameters(self, environment_params):
        """Update simulation environment parameters"""
        if self.simulation_mode:
            self.environment.update(environment_params)
            logger.info(f"🌍 Environment updated: {environment_params}")
            return {"status": "updated", "environment": self.environment}
        else:
            return {"status": "ignored", "message": "Environment params only apply in simulation mode"}