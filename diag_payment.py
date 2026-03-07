from DB.db import get_db_connection
import os

def debug():
    connection = get_db_connection()
    if not connection:
        return
    try:
        cursor = connection.cursor(dictionary=True)
        print("\n--- PAYMENT TABLE SCHEMA ---")
        cursor.execute("DESCRIBE Payment")
        for row in cursor.fetchall():
            print(row)
            
        print("\n--- RECENT PAYMENTS ---")
        cursor.execute("SELECT * FROM Payment ORDER BY id DESC LIMIT 5")
        for row in cursor.fetchall():
            print(row)
    except Exception as e:
        # Try PaymentId if id fails
        try:
            cursor.execute("SELECT * FROM Payment ORDER BY PaymentId DESC LIMIT 5")
            for row in cursor.fetchall():
                print(row)
        except:
             print(f"Error: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    debug()
