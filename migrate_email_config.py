import os
import mysql.connector
from DB.db import get_db_connection

def migrate():
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database.")
        return

    tables_to_update = [
        "ProductMaster",
        "BundleMaster",
        "CourseMaster",
        "SubscriptionPlan"
    ]

    try:
        cursor = connection.cursor()
        for table in tables_to_update:
            print(f"Checking table {table}...")
            
            # Check if EmailSubject already exists
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'EmailSubject'")
            if not cursor.fetchone():
                print(f"Adding EmailSubject to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN EmailSubject VARCHAR(255) DEFAULT NULL")
            
            # Check if EmailBody already exists
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'EmailBody'")
            if not cursor.fetchone():
                print(f"Adding EmailBody to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN EmailBody TEXT DEFAULT NULL")
            
        connection.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    migrate()
