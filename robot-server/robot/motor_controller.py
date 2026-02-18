"""
Motor Controller for Medi Runner Robot
Handles movement, speed control, and motor coordination

Hardware:
    - L298N Motor Driver
    - GPIO pins (BCM): IN1=17, IN2=27, IN3=22, IN4=23, ENA=24, ENB=25
    - PWM frequency: 1000 Hz
"""

import asyncio
import logging
import time
import random
import math
import sys
from pathlib import Path

# Ensure we can import config from the robot-server root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import RPi.GPIO as GPIO
except ImportError:
    # Mock GPIO for development / testing without Pi hardware
    class _MockPWM:
        def start(self, duty): pass
        def ChangeDutyCycle(self, duty): pass
        def stop(self): pass

    class _MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        HIGH = 1
        LOW = 0
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode): pass
        @staticmethod
        def output(pin, state): pass
        @staticmethod
        def PWM(pin, freq): return _MockPWM()
        @staticmethod
        def cleanup(channel=None): pass
        @staticmethod
        def setwarnings(flag): pass

    GPIO = _MockGPIO()

from config import GPIO_PINS, MOTOR_SETTINGS

logger = logging.getLogger(__name__)

class PIDController:
    """PID Controller for precise motor control"""
    
    def __init__(self, kp=1.0, ki=0.0, kd=0.0, setpoint=0.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        
        # PID state
        self.previous_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()
        
        # Limits
        self.integral_limit = 100.0
        self.output_limit = 100.0
        
        logger.info(f"🎛️ PID Controller initialized: Kp={kp}, Ki={ki}, Kd={kd}")
    
    def update(self, current_value):
        """Calculate PID output"""
        current_time = time.time()
        dt = current_time - self.last_time
        
        if dt <= 0:
            return 0.0
        
        # Calculate error
        error = self.setpoint - current_value
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term
        self.integral += error * dt
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        i_term = self.ki * self.integral
        
        # Derivative term
        derivative = (error - self.previous_error) / dt
        d_term = self.kd * derivative
        
        # Calculate output
        output = p_term + i_term + d_term
        output = max(-self.output_limit, min(self.output_limit, output))
        
        # Update state
        self.previous_error = error
        self.last_time = current_time
        
        return output
    
    def reset(self):
        """Reset PID controller state"""
        self.previous_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()
        logger.info("🔄 PID controller reset")
    
    def set_pid_values(self, kp=None, ki=None, kd=None):
        """Update PID values"""
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
        if kd is not None:
            self.kd = kd
        
        logger.info(f"🎛️ PID values updated: Kp={self.kp}, Ki={self.ki}, Kd={self.kd}")
    
    def get_pid_values(self):
        """Get current PID values"""
        return {
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd,
            "setpoint": self.setpoint
        }

class MotorController:
    """Motor controller with simulation capabilities"""
    
    def __init__(self, simulation_mode=True):
        self.simulation_mode = simulation_mode
        self.is_initialized = False
        
        # Motor state
        self.left_motor_speed = 0
        self.right_motor_speed = 0
        self.is_moving = False
        self.current_direction = "stopped"
        
        # Position tracking (simulation)
        self.position = {"x": 0.0, "y": 0.0, "angle": 0.0}
        self.odometry_enabled = True
        
        # Motor characteristics
        self.max_speed = 100
        self.acceleration_rate = 10  # speed units per second
        
        # PID controller for line following
        self.pid_controller = PIDController(kp=1.0, ki=0.0, kd=0.0, setpoint=0.0)
        self.line_following_active = False
        
        logger.info(f"🔧 Motor Controller initialized (simulation: {simulation_mode})")
    
    # ---- GPIO pin references (L298N) ----
    PIN_IN1 = GPIO_PINS.get('MOTOR_IN1', 17)
    PIN_IN2 = GPIO_PINS.get('MOTOR_IN2', 27)
    PIN_IN3 = GPIO_PINS.get('MOTOR_IN3', 22)
    PIN_IN4 = GPIO_PINS.get('MOTOR_IN4', 23)
    PIN_ENA = GPIO_PINS.get('MOTOR_ENA', 24)
    PIN_ENB = GPIO_PINS.get('MOTOR_ENB', 25)
    PWM_FREQ = MOTOR_SETTINGS.get('PWM_FREQUENCY', 1000)

    # Direction → (IN1, IN2, IN3, IN4)
    _DIR_MAP = {
        'forward':  (GPIO.HIGH, GPIO.LOW,  GPIO.HIGH, GPIO.LOW),
        'backward': (GPIO.LOW,  GPIO.HIGH, GPIO.LOW,  GPIO.HIGH),
        'left':     (GPIO.LOW,  GPIO.HIGH, GPIO.HIGH, GPIO.LOW),
        'right':    (GPIO.HIGH, GPIO.LOW,  GPIO.LOW,  GPIO.HIGH),
    }

    async def initialize(self):
        """Initialize motor controller (sets up GPIO when not in simulation)."""
        logger.info("🔧 Initializing motor systems...")

        if self.simulation_mode:
            await asyncio.sleep(0.5)
            logger.info("✅ Motor simulation initialized")
        else:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)

            # Direction pins
            for pin in (self.PIN_IN1, self.PIN_IN2, self.PIN_IN3, self.PIN_IN4):
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)

            # Enable / PWM pins
            GPIO.setup(self.PIN_ENA, GPIO.OUT)
            GPIO.setup(self.PIN_ENB, GPIO.OUT)

            self.pwm_left  = GPIO.PWM(self.PIN_ENA, self.PWM_FREQ)
            self.pwm_right = GPIO.PWM(self.PIN_ENB, self.PWM_FREQ)
            self.pwm_left.start(0)
            self.pwm_right.start(0)

            logger.info(
                f"✅ GPIO initialised  IN1={self.PIN_IN1} IN2={self.PIN_IN2} "
                f"IN3={self.PIN_IN3} IN4={self.PIN_IN4} "
                f"ENA={self.PIN_ENA} ENB={self.PIN_ENB} PWM@{self.PWM_FREQ}Hz"
            )

        self.is_initialized = True
        return True

    async def cleanup(self):
        """Cleanup motor controller – stop motors and release GPIO."""
        if self.is_moving:
            await self.stop()

        if not self.simulation_mode:
            try:
                if hasattr(self, 'pwm_left'):
                    self.pwm_left.stop()
                if hasattr(self, 'pwm_right'):
                    self.pwm_right.stop()
                GPIO.cleanup()
                logger.info("✅ GPIO cleaned up")
            except Exception as e:
                logger.error(f"GPIO cleanup error: {e}")

        logger.info("🧹 Motor controller cleanup complete")
        self.is_initialized = False
    
    async def move(self, direction, speed=50, duration=0):
        """
        Move robot in specified direction
        
        Args:
            direction: forward, backward, left, right
            speed: 0-100 speed percentage
            duration: movement duration in seconds (0 = continuous)
        """
        if not self.is_initialized:
            raise Exception("Motor controller not initialized")
        
        # Validate inputs
        speed = max(0, min(100, speed))
        
        logger.info(f"🤖 Moving {direction} at {speed}% speed")
        
        if self.simulation_mode:
            await self._simulate_movement(direction, speed, duration)
        else:
            await self._execute_physical_movement(direction, speed, duration)
        
        return {
            "action": "move",
            "direction": direction,
            "speed": speed,
            "duration": duration,
            "status": "completed"
        }
    
    def _gpio_all_low(self):
        """Set all direction pins LOW and PWM to 0 – immediate physical stop."""
        for pin in (self.PIN_IN1, self.PIN_IN2, self.PIN_IN3, self.PIN_IN4):
            GPIO.output(pin, GPIO.LOW)
        if hasattr(self, 'pwm_left'):
            self.pwm_left.ChangeDutyCycle(0)
        if hasattr(self, 'pwm_right'):
            self.pwm_right.ChangeDutyCycle(0)

    async def stop(self):
        """Stop all motor movement"""
        logger.info("🛑 Stopping robot movement")

        self.left_motor_speed = 0
        self.right_motor_speed = 0
        self.is_moving = False
        self.current_direction = "stopped"

        if self.simulation_mode:
            await asyncio.sleep(0.1)
        else:
            self._gpio_all_low()

        logger.info("✅ Robot stopped")
        return {"action": "stop", "status": "completed"}

    async def emergency_stop(self):
        """Emergency stop – immediate halt, cuts power to motors."""
        logger.warning("🚨 EMERGENCY STOP ACTIVATED")

        self.left_motor_speed = 0
        self.right_motor_speed = 0
        self.is_moving = False
        self.current_direction = "emergency_stopped"

        if not self.simulation_mode:
            self._gpio_all_low()

        logger.warning("🚨 Emergency stop completed")
        return {"action": "emergency_stop", "status": "executed"}
    
    async def set_speed(self, left_speed, right_speed):
        """Set individual motor speeds for differential steering"""
        if not self.is_initialized:
            raise Exception("Motor controller not initialized")
        
        # Clamp speeds to valid range
        left_speed = max(-100, min(100, left_speed))
        right_speed = max(-100, min(100, right_speed))
        
        self.left_motor_speed = left_speed
        self.right_motor_speed = right_speed
        
        if self.simulation_mode:
            await self._update_simulated_position()
        else:
            # Set physical motor speeds
            pass
        
        logger.debug(f"🎛️ Motor speeds set: L={left_speed}, R={right_speed}")
        
        return {
            "left_speed": left_speed,
            "right_speed": right_speed,
            "status": "updated"
        }
    
    async def get_status(self):
        """Get current motor status"""
        encoder_data = await self._get_encoder_data() if not self.simulation_mode else self._get_simulated_encoder_data()
        
        return {
            "motors": {
                "left_speed": self.left_motor_speed,
                "right_speed": self.right_motor_speed,
                "is_moving": self.is_moving,
                "direction": self.current_direction
            },
            "position": self.position.copy(),
            "encoders": encoder_data,
            "status": "online" if self.is_initialized else "offline"
        }
    
    async def _simulate_movement(self, direction, speed, duration):
        """Simulate robot movement for testing"""
        self.is_moving = True
        self.current_direction = direction
        
        # Convert direction to motor speeds
        if direction == "forward":
            self.left_motor_speed = speed
            self.right_motor_speed = speed
        elif direction == "backward":
            self.left_motor_speed = -speed
            self.right_motor_speed = -speed
        elif direction == "left":
            self.left_motor_speed = -speed // 2
            self.right_motor_speed = speed // 2
        elif direction == "right":
            self.left_motor_speed = speed // 2
            self.right_motor_speed = -speed // 2
        
        # Simulate movement duration
        if duration > 0:
            # Update position during movement
            update_interval = 0.1
            updates = int(duration / update_interval)
            
            for _ in range(updates):
                await self._update_simulated_position()
                await asyncio.sleep(update_interval)
            
            # Auto-stop after duration
            await self.stop()
        else:
            # Continuous movement
            await self._update_simulated_position()
    
    async def _update_simulated_position(self):
        """Update simulated robot position based on motor speeds"""
        if not self.is_moving:
            return
        
        # Simple position update based on differential drive
        dt = 0.1  # time step
        wheel_base = 0.2  # distance between wheels in meters
        
        # Convert motor speeds to linear and angular velocities
        left_vel = self.left_motor_speed * 0.01  # convert percentage to m/s
        right_vel = self.right_motor_speed * 0.01
        
        linear_vel = (left_vel + right_vel) / 2
        angular_vel = (right_vel - left_vel) / wheel_base
        
        # Update position
        self.position["x"] += linear_vel * dt * 1000  # convert to mm
        self.position["y"] += 0  # simplified - assume straight line
        self.position["angle"] += angular_vel * dt * 57.3  # convert to degrees
        
        # Keep angle in 0-360 range
        self.position["angle"] = self.position["angle"] % 360
    
    async def _execute_physical_movement(self, direction, speed, duration):
        """Drive the L298N motor driver via GPIO."""
        self.is_moving = True
        self.current_direction = direction

        # --- Set direction pins ---
        pins = self._DIR_MAP.get(direction)
        if pins is None:
            logger.error(f"Unknown direction: {direction}")
            return

        in1, in2, in3, in4 = pins
        GPIO.output(self.PIN_IN1, in1)
        GPIO.output(self.PIN_IN2, in2)
        GPIO.output(self.PIN_IN3, in3)
        GPIO.output(self.PIN_IN4, in4)

        # --- Set speed via PWM ---
        duty = max(0, min(100, speed))
        if hasattr(self, 'pwm_left') and hasattr(self, 'pwm_right'):
            self.pwm_left.ChangeDutyCycle(duty)
            self.pwm_right.ChangeDutyCycle(duty)

        # Track motor speeds (used by status / position tracking)
        if direction == 'forward':
            self.left_motor_speed = speed
            self.right_motor_speed = speed
        elif direction == 'backward':
            self.left_motor_speed = -speed
            self.right_motor_speed = -speed
        elif direction == 'left':
            self.left_motor_speed = -speed // 2
            self.right_motor_speed = speed // 2
        elif direction == 'right':
            self.left_motor_speed = speed // 2
            self.right_motor_speed = -speed // 2

        logger.info(
            f"🔩 GPIO  IN1={in1} IN2={in2} IN3={in3} IN4={in4}  "
            f"PWM={duty}%  dir={direction}"
        )

        # Auto-stop after duration (0 = continuous)
        if duration > 0:
            await asyncio.sleep(duration)
            await self.stop()
    
    async def _get_encoder_data(self):
        """Get data from motor encoders (physical hardware)"""
        # This would read actual encoder values
        return self._get_simulated_encoder_data()
    
    def _get_simulated_encoder_data(self):
        """Generate simulated encoder data"""
        # Simulate encoder ticks based on movement
        base_ticks = time.time() * 100  # simulate ticks over time
        
        return {
            "left_encoder": int(base_ticks + random.randint(-10, 10)),
            "right_encoder": int(base_ticks + random.randint(-10, 10)),
            "left_rpm": abs(self.left_motor_speed) * 2.5,  # simulate RPM
            "right_rpm": abs(self.right_motor_speed) * 2.5
        }
    
    async def calibrate_motors(self):
        """Calibrate motor characteristics"""
        logger.info("🔧 Starting motor calibration...")
        
        if self.simulation_mode:
            await asyncio.sleep(1)  # Simulate calibration time
            logger.info("✅ Motor calibration completed (simulated)")
        else:
            # Real calibration would measure actual motor response
            pass
        
        return {
            "calibration": "completed",
            "max_speed": self.max_speed,
            "acceleration_rate": self.acceleration_rate
        }
    
    async def set_pid_values(self, kp=None, ki=None, kd=None):
        """Update PID controller values"""
        self.pid_controller.set_pid_values(kp=kp, ki=ki, kd=kd)
        return self.pid_controller.get_pid_values()
    
    async def get_pid_values(self):
        """Get current PID controller values"""
        return self.pid_controller.get_pid_values()
    
    async def reset_pid(self):
        """Reset PID controller state"""
        self.pid_controller.reset()
        return {"status": "reset"}
    
    async def start_line_following(self, base_speed=50):
        """Start line following using PID control"""
        if not self.is_initialized:
            raise Exception("Motor controller not initialized")
        
        logger.info(f"🎯 Starting line following with base speed {base_speed}")
        self.line_following_active = True
        self.pid_controller.setpoint = 0.0  # Center of line
        
        # Start line following task
        asyncio.create_task(self._line_following_loop(base_speed))
        
        return {
            "action": "start_line_following",
            "base_speed": base_speed,
            "pid_values": self.pid_controller.get_pid_values(),
            "status": "started"
        }
    
    async def stop_line_following(self):
        """Stop line following"""
        logger.info("🛑 Stopping line following")
        self.line_following_active = False
        await self.stop()
        return {"action": "stop_line_following", "status": "stopped"}
    
    async def _line_following_loop(self, base_speed):
        """Main line following control loop"""
        try:
            while self.line_following_active:
                # Get line position from sensors (simulated)
                line_position = await self._get_line_position()
                
                if line_position is None:
                    # Lost line - stop or search
                    logger.warning("⚠️ Line lost - stopping")
                    await self.stop()
                    break
                
                # Calculate PID correction
                correction = self.pid_controller.update(line_position)
                
                # Apply correction to motor speeds
                left_speed = base_speed - correction
                right_speed = base_speed + correction
                
                # Clamp speeds
                left_speed = max(-100, min(100, left_speed))
                right_speed = max(-100, min(100, right_speed))
                
                # Set motor speeds
                await self.set_speed(left_speed, right_speed)
                
                # Control loop delay
                await asyncio.sleep(0.05)  # 20 Hz control loop
                
        except Exception as e:
            logger.error(f"❌ Line following error: {e}")
            self.line_following_active = False
            await self.stop()
    
    async def _get_line_position(self):
        """Get line position from sensors (simulated)"""
        if self.simulation_mode:
            # Simulate line sensor readings
            # Return position from -1 (left) to +1 (right), 0 = center
            # Add some noise and occasional line loss
            if random.random() < 0.05:  # 5% chance of losing line
                return None
            
            # Simulate following a slightly curved line
            base_position = math.sin(time.time() * 0.5) * 0.3
            noise = random.uniform(-0.1, 0.1)
            return base_position + noise
        else:
            # Real sensor reading would go here
            # Example: Read from IR sensors, camera, etc.
            return 0.0
    
    async def get_diagnostics(self):
        """Get detailed motor diagnostics"""
        return {
            "controller": {
                "initialized": self.is_initialized,
                "simulation_mode": self.simulation_mode,
                "current_time": time.time()
            },
            "motors": {
                "left": {
                    "speed": self.left_motor_speed,
                    "status": "operational",
                    "temperature": 25.0 + random.uniform(-5, 15)  # simulated temp
                },
                "right": {
                    "speed": self.right_motor_speed, 
                    "status": "operational",
                    "temperature": 25.0 + random.uniform(-5, 15)
                }
            },
            "movement": {
                "is_moving": self.is_moving,
                "direction": self.current_direction,
                "position": self.position
            }
        }