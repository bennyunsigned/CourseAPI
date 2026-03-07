import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def count_stuff():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "VidyaRoop"),
            connect_timeout=10
        )
        cur = conn.cursor(dictionary=True)
        
        cur.execute("SELECT COUNT(*) as c FROM Payment")
        print(f"Total Payments: {cur.fetchone()['c']}")
        
        cur.execute("SELECT status, COUNT(*) as c FROM Payment GROUP BY status")
        print(f"Payment Statuses: {cur.fetchall()}")
        
        cur.execute("SELECT COUNT(*) as c FROM EmailMaster")
        print(f"Total Emails: {cur.fetchone()['c']}")
        
        cur.execute("SELECT status, COUNT(*) as c FROM EmailMaster GROUP BY status")
        print(f"Email Statuses: {cur.fetchall()}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    count_stuff()
