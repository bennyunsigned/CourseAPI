from DB.db import get_db_connection
import json

def debug():
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return
    try:
        cursor = connection.cursor(dictionary=True)
        # Check last 10 payments
        print("\n--- LAST 10 PAYMENTS ---")
        cursor.execute("SELECT id, payment_id, user_id, amount, payment_type, status, product_id, bundle_id, course_id FROM Payment ORDER BY id DESC LIMIT 10")
        for row in cursor.fetchall():
            print(row)
        
        # Check last 10 emails
        print("\n--- LAST 10 EMAILS ---")
        cursor.execute("SELECT EmailId, recipient_email, subject, status, attempts, created_at FROM EmailMaster ORDER BY EmailId DESC LIMIT 10")
        for row in cursor.fetchall():
            print(row)
            
        # Check tables existence
        print("\n--- SCHEMA CHECK ---")
        for t in ["ProductMaster", "BundleMaster", "CourseMaster", "SubscriptionPlan"]:
            cursor.execute(f"SHOW COLUMNS FROM {t} LIKE 'EmailSubject'")
            has_sub = cursor.fetchone() is not None
            cursor.execute(f"SHOW COLUMNS FROM {t} LIKE 'EmailBody'")
            has_body = cursor.fetchone() is not None
            print(f"Table {t}: EmailSubject={has_sub}, EmailBody={has_body}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    debug()
