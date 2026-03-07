from DB.db import get_db_connection
import os

def run_sql_file(file_path):
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database.")
        return

    try:
        cursor = connection.cursor()
        with open(file_path, 'r') as f:
            sql = f.read()
        
        # Split by semicolon to execute one by one
        commands = sql.split(';')
        for command in commands:
            if command.strip():
                cursor.execute(command)
        
        connection.commit()
        print("SQL script executed successfully.")
    except Exception as e:
        print(f"Error executing SQL: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    schema_path = os.path.join(os.path.dirname(__file__), "DB", "bundle_schema.sql")
    run_sql_file(schema_path)
