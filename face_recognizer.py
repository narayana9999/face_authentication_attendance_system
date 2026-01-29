import os
import pickle
import face_recognition
import cv2
import numpy as np
from datetime import datetime
import config
from face_detector import FaceDetector
from attendance_manager import AttendanceManager

class FaceRecognizer:
    def __init__(self):
        self.detector = FaceDetector()
        self.db_manager = AttendanceManager()
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_employee_ids = []
        self.tolerance = config.FACE_RECOGNITION_TOLERANCE
        self.load_encodings()
    
    def load_encodings(self):
        """Load face encodings from pickle file"""
        if os.path.exists(config.ENCODINGS_PATH):
            try:
                with open(config.ENCODINGS_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data.get('encodings', [])
                    self.known_face_names = data.get('names', [])
                    self.known_employee_ids = data.get('employee_ids', [])
                print(f"Loaded {len(self.known_face_encodings)} face encodings")
            except Exception as e:
                print(f"Error loading encodings: {e}")
        else:
            print("No existing encodings found. Starting fresh.")
    
    def save_encodings(self):
        """Save face encodings to pickle file"""
        data = {
            'encodings': self.known_face_encodings,
            'names': self.known_face_names,
            'employee_ids': self.known_employee_ids
        }
        
        with open(config.ENCODINGS_PATH, 'wb') as f:
            pickle.dump(data, f)
        
        print("Encodings saved successfully")
    
    def register_new_face(self, frame, name, employee_id, email=None, department=None):
        """
        Register a new user's face
        Captures multiple images and stores average encoding
        """
        # Register user in database first
        user_id, message = self.db_manager.register_user(name, employee_id, email, department)
        
        if user_id is None:
            return False, message
        
        # Detect face in frame
        face_locations = self.detector.detect_faces(frame)
        
        if len(face_locations) == 0:
            return False, "No face detected. Please ensure your face is visible."
        
        if len(face_locations) > 1:
            return False, "Multiple faces detected. Please ensure only one person is in frame."
        
        # Get face encoding
        encodings = self.detector.get_face_encodings(frame, face_locations)
        
        if len(encodings) == 0:
            return False, "Could not generate face encoding. Please try again."
        
        encoding = encodings[0]
        
        # Add to known faces
        self.known_face_encodings.append(encoding)
        self.known_face_names.append(name)
        self.known_employee_ids.append(employee_id)
        
        # Save face image
        face_dir = os.path.join(config.FACES_DIR, employee_id)
        os.makedirs(face_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = os.path.join(face_dir, f"{timestamp}.jpg")
        cv2.imwrite(image_path, frame)
        
        # Save encodings
        self.save_encodings()
        
        return True, f"User {name} registered successfully!"
    
    def recognize_face(self, frame):
        """
        Recognize faces in the frame
        Returns: list of (name, employee_id, face_location, distance)
        """
        if len(self.known_face_encodings) == 0:
            return []
        
        # Detect faces
        face_locations = self.detector.detect_faces(frame)
        
        if len(face_locations) == 0:
            return []
        
        # Get encodings for detected faces
        face_encodings = self.detector.get_face_encodings(frame, face_locations)
        
        results = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Compare with known faces
            matches = face_recognition.compare_faces(
                self.known_face_encodings,
                face_encoding,
                tolerance=self.tolerance
            )
            
            name = "Unknown"
            employee_id = None
            
            # Calculate face distances
            face_distances = face_recognition.face_distance(
                self.known_face_encodings,
                face_encoding
            )
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
                    employee_id = self.known_employee_ids[best_match_index]
                    distance = face_distances[best_match_index]
                    
                    results.append({
                        'name': name,
                        'employee_id': employee_id,
                        'face_location': face_location,
                        'distance': distance,
                        'confidence': round((1 - distance) * 100, 2)
                    })
        
        return results
    
    def mark_attendance(self, employee_id):
        """
        Automatically determine and mark punch-in or punch-out
        """
        # Get last attendance record
        last_record = self.db_manager.get_last_attendance(employee_id)
        
        # Determine action
        if last_record is None:
            action = "punch-in"
        else:
            last_action, last_time = last_record
            # If last was punch-in, now do punch-out and vice versa
            action = "punch-out" if last_action == "punch-in" else "punch-in"
        
        # Mark attendance
        success, message = self.db_manager.mark_attendance(employee_id, action)
        
        return success, message, action
    
    def delete_user_encoding(self, employee_id):
        """Remove user's face encoding"""
        try:
            if employee_id in self.known_employee_ids:
                index = self.known_employee_ids.index(employee_id)
                
                # Remove from lists
                del self.known_face_encodings[index]
                del self.known_face_names[index]
                del self.known_employee_ids[index]
                
                # Save updated encodings
                self.save_encodings()
                
                # Delete face images
                import shutil
                face_dir = os.path.join(config.FACES_DIR, employee_id)
                if os.path.exists(face_dir):
                    shutil.rmtree(face_dir)
                
                return True, "Face encoding deleted"
            else:
                return False, "User encoding not found"
        except Exception as e:
            return False, f"Error: {str(e)}"