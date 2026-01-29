import os

# Project paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
FACES_DIR = os.path.join(BASE_DIR, 'registered_faces')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Database
DB_PATH = os.path.join(DATA_DIR, 'attendance.db')
ENCODINGS_PATH = os.path.join(DATA_DIR, 'encodings.pkl')

# Face recognition settings
FACE_RECOGNITION_TOLERANCE = 0.6  # Lower = more strict
FACE_DETECTION_MODEL = 'hog'  # 'hog' or 'cnn' (cnn is more accurate but slower)
NUMBER_OF_TIMES_TO_UPSAMPLE = 1

# Attendance settings
MIN_TIME_BETWEEN_PUNCHES = 30  # seconds - prevent accidental double entries
WORK_START_TIME = "09:00:00"
WORK_END_TIME = "18:00:00"

# Spoof detection settings
ENABLE_BLINK_DETECTION = True
ENABLE_MOVEMENT_DETECTION = True
CONSECUTIVE_FRAMES_FOR_RECOGNITION = 3

# Camera settings
CAMERA_INDEX = 0  # Default camera
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FACES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)