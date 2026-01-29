import cv2
import numpy as np
from datetime import datetime, timedelta

def calculate_eye_aspect_ratio(eye_landmarks):
    """
    Calculate Eye Aspect Ratio (EAR) for blink detection
    """
    # Vertical eye landmarks
    A = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
    B = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))
    
    # Horizontal eye landmark
    C = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))
    
    # EAR calculation
    ear = (A + B) / (2.0 * C)
    return ear

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%I:%M %p')
    except:
        return timestamp_str

def get_time_difference(timestamp_str):
    """Get time difference from now"""
    try:
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        diff = datetime.now() - dt
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return f"{int(seconds)} seconds ago"
        elif seconds < 3600:
            return f"{int(seconds / 60)} minutes ago"
        else:
            return f"{int(seconds / 3600)} hours ago"
    except:
        return "N/A"

def add_text_with_background(frame, text, position, font_scale=0.6, 
                             color=(255, 255, 255), bg_color=(0, 0, 0)):
    """Add text with background for better visibility"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    
    # Get text size
    (text_width, text_height), baseline = cv2.getTextSize(
        text, font, font_scale, thickness
    )
    
    x, y = position
    
    # Draw background rectangle
    cv2.rectangle(
        frame,
        (x, y - text_height - baseline),
        (x + text_width, y + baseline),
        bg_color,
        cv2.FILLED
    )
    
    # Draw text
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)
    
    return frame