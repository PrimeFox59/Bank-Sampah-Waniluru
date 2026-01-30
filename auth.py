import streamlit as st
from database import get_connection, hash_password
from datetime import datetime

def log_audit(user_id, action, details=""):
    """Log user actions to audit log"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_log (user_id, action, details)
        VALUES (?, ?, ?)
    ''', (user_id, action, details))
    conn.commit()
    conn.close()

def authenticate_user(username, password):
    """Authenticate user credentials"""
    conn = get_connection()
    cursor = conn.cursor()
    
    hashed_password = hash_password(password)
    cursor.execute('''
        SELECT id, username, full_name, role, active
        FROM users
        WHERE username = ? AND password = ? AND active = 1
    ''', (username, hashed_password))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'username': user[1],
            'full_name': user[2],
            'role': user[3],
            'active': user[4]
        }
    return None

def get_user_by_id(user_id):
    """Get user information by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_all_users(role=None):
    """Get all users, optionally filtered by role"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if role:
        cursor.execute('SELECT * FROM users WHERE role = ? ORDER BY full_name', (role,))
    else:
        cursor.execute('SELECT * FROM users ORDER BY role, full_name')
    
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def create_user(username, password, full_name, role, nik="", address="", phone=""):
    """Create a new user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, password, full_name, nik, address, phone, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, hash_password(password), full_name, nik, address, phone, role))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return True, user_id
    except Exception as e:
        conn.close()
        return False, str(e)

def update_user(user_id, full_name, nik="", address="", phone=""):
    """Update user information"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE users 
            SET full_name = ?, nik = ?, address = ?, phone = ?
            WHERE id = ?
        ''', (full_name, nik, address, phone, user_id))
        conn.commit()
        conn.close()
        return True, "User berhasil diupdate"
    except Exception as e:
        conn.close()
        return False, str(e)

def delete_user(user_id):
    """Delete a user"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return True, "User berhasil dihapus"
    except Exception as e:
        conn.close()
        return False, str(e)

def update_user_password(user_id, new_password):
    """Update user password"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET password = ? WHERE id = ?
    ''', (hash_password(new_password), user_id))
    conn.commit()
    conn.close()

def toggle_user_status(user_id):
    """Toggle user active status"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET active = 1 - active WHERE id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def check_superuser_session():
    """Check if current session is a superuser acting as another user"""
    if 'superuser_original_id' in st.session_state:
        return True
    return False

def start_superuser_session(super_user_id, target_user_id):
    """Start a superuser session acting as another user"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO active_sessions (super_user_id, acting_as_user_id)
        VALUES (?, ?)
    ''', (super_user_id, target_user_id))
    conn.commit()
    conn.close()

def end_superuser_session():
    """End superuser session and return to original account"""
    if 'superuser_original_id' in st.session_state:
        original_user = get_user_by_id(st.session_state['superuser_original_id'])
        st.session_state['user'] = {
            'id': original_user['id'],
            'username': original_user['username'],
            'full_name': original_user['full_name'],
            'role': original_user['role']
        }
        del st.session_state['superuser_original_id']
        del st.session_state['superuser_original_name']
        st.rerun()
