import cv2
import face_recognition
import numpy as np
import config

class FaceDetector:
    def __init__(self):
        self.detection_model = config.FACE_DETECTION_MODEL
        self.upsample_times = config.NUMBER_OF_TIMES_TO_UPSAMPLE
    
    def detect_faces(self, frame):
        """
        Detect faces in a frame
        Returns: list of face locations [(top, right, bottom, left), ...]
        """
        # Convert BGR (OpenCV) to RGB (face_recognition)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect face locations
        face_locations = face_recognition.face_locations(
            rgb_frame,
            number_of_times_to_upsample=self.upsample_times,
            model=self.detection_model
        )
        
        return face_locations
    
    def get_face_encodings(self, frame, face_locations=None):
        """
        Generate 128D face encodings for detected faces
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        if face_locations is None:
            face_locations = self.detect_faces(frame)
        
        # Generate encodings
        encodings = face_recognition.face_encodings(
            rgb_frame,
            known_face_locations=face_locations
        )
        
        return encodings
    
    def get_facial_landmarks(self, frame, face_locations=None):
        """
        Get facial landmarks (68 points) for each face
        Useful for blink detection and spoof prevention
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        if face_locations is None:
            face_locations = self.detect_faces(frame)
        
        landmarks = face_recognition.face_landmarks(
            rgb_frame,
            face_locations=face_locations
        )
        
        return landmarks
    
    def draw_face_box(self, frame, face_location, name="Unknown", color=(0, 255, 0)):
        """
        Draw bounding box and label on face
        """
        top, right, bottom, left = face_location
        
        # Draw rectangle
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        
        # Draw label background
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        
        # Draw name text
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)
        
        return frame
    
    def preprocess_frame(self, frame):
        """
        Preprocess frame for better face detection
        Handles lighting variations
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge channels
        lab = cv2.merge([l, a, b])
        
        # Convert back to BGR
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        return enhanced
    
    def resize_frame(self, frame, scale=0.25):
        """
        Resize frame for faster processing
        """
        small_frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
        return small_frame