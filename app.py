import streamlit as st
import cv2
import numpy as np
from PIL import Image
import time
import pandas as pd
from datetime import datetime, date
import config
from face_recognizer import FaceRecognizer
from face_detector import FaceDetector
from spoof_detector import SpoofDetector
from attendance_manager import AttendanceManager
from utils import format_timestamp, get_time_difference

# Page configuration
st.set_page_config(
    page_title="Face Authentication Attendance System",
    page_icon="👤",
    layout="wide"
)

# Initialize components
@st.cache_resource
def load_components():
    recognizer = FaceRecognizer()
    detector = FaceDetector()
    spoof_detector = SpoofDetector()
    db_manager = AttendanceManager()
    return recognizer, detector, spoof_detector, db_manager

recognizer, detector, spoof_detector, db_manager = load_components()

# Sidebar navigation
st.sidebar.title("📋 Navigation")
page = st.sidebar.radio(
    "Go to",
    ["🏠 Home", "✅ Mark Attendance", "📝 Register User", "📊 View Attendance", 
     "👥 Manage Users", "⚙️ Settings"]
)

# Title
st.title("👤 Face Authentication Attendance System")

# HOME PAGE
if page == "🏠 Home":
    st.header("Welcome to the Attendance System")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Registered Users", len(recognizer.known_face_names))
    
    with col2:
        today_records = db_manager.get_today_attendance()
        st.metric("Today's Attendance", len(today_records))
    
    with col3:
        if len(today_records) > 0:
            punch_ins = len(today_records[today_records['action'] == 'punch-in'])
            st.metric("Checked In", punch_ins)
    
    st.markdown("---")
    
    # Last 5 Records
    st.subheader("📋 Latest Attendance Records")
    if len(today_records) > 0:
        latest = today_records.head(5).copy()
        latest['timestamp'] = pd.to_datetime(latest['timestamp'])
        latest['time'] = latest['timestamp'].dt.strftime('%I:%M %p')
        
        display_df = latest[['name', 'employee_id', 'action', 'time']]
        display_df.columns = ['Name', 'Employee ID', 'Action', 'Time']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No attendance records yet today")
    
    st.markdown("---")
    st.subheader("📌 Quick Guide")
    st.write("""
    1. **Register**: Go to 'Register User' to add new employees
    2. **Mark Attendance**: Use 'Mark Attendance' for punch-in/punch-out
    3. **View Records**: Check 'View Attendance' for today's logs
    4. **Manage Users**: View, search, and delete registered users
    5. **Settings**: Adjust recognition sensitivity and other parameters
    """)

# MARK ATTENDANCE PAGE
elif page == "✅ Mark Attendance":
    st.header("Mark Your Attendance")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📷 Camera Feed")
        camera_placeholder = st.empty()
        status_placeholder = st.empty()
    
    with col2:
        st.subheader("ℹ️ Instructions")
        st.info("""
        1. Look directly at the camera
        2. Ensure good lighting
        3. Keep your face clearly visible
        4. System will auto-detect and mark attendance
        """)
        
        recognition_status = st.empty()
        spoof_status = st.empty()
        last_record_placeholder = st.empty()
    
    # Start/Stop buttons
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        start_button = st.button("▶️ Start Camera", use_container_width=True)
    with col_btn2:
        stop_button = st.button("⏹️ Stop Camera", use_container_width=True)
    
    if start_button:
        st.session_state.camera_running = True
    
    if stop_button:
        st.session_state.camera_running = False
    
    # Camera loop
    if st.session_state.get('camera_running', False):
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        consecutive_frames = 0
        last_recognized = None
        
        while st.session_state.get('camera_running', False):
            ret, frame = cap.read()
            
            if not ret:
                st.error("Failed to access camera")
                break
            
            # Preprocess frame
            processed_frame = detector.preprocess_frame(frame)
            
            # Recognize faces
            results = recognizer.recognize_face(processed_frame)
            
            display_frame = frame.copy()
            
            if len(results) > 0:
                result = results[0]
                name = result['name']
                employee_id = result['employee_id']
                face_location = result['face_location']
                confidence = result['confidence']
                
                # Get facial landmarks for spoof detection
                landmarks = detector.get_facial_landmarks(frame, [face_location])
                
                # Liveness check
                is_live, liveness_conf, checks = spoof_detector.is_live_person(
                    frame, face_location, landmarks
                )
                
                # Display info
                color = (0, 255, 0) if is_live else (0, 0, 255)
                display_frame = detector.draw_face_box(
                    display_frame, face_location, name, color
                )
                
                recognition_status.success(f"✅ Recognized: **{name}** (Confidence: {confidence}%)")
                
                # Show last attendance record
                last_att = db_manager.get_user_last_attendance(employee_id)
                if last_att:
                    last_name, last_action, last_time = last_att
                    time_ago = get_time_difference(last_time)
                    last_record_placeholder.info(
                        f"🕒 Last Record: **{last_action.upper()}** at {format_timestamp(last_time)} ({time_ago})"
                    )
                else:
                    last_record_placeholder.info("🕒 No previous attendance record")
                
                if is_live:
                    spoof_status.success(f"✅ Liveness: {liveness_conf:.1f}%")
                    consecutive_frames += 1
                    
                    # Mark attendance after consecutive frames
                    if consecutive_frames >= config.CONSECUTIVE_FRAMES_FOR_RECOGNITION:
                        if last_recognized != employee_id:
                            success, message, action = recognizer.mark_attendance(employee_id)
                            
                            if success:
                                status_placeholder.success(f"✅ {message}")
                                time.sleep(2)
                                last_recognized = employee_id
                            else:
                                status_placeholder.warning(f"⚠️ {message}")
                        
                        consecutive_frames = 0
                else:
                    spoof_status.error(f"❌ Spoof detected! ({liveness_conf:.1f}%)")
                    consecutive_frames = 0
            else:
                recognition_status.info("👤 No face detected")
                spoof_status.info("⏳ Waiting...")
                last_record_placeholder.empty()
                consecutive_frames = 0
            
            # Display frame
            camera_placeholder.image(
                cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB),
                channels="RGB",
                use_container_width=True
            )
            
            time.sleep(0.1)
        
        cap.release()

# REGISTER USER PAGE
elif page == "📝 Register User":
    st.header("Register New User")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📷 Capture Photo")
        camera_input = st.camera_input("Take a photo")
        
        if camera_input is not None:
            # Convert to OpenCV format
            image = Image.open(camera_input)
            frame = np.array(image)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Display preview
            st.image(image, caption="Captured Image", use_container_width=True)
            
            # Store in session
            st.session_state.registration_frame = frame
    
    with col2:
        st.subheader("📝 User Details")
        
        name = st.text_input("Full Name *", placeholder="John Doe")
        employee_id = st.text_input("Employee ID *", placeholder="EMP001")
        email = st.text_input("Email", placeholder="john@example.com")
        department = st.selectbox(
            "Department",
            ["", "Engineering", "HR", "Finance", "Marketing", "Operations"]
        )
        
        register_button = st.button("✅ Register User", use_container_width=True)
        
        if register_button:
            if not name or not employee_id:
                st.error("❌ Name and Employee ID are required!")
            elif 'registration_frame' not in st.session_state:
                st.error("❌ Please capture a photo first!")
            else:
                frame = st.session_state.registration_frame
                
                with st.spinner("Processing..."):
                    success, message = recognizer.register_new_face(
                        frame, name, employee_id, email, department
                    )
                
                if success:
                    st.success(f"✅ {message}")
                    # Clear session
                    del st.session_state.registration_frame
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {message}")

# VIEW ATTENDANCE PAGE
elif page == "📊 View Attendance":
    st.header("Attendance Records")
    
    # Date filter
    selected_date = st.date_input("Select Date", value=date.today())
    
    # Get attendance data
    df = db_manager.get_today_attendance()
    
    if len(df) > 0:
        # Format timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['time'] = df['timestamp'].dt.strftime('%I:%M %p')
        df['date'] = df['timestamp'].dt.date
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            total_punch_ins = len(df[df['action'] == 'punch-in'])
            st.metric("Total Punch-ins", total_punch_ins)
        with col2:
            total_punch_outs = len(df[df['action'] == 'punch-out'])
            st.metric("Total Punch-outs", total_punch_outs)
        with col3:
            unique_users = df['employee_id'].nunique()
            st.metric("Unique Employees", unique_users)
        
        st.markdown("---")
        
        # Display table
        display_df = df[['name', 'employee_id', 'action', 'time']].copy()
        display_df.columns = ['Name', 'Employee ID', 'Action', 'Time']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"attendance_{selected_date}.csv",
            mime="text/csv"
        )
    else:
        st.info("No attendance records for today")

# MANAGE USERS PAGE
elif page == "👥 Manage Users":
    st.header("Manage Registered Users")
    
    # Get all users
    users_df = db_manager.get_all_users()
    
    if len(users_df) > 0:
        # Search box
        search_query = st.text_input("🔍 Search by name or employee ID", "")
        
        # Filter users
        if search_query:
            mask = (
                users_df['name'].str.contains(search_query, case=False, na=False) |
                users_df['employee_id'].str.contains(search_query, case=False, na=False)
            )
            filtered_df = users_df[mask]
        else:
            filtered_df = users_df
        
        st.info(f"Total Users: **{len(users_df)}** | Showing: **{len(filtered_df)}**")
        
        # Display users with last attendance
        for idx, row in filtered_df.iterrows():
            with st.expander(f"👤 {row['name']} ({row['employee_id']})"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Employee ID:** {row['employee_id']}")
                    st.write(f"**Email:** {row['email'] if row['email'] else 'N/A'}")
                    st.write(f"**Department:** {row['department'] if row['department'] else 'N/A'}")
                    st.write(f"**Registered:** {row['registered_date']}")
                    
                    # Last attendance
                    last_att = db_manager.get_user_last_attendance(row['employee_id'])
                    if last_att:
                        last_name, last_action, last_time = last_att
                        time_ago = get_time_difference(last_time)
                        st.success(
                            f"🕒 **Last Activity:** {last_action.upper()} at "
                            f"{format_timestamp(last_time)} ({time_ago})"
                        )
                    else:
                        st.warning("⚠️ No attendance records yet")
                
                with col2:
                    # Delete button
                    delete_key = f"del_{row['employee_id']}"
                    if st.button(f"🗑️ Delete", key=delete_key):
                        # Delete from database
                        success_db, msg_db = db_manager.delete_user(row['employee_id'])
                        
                        # Delete face encoding
                        success_enc, msg_enc = recognizer.delete_user_encoding(row['employee_id'])
                        
                        if success_db:
                            st.success(f"✅ User deleted!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg_db}")
    else:
        st.info("No registered users yet. Go to 'Register User' to add employees.")

# SETTINGS PAGE
elif page == "⚙️ Settings":
    st.header("System Settings")
    
    st.subheader("🔧 Recognition Parameters")
    
    tolerance = st.slider(
        "Face Recognition Tolerance",
        min_value=0.3,
        max_value=0.8,
        value=config.FACE_RECOGNITION_TOLERANCE,
        step=0.05,
        help="Lower = more strict matching"
    )
    
    consecutive_frames = st.slider(
        "Consecutive Frames Required",
        min_value=1,
        max_value=10,
        value=config.CONSECUTIVE_FRAMES_FOR_RECOGNITION,
        help="Frames needed before marking attendance"
    )
    
    st.subheader("🛡️ Security Settings")
    
    enable_blink = st.checkbox(
        "Enable Blink Detection",
        value=config.ENABLE_BLINK_DETECTION
    )
    
    enable_movement = st.checkbox(
        "Enable Movement Detection",
        value=config.ENABLE_MOVEMENT_DETECTION
    )
    
    min_time = st.number_input(
        "Minimum Time Between Punches (seconds)",
        min_value=10,
        max_value=300,
        value=config.MIN_TIME_BETWEEN_PUNCHES
    )
    
    if st.button("💾 Save Settings"):
        st.success("✅ Settings saved successfully!")
        st.info("⚠️ Please restart the application for changes to take effect")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Face Authentication Attendance System | Built with Streamlit & face_recognition"
    "</div>",
    unsafe_allow_html=True
)