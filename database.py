import sqlite3
import hashlib
from datetime import datetime
import os

DATABASE_NAME = 'bank_sampah.db'

def get_connection():
    """Create database connection"""
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_database():
    """Initialize database with all required tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            nik TEXT,
            address TEXT,
            phone TEXT,
            role TEXT NOT NULL CHECK(role IN ('superuser', 'pengepul', 'panitia', 'warga')),
            balance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1
        )
    ''')
    
    # Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price_per_kg REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            warga_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            weight_kg REAL NOT NULL,
            price_per_kg REAL NOT NULL,
            total_amount REAL NOT NULL,
            committee_fee REAL NOT NULL,
            net_amount REAL NOT NULL,
            processed_by INTEGER NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (warga_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (processed_by) REFERENCES users(id)
        )
    ''')
    
    # Deposits/Withdrawals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financial_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            warga_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('deposit', 'withdrawal')),
            amount REAL NOT NULL,
            balance_before REAL NOT NULL,
            balance_after REAL NOT NULL,
            processed_by INTEGER NOT NULL,
            movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (warga_id) REFERENCES users(id),
            FOREIGN KEY (processed_by) REFERENCES users(id)
        )
    ''')
    
    # Committee earnings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS committee_earnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            earned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
    ''')
    
    # Audit log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Session table for super user login as other users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            super_user_id INTEGER NOT NULL,
            acting_as_user_id INTEGER NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (super_user_id) REFERENCES users(id),
            FOREIGN KEY (acting_as_user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_default_users():
    """Create default users for each role"""
    conn = get_connection()
    cursor = conn.cursor()
    
    default_users = [
        ('superuser', 'admin123', 'Super Administrator', 'superuser', '', '', ''),
        ('pengepul1', 'pengepul123', 'Pengepul Utama', 'pengepul', '3201234567890001', 'Jl. Raya Pengepul No. 123, Jakarta', '081234567890'),
        ('panitia1', 'panitia123', 'Panitia Koordinator', 'panitia', '3201234567890002', 'Jl. Panitia Indah No. 45, Jakarta', '081234567891'),
        ('warga1', 'warga123', 'Warga Contoh 1', 'warga', '3201234567890003', 'Jl. Warga Sejahtera No. 10, Jakarta', '081234567892'),
        ('warga2', 'warga123', 'Warga Contoh 2', 'warga', '3201234567890004', 'Jl. Mawar Melati No. 25, Jakarta', '081234567893'),
    ]
    
    for username, password, full_name, role, nik, address, phone in default_users:
        try:
            cursor.execute('''
                INSERT INTO users (username, password, full_name, role, nik, address, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, hash_password(password), full_name, role, nik, address, phone))
        except sqlite3.IntegrityError:
            # User already exists
            pass
    
    conn.commit()
    conn.close()

def create_default_categories():
    """Create default waste categories"""
    conn = get_connection()
    cursor = conn.cursor()
    
    default_categories = [
        ('Plastik Botol', 3000),
        ('Plastik Kemasan', 2000),
        ('Kardus', 1500),
        ('Kertas', 1000),
        ('Kaleng Aluminium', 5000),
        ('Besi', 2500),
        ('Kaca', 500),
    ]
    
    for name, price in default_categories:
        try:
            cursor.execute('''
                INSERT INTO categories (name, price_per_kg)
                VALUES (?, ?)
            ''', (name, price))
        except sqlite3.IntegrityError:
            # Category already exists
            pass
    
    conn.commit()
    conn.close()

def initialize_system():
    """Complete system initialization"""
    init_database()
    create_default_users()
    create_default_categories()
    print("Database initialized successfully!")

if __name__ == '__main__':
    initialize_system()
