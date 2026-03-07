import os
import json
import mock
from fastapi.testclient import TestClient
from app import app
from Services import productService, bundleService, emailService
from DB.db import get_db_connection

client = TestClient(app)

def verify_emails():
    print("--- Starting Email Refinement Verification ---")
    
    # 1. Simulate Bundle Payment
    bundle_id = 1
    payment_id_bundle = "test_bundle_456"
    print(f"Testing Bundle {bundle_id} aggregation...")
    
    try:
        # Mock gateway status
        with mock.patch("Controllers.paymentGatewayController.gateway.get_payment_status") as mock_status:
            mock_status.return_value = {
                "success": True,
                "payment_request": {"id": payment_id_bundle, "status": "Completed"}
            }
            
            # Insert mock payment
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM Payment WHERE payment_id=%s", (payment_id_bundle,))
            cur.execute(
                "INSERT INTO Payment (user_id, payment_id, amount, payment_type, status, bundle_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (1, payment_id_bundle, 500.0, 'bundle', 'created', bundle_id)
            )
            conn.commit()
            
            # Confirm
            resp = client.post("/api/payment-gateway/confirm", json={"payment_id": payment_id_bundle})
            if resp.status_code == 200:
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT * FROM EmailMaster WHERE subject LIKE %s ORDER BY EmailId DESC LIMIT 1", (f"%{payment_id_bundle}%",))
                row = cur.fetchone()
                if row:
                    atts = json.loads(row['attachments'] or "[]")
                    print(f"Bundle Email Subject: {row['subject']}")
                    print(f"Bundle Attachment Count: {len(atts)}")
                    # Verification: Bundle should have multiple attachments if products have them
                else:
                    print("Bundle email record not found!")
            else:
                print(f"Bundle confirm failed: {resp.text}")

    except Exception as e:
        print(f"Error testing bundle: {e}")

    # 2. Simulate Course Payment (Success Image)
    course_id = 1
    payment_id_course = "test_course_789"
    print(f"\nTesting Course {course_id} success image...")
    
    try:
        with mock.patch("Controllers.paymentGatewayController.gateway.get_payment_status") as mock_status:
            mock_status.return_value = {
                "success": True,
                "payment_request": {"id": payment_id_course, "status": "Completed"}
            }
            
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM Payment WHERE payment_id=%s", (payment_id_course,))
            cur.execute(
                "INSERT INTO Payment (user_id, payment_id, amount, payment_type, status, course_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (1, payment_id_course, 1000.0, 'individual', 'created', course_id)
            )
            conn.commit()
            
            resp = client.post("/api/payment-gateway/confirm", json={"payment_id": payment_id_course})
            if resp.status_code == 200:
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT * FROM EmailMaster WHERE subject LIKE %s ORDER BY EmailId DESC LIMIT 1", (f"%{payment_id_course}%",))
                row = cur.fetchone()
                if row:
                    print(f"Course Email Subject: {row['subject']}")
                    has_img = "success_image.png" in row['body']
                    print(f"Course Email has success image: {has_img}")
                else:
                    print("Course email record not found!")
            else:
                print(f"Course confirm failed: {resp.text}")

    except Exception as e:
        print(f"Error testing course: {e}")

    print("\n--- Verification Finished ---")

if __name__ == "__main__":
    verify_emails()
