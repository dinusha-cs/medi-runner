"""
Computer Vision Service
Handles image processing, sign detection, and visual recognition.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple

try:
    import cv2
    import numpy as np
except ImportError:
    # Mock imports for development
    class MockCV2:
        @staticmethod
        def cvtColor(img, code): return img
        @staticmethod
        def GaussianBlur(img, kernel, sigma): return img
        @staticmethod
        def threshold(img, thresh, max_val, type): return 0, img
        @staticmethod
        def findContours(img, mode, method): return [], []
        @staticmethod
        def contourArea(contour): return 100
        @staticmethod
        def boundingRect(contour): return (0, 0, 50, 50)
        @staticmethod
        def putText(img, text, pos, font, scale, color, thickness): pass
        @staticmethod
        def rectangle(img, pt1, pt2, color, thickness): pass
        
        COLOR_BGR2GRAY = 'gray'
        COLOR_BGR2HSV = 'hsv'
        THRESH_BINARY = 'binary'
        RETR_EXTERNAL = 'external'
        CHAIN_APPROX_SIMPLE = 'simple'
        FONT_HERSHEY_SIMPLEX = 'font'
    
    cv2 = MockCV2()
    
    class MockNumPy:
        @staticmethod
        def zeros(shape, dtype=None): return []
        @staticmethod
        def array(data): return data
        @staticmethod
        def uint8(): return 'uint8'
    
    np = MockNumPy()

from config import CV_SETTINGS, SIMULATION_MODE
from utils.logger import setup_logger


class ComputerVision:
    """
    Computer vision service for sign detection and image analysis.
    """
    
    def __init__(self):
        self.logger = setup_logger('ComputerVision')
        self.simulation_mode = SIMULATION_MODE
        
        # Computer vision settings
        self.sign_confidence = CV_SETTINGS['SIGN_DETECTION_CONFIDENCE']
        self.object_confidence = CV_SETTINGS['OBJECT_DETECTION_CONFIDENCE']
        self.processing_fps = CV_SETTINGS['IMAGE_PROCESSING_FPS']
        
        # Known hospital signs and their meanings
        self.hospital_signs = {
            'emergency': {'action': 'priority_route', 'color': (0, 0, 255)},
            'pharmacy': {'action': 'delivery_point', 'color': (0, 255, 0)},
            'surgery': {'action': 'restricted_area', 'color': (0, 0, 255)},
            'exit': {'action': 'navigation_point', 'color': (255, 0, 0)},
            'elevator': {'action': 'transport_zone', 'color': (255, 255, 0)},
            'stairs': {'action': 'navigation_point', 'color': (128, 128, 128)}
        }
        
        # Processing state
        self.last_processed_frame = None
        self.processing_lock = asyncio.Lock()
        
        # Detection history for smoothing
        self.detection_history = []
        self.history_size = 5
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'signs_detected': 0,
            'objects_detected': 0,
            'processing_time_avg': 0
        }
    
    async def start(self):
        """
        Start the computer vision service.
        """
        self.logger.info("Computer vision service started")
        
        if self.simulation_mode:
            self.logger.info("Running in simulation mode - using mock vision data")
    
    async def stop(self):
        """
        Stop the computer vision service.
        """
        self.logger.info("Computer vision service stopped")
    
    async def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Process camera frame for object and sign detection.
        
        Args:
            frame: Input camera frame
            
        Returns:
            Dictionary containing detection results
        """
        async with self.processing_lock:
            start_time = time.time()
            
            if self.simulation_mode:
                return self._simulate_detections()
            
            try:
                results = {
                    'timestamp': start_time,
                    'signs': await self._detect_signs(frame),
                    'objects': await self._detect_objects(frame),
                    'line_guidance': await self._detect_line_guidance(frame)
                }
                
                # Update statistics
                processing_time = time.time() - start_time
                self.stats['frames_processed'] += 1
                self.stats['processing_time_avg'] = (
                    (self.stats['processing_time_avg'] * (self.stats['frames_processed'] - 1) + processing_time) /
                    self.stats['frames_processed']
                )
                
                # Store for history
                self.detection_history.append(results)
                if len(self.detection_history) > self.history_size:
                    self.detection_history.pop(0)
                
                self.last_processed_frame = frame.copy()
                
                return results
                
            except Exception as e:
                self.logger.error(f"Error processing frame: {e}")
                return {
                    'timestamp': start_time,
                    'signs': [],
                    'objects': [],
                    'line_guidance': None,
                    'error': str(e)
                }
    
    def _simulate_detections(self) -> Dict[str, Any]:
        """
        Generate simulated detection data for testing.
        """
        return {
            'timestamp': time.time(),
            'signs': [
                {
                    'type': 'pharmacy',
                    'confidence': 0.85,
                    'position': {'x': 320, 'y': 240, 'width': 80, 'height': 60},
                    'action': 'delivery_point'
                }
            ],
            'objects': [
                {
                    'type': 'person',
                    'confidence': 0.75,
                    'position': {'x': 200, 'y': 180, 'width': 60, 'height': 120}
                }
            ],
            'line_guidance': {
                'direction': 'straight',
                'confidence': 0.9
            }
        }
    
    async def _detect_signs(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect hospital signs in the frame.
        """
        signs = []
        
        try:
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Detect signs by color and shape
            for sign_type, properties in self.hospital_signs.items():
                detected = await self._detect_sign_by_color(hsv, properties['color'], sign_type)
                if detected:
                    signs.extend(detected)
            
            self.stats['signs_detected'] += len(signs)
            
        except Exception as e:
            self.logger.error(f"Error in sign detection: {e}")
        
        return signs
    
    async def _detect_sign_by_color(self, hsv_frame: np.ndarray, target_color: Tuple[int, int, int], sign_type: str) -> List[Dict[str, Any]]:
        """
        Detect signs of a specific color.
        """
        # This is a simplified color-based detection
        # In practice, you'd use more sophisticated methods or trained models
        
        # Define color range (this needs proper calibration)
        lower_bound = np.array([max(0, target_color[0] - 20), 50, 50])
        upper_bound = np.array([min(179, target_color[0] + 20), 255, 255])
        
        # Create mask
        mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_signs = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area
            if area > CV_SETTINGS['CONTOUR_MIN_AREA']:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate confidence based on area and aspect ratio
                confidence = min(0.95, area / 1000.0)  # Simplified confidence calculation
                
                if confidence > self.sign_confidence:
                    detected_signs.append({
                        'type': sign_type,
                        'confidence': confidence,
                        'position': {'x': x, 'y': y, 'width': w, 'height': h},
                        'action': self.hospital_signs[sign_type]['action'],
                        'area': area
                    })
        
        return detected_signs
    
    async def _detect_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect general objects (people, obstacles, etc.).
        """
        objects = []
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, CV_SETTINGS['GAUSSIAN_BLUR_KERNEL'], 0)
            
            # Simple threshold-based object detection
            # This could be replaced with more sophisticated methods (YOLO, etc.)
            _, thresh = cv2.threshold(blurred, 100, 255, cv2.THRESH_BINARY)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                if area > 1000:  # Minimum size for objects
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Classify object based on dimensions
                    aspect_ratio = w / h
                    object_type = self._classify_object(w, h, aspect_ratio)
                    
                    confidence = min(0.9, area / 5000.0)  # Simplified confidence
                    
                    if confidence > self.object_confidence:
                        objects.append({
                            'type': object_type,
                            'confidence': confidence,
                            'position': {'x': x, 'y': y, 'width': w, 'height': h},
                            'area': area
                        })
            
            self.stats['objects_detected'] += len(objects)
            
        except Exception as e:
            self.logger.error(f"Error in object detection: {e}")
        
        return objects
    
    def _classify_object(self, width: int, height: int, aspect_ratio: float) -> str:
        """
        Simple object classification based on dimensions.
        """
        if 0.3 <= aspect_ratio <= 0.8 and height > 100:
            return 'person'
        elif aspect_ratio > 1.5:
            return 'vehicle'
        elif width > 50 and height > 50:
            return 'obstacle'
        else:
            return 'unknown'
    
    async def _detect_line_guidance(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Detect line guidance information for navigation assistance.
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Focus on bottom third of image for floor lines
            h, w = gray.shape
            roi = gray[int(h * 0.6):h, :]
            
            # Apply threshold to detect dark lines on light floor
            _, thresh = cv2.threshold(roi, 80, 255, cv2.THRESH_BINARY_INV)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Find the largest contour (assumed to be the line)
                largest_contour = max(contours, key=cv2.contourArea)
                
                if cv2.contourArea(largest_contour) > 500:
                    # Calculate line center
                    M = cv2.moments(largest_contour)
                    if M['m00'] != 0:
                        cx = int(M['m10'] / M['m00'])
                        
                        # Determine direction based on line position
                        image_center = w // 2
                        offset = cx - image_center
                        
                        if abs(offset) < 20:
                            direction = 'straight'
                        elif offset < -20:
                            direction = 'turn_right'  # Line is to the left, turn right
                        else:
                            direction = 'turn_left'   # Line is to the right, turn left
                        
                        return {
                            'direction': direction,
                            'offset': offset,
                            'confidence': 0.8,
                            'line_center': cx
                        }
            
        except Exception as e:
            self.logger.error(f"Error in line guidance detection: {e}")
        
        return None
    
    async def annotate_frame(self, frame: np.ndarray, detections: Dict[str, Any]) -> np.ndarray:
        """
        Annotate frame with detection results for visualization.
        """
        annotated = frame.copy()
        
        try:
            # Draw detected signs
            for sign in detections.get('signs', []):
                pos = sign['position']
                x, y, w, h = pos['x'], pos['y'], pos['width'], pos['height']
                
                # Draw bounding box
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Draw label
                label = f"{sign['type']} ({sign['confidence']:.2f})"
                cv2.putText(annotated, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Draw detected objects
            for obj in detections.get('objects', []):
                pos = obj['position']
                x, y, w, h = pos['x'], pos['y'], pos['width'], pos['height']
                
                # Draw bounding box
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 0, 0), 2)
                
                # Draw label
                label = f"{obj['type']} ({obj['confidence']:.2f})"
                cv2.putText(annotated, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            
            # Draw line guidance
            line_guidance = detections.get('line_guidance')
            if line_guidance:
                direction = line_guidance['direction']
                cv2.putText(annotated, f"Direction: {direction}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        except Exception as e:
            self.logger.error(f"Error annotating frame: {e}")
        
        return annotated
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current computer vision status.
        """
        return {
            'simulation_mode': self.simulation_mode,
            'stats': self.stats.copy(),
            'last_processed_time': time.time() if self.last_processed_frame is not None else None,
            'detection_history_size': len(self.detection_history),
            'supported_signs': list(self.hospital_signs.keys()),
            'timestamp': time.time()
        }
    
    async def update_config(self, settings: Dict[str, Any]):
        """
        Update computer vision configuration.
        """
        self.logger.info(f"Updating computer vision configuration: {settings}")
        
        if 'sign_confidence' in settings:
            self.sign_confidence = settings['sign_confidence']
        
        if 'object_confidence' in settings:
            self.object_confidence = settings['object_confidence']
        
        if 'processing_fps' in settings:
            self.processing_fps = settings['processing_fps']
