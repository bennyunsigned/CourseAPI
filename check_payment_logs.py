import mysql.connector
import os
import json
from dotenv import load_dotenv

load_dotenv()

def check_logs():
    try:
        conn = mysql.connector.connect( host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"), database=os.getenv("DB_NAME"), connect_timeout=5 )
        cur = conn.cursor(dictionary=True)
        
        print("Checking PaymentLog...")
        cur.execute("SELECT * FROM PaymentLog ORDER BY id DESC LIMIT 20")
        logs = cur.fetchall()
        print(f"Latest logs: {json.dumps(logs, indent=2, default=str)}")
        
        print("\nChecking Payments...")
        cur.execute("SELECT id, payment_id, status, payment_type, created_at FROM Payment ORDER BY id DESC LIMIT 10")
        payments = cur.fetchall()
        print(f"Latest payments: {json.dumps(payments, indent=2, default=str)}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_logs()
