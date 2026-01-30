"""Check database tables"""
import sqlite3

conn = sqlite3.connect('bank_sampah.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [row[0] for row in cursor.fetchall()]
print("Tables in database:", tables)

if 'users' in tables:
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    print("Columns in users table:", columns)

conn.close()
