import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import pytz
import config

class AttendanceManager:
    def __init__(self):
        self.db_path = config.DB_PATH
        self.timezone = pytz.timezone('Asia/Kolkata')  # IST timezone
        self.init_database()
    
    def get_current_time(self):
        """Get current time in IST"""
        return datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S')
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                employee_id TEXT UNIQUE NOT NULL,
                email TEXT,
                department TEXT,
                registered_date TEXT
            )
        ''')
        
        # Attendance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                employee_id TEXT,
                action TEXT CHECK(action IN ('punch-in', 'punch-out')),
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_user(self, name, employee_id, email=None, department=None):
        """Register a new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            current_time = self.get_current_time()
            cursor.execute('''
                INSERT INTO users (name, employee_id, email, department, registered_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, employee_id, email, department, current_time))
            conn.commit()
            user_id = cursor.lastrowid
            return user_id, "User registered successfully"
        except sqlite3.IntegrityError:
            return None, "Employee ID already exists"
        finally:
            conn.close()
    
    def get_last_attendance(self, employee_id):
        """Get last attendance record for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT action, timestamp FROM attendance
            WHERE employee_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (employee_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result
    
    def mark_attendance(self, employee_id, action):
        """Mark punch-in or punch-out"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user_id
        cursor.execute('SELECT user_id FROM users WHERE employee_id = ?', (employee_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return False, "User not found"
        
        user_id = user[0]
        
        # Check for recent entries (prevent duplicates)
        last_record = self.get_last_attendance(employee_id)
        if last_record:
            last_time = datetime.strptime(last_record[1], '%Y-%m-%d %H:%M:%S')
            current_time = datetime.now(self.timezone).replace(tzinfo=None)
            time_diff = (current_time - last_time).total_seconds()
            
            if time_diff < config.MIN_TIME_BETWEEN_PUNCHES:
                conn.close()
                return False, f"Please wait {int(config.MIN_TIME_BETWEEN_PUNCHES - time_diff)} seconds"
        
        # Insert attendance record with IST time
        current_time = self.get_current_time()
        cursor.execute('''
            INSERT INTO attendance (user_id, employee_id, action, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (user_id, employee_id, action, current_time))
        
        conn.commit()
        conn.close()
        return True, f"{action.capitalize()} recorded successfully"
    
    def get_user_by_employee_id(self, employee_id):
        """Get user details"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE employee_id = ?', (employee_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def get_today_attendance(self):
        """Get all attendance records for today (IST)"""
        conn = sqlite3.connect(self.db_path)
        
        # Get today's date in IST
        today_date = datetime.now(self.timezone).strftime('%Y-%m-%d')
        
        query = f'''
            SELECT u.name, u.employee_id, a.action, a.timestamp
            FROM attendance a
            JOIN users u ON a.user_id = u.user_id
            WHERE DATE(a.timestamp) = DATE('{today_date}')
            ORDER BY a.timestamp DESC
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def delete_user(self, employee_id):
        """Delete a user and all their attendance records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if user exists
            cursor.execute('SELECT user_id, name FROM users WHERE employee_id = ?', (employee_id,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return False, "User not found"
            
            user_id, name = user
            
            # Delete attendance records
            cursor.execute('DELETE FROM attendance WHERE user_id = ?', (user_id,))
            
            # Delete user
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            
            return True, f"User {name} deleted successfully"
        except Exception as e:
            conn.close()
            return False, f"Error deleting user: {str(e)}"
    
    def get_all_users(self):
        """Get all registered users"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT user_id, name, employee_id, email, department, registered_date
            FROM users
            ORDER BY name
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_user_last_attendance(self, employee_id):
        """Get detailed last attendance for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.name, a.action, a.timestamp
            FROM attendance a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.employee_id = ?
            ORDER BY a.timestamp DESC
            LIMIT 1
        ''', (employee_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result