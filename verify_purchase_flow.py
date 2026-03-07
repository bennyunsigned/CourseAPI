import os
import json
import mock
from fastapi.testclient import TestClient
from app import app
from Services import productService, emailService
from DB.db import get_db_connection

client = TestClient(app)

def test_purchase_flow_with_custom_email():
    # 1. Setup a test product with custom email settings
    test_product_id = 1 # Assuming a product with ID 1 exists or create one
    try:
        product = productService.get_product_by_id(test_product_id)
    except:
        # Create dummy if not exists
        from Models.productModel import ProductRequest
        product = productService.create_product(ProductRequest(
            product_name="Test Verification Product",
            product_price=100.0,
            product_discount_price=90.0,
            product_description="Test Description",
            product_content="Test Content",
            product_image="test.jpg",
            is_active=True,
            email_subject="Success: {{item_name}}",
            email_body="Hello {{user_name}}, thanks for buying {{item_name}}. Payment: {{payment_id}}"
        ))
        test_product_id = product.product_id

    # 2. Mock Gateway and confirm_payment
    # Instead of full mock, we can just call confirm_payment logic if we mock the gateway.get_payment_status
    
    payment_id = "test_pay_123"
    
    # Mocking gateway.get_payment_status in paymentGatewayController
    with mock.patch("Controllers.paymentGatewayController.gateway.get_payment_status") as mock_status:
        mock_status.return_value = {
            "success": True,
            "payment_request": {
                "id": payment_id,
                "status": "Completed"
            }
        }
        
        # We also need an intent row in Payment table
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM Payment WHERE payment_id=%s", (payment_id,))
        cur.execute(
            "INSERT INTO Payment (user_id, payment_id, amount, payment_type, status, product_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (1, payment_id, 90.0, 'product', 'created', test_product_id)
        )
        conn.commit()
        cur.close()
        conn.close()

        # 3. Call confirmation endpoint
        response = client.post("/api/payment-gateway/confirm", json={"payment_id": payment_id})
        assert response.status_code == 200
        
        # 4. Verify email in EmailMaster
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM EmailMaster WHERE subject LIKE %s ORDER BY id DESC LIMIT 1", (f"%{payment_id}%",))
        email_row = cur.fetchone()
        
        if email_row:
            print("Email Subject:", email_row['subject'])
            print("Email Body snippet:", email_row['body'][:100])
            assert f"{payment_id}" in email_row['body']
            assert "Test Verification Product" in email_row['subject'] or "Test Verification Product" in email_row['body']
        else:
            print("Email record not found!")
            assert False
        
        cur.close()
        conn.close()
        print("Verification successful!")

if __name__ == "__main__":
    try:
        test_purchase_flow_with_custom_email()
    except Exception as e:
        print(f"Verification failed: {e}")
