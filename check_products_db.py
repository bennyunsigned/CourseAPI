import os
import mysql.connector
from dotenv import load_dotenv
load_dotenv()

def check_db():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        cursor = conn.cursor(dictionary=True)
        
        print("--- Table Structure ---")
        cursor.execute("DESCRIBE ProductMaster")
        for row in cursor.fetchall():
            print(row)
            
        print("\n--- Table Content (All) ---")
        cursor.execute("SELECT * FROM ProductMaster")
        rows = cursor.fetchall()
        print(f"Total records found: {len(rows)}")
        for row in rows:
            print(row)
            
        print("\n--- Table Content (Active Only) ---")
        cursor.execute("SELECT * FROM ProductMaster WHERE IsActive = TRUE")
        rows_active = cursor.fetchall()
        print(f"Active records found: {len(rows_active)}")
        for row in rows_active:
            print(row)
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
