from DB.db import get_db_connection
import mysql.connector

def check():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Tosh#140695",
            database="VidyaRoop",
            connect_timeout=5
        )
        cursor = connection.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM EmailMaster GROUP BY status")
        print("--- EMAIL STATUS COUNTS ---")
        for row in cursor.fetchall():
            print(row)
            
        cursor.execute("SELECT status, COUNT(*) FROM Payment GROUP BY status")
        print("--- PAYMENT STATUS COUNTS ---")
        for row in cursor.fetchall():
            print(row)
            
        connection.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
