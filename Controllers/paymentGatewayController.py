from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel
from Services.PaymentGateway import get_payment_gateway
import os
import logging
import mysql.connector
from datetime import datetime, timedelta
import calendar
from DB.db import get_db_connection
from Services import emailService, productService, bundleService, courseService
from Utils.ExceptionHandler import log_exception_to_file
from Services.paymentService import get_or_create_user
import json

router = APIRouter(tags=["Payment Gateway"])

# Initialize Payment Gateway (Factory decides implementation based on env)
gateway = get_payment_gateway()

# basic logger
logger = logging.getLogger("paymentGateway")
if not logger.handlers:
    logging.basicConfig()

# Moving table init to app startup to avoid locks

def log_payment_event(payment_id: str | None, level: str, step: str, message: str) -> None:
    """Insert a log record into PaymentLog."""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO PaymentLog (payment_id, level, step, message) VALUES (%s, %s, %s, %s)",
            (payment_id, level, step, message)
        )
        connection.commit()
    except Exception as e:
        logger.exception("Failed to write payment log: %s", e)
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass

def _get_user_email(user_id: int) -> str:
    """Return user's email from Users table."""
    try:
        conn = get_db_connection()
        if not conn: return ""
        cur = conn.cursor()
        cur.execute("SELECT email FROM Users WHERE id=%s", (user_id,))
        r = cur.fetchone()
        cur.close()
        conn.close()
        if r: return r[0] or ""
    except: pass
    return ""

class PaymentRequest(BaseModel):
    amount: float = 0 
    purpose: str
    buyer_name: str = ""
    email: str = ""
    phone: str = ""
    redirect_url: str = ""
    payment_type: str # 'individual', 'subscription', 'product', 'bundle'
    user_id: int = None 
    course_id: int = None 
    subscription_type: str = None 
    product_id: int = None 
    bundle_id: int = None 

@router.post("/payment/create", status_code=status.HTTP_201_CREATED)
async def create_payment(data: PaymentRequest):
    try:
        log_payment_event(None, 'INFO', 'create_payment.start', f'Request: user_id={data.user_id}, amount={data.amount}, purpose={data.purpose}, type={data.payment_type}')
        
        user_id = data.user_id
        if data.payment_type in ('product', 'bundle') and not user_id:
            user_id = get_or_create_user(data.buyer_name, data.email, data.phone)

        amount = data.amount
        if not amount or amount == 0:
            if data.payment_type == 'product' and data.product_id:
                product = productService.get_product_by_id(data.product_id)
                amount = product.product_discount_price if product.product_discount_price > 0 else product.product_price
            elif data.payment_type == 'bundle' and data.bundle_id:
                bundle = bundleService.get_bundle_by_id(data.bundle_id)
                amount = bundle.bundle_discount_price if bundle.bundle_discount_price > 0 else bundle.bundle_price

        response = gateway.create_payment_request(
            amount=str(amount),
            purpose=data.purpose,
            buyer_name=data.buyer_name,
            email=data.email,
            phone=data.phone,
            redirect_url=data.redirect_url
        )

        payment_req = response.get('payment_request') if isinstance(response, dict) else None
        if not payment_req:
            logger.error("Gateway payment create failed: %s", response)
            log_payment_event(None, 'ERROR', 'create_payment.gateway_error', str(response))
            error_msg = response.get('message') if isinstance(response, dict) else 'Unknown Gateway error'
            raise HTTPException(status_code=400, detail=f"Gateway error: {error_msg}")

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            query = """
                INSERT INTO Payment (user_id, payment_id, amount, payment_type, status, course_id, subscription_type, product_id, bundle_id, email, buyer_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (user_id, payment_req['id'], amount, data.payment_type, 'created', data.course_id, data.subscription_type, data.product_id, data.bundle_id, data.email, data.buyer_name))
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        log_payment_event(payment_req['id'], 'INFO', 'create_payment.db_insert', 'Inserted payment intent')
        return response
    except HTTPException: raise
    except Exception as e:
        logger.exception("Error creating payment")
        log_payment_event(None, 'ERROR', 'create_payment.exception', str(e))
        log_exception_to_file(e, context='create_payment')
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/payment/confirm", status_code=status.HTTP_200_OK)
async def confirm_payment(payment_id: str = Body(...), payment_type: str = Body(None), user_id: int = Body(None), amount: float = Body(None)):
    connection = get_db_connection()
    try:
        log_payment_event(payment_id, 'INFO', 'confirm_payment.start', f'Confirming payment for {payment_id}')
        logger.info(f"Confirming payment: id={payment_id}, type={payment_type}, user={user_id}, amount={amount}")
        
        # Try different column names for compatibility
        cursor_fetch = connection.cursor(dictionary=True)
        # Search by payment_id (Standard)
        # Actually, if Razorpay, we stored plink_id in 'payment_id' column during creation (Line 115)
        cursor_fetch.execute("SELECT * FROM Payment WHERE payment_id=%s", (payment_id,))
        row = cursor_fetch.fetchone()
        cursor_fetch.close()
        
        if row:
            # Prioritize database values to avoid misidentification by frontend
            db_payment_type = row.get('payment_type')
            if db_payment_type:
                logger.info(f"Payment {payment_id} identified as {db_payment_type} from DB (Frontend sent: {payment_type})")
                payment_type = db_payment_type
            else:
                payment_type = payment_type or "individual" # Default
                
            user_id = user_id or row.get('user_id') or row.get('UserId')
            amount = amount or row.get('amount') or row.get('AmountPaid')
            course_id = row.get('course_id') or row.get('CourseId')
            subscription_type = row.get('subscription_type')
            product_id = row.get('product_id')
            bundle_id = row.get('bundle_id')
            email_from_db = row.get('email')
            # Extract buyer name if available
            user_name_from_db = row.get('buyer_name') or row.get('BuyerName') or "Customer"
            logger.info(f"Retrieved from DB: user={user_id}, amount={amount}, type={payment_type}, item_id={product_id or bundle_id or course_id}")
        else:
            raise HTTPException(status_code=404, detail="Payment intent not found")

        status_resp = gateway.get_payment_status(payment_id)
        payment_request = status_resp.get('payment_request') if isinstance(status_resp, dict) else None
        
        is_successful = False
        status_str = "Unknown"
        if payment_request:
            status_str = payment_request.get('status') or (payment_request.get('payment', {}) or {}).get('status')
            if str(status_str).lower() in ('completed', 'success', 'credit', 'paid'):
                is_successful = True
            else:
                payments = payment_request.get('payments', [])
                if isinstance(payments, list):
                    for p in payments:
                        if str(p.get('status')).lower() in ('completed', 'success', 'credit', 'paid'):
                            is_successful = True
                            status_str = p.get('status')
                            break

        if not is_successful:
            cursor = connection.cursor()
            cursor.execute("UPDATE Payment SET status=%s WHERE payment_id=%s", (str(status_str), payment_id))
            connection.commit()
            cursor.close()
            
            # Queue failure email
            recipient = email_from_db or _get_user_email(user_id)
            emailService.insert_email(recipient, f"[Vidyaroop] Payment Failed — {payment_id}", f"Payment {payment_id} failed with status {status_str}.", None)
            raise HTTPException(status_code=400, detail=f"Payment not completed: {status_str}")

        # Success: update DB and insert purchases
        cursor = connection.cursor()
        cursor.execute("UPDATE Payment SET status='success' WHERE payment_id=%s", (payment_id,))
        
        if payment_type == 'individual' and course_id:
             # Course IDs handle (comma separated)
             c_ids = [int(x.strip()) for x in str(course_id).split(',') if x.strip()]
             for cid in c_ids:
                 cursor.execute("SELECT COUNT(*) FROM UserCoursePurchase WHERE user_id=%s AND course_id=%s", (user_id, cid))
                 if cursor.fetchone()[0] == 0:
                     cursor.execute("INSERT INTO UserCoursePurchase (user_id, course_id, payment_id) VALUES (%s, %s, %s)", (user_id, cid, payment_id))
                     cursor.execute("UPDATE Cart SET Status='Deleted' WHERE UserId=%s AND CourseId=%s AND Status='Active'", (user_id, cid))
        
        elif payment_type == 'subscription' and subscription_type:
            now = datetime.now()
            # Basic duration calc
            months = 1
            if subscription_type == 'S06': months = 6
            elif subscription_type == 'S12': months = 12
            elif subscription_type == 'LFT': months = 60 # 5 years
            
            end_date = now + timedelta(days=months*30)
            cursor.execute("INSERT INTO UserSubscription (user_id, subscription_type, payment_id, end_date) VALUES (%s, %s, %s, %s)", (user_id, subscription_type, payment_id, end_date))
            
        elif payment_type == 'product' and product_id:
            cursor.execute("INSERT INTO ProductPayment (UserID, ProductID, Amount, PaymentID) VALUES (%s, %s, %s, %s)", (user_id, product_id, amount, payment_id))
            
        elif payment_type == 'bundle' and bundle_id:
            cursor.execute("INSERT INTO BundlePayment (UserID, BundleID, Amount, PaymentID) VALUES (%s, %s, %s, %s)", (user_id, bundle_id, amount, payment_id))

        connection.commit()
        cursor.close()

        # Success Email
        try:
            logger.info(f"Generating success email for {payment_type}, user_id={user_id}, item_id={product_id or bundle_id or course_id}")
            item_name = "Purchase"
            custom_subject = None
            custom_body = None
            attachments_list = []
            item_details_for_email = {}

            if payment_type == 'product':
                p = productService.get_product_by_id(product_id)
                item_name, custom_subject, custom_body = p.product_name, p.email_subject, p.email_body
                item_details_for_email = {"name": item_name, "is_course_subscription": False, "description": p.product_description}
                atts = productService.get_product_attachments(product_id)
                attachments_list = [{"file_url": a.file_url, "file_name": a.file_name} for a in atts]
            elif payment_type == 'bundle':
                b = bundleService.get_bundle_by_id(bundle_id)
                item_name, custom_subject, custom_body = b.bundle_name, b.email_subject, b.email_body
                item_details_for_email = {"name": item_name, "is_course_subscription": False, "description": b.bundle_description}
                product_names = []
                # For bundle payment, attach all attachments from all products in the bundle
                for p_item in b.products:
                    product_names.append(p_item.product_name)
                    atts = productService.get_product_attachments(p_item.product_id)
                    attachments_list.extend([{"file_url": a.file_url, "file_name": a.file_name} for a in atts])
                item_details_for_email["products_list"] = product_names
            elif payment_type == 'individual':
                item_name = "Course Access"
                # For individual course/subscription, we'll indicate it needs a success image
                item_details_for_email = {"name": item_name, "is_course_subscription": True}
                if course_id:
                    c_ids = [int(x.strip()) for x in str(course_id).split(',') if x.strip() and x.strip().isdigit()]
                    if len(c_ids) == 1:
                        c = courseService.get_course_by_id(c_ids[0])
                        item_name, custom_subject, custom_body = c.course_name, c.email_subject, c.email_body
                        item_details_for_email.update({"name": item_name, "email_subject": custom_subject, "email_body": custom_body})
            elif payment_type == 'subscription':
                item_name = f"Subscription {subscription_type}"
                item_details_for_email = {"name": item_name, "is_course_subscription": True}
                try:
                    cur = connection.cursor(dictionary=True)
                    cur.execute("SELECT PlanName, EmailSubject, EmailBody FROM SubscriptionPlan WHERE PlanId=%s", (subscription_type,))
                    plan = cur.fetchone()
                    if plan: 
                        item_name, custom_subject, custom_body = plan["PlanName"], plan["EmailSubject"], plan["EmailBody"]
                        item_details_for_email.update({"name": item_name, "email_subject": custom_subject, "email_body": custom_body})
                    cur.close()
                except Exception as ex:
                    logger.warning(f"Failed to fetch subscription plan details for email: {ex}")

            email_recipient = email_from_db or _get_user_email(user_id)
            
            # If still no name, try to fetch from Users table
            final_user_name = user_name_from_db
            if final_user_name == "Customer" and user_id:
                try:
                    conn_u = get_db_connection()
                    cur_u = conn_u.cursor(dictionary=True)
                    cur_u.execute("SELECT name FROM Users WHERE id=%s", (user_id,))
                    u_row = cur_u.fetchone()
                    if u_row and u_row['name']:
                        final_user_name = u_row['name']
                    cur_u.close()
                    conn_u.close()
                except: pass

            logger.info(f"Sending email to {email_recipient} for {item_name}")

            # Prepare final item_details
            item_details_for_email.update({
                "name": item_name,
                "email_subject": custom_subject,
                "email_body": custom_body,
                "attachments_json": json.dumps(attachments_list) if attachments_list else None,
                "payment_id": payment_id,
                "amount": amount,
                "item_type": payment_type
            })
            
            emailService.send_purchase_success_email(
                user_email=email_recipient,
                user_name=final_user_name, 
                payment_id=payment_id,
                amount=amount,
                item_type=payment_type,
                item_details=item_details_for_email
            )
            logger.info("Success email queued/sent successfully.")
        except Exception as e:
            logger.error(f"Email error for payment_id {payment_id}: {e}", exc_info=True)

        return {"success": True}
    except Exception as e:
        logger.exception("Confirm error")
        log_exception_to_file(e, context='confirm_payment')
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        connection.close()

@router.get("/status/{payment_request_id}")
async def get_status(payment_request_id: str):
    return gateway.get_payment_status(payment_request_id)

@router.get("/list")
async def list_reqs():
    return gateway.list_payment_requests()

@router.delete("/delete/{payment_request_id}")
async def delete_req(payment_request_id: str):
    return gateway.delete_payment_request(payment_request_id)
