import RPi.GPIO as GPIO
import time
import subprocess

# --- PIN DEFINITIONS (From your image) ---
# Right Motor (Motor B)
IN1, IN2, ENB = 23, 22, 16
# Left Motor (Motor A)
IN3, IN4, ENA = 27, 17, 20

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup([IN1, IN2, IN3, IN4, ENA, ENB], GPIO.OUT)

# Initialize PWM for speed control
pwm_a = GPIO.PWM(ENA, 100)
pwm_b = GPIO.PWM(ENB, 100)
pwm_a.start(0)
pwm_b.start(0)

# --- MOVEMENT FUNCTIONS ---

def move_forward(speed):
    """Both motors spin forward"""
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    pwm_a.ChangeDutyCycle(speed)
    pwm_b.ChangeDutyCycle(speed)

def move_backward(speed):
    """Both motors spin backward"""
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_a.ChangeDutyCycle(speed)
    pwm_b.ChangeDutyCycle(speed)

def turn_left(speed):
    """Pivot right (Left wheel moves, Right wheel stops)"""
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    pwm_a.ChangeDutyCycle(speed)
    pwm_b.ChangeDutyCycle(0)

def turn_right(speed):
    """Pivot left (Right wheel moves, Left wheel stops)"""
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_a.ChangeDutyCycle(0)
    pwm_b.ChangeDutyCycle(speed)

def stop(duration=0):
    """Cuts power to motors"""
    pwm_a.ChangeDutyCycle(0)
    pwm_b.ChangeDutyCycle(0)
    GPIO.output([IN1, IN2, IN3, IN4], GPIO.LOW)
    if duration > 0:
        time.sleep(duration)

def take_snapshot():
    """Captures a photo using rpicam-still"""
    print("📸 Taking snapshot...")
    # Saves a photo named 'mission_capture.jpg'
    subprocess.run(["rpicam-still", "-o", "mission_capture.jpg", "--timeout", "1000"])
    print("Snapshot saved.")

# --- MISSION SEQUENCE ---

try:
    print("Mission Started.")
    move_forward(60)
    time.sleep(1)

    stop(1)

    move_backward(60)
    time.sleep(1)
    
    # # 2 seconds forward
    # move_forward(60)
    # time.sleep(1)
    
    # # Stop for 1 second
    # stop(1)
    
    # # # Turn right for 2 seconds
    # turn_right(60)
    # time.sleep(1) 

    # stop(1)

    # move_forward(60)
    # time.sleep(2)

    # stop(1)

    # turn_left(60)
    # time.sleep(1)

    # stop(1)

    # move_forward(60)
    # time.sleep(2)

    # stop(1)

    # #SS
    # take_snapshot()

    # move_backward(60)
    # time.sleep(2)

    # stop()
    # print("Mission Finished Successfully.")

    # # take_snapshot()


except KeyboardInterrupt:
    print("\nMission interrupted by user.")
finally:
    pwm_a.stop()
    pwm_b.stop()
    GPIO.cleanup()