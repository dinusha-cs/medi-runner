# Robot Server Configuration
# Copy this file to config.py and adjust values as needed

# WebSocket Server Settings
WS_HOST = '0.0.0.0'  # Listen on all interfaces
WS_PORT = 8765
WS_MAX_CONNECTIONS = 10

# Camera Settings
CAMERA_RESOLUTION = (640, 480)
CAMERA_FPS = 30
CAMERA_ROTATION = 0
CAMERA_BRIGHTNESS = 50
CAMERA_CONTRAST = 50

# GPIO Pin Assignments (BCM numbering)
GPIO_PINS = {
    # Motor Driver (L298N)
    'MOTOR_IN1': 17,
    'MOTOR_IN2': 27,
    'MOTOR_IN3': 22,
    'MOTOR_IN4': 23,
    'MOTOR_ENA': 24,
    'MOTOR_ENB': 25,
    
    # IR Sensor Array
    'IR_SENSOR_1': 6,   # Far left
    'IR_SENSOR_2': 12,  # Left
    'IR_SENSOR_3': 13,  # Center
    'IR_SENSOR_4': 19,  # Right
    'IR_SENSOR_5': 16,  # Far right
    
    # Audio
    'BUZZER': 5,
    
    # Additional sensors (optional)
    'ULTRASONIC_TRIG': 20,
    'ULTRASONIC_ECHO': 21
}

# Motor Control Settings
MOTOR_SETTINGS = {
    'PWM_FREQUENCY': 1000,  # Hz
    'MAX_SPEED': 100,
    'MIN_SPEED': 30,
    'TURN_SPEED': 60,
    'ACCELERATION_STEP': 5,
    'DECELERATION_STEP': 10
}

# Line Following Parameters
LINE_FOLLOWING = {
    'BASE_SPEED': 50,
    'TURN_SPEED': 40,
    'SHARP_TURN_SPEED': 30,
    'CORRECTION_FACTOR': 0.8,
    'LOST_LINE_TIMEOUT': 2.0,  # seconds
    'INTERSECTION_DELAY': 1.0   # seconds
}

# Computer Vision Settings
CV_SETTINGS = {
    'SIGN_DETECTION_CONFIDENCE': 0.7,
    'OBJECT_DETECTION_CONFIDENCE': 0.5,
    'IMAGE_PROCESSING_FPS': 10,
    'CONTOUR_MIN_AREA': 100,
    'GAUSSIAN_BLUR_KERNEL': (5, 5)
}

# Communication Settings
COMMUNICATION = {
    'HEARTBEAT_INTERVAL': 5.0,  # seconds
    'COMMAND_TIMEOUT': 10.0,    # seconds
    'RECONNECT_ATTEMPTS': 5,
    'RECONNECT_DELAY': 2.0      # seconds
}

# Safety Settings
SAFETY = {
    'EMERGENCY_STOP_ENABLED': True,
    'OBSTACLE_DETECTION_DISTANCE': 20,  # cm
    'MAX_OPERATION_TIME': 3600,         # seconds (1 hour)
    'BATTERY_LOW_THRESHOLD': 20,        # percentage
    'TEMPERATURE_THRESHOLD': 70         # Celsius
}

# Logging Configuration
LOGGING = {
    'LEVEL': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'FILE': 'robot.log',
    'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
    'BACKUP_COUNT': 3
}

# Development/Debug Settings
DEBUG = True
SIMULATION_MODE = False  # Set to True for development without hardware
VERBOSE_LOGGING = False

# Mission Settings
MISSION = {
    'MAX_WAYPOINTS': 50,
    'WAYPOINT_TOLERANCE': 10,   # cm
    'DEFAULT_SPEED': 50,
    'PAUSE_DURATION': 1.0,      # seconds at waypoints
    'MAX_MISSION_TIME': 1800    # seconds (30 minutes)
}

# AI Model Paths (if using custom models)
AI_MODELS = {
    'SIGN_DETECTION': 'models/sign_detection.tflite',
    'OBJECT_DETECTION': 'models/object_detection.tflite',
    'LINE_DETECTION': 'models/line_detection.tflite'
}
