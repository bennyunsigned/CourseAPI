from DB.db import get_db_connection
from Models.paymentModel import ProductPaymentRequest, BundlePaymentRequest, PaymentResponse
from Utils.AES import AESCipher
import mysql.connector
import secrets
import string

def get_or_create_user(name: str, email: str, phone: str) -> int:
    """Check if user exists by email/phone, otherwise create a new user."""
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Check if user already exists
            cursor.execute("SELECT id FROM Users WHERE email = %s OR phone = %s LIMIT 1", (email, phone))
            user = cursor.fetchone()
            if user:
                return user["id"]
            
            # Create a new user with a random password since it's guest checkout
            aes_cipher = AESCipher()
            random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            encrypted_password = aes_cipher.encrypt(random_password)
            
            insert_query = """
                INSERT INTO Users (name, email, password, phone, provider, role, is_activated)
                VALUES (%s, %s, %s, %s, 'local', 'User', 1)
            """
            cursor.execute(insert_query, (name, email, encrypted_password, phone))
            connection.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            raise Exception(f"Database error during user creation: {err}")
        finally:
            if cursor: cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def process_product_payment(data: ProductPaymentRequest) -> PaymentResponse:
    """Process a guest payment for a product."""
    user_id = get_or_create_user(data.name, data.email, data.phone)
    
    amount = data.amount
    if amount is None:
        # Fetch price from ProductMaster
        from Services.productService import get_product_by_id
        product = get_product_by_id(data.product_id)
        amount = product.product_discount_price if product.product_discount_price > 0 else product.product_price

    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO ProductPayment (UserID, ProductID, Amount, PaymentID)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (user_id, data.product_id, amount, data.payment_id))
            connection.commit()
            payment_record_id = cursor.lastrowid
            
            return PaymentResponse(
                message="Product payment recorded successfully",
                user_id=user_id,
                payment_record_id=payment_record_id
            )
        except mysql.connector.Error as err:
            raise Exception(f"Database error recording product payment: {err}")
        finally:
            if cursor: cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def process_bundle_payment(data: BundlePaymentRequest) -> PaymentResponse:
    """Process a guest payment for a bundle."""
    user_id = get_or_create_user(data.name, data.email, data.phone)
    
    amount = data.amount
    if amount is None:
        # Fetch price from BundleMaster
        from Services.bundleService import get_bundle_by_id
        bundle = get_bundle_by_id(data.bundle_id)
        amount = bundle.bundle_discount_price if bundle.bundle_discount_price > 0 else bundle.bundle_price

    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO BundlePayment (UserID, BundleID, Amount, PaymentID)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (user_id, data.bundle_id, amount, data.payment_id))
            connection.commit()
            payment_record_id = cursor.lastrowid
            
            return PaymentResponse(
                message="Bundle payment recorded successfully",
                user_id=user_id,
                payment_record_id=payment_record_id
            )
        except mysql.connector.Error as err:
            raise Exception(f"Database error recording bundle payment: {err}")
        finally:
            if cursor: cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")
