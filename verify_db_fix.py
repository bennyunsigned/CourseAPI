import os
import mysql.connector
from DB.db import get_db_connection

def verify():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect")
        return
    
    try:
        cursor = conn.cursor()
        
        # Check ProductMaster
        cursor.execute("SHOW TABLES LIKE 'ProductMaster'")
        if cursor.fetchone():
            print("OK: ProductMaster table exists")
        else:
            print("FAIL: ProductMaster table MISSING")
            
        # Check is_activated column
        cursor.execute("DESCRIBE Users")
        columns = [row[0] for row in cursor.fetchall()]
        if 'is_activated' in columns:
            print("OK: is_activated column exists in Users")
        else:
            print("FAIL: is_activated column MISSING in Users")
            
        # Check Stored Procedure
        cursor.execute("SHOW PROCEDURE STATUS WHERE Name = 'GetCartProductsByUser'")
        if cursor.fetchone():
            print("OK: GetCartProductsByUser procedure exists")
        else:
            print("FAIL: GetCartProductsByUser procedure MISSING")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    verify()
