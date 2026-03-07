from DB.db import get_db_connection
import json

def diag():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect")
        return
    try:
        cur = conn.cursor(dictionary=True)
        # Check specific payment ID from user
        print("Checking payment 'plink_SLdkY9dEWEaVOy'...")
        cur.execute("SELECT * FROM Payment WHERE payment_id='plink_SLdkY9dEWEaVOy'")
        row = cur.fetchone()
        if row:
            print(f"Found: {row}")
        else:
            print("Not found in Payment table.")

        # Check latest 5 payments
        print("\nLatest 5 payments:")
        cur.execute("SELECT * FROM Payment ORDER BY id DESC LIMIT 5")
        rows = cur.fetchall()
        for r in rows:
            print(r)
            
        cur.close()
    finally:
        conn.close()

if __name__ == '__main__':
    diag()
