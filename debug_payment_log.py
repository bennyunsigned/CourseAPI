import os
import sys
from DB.db import get_db_connection

def fetch_logs():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to DB")
        return

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM PaymentLog ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        for row in rows:
            print(f"[{row['event_time']}] {row['level']} - {row['step']}: {row['message']}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fetch_logs()
