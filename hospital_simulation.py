#!/usr/bin/env python3
"""
Enhanced 2D Robot Simulation with Hospital Environment
Visual pygame-based simulation for the Medi Runner robot
"""

import pygame
import json
import math
import time
import asyncio
# import websocket  # Optional - commented out for now
import threading
from typing import Dict, List, Tuple

# Initialize Pygame
pygame.init()

class HospitalEnvironment:
    """Hospital environment with rooms, corridors, and obstacles"""
    
    def __init__(self):
        self.rooms = [
            {"id": "base", "name": "Base Station", "x": 50, "y": 50, "width": 40, "height": 30, "color": (100, 150, 100)},
            {"id": "pharmacy", "name": "Pharmacy", "x": 200, "y": 100, "width": 50, "height": 35, "color": (100, 100, 200)},
            {"id": "101", "name": "Room 101", "x": 400, "y": 80, "width": 45, "height": 30, "color": (200, 150, 100)},
            {"id": "102", "name": "Room 102", "x": 400, "y": 150, "width": 45, "height": 30, "color": (200, 150, 100)},
            {"id": "surgery", "name": "Surgery", "x": 300, "y": 250, "width": 60, "height": 40, "color": (200, 100, 100)},
            {"id": "icu", "name": "ICU", "x": 500, "y": 200, "width": 70, "height": 50, "color": (150, 100, 200)}
        ]
        
        self.corridors = [
            {"start": (50, 120), "end": (600, 120), "width": 20},  # Main horizontal corridor
            {"start": (150, 50), "end": (150, 300), "width": 20},   # Vertical corridor 1
            {"start": (350, 80), "end": (350, 290), "width": 20},   # Vertical corridor 2
            {"start": (480, 180), "end": (480, 250), "width": 15}   # ICU access corridor
        ]
        
        self.obstacles = [
            {"x": 180, "y": 140, "width": 15, "height": 10, "type": "chair", "color": (139, 69, 19)},
            {"x": 280, "y": 105, "width": 20, "height": 8, "type": "equipment", "color": (105, 105, 105)},
            {"x": 420, "y": 190, "width": 12, "height": 12, "type": "cart", "color": (160, 160, 160)}
        ]
        
        self.scale_factor = 2.0  # Scale for display

class Robot:
    """Robot representation with physics simulation"""
    
    def __init__(self, x=60, y=65):
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0  # degrees
        self.speed = 0.0
        self.angular_speed = 0.0
        
        # Robot physical properties
        self.width = 12
        self.height = 8
        self.sensor_range = 50
        
        # Status
        self.battery = 85.0
        self.status = "idle"
        self.mission = None
        
        # Trail for path visualization
        self.trail = []
        self.max_trail_length = 100

    def update(self, dt):
        """Update robot position based on current speed"""
        if self.speed != 0 or self.angular_speed != 0:
            # Update angle
            self.angle += self.angular_speed * dt
            self.angle = self.angle % 360
            
            # Update position
            rad_angle = math.radians(self.angle)
            self.x += self.speed * math.cos(rad_angle) * dt
            self.y += self.speed * math.sin(rad_angle) * dt
            
            # Add to trail
            self.trail.append((self.x, self.y))
            if len(self.trail) > self.max_trail_length:
                self.trail.pop(0)
            
            # Simulate battery drain
            self.battery = max(0, self.battery - 0.001 * dt)

class RobotSimulationGUI:
    """Main simulation window with hospital environment"""
    
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Medi Runner Robot Simulation")
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.BLUE = (0, 0, 255)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.GRAY = (128, 128, 128)
        self.LIGHT_GRAY = (200, 200, 200)
        self.DARK_BLUE = (0, 0, 139)
        
        # Initialize components
        self.environment = HospitalEnvironment()
        self.robot = Robot()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Camera/viewport
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        
        # GUI state
        self.running = True
        self.paused = False
        self.show_sensors = True
        self.show_trail = True
        
        # WebSocket connection (optional)
        self.ws_connected = False
        self.ws_thread = None
        
    def draw_environment(self):
        """Draw the hospital environment"""
        scale = self.environment.scale_factor * self.zoom
        
        # Draw floor
        self.screen.fill(self.LIGHT_GRAY)
        
        # Draw corridors
        for corridor in self.environment.corridors:
            start_x = (corridor["start"][0] - self.camera_x) * scale
            start_y = (corridor["start"][1] - self.camera_y) * scale
            end_x = (corridor["end"][0] - self.camera_x) * scale
            end_y = (corridor["end"][1] - self.camera_y) * scale
            
            pygame.draw.line(self.screen, self.WHITE, 
                           (start_x, start_y), (end_x, end_y), 
                           int(corridor["width"] * scale))
        
        # Draw rooms
        for room in self.environment.rooms:
            x = (room["x"] - self.camera_x) * scale
            y = (room["y"] - self.camera_y) * scale
            w = room["width"] * scale
            h = room["height"] * scale
            
            # Room rectangle
            pygame.draw.rect(self.screen, room["color"], (x, y, w, h))
            pygame.draw.rect(self.screen, self.BLACK, (x, y, w, h), 2)
            
            # Room label
            text = self.small_font.render(room["name"], True, self.BLACK)
            self.screen.blit(text, (x + 5, y + 5))
        
        # Draw obstacles
        for obstacle in self.environment.obstacles:
            x = (obstacle["x"] - self.camera_x) * scale
            y = (obstacle["y"] - self.camera_y) * scale
            w = obstacle["width"] * scale
            h = obstacle["height"] * scale
            
            pygame.draw.rect(self.screen, obstacle["color"], (x, y, w, h))
            pygame.draw.rect(self.screen, self.BLACK, (x, y, w, h), 1)
    
    def draw_robot(self):
        """Draw the robot with sensors and status"""
        scale = self.environment.scale_factor * self.zoom
        
        # Robot position on screen
        screen_x = (self.robot.x - self.camera_x) * scale
        screen_y = (self.robot.y - self.camera_y) * scale
        
        # Draw trail
        if self.show_trail and len(self.robot.trail) > 1:
            trail_points = []
            for px, py in self.robot.trail[-20:]:  # Show last 20 points
                sx = (px - self.camera_x) * scale
                sy = (py - self.camera_y) * scale
                trail_points.append((sx, sy))
            
            if len(trail_points) > 1:
                pygame.draw.lines(self.screen, (100, 150, 255), False, trail_points, 2)
        
        # Robot body
        robot_points = self._get_robot_corners(screen_x, screen_y, scale)
        pygame.draw.polygon(self.screen, self.BLUE, robot_points)
        pygame.draw.polygon(self.screen, self.BLACK, robot_points, 2)
        
        # Direction indicator
        dir_length = 20 * scale
        end_x = screen_x + dir_length * math.cos(math.radians(self.robot.angle))
        end_y = screen_y + dir_length * math.sin(math.radians(self.robot.angle))
        pygame.draw.line(self.screen, self.RED, (screen_x, screen_y), (end_x, end_y), 3)
        
        # Sensors (if enabled)
        if self.show_sensors:
            self._draw_sensors(screen_x, screen_y, scale)
        
        # Robot status text
        status_text = f"Battery: {self.robot.battery:.1f}% | Status: {self.robot.status}"
        text_surface = self.font.render(status_text, True, self.BLACK)
        self.screen.blit(text_surface, (10, 10))
        
        # Position text
        pos_text = f"Pos: ({self.robot.x:.1f}, {self.robot.y:.1f}) | Angle: {self.robot.angle:.1f}°"
        pos_surface = self.small_font.render(pos_text, True, self.BLACK)
        self.screen.blit(pos_surface, (10, 35))
    
    def _get_robot_corners(self, center_x, center_y, scale):
        """Get robot corner points for drawing"""
        w = self.robot.width * scale / 2
        h = self.robot.height * scale / 2
        angle = math.radians(self.robot.angle)
        
        # Local corners
        corners = [(-w, -h), (w, -h), (w, h), (-w, h)]
        
        # Rotate and translate
        rotated_corners = []
        for x, y in corners:
            rx = x * math.cos(angle) - y * math.sin(angle) + center_x
            ry = x * math.sin(angle) + y * math.cos(angle) + center_y
            rotated_corners.append((rx, ry))
        
        return rotated_corners
    
    def _draw_sensors(self, center_x, center_y, scale):
        """Draw sensor range visualization"""
        sensor_range = self.robot.sensor_range * scale
        
        # Ultrasonic sensor (forward)
        end_x = center_x + sensor_range * math.cos(math.radians(self.robot.angle))
        end_y = center_y + sensor_range * math.sin(math.radians(self.robot.angle))
        pygame.draw.line(self.screen, (0, 255, 0), (center_x, center_y), (end_x, end_y), 1)
        
        # Line sensors (left, center, right)
        for angle_offset in [-30, 0, 30]:
            sensor_angle = self.robot.angle + angle_offset
            sensor_length = 25 * scale
            sx = center_x + sensor_length * math.cos(math.radians(sensor_angle))
            sy = center_y + sensor_length * math.sin(math.radians(sensor_angle))
            pygame.draw.line(self.screen, (255, 255, 0), (center_x, center_y), (sx, sy), 1)
    
    def draw_controls(self):
        """Draw control instructions"""
        controls = [
            "Controls:",
            "W/S - Forward/Backward",
            "A/D - Turn Left/Right",
            "SPACE - Stop",
            "R - Reset Position",
            "T - Toggle Trail",
            "ESC - Exit"
        ]
        
        y_offset = self.height - len(controls) * 20 - 10
        for i, control in enumerate(controls):
            color = self.BLACK if i == 0 else self.GRAY
            text = self.small_font.render(control, True, color)
            self.screen.blit(text, (10, y_offset + i * 18))
    
    def handle_input(self):
        """Handle keyboard input for robot control"""
        keys = pygame.key.get_pressed()
        
        # Movement controls
        if keys[pygame.K_w]:
            self.robot.speed = 40  # Forward
            self.robot.status = "moving forward"
        elif keys[pygame.K_s]:
            self.robot.speed = -30  # Backward
            self.robot.status = "moving backward"
        else:
            self.robot.speed = 0
        
        # Turning controls
        if keys[pygame.K_a]:
            self.robot.angular_speed = -60  # Turn left
            if self.robot.status == "idle":
                self.robot.status = "turning left"
        elif keys[pygame.K_d]:
            self.robot.angular_speed = 60   # Turn right
            if self.robot.status == "idle":
                self.robot.status = "turning right"
        else:
            self.robot.angular_speed = 0
        
        # Stop
        if keys[pygame.K_SPACE]:
            self.robot.speed = 0
            self.robot.angular_speed = 0
            self.robot.status = "stopped"
        
        # Reset position
        if keys[pygame.K_r]:
            self.robot.x = 60
            self.robot.y = 65
            self.robot.angle = 0
            self.robot.trail.clear()
            self.robot.status = "reset"
        
        # Update status when idle
        if self.robot.speed == 0 and self.robot.angular_speed == 0 and self.robot.status not in ["stopped", "reset"]:
            self.robot.status = "idle"
    
    def run(self):
        """Main simulation loop"""
        print("🚀 Starting Hospital Robot Simulation")
        print("Controls: W/A/S/D for movement, SPACE to stop, ESC to exit")
        
        while self.running:
            dt = self.clock.tick(60) / 1000.0  # 60 FPS
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_t:
                        self.show_trail = not self.show_trail
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
            
            if not self.paused:
                # Handle input and update robot
                self.handle_input()
                self.robot.update(dt)
                
                # Update camera to follow robot
                self.camera_x = self.robot.x - self.width / (2 * self.environment.scale_factor * self.zoom)
                self.camera_y = self.robot.y - self.height / (2 * self.environment.scale_factor * self.zoom)
            
            # Draw everything
            self.draw_environment()
            self.draw_robot()
            self.draw_controls()
            
            # Display pause status
            if self.paused:
                pause_text = self.font.render("PAUSED - Press P to resume", True, self.RED)
                self.screen.blit(pause_text, (self.width//2 - 100, self.height//2))
            
            pygame.display.flip()
        
        pygame.quit()
        print("✅ Simulation ended")

def main():
    """Launch the robot simulation"""
    print("🏥 Medi Runner Hospital Robot Simulation")
    print("=========================================")
    
    try:
        simulation = RobotSimulationGUI(width=1000, height=700)
        simulation.run()
    except KeyboardInterrupt:
        print("🛑 Simulation interrupted")
    except Exception as e:
        print(f"❌ Simulation error: {e}")

if __name__ == "__main__":
    main()