"""
Motor Controller for L298N Motor Driver
Handles robot movement, speed control, and motor management.
"""

import asyncio
import time
from typing import Optional, Tuple, Dict, Any

try:
    import RPi.GPIO as GPIO
except ImportError:
    # Mock GPIO for development/testing
    class MockGPIO:
        BCM = 'BCM'
        OUT = 'OUT'
        HIGH = 1
        LOW = 0
        
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode): pass
        @staticmethod
        def output(pin, state): pass
        @staticmethod
        def PWM(pin, freq): 
            return MockPWM()
        @staticmethod
        def cleanup(): pass
    
    class MockPWM:
        def start(self, duty): pass
        def ChangeDutyCycle(self, duty): pass
        def stop(self): pass
    
    GPIO = MockGPIO()

from config import GPIO_PINS, MOTOR_SETTINGS, SIMULATION_MODE
from utils.logger import setup_logger


class MotorController:
    """
    Controls robot motors using L298N motor driver.
    """
    
    def __init__(self):
        self.logger = setup_logger('MotorController')
        self.simulation_mode = SIMULATION_MODE
        
        # Motor control pins
        self.pins = {
            'in1': GPIO_PINS['MOTOR_IN1'],
            'in2': GPIO_PINS['MOTOR_IN2'], 
            'in3': GPIO_PINS['MOTOR_IN3'],
            'in4': GPIO_PINS['MOTOR_IN4'],
            'ena': GPIO_PINS['MOTOR_ENA'],
            'enb': GPIO_PINS['MOTOR_ENB']
        }
        
        # PWM objects for speed control
        self.pwm_left = None
        self.pwm_right = None
        
        # Current state
        self.current_speed = 0
        self.current_direction = 'stopped'
        self.is_moving = False
        
        # Movement lock to prevent concurrent movements
        self.movement_lock = asyncio.Lock()
        
        # Initialize GPIO if not in simulation mode
        if not self.simulation_mode:
            self._setup_gpio()
    
    def _setup_gpio(self):
        """
        Initialize GPIO pins for motor control.
        """
        try:
            GPIO.setmode(GPIO.BCM)
            
            # Setup motor control pins as outputs
            for pin in self.pins.values():
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            
            # Setup PWM for speed control
            self.pwm_left = GPIO.PWM(self.pins['ena'], MOTOR_SETTINGS['PWM_FREQUENCY'])
            self.pwm_right = GPIO.PWM(self.pins['enb'], MOTOR_SETTINGS['PWM_FREQUENCY'])
            
            self.pwm_left.start(0)
            self.pwm_right.start(0)
            
            self.logger.info("Motor GPIO initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize motor GPIO: {e}")
            raise
    
    async def start(self):
        """
        Start the motor controller.
        """
        self.logger.info("Motor controller started")
    
    async def stop(self):
        """
        Stop the motor controller and cleanup GPIO.
        """
        await self.stop_motors()
        
        if not self.simulation_mode:
            try:
                if self.pwm_left:
                    self.pwm_left.stop()
                if self.pwm_right:
                    self.pwm_right.stop()
                GPIO.cleanup()
                self.logger.info("Motor GPIO cleaned up")
            except Exception as e:
                self.logger.error(f"Error during GPIO cleanup: {e}")
    
    async def move(self, direction: str, speed: int = 50, duration: Optional[float] = None):
        """
        Move the robot in the specified direction.
        
        Args:
            direction: 'forward', 'backward', 'left', 'right', 'stop'
            speed: Speed percentage (0-100)
            duration: Optional movement duration in seconds
        """
        async with self.movement_lock:
            try:
                # Validate parameters
                speed = max(0, min(100, speed))
                
                if direction == 'stop':
                    await self.stop_motors()
                    return
                
                self.logger.info(f"Moving {direction} at {speed}% speed")
                
                # Set motor directions
                await self._set_motor_direction(direction)
                
                # Set motor speed
                await self._set_motor_speed(speed)
                
                self.current_direction = direction
                self.current_speed = speed
                self.is_moving = True
                
                # If duration is specified, stop after that time
                if duration:
                    await asyncio.sleep(duration)
                    await self.stop_motors()
                
            except Exception as e:
                self.logger.error(f"Error in move command: {e}")
                await self.stop_motors()
                raise
    
    async def _set_motor_direction(self, direction: str):
        """
        Set motor direction based on movement command.
        """
        if self.simulation_mode:
            self.logger.debug(f"[SIMULATION] Setting direction: {direction}")
            return
        
        # Motor direction mappings
        directions = {
            'forward': (GPIO.HIGH, GPIO.LOW, GPIO.HIGH, GPIO.LOW),
            'backward': (GPIO.LOW, GPIO.HIGH, GPIO.LOW, GPIO.HIGH),
            'left': (GPIO.LOW, GPIO.HIGH, GPIO.HIGH, GPIO.LOW),
            'right': (GPIO.HIGH, GPIO.LOW, GPIO.LOW, GPIO.HIGH)
        }
        
        if direction in directions:
            in1, in2, in3, in4 = directions[direction]
            GPIO.output(self.pins['in1'], in1)
            GPIO.output(self.pins['in2'], in2)
            GPIO.output(self.pins['in3'], in3)
            GPIO.output(self.pins['in4'], in4)
    
    async def _set_motor_speed(self, speed: int):
        """
        Set motor speed using PWM.
        """
        if self.simulation_mode:
            self.logger.debug(f"[SIMULATION] Setting speed: {speed}%")
            return
        
        # Ensure minimum speed for motor operation
        if speed > 0 and speed < MOTOR_SETTINGS['MIN_SPEED']:
            speed = MOTOR_SETTINGS['MIN_SPEED']
        
        # Apply speed to both motors
        if self.pwm_left and self.pwm_right:
            self.pwm_left.ChangeDutyCycle(speed)
            self.pwm_right.ChangeDutyCycle(speed)
    
    async def stop_motors(self):
        """
        Stop all motor movement.
        """
        if self.simulation_mode:
            self.logger.debug("[SIMULATION] Stopping motors")
        else:
            # Set all direction pins to LOW
            for pin_name in ['in1', 'in2', 'in3', 'in4']:
                GPIO.output(self.pins[pin_name], GPIO.LOW)
            
            # Set PWM to 0
            if self.pwm_left and self.pwm_right:
                self.pwm_left.ChangeDutyCycle(0)
                self.pwm_right.ChangeDutyCycle(0)
        
        self.current_direction = 'stopped'
        self.current_speed = 0
        self.is_moving = False
        
        self.logger.debug("Motors stopped")
    
    async def gradual_speed_change(self, target_speed: int, step_size: int = 5, delay: float = 0.1):
        """
        Gradually change motor speed to avoid sudden movements.
        """
        current = self.current_speed
        
        while abs(current - target_speed) > step_size:
            if current < target_speed:
                current = min(current + step_size, target_speed)
            else:
                current = max(current - step_size, target_speed)
            
            await self._set_motor_speed(current)
            self.current_speed = current
            await asyncio.sleep(delay)
        
        # Final adjustment
        await self._set_motor_speed(target_speed)
        self.current_speed = target_speed
    
    async def turn_by_angle(self, angle: int, base_speed: int = 60):
        """
        Turn robot by specified angle (positive = right, negative = left).
        
        Args:
            angle: Degrees to turn (-180 to +180)
            base_speed: Base turning speed
        """
        direction = 'right' if angle > 0 else 'left'
        
        # Calculate turn duration based on angle
        # This will need calibration based on robot characteristics
        turn_duration = abs(angle) / 90.0 * 1.0  # 1 second for 90 degrees
        
        self.logger.info(f"Turning {direction} by {abs(angle)} degrees")
        
        await self.move(direction, base_speed, turn_duration)
    
    async def follow_line(self, sensor_data: list, base_speed: int = 50):
        """
        Line following algorithm based on IR sensor input.
        
        Args:
            sensor_data: List of sensor readings [left_far, left, center, right, right_far]
            base_speed: Base movement speed
        """
        # Line following logic based on sensor patterns
        patterns = {
            (0, 0, 1, 0, 0): ('forward', base_speed),      # On line
            (0, 1, 1, 0, 0): ('forward', base_speed - 10), # Slight left
            (0, 0, 1, 1, 0): ('forward', base_speed - 10), # Slight right
            (1, 1, 0, 0, 0): ('left', base_speed - 20),    # Turn left
            (0, 0, 0, 1, 1): ('right', base_speed - 20),   # Turn right
            (1, 1, 1, 0, 0): ('left', base_speed - 15),    # Sharp left
            (0, 0, 1, 1, 1): ('right', base_speed - 15),   # Sharp right
            (1, 1, 1, 1, 1): ('stop', 0),                 # Intersection or end
            (0, 0, 0, 0, 0): ('search', base_speed - 30)  # Lost line
        }
        
        pattern = tuple(sensor_data)
        
        if pattern in patterns:
            direction, speed = patterns[pattern]
            
            if direction == 'search':
                # Lost line recovery - slight zigzag
                await self.move('left', speed, 0.2)
                await self.move('right', speed, 0.4)
                await self.move('left', speed, 0.2)
            else:
                await self.move(direction, speed)
        else:
            # Unknown pattern, stop for safety
            self.logger.warning(f"Unknown sensor pattern: {pattern}")
            await self.stop_motors()
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current motor status.
        """
        return {
            'direction': self.current_direction,
            'speed': self.current_speed,
            'is_moving': self.is_moving,
            'simulation_mode': self.simulation_mode,
            'timestamp': time.time()
        }
    
    async def update_config(self, settings: Dict[str, Any]):
        """
        Update motor configuration settings.
        """
        self.logger.info(f"Updating motor configuration: {settings}")
        
        # Apply new settings (this would update global config)
        # Implementation depends on specific requirements
        pass
