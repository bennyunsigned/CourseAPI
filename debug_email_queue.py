import mysql.connector
import json
import os
from dotenv import load_dotenv

load_dotenv()

def check_queue():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "VidyaRoop"),
            connect_timeout=10
        )
        cur = conn.cursor(dictionary=True)
        
        print("Checking EmailMaster...")
        cur.execute("SELECT EmailId, recipient_email, subject, status, attempts, created_at FROM EmailMaster ORDER BY EmailId DESC LIMIT 10")
        emails = cur.fetchall()
        print(f"Latest 10 emails: {json.dumps(emails, indent=2, default=str)}")
        
        print("\nChecking latest Payments...")
        cur.execute("SELECT id, payment_id, status, payment_type, user_id FROM Payment ORDER BY id DESC LIMIT 5")
        payments = cur.fetchall()
        print(f"Latest 5 payments: {json.dumps(payments, indent=2, default=str)}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_queue()
