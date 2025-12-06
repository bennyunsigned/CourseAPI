import mysql.connector
import sys
import os

# quick hack to import DB
sys.path.append(os.getcwd())
from DB.db import get_db_connection

def check_columns():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect")
        return
    cursor = conn.cursor()
    cursor.execute("DESCRIBE Users")
    for row in cursor.fetchall():
        print(row)
    conn.close()

if __name__ == "__main__":
    check_columns()
