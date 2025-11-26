"""
Sensor Controller for IR sensors and Pi Camera
Handles sensor data collection, processing, and calibration.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional

try:
    import RPi.GPIO as GPIO
    import cv2
    import numpy as np
except ImportError:
    # Mock imports for development
    class MockGPIO:
        BCM = 'BCM'
        IN = 'IN'
        PUD_UP = 'PUD_UP'
        
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode, pull_up_down=None): pass
        @staticmethod
        def input(pin): return 0
        @staticmethod
        def cleanup(): pass
    
    GPIO = MockGPIO()
    
    class MockCV2:
        @staticmethod
        def VideoCapture(index): return MockCamera()
        
        CAP_PROP_FRAME_WIDTH = 'width'
        CAP_PROP_FRAME_HEIGHT = 'height'
        CAP_PROP_FPS = 'fps'
    
    class MockCamera:
        def read(self): return True, np.zeros((480, 640, 3), dtype=np.uint8)
        def set(self, prop, value): pass
        def release(self): pass
        def isOpened(self): return True
    
    cv2 = MockCV2()
    np = type('numpy', (), {'zeros': lambda shape, dtype=None: [[[]]]})  # Simple mock

from config import GPIO_PINS, CAMERA_RESOLUTION, CAMERA_FPS, SIMULATION_MODE
from utils.logger import setup_logger


class SensorController:
    """
    Manages IR sensors and camera for robot navigation and vision.
    """
    
    def __init__(self):
        self.logger = setup_logger('SensorController')
        self.simulation_mode = SIMULATION_MODE
        
        # IR sensor pins
        self.ir_pins = [
            GPIO_PINS['IR_SENSOR_1'],  # Far left
            GPIO_PINS['IR_SENSOR_2'],  # Left
            GPIO_PINS['IR_SENSOR_3'],  # Center
            GPIO_PINS['IR_SENSOR_4'],  # Right
            GPIO_PINS['IR_SENSOR_5']   # Far right
        ]
        
        # Camera setup
        self.camera = None
        self.camera_resolution = CAMERA_RESOLUTION
        self.camera_fps = CAMERA_FPS
        
        # Sensor calibration data
        self.ir_thresholds = [0.5] * 5  # Calibrated thresholds for each sensor
        self.ir_baseline = [0] * 5      # Baseline readings
        
        # Sensor reading history for smoothing
        self.ir_history = [[] for _ in range(5)]
        self.history_size = 5
        
        # Camera frame buffer
        self.latest_frame = None
        self.frame_lock = asyncio.Lock()
        
        # Initialize hardware if not in simulation mode
        if not self.simulation_mode:
            self._setup_gpio()
            self._setup_camera()
    
    def _setup_gpio(self):
        """
        Initialize GPIO pins for IR sensors.
        """
        try:
            GPIO.setmode(GPIO.BCM)
            
            # Setup IR sensor pins as inputs with pull-up resistors
            for pin in self.ir_pins:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            self.logger.info("Sensor GPIO initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize sensor GPIO: {e}")
            raise
    
    def _setup_camera(self):
        """
        Initialize Pi Camera.
        """
        try:
            self.camera = cv2.VideoCapture(0)
            
            if not self.camera.isOpened():
                raise Exception("Could not open camera")
            
            # Set camera properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_resolution[1])
            self.camera.set(cv2.CAP_PROP_FPS, self.camera_fps)
            
            self.logger.info(f"Camera initialized: {self.camera_resolution} @ {self.camera_fps}fps")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {e}")
            # Continue without camera in case it's not available
            self.camera = None
    
    async def start(self):
        """
        Start the sensor controller and background tasks.
        """
        self.logger.info("Sensor controller started")
        
        # Start camera frame capture loop
        if self.camera:
            asyncio.create_task(self._camera_loop())
    
    async def stop(self):
        """
        Stop the sensor controller and cleanup resources.
        """
        if not self.simulation_mode:
            try:
                if self.camera:
                    self.camera.release()
                GPIO.cleanup()
                self.logger.info("Sensor resources cleaned up")
            except Exception as e:
                self.logger.error(f"Error during sensor cleanup: {e}")
    
    async def _camera_loop(self):
        """
        Continuously capture frames from the camera.
        """
        while True:
            try:
                if self.camera and self.camera.isOpened():
                    ret, frame = self.camera.read()
                    
                    if ret:
                        async with self.frame_lock:
                            self.latest_frame = frame.copy()
                    else:
                        self.logger.warning("Failed to read camera frame")
                
                # Control frame rate
                await asyncio.sleep(1.0 / self.camera_fps)
                
            except Exception as e:
                self.logger.error(f"Error in camera loop: {e}")
                await asyncio.sleep(1)
    
    async def read_ir_sensors(self) -> List[int]:
        """
        Read IR sensor array and return digital values.
        
        Returns:
            List of sensor readings [0,1,0,1,1] format
        """
        if self.simulation_mode:
            # Return simulated sensor data
            return [0, 0, 1, 0, 0]  # Simulate robot on line
        
        try:
            raw_readings = []
            
            # Read all IR sensors
            for pin in self.ir_pins:
                reading = GPIO.input(pin)
                raw_readings.append(1 - reading)  # Invert because of pull-up
            
            # Apply smoothing filter
            smoothed_readings = self._smooth_sensor_data(raw_readings)
            
            # Apply calibration thresholds
            digital_readings = [
                1 if reading > threshold else 0
                for reading, threshold in zip(smoothed_readings, self.ir_thresholds)
            ]
            
            return digital_readings
            
        except Exception as e:
            self.logger.error(f"Error reading IR sensors: {e}")
            return [0] * 5
    
    def _smooth_sensor_data(self, raw_readings: List[int]) -> List[float]:
        """
        Apply smoothing filter to reduce sensor noise.
        """
        smoothed = []
        
        for i, reading in enumerate(raw_readings):
            # Add to history
            self.ir_history[i].append(reading)
            
            # Keep only recent readings
            if len(self.ir_history[i]) > self.history_size:
                self.ir_history[i].pop(0)
            
            # Calculate moving average
            avg = sum(self.ir_history[i]) / len(self.ir_history[i])
            smoothed.append(avg)
        
        return smoothed
    
    async def capture_image(self) -> Optional[np.ndarray]:
        """
        Capture a single image from the camera.
        
        Returns:
            Camera frame as numpy array, or None if not available
        """
        if self.simulation_mode:
            # Return simulated image
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        async with self.frame_lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
        
        return None
    
    async def get_line_position(self) -> Dict[str, Any]:
        """
        Calculate line position based on sensor readings.
        
        Returns:
            Dictionary with line position information
        """
        sensor_data = await self.read_ir_sensors()
        
        # Calculate weighted position (-2 to +2, 0 = center)
        weights = [-2, -1, 0, 1, 2]
        total_weight = 0
        weighted_sum = 0
        
        for i, (sensor, weight) in enumerate(zip(sensor_data, weights)):
            if sensor:
                total_weight += 1
                weighted_sum += weight
        
        if total_weight == 0:
            # No line detected
            position = None
            error = 999  # Large error value
        else:
            position = weighted_sum / total_weight
            error = abs(position)
        
        return {
            'position': position,
            'error': error,
            'sensors': sensor_data,
            'line_detected': total_weight > 0,
            'intersection': total_weight >= 4,  # Most sensors active
            'timestamp': time.time()
        }
    
    async def calibrate(self, calibration_time: float = 5.0):
        """
        Calibrate IR sensors by measuring baseline values.
        
        Args:
            calibration_time: How long to calibrate in seconds
        """
        self.logger.info(f"Starting sensor calibration for {calibration_time} seconds...")
        
        if self.simulation_mode:
            self.logger.info("[SIMULATION] Sensor calibration completed")
            return
        
        # Collect readings during calibration period
        readings_sum = [0] * 5
        reading_count = 0
        
        start_time = time.time()
        
        while (time.time() - start_time) < calibration_time:
            try:
                # Read raw sensor values
                for i, pin in enumerate(self.ir_pins):
                    reading = GPIO.input(pin)
                    readings_sum[i] += (1 - reading)  # Invert for pull-up
                
                reading_count += 1
                await asyncio.sleep(0.05)  # 20Hz sampling
                
            except Exception as e:
                self.logger.error(f"Error during calibration: {e}")
                break
        
        if reading_count > 0:
            # Calculate average baseline values
            self.ir_baseline = [s / reading_count for s in readings_sum]
            
            # Set thresholds slightly above baseline
            self.ir_thresholds = [baseline + 0.1 for baseline in self.ir_baseline]
            
            self.logger.info(f"Calibration complete. Baselines: {self.ir_baseline}")
            self.logger.info(f"Thresholds: {self.ir_thresholds}")
        else:
            self.logger.error("Calibration failed - no readings collected")
    
    async def detect_obstacles(self, image: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
        """
        Detect obstacles in camera image using computer vision.
        
        Args:
            image: Optional image to process, otherwise uses latest frame
        
        Returns:
            List of detected obstacles with position and size info
        """
        if image is None:
            image = await self.capture_image()
        
        if image is None:
            return []
        
        obstacles = []
        
        try:
            # Convert to grayscale for processing
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Simple threshold-based obstacle detection
            # This is a basic implementation - could be enhanced with ML models
            _, thresh = cv2.threshold(blurred, 100, 255, cv2.THRESH_BINARY)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Process significant contours as potential obstacles
            for contour in contours:
                area = cv2.contourArea(contour)
                
                if area > 500:  # Minimum area threshold
                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    obstacles.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'area': area,
                        'center_x': x + w // 2,
                        'center_y': y + h // 2
                    })
            
        except Exception as e:
            self.logger.error(f"Error in obstacle detection: {e}")
        
        return obstacles
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current sensor status.
        """
        ir_data = await self.read_ir_sensors()
        line_data = await self.get_line_position()
        
        return {
            'ir_sensors': ir_data,
            'line_position': line_data,
            'camera_available': self.camera is not None,
            'simulation_mode': self.simulation_mode,
            'calibrated': any(t > 0 for t in self.ir_thresholds),
            'timestamp': time.time()
        }
    
    async def update_config(self, settings: Dict[str, Any]):
        """
        Update sensor configuration settings.
        """
        self.logger.info(f"Updating sensor configuration: {settings}")
        
        if 'thresholds' in settings:
            self.ir_thresholds = settings['thresholds']
        
        if 'history_size' in settings:
            self.history_size = settings['history_size']
            # Reset history buffers
            self.ir_history = [[] for _ in range(5)]
