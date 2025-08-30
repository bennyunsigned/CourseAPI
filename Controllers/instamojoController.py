

from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel
from instamojo_wrapper import Instamojo
import mysql.connector
from DB.db import get_db_connection

router = APIRouter(prefix="/instamojo", tags=["Instamojo"])


# Initialize Instamojo API (replace with your API key and Auth token)
API_KEY = 'YOUR_API_KEY'
AUTH_TOKEN = 'YOUR_AUTH_TOKEN'
API_URL = 'https://www.instamojo.com/api/1.1/'
api = Instamojo(api_key=API_KEY, auth_token=AUTH_TOKEN, endpoint=API_URL)


class PaymentRequest(BaseModel):
    amount: float
    purpose: str
    buyer_name: str = ""
    email: str = ""
    phone: str = ""
    redirect_url: str = ""
    payment_type: str # 'individual' or 'subscription'
    user_id: int
    course_id: int = None # Only for individual purchase
    subscription_type: str = None # Only for subscription





@router.post("/payment/create", status_code=status.HTTP_201_CREATED)
async def create_payment(data: PaymentRequest):
    try:
        response = api.payment_request_create(
            amount=str(data.amount),
            purpose=data.purpose,
            buyer_name=data.buyer_name,
            email=data.email,
            phone=data.phone,
            redirect_url=data.redirect_url
        )
        # Track payment intent in Payment table
        connection = get_db_connection()
        cursor = connection.cursor()
        query = """
            INSERT INTO Payment (user_id, payment_id, amount, payment_type, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (data.user_id, response['payment_request']['id'], data.amount, data.payment_type, 'created'))
        connection.commit()
        cursor.close()
        connection.close()
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payment/confirm", status_code=status.HTTP_200_OK)
async def confirm_payment(payment_id: str = Body(...), payment_type: str = Body(...), user_id: int = Body(...), course_id: int = Body(None), subscription_type: str = Body(None), amount: float = Body(None)):
    """
    Call this endpoint after payment is successful (webhook or redirect handler).
    Also updates Payment table status.
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        # Update payment status
        cursor.execute("UPDATE Payment SET status='success' WHERE payment_id=%s", (payment_id,))
        if payment_type == 'individual' and course_id:
            query = """
                INSERT INTO UserCoursePurchase (user_id, course_id, payment_id)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (user_id, course_id, payment_id))
        elif payment_type == 'subscription' and subscription_type:
            query = """
                INSERT INTO UserSubscription (user_id, subscription_type, payment_id)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (user_id, subscription_type, payment_id))
        else:
            raise HTTPException(status_code=400, detail="Invalid payment type or missing data.")
        connection.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if connection:
            cursor.close()
            connection.close()

# Get all payment records for a user
@router.get("/payment/user/{user_id}")
async def get_user_payments(user_id: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Payment WHERE user_id=%s", (user_id,))
        payments = cursor.fetchall()
        return payments
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if connection:
            cursor.close()
            connection.close()

# Call procedure to get all user purchase and subscription details
@router.get("/user/details/{user_id}")
async def get_user_purchase_and_subscription_details(user_id: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.callproc('GetUserPurchaseAndSubscriptionDetails', [user_id])
        results = []
        for result in cursor.stored_results():
            results.append(result.fetchall())
        return {
            "subscriptions": results[0] if len(results) > 0 else [],
            "purchased_courses": results[1] if len(results) > 1 else []
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if connection:
            cursor.close()
            connection.close()

@router.get("/payment/status/{payment_request_id}")
async def get_payment_status(payment_request_id: str):
    try:
        response = api.payment_request_status(payment_request_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/payment/list")
async def list_payments():
    try:
        response = api.payment_requests_list()
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/payment/delete/{payment_request_id}")
async def delete_payment(payment_request_id: str):
    try:
        response = api.payment_request_delete(payment_request_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


