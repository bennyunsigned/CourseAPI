
import mysql.connector
import sys
import os
import time
from datetime import datetime, timedelta

# quick hack to import DB
sys.path.append(os.getcwd())
from DB.db import get_db_connection
from Services.authService import cleanup_unactivated_users

def verify():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect DB")
        return

    cur = conn.cursor()
    # Insert OLD unactivated user
    old_email = "test_cleanup_old@example.com"
    cur.execute("DELETE FROM Users WHERE email = %s", (old_email,)) # cleanup previous run
    cur.execute("DELETE FROM Users WHERE email = 'test_cleanup_new@example.com'")
    conn.commit()

    print(f"Inserting old user: {old_email}")
    cur.execute("""
        INSERT INTO Users (name, email, password, phone, provider, role, is_activated, created_at)
        VALUES ('Test Old', %s, 'pass', '123', 'local', 'User', 0, NOW() - INTERVAL 30 MINUTE)
    """, (old_email,))
    
    # Insert NEW unactivated user
    new_email = "test_cleanup_new@example.com"
    print(f"Inserting new user: {new_email}")
    cur.execute("""
        INSERT INTO Users (name, email, password, phone, provider, role, is_activated, created_at)
        VALUES ('Test New', %s, 'pass', '123', 'local', 'User', 0, NOW())
    """, (new_email,))
    conn.commit()

    # Run Cleanup
    print("Running cleanup...")
    deleted = cleanup_unactivated_users()
    print(f"Deleted count: {deleted}")

    # Verify
    cur.execute("SELECT email FROM Users WHERE email IN (%s, %s)", (old_email, new_email))
    remaining = [r[0] for r in cur.fetchall()]
    print(f"Remaining users: {remaining}")

    if old_email not in remaining and new_email in remaining:
        print("SUCCESS: Old user deleted, new user kept.")
    else:
        print("FAILURE: Incorrect cleanup result.")
        if old_email in remaining:
            print(f" - Old user {old_email} was NOT deleted.")
        if new_email not in remaining:
            print(f" - New user {new_email} WAS deleted.")

    # Cleanup test data
    cur.execute("DELETE FROM Users WHERE email = %s", (new_email,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    verify()
