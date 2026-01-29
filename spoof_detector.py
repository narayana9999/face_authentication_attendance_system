import cv2
import numpy as np
from scipy.spatial import distance as dist
import config

class SpoofDetector:
    def __init__(self):
        self.EYE_AR_THRESHOLD = 0.25  # Below this = blink detected
        self.BLINK_FRAMES = 2  # Consecutive frames for valid blink
        self.blink_counter = 0
        self.total_blinks = 0
        self.movement_history = []
        self.MOVEMENT_THRESHOLD = 10  # Pixels
    
    def calculate_eye_aspect_ratio(self, eye_points):
        """
        Calculate Eye Aspect Ratio (EAR)
        eye_points: list of (x, y) tuples for eye landmarks
        """
        if len(eye_points) < 6:
            return 0.3  # Default value
        
        # Vertical distances
        A = dist.euclidean(eye_points[1], eye_points[5])
        B = dist.euclidean(eye_points[2], eye_points[4])
        
        # Horizontal distance
        C = dist.euclidean(eye_points[0], eye_points[3])
        
        # EAR formula
        ear = (A + B) / (2.0 * C)
        return ear
    
    def detect_blink(self, facial_landmarks):
        """
        Detect if person blinked
        Returns: (is_blinking, total_blinks)
        """
        if not facial_landmarks or len(facial_landmarks) == 0:
            return False, self.total_blinks
        
        landmarks = facial_landmarks[0]
        
        # Get eye landmarks
        left_eye = landmarks.get('left_eye', [])
        right_eye = landmarks.get('right_eye', [])
        
        if not left_eye or not right_eye:
            return False, self.total_blinks
        
        # Calculate EAR for both eyes
        left_ear = self.calculate_eye_aspect_ratio(left_eye)
        right_ear = self.calculate_eye_aspect_ratio(right_eye)
        
        # Average EAR
        ear = (left_ear + right_ear) / 2.0
        
        # Check if blinking
        is_blinking = False
        
        if ear < self.EYE_AR_THRESHOLD:
            self.blink_counter += 1
        else:
            if self.blink_counter >= self.BLINK_FRAMES:
                self.total_blinks += 1
                is_blinking = True
            self.blink_counter = 0
        
        return is_blinking, self.total_blinks
    
    def detect_movement(self, face_location):
        """
        Detect if face has moved (not a static photo)
        """
        if face_location is None:
            return False
        
        top, right, bottom, left = face_location
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        
        # Store movement history
        self.movement_history.append((center_x, center_y))
        
        # Keep only last 10 positions
        if len(self.movement_history) > 10:
            self.movement_history.pop(0)
        
        # Check if there's movement
        if len(self.movement_history) < 5:
            return False
        
        # Calculate variance in positions
        positions = np.array(self.movement_history)
        variance = np.var(positions, axis=0)
        
        # If variance is above threshold, movement detected
        has_moved = np.any(variance > self.MOVEMENT_THRESHOLD)
        
        return has_moved
    
    def check_texture_analysis(self, frame, face_location):
        """
        Simple texture analysis to detect print/screen photos
        Real faces have more texture variation
        """
        top, right, bottom, left = face_location
        
        # Extract face region
        face_region = frame[top:bottom, left:right]
        
        if face_region.size == 0:
            return False
        
        # Convert to grayscale
        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        
        # Calculate Laplacian variance (measure of blur/sharpness)
        laplacian_var = cv2.Laplacian(gray_face, cv2.CV_64F).var()
        
        # Real faces typically have higher variance (more detail)
        # Photos/screens tend to be blurry
        TEXTURE_THRESHOLD = 100
        
        is_real = laplacian_var > TEXTURE_THRESHOLD
        
        return is_real
    
    def check_color_analysis(self, frame, face_location):
        """
        Analyze color distribution
        Real faces have specific color characteristics
        """
        top, right, bottom, left = face_location
        face_region = frame[top:bottom, left:right]
        
        if face_region.size == 0:
            return False
        
        # Convert to HSV
        hsv_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV)
        
        # Check skin color range
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        skin_mask = cv2.inRange(hsv_face, lower_skin, upper_skin)
        skin_ratio = np.sum(skin_mask > 0) / skin_mask.size
        
        # Real faces should have significant skin color
        SKIN_THRESHOLD = 0.3
        
        return skin_ratio > SKIN_THRESHOLD
    
    def is_live_person(self, frame, face_location, facial_landmarks):
        """
        Comprehensive liveness check
        Returns: (is_live, confidence_score, details)
        """
        checks = {
            'texture': False,
            'color': False,
            'movement': False,
            'blink': False
        }
        
        # Texture analysis
        if config.ENABLE_MOVEMENT_DETECTION:
            checks['texture'] = self.check_texture_analysis(frame, face_location)
            checks['color'] = self.check_color_analysis(frame, face_location)
            checks['movement'] = self.detect_movement(face_location)
        
        # Blink detection
        if config.ENABLE_BLINK_DETECTION and facial_landmarks:
            is_blinking, total_blinks = self.detect_blink(facial_landmarks)
            checks['blink'] = total_blinks > 0
        
        # Calculate confidence
        passed_checks = sum(checks.values())
        total_checks = len(checks)
        confidence = (passed_checks / total_checks) * 100
        
        # Need at least 50% checks to pass
        is_live = confidence >= 50
        
        return is_live, confidence, checks
    
    def reset(self):
        """Reset counters"""
        self.blink_counter = 0
        self.total_blinks = 0
        self.movement_history = []