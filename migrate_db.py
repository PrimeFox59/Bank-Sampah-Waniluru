"""
Migration script to add NIK, address, and phone fields to users table
"""

import sqlite3

DATABASE_NAME = 'bank_sampah.db'

def migrate_database():
    """Add new columns to users table"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    
    print(f"Current columns: {columns}")
    
    # Add NIK column if not exists
    if 'nik' not in columns:
        print("Adding 'nik' column...")
        cursor.execute('ALTER TABLE users ADD COLUMN nik TEXT DEFAULT ""')
        print("✓ Added 'nik' column")
    
    # Add address column if not exists
    if 'address' not in columns:
        print("Adding 'address' column...")
        cursor.execute('ALTER TABLE users ADD COLUMN address TEXT DEFAULT ""')
        print("✓ Added 'address' column")
    
    # Add phone column if not exists
    if 'phone' not in columns:
        print("Adding 'phone' column...")
        cursor.execute('ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ""')
        print("✓ Added 'phone' column")
    
    conn.commit()
    
    # Update default users with sample data
    print("\nUpdating default users with sample NIK and address...")
    updates = [
        ('3201234567890001', 'Jl. Raya Pengepul No. 123, Jakarta', '081234567890', 'pengepul1'),
        ('3201234567890002', 'Jl. Admin Indah No. 45, Jakarta', '081234567891', 'panitia1'),
        ('3201234567890003', 'Jl. Warga Sejahtera No. 10, Jakarta', '081234567892', 'warga1'),
        ('3201234567890004', 'Jl. Mawar Melati No. 25, Jakarta', '081234567893', 'warga2'),
    ]
    
    for nik, address, phone, username in updates:
        cursor.execute('''
            UPDATE users 
            SET nik = ?, address = ?, phone = ?
            WHERE username = ?
        ''', (nik, address, phone, username))
        print(f"✓ Updated {username}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration completed successfully!")

if __name__ == '__main__':
    migrate_database()
