import os
import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

def create_database_if_not_exists():
    """Create the database if it does not exist."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        cursor = connection.cursor()
        db_name = os.getenv("DB_NAME")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"Database '{db_name}' ensured to exist.")
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"Error while creating database: {err}")

def get_db_connection():
    """Establish and return a database connection."""
    create_database_if_not_exists()  # Ensure the database exists before connecting
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        print("Database connection established successfully.")
        return connection
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Error: Invalid username or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Error: Database does not exist")
        else:
            print(err)
        return None

def main():
    """Main function to create the database and check the connection."""
    print("Starting database setup...")
    create_database_if_not_exists()
    connection = get_db_connection()
    if connection:
        print("Database setup completed successfully.")
        connection.close()
    else:
        print("Database setup failed.")

if __name__ == "__main__":
    main()