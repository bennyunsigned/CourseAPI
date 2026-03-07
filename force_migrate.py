import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def force_migrate():
    hosts = ["localhost", "127.0.0.1"]
    connection = None
    
    for host in hosts:
        try:
            print(f"Attempting to connect to {host}...")
            connection = mysql.connector.connect(
                host=host,
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME", "VidyaRoop"),
                connect_timeout=5
            )
            print(f"Connected to {host} successfully.")
            break
        except Exception as e:
            print(f"Failed to connect to {host}: {e}")
            
    if not connection:
        print("Could not connect to database on any host.")
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
            print(f"\nProcessing table: {table}")
            cursor.execute(f"DESCRIBE {table}")
            columns = [row[0].lower() for row in cursor.fetchall()]
            
            if "emailsubject" not in columns:
                print(f"Adding EmailSubject to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN EmailSubject VARCHAR(255) DEFAULT NULL")
            else:
                print(f"EmailSubject already exists in {table}.")
                
            if "emailbody" not in columns:
                print(f"Adding EmailBody to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN EmailBody TEXT DEFAULT NULL")
            else:
                print(f"EmailBody already exists in {table}.")
            
            connection.commit()
            print(f"Table {table} updated.")
            
        print("\nForce migration completed successfully.")
    except Exception as e:
        print(f"Force migration failed: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    force_migrate()
