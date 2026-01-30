"""
Simple test script to verify the new features
"""

from database import get_connection, initialize_system
from auth import create_user, update_user, delete_user, get_all_users

# Initialize system
print("=== Initializing System ===")
initialize_system()
print("✓ System initialized")

# Test get_all_users
print("\n=== Testing get_all_users ===")
all_users = get_all_users()
print(f"Total users: {len(all_users)}")
for user in all_users:
    print(f"- {user['username']}: {user['full_name']} ({user['role']})")
    if user.get('nik'):
        print(f"  NIK: {user['nik']}, Phone: {user.get('phone', '-')}")

# Test get warga only
print("\n=== Testing get warga only ===")
warga_users = get_all_users('warga')
print(f"Total warga: {len(warga_users)}")
for user in warga_users:
    print(f"- {user['full_name']}: NIK={user.get('nik', 'N/A')}, Address={user.get('address', 'N/A')[:30]}...")

# Test create_user with new fields
print("\n=== Testing create_user with NIK and Address ===")
success, result = create_user(
    'testwarga1',
    'test123',
    'Test Warga Baru',
    'warga',
    '3201234567890099',
    'Jl. Testing No. 999, Jakarta Selatan',
    '08123456789'
)
if success:
    print(f"✓ User created successfully: ID={result}")
    
    # Verify
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (result,))
    user = dict(cursor.fetchone())
    conn.close()
    print(f"  Verified: {user['full_name']}, NIK={user['nik']}, Phone={user['phone']}")
    
    # Test update_user
    print("\n=== Testing update_user ===")
    success2, msg = update_user(
        result,
        'Test Warga Updated',
        '3201234567890100',
        'Jl. Updated Street No. 1000, Jakarta',
        '08199999999'
    )
    if success2:
        print(f"✓ {msg}")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (result,))
        user_updated = dict(cursor.fetchone())
        conn.close()
        print(f"  Verified: {user_updated['full_name']}, NIK={user_updated['nik']}")
    
    # Test delete_user
    print("\n=== Testing delete_user ===")
    success3, msg = delete_user(result)
    if success3:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")
else:
    print(f"✗ Failed to create user: {result}")

print("\n=== All Tests Completed ===")
