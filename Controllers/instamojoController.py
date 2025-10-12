

from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel
from instamojo_wrapper import Instamojo
import os
import logging
import mysql.connector
from datetime import datetime, timedelta
import calendar
from DB.db import get_db_connection
from Services import emailService
from Utils.ExceptionHandler import log_exception_to_file

router = APIRouter(prefix="/instamojo", tags=["Instamojo"])


# Initialize Instamojo API (read from env vars when available)
API_KEY = os.getenv("INSTAMOJO_API_KEY") 
AUTH_TOKEN = os.getenv("INSTAMOJO_AUTH_TOKEN") 
API_URL = os.getenv("INSTAMOJO_API_URL")
api = Instamojo(api_key=API_KEY, auth_token=AUTH_TOKEN, endpoint=API_URL)

# basic logger
logger = logging.getLogger("instamojo")
if not logger.handlers:
    logging.basicConfig()

# NOTE: payment intent is persisted on create and the status should be updated to 'success' on confirm


def ensure_payment_log_table():
    """Create PaymentLog table if it doesn't exist."""
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS PaymentLog (
                id INT AUTO_INCREMENT PRIMARY KEY,
                payment_id VARCHAR(255),
                event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level VARCHAR(16),
                step VARCHAR(128),
                message TEXT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def ensure_payment_table_columns():
    """Ensure Payment table has course_id and subscription_type columns (used to persist intent data)."""
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        # Check and add course_id if missing
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='Payment' AND COLUMN_NAME='course_id'"
        )
        has_course = cursor.fetchone()[0] > 0
        if not has_course:
            try:
                cursor.execute("ALTER TABLE Payment ADD COLUMN course_id INT DEFAULT NULL")
            except Exception as e:
                logger.exception("Failed to add course_id column: %s", e)

        # Check and add subscription_type if missing
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='Payment' AND COLUMN_NAME='subscription_type'"
        )
        has_sub = cursor.fetchone()[0] > 0
        if not has_sub:
            try:
                cursor.execute("ALTER TABLE Payment ADD COLUMN subscription_type VARCHAR(255) DEFAULT NULL")
            except Exception as e:
                logger.exception("Failed to add subscription_type column: %s", e)

        connection.commit()
    except Exception as e:
        # don't fail hard; just log
        logger.exception("Failed to ensure payment table columns: %s", e)
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass


def log_payment_event(payment_id: str | None, level: str, step: str, message: str) -> None:
    """Insert a log record into PaymentLog. Swallows errors to avoid blocking payment flow."""
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
    """Return user's email from Users table or empty string if not found."""
    try:
        conn = get_db_connection()
        if not conn:
            return ""
        cur = conn.cursor()
        cur.execute("SELECT email FROM Users WHERE id=%s", (user_id,))
        r = cur.fetchone()
        try:
            cur.close()
            conn.close()
        except Exception:
            pass
        if r and len(r) > 0:
            return r[0] or ""
    except Exception:
        pass
    return ""


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
    # ensure log table exists
    ensure_payment_log_table()
    try:
        log_payment_event(None, 'INFO', 'create_payment.start', f'Request: user_id={data.user_id}, amount={data.amount}, purpose={data.purpose}')
        response = api.payment_request_create(
            amount=str(data.amount),
            purpose=data.purpose,
            buyer_name=data.buyer_name,
            email=data.email,
            phone=data.phone,
            redirect_url=data.redirect_url
        )
        logger.debug("Instamojo create response: %s", response)

        # response should contain 'payment_request' on success
        payment_req = response.get('payment_request') if isinstance(response, dict) else None
        if not payment_req:
            # log full response and surface helpful error
            logger.error("Instamojo payment create failed: %s", response)
            log_payment_event(None, 'ERROR', 'create_payment.instamojo_response_missing', str(response))
            error_msg = response.get('message') if isinstance(response, dict) else 'Unknown Instamojo error'
            raise HTTPException(status_code=400, detail=f"Instamojo error: {error_msg}")

        # Track payment intent in Payment table
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            # ensure payment table columns exist for persisted intent data
            ensure_payment_table_columns()
            query = """
                INSERT INTO Payment (user_id, payment_id, amount, payment_type, status, course_id, subscription_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (data.user_id, payment_req['id'], data.amount, data.payment_type, 'created', data.course_id, data.subscription_type))
            connection.commit()
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                connection.close()
            except Exception:
                pass

        log_payment_event(payment_req['id'], 'INFO', 'create_payment.db_insert', 'Inserted payment intent with status created')
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating instamojo payment")
        log_payment_event(None, 'ERROR', 'create_payment.exception', str(e))
        # write full traceback to Exception file and re-raise
        try:
            log_exception_to_file(e, context='create_payment')
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payment/confirm", status_code=status.HTTP_200_OK)
async def confirm_payment(payment_id: str = Body(...), payment_type: str = Body(...), user_id: int = Body(...), course_id: str = Body(None), subscription_type: str = Body(None), amount: float = Body(None)):
    """
    Call this endpoint after payment is successful (webhook or redirect handler).
    Also updates Payment table status.
    """
    connection = get_db_connection()
    try:
        log_payment_event(payment_id, 'INFO', 'confirm_payment.start', f'Confirming payment for payment_type={payment_type}, user_id={user_id}')
        # If necessary data isn't provided by the redirect, try to read it from Payment intent row
        if not all([payment_type, user_id is not None, course_id is not None or subscription_type is not None]):
            try:
                cursor_fetch = connection.cursor(dictionary=True)
                cursor_fetch.execute("SELECT user_id, payment_type, course_id, subscription_type FROM Payment WHERE payment_id=%s", (payment_id,))
                row = cursor_fetch.fetchone()
                cursor_fetch.close()
                if row:
                    if not payment_type:
                        payment_type = row.get('payment_type')
                    if not user_id:
                        user_id = row.get('user_id')
                    if not course_id:
                        course_id = row.get('course_id')
                    if not subscription_type:
                        subscription_type = row.get('subscription_type')
            except Exception as e:
                logger.exception("Failed to fetch intent data from Payment table: %s", e)
                log_payment_event(payment_id, 'ERROR', 'confirm_payment.fetch_intent_failed', str(e))
        # Verify payment with Instamojo before marking success
        try:
            status_resp = api.payment_request_status(payment_id)
            logger.debug("Instamojo status response for %s: %s", payment_id, status_resp)
            log_payment_event(payment_id, 'DEBUG', 'confirm_payment.instamojo_status_resp', str(status_resp))
            # expected structure: {'success': True, 'payment_request': {..., 'status': 'Completed' or 'Failed', 'payment': {...}}}
        except Exception as e:
            logger.exception("Failed to fetch payment status from Instamojo")
            log_payment_event(payment_id, 'ERROR', 'confirm_payment.status_fetch_failed', str(e))
            raise HTTPException(status_code=400, detail="Failed to verify payment with Instamojo")

        # Determine success
        payment_request = status_resp.get('payment_request') if isinstance(status_resp, dict) else None
        status_str = None
        if payment_request:
            # Instamojo may include 'status' at different places; check top-level and nested
            status_str = payment_request.get('status') or (payment_request.get('payment', {}) or {}).get('status')

        if not payment_request or status_str is None:
            logger.error("Unexpected status response: %s", status_resp)
            log_payment_event(payment_id, 'ERROR', 'confirm_payment.invalid_status_response', str(status_resp))
            raise HTTPException(status_code=400, detail="Invalid status response from Instamojo")

        if str(status_str).lower() not in ('completed', 'success'):
            # mark failed and return
            cursor = connection.cursor()
            try:
                cursor.execute("UPDATE Payment SET status=%s WHERE payment_id=%s", (str(status_str), payment_id))
                connection.commit()
                # queue failure email
                try:
                    subject = f"[Vidyaroop] Payment Failed — {payment_id}"
                    # HTML body (no user id)
                    body = f"""
                    <html>
                      <body style="font-family: Arial, sans-serif; color: #333;">
                        <div style="max-width:600px;margin:0 auto;padding:20px;border:1px solid #eaeaea;border-radius:8px;">
                          <h2 style="color:#d9534f;">Payment Failed</h2>
                          <p>We were unable to process payment <strong>{payment_id}</strong>.</p>
                          <p>Status: <strong>{status_str}</strong></p>
                          <p>If you need help, visit <a href="https://vidyaroop.com">Vidyaroop.com</a> or reply to this email.</p>
                          <hr>
                          <p style="font-size:12px;color:#888;">&copy; Vidyaroop.com</p>
                        </div>
                      </body>
                    </html>
                    """
                    recipient = _get_user_email(user_id) or ''
                    emailService.insert_email(recipient, subject, body, None)
                except Exception:
                    # don't block payment flow on email errors
                    pass
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
            log_payment_event(payment_id, 'WARN', 'confirm_payment.not_completed', f'Payment not completed: {status_str}')
            raise HTTPException(status_code=400, detail=f"Payment not completed: {status_str}")

        # Payment completed: update DB and insert purchases
        cursor = connection.cursor()
        try:
            cursor.execute("UPDATE Payment SET status='success' WHERE payment_id=%s", (payment_id,))
            log_payment_event(payment_id, 'INFO', 'confirm_payment.marked_success', 'Payment status set to success')
            if payment_type == 'individual' and course_id:
                # course_id may be a single integer or a comma-separated string of IDs
                # normalize to list of ints
                course_ids = []
                # Try parameter first
                try:
                    if isinstance(course_id, str) and ',' in course_id:
                        parts = [p.strip() for p in course_id.split(',') if p.strip()]
                        for p in parts:
                            try:
                                course_ids.append(int(p))
                            except Exception:
                                logger.warning("Skipping invalid course id part: %s", p)
                    else:
                        # single value - may be string of int or int
                        course_ids.append(int(course_id))
                except Exception:
                    # fallback: try to read from payment intent row (fetched earlier)
                    try:
                        cursor_fetch = connection.cursor(dictionary=True)
                        cursor_fetch.execute("SELECT course_id FROM Payment WHERE payment_id=%s", (payment_id,))
                        intent_row = cursor_fetch.fetchone()
                        cursor_fetch.close()
                        if intent_row and intent_row.get('course_id') is not None:
                            raw = intent_row.get('course_id')
                            if isinstance(raw, str) and ',' in raw:
                                for p in [x.strip() for x in raw.split(',') if x.strip()]:
                                    try:
                                        course_ids.append(int(p))
                                    except Exception:
                                        logger.warning("Skipping invalid course id in intent: %s", p)
                            else:
                                try:
                                    course_ids.append(int(raw))
                                except Exception:
                                    pass
                    except Exception:
                        logger.exception("Failed to fetch course_id from Payment intent as fallback")

                if not course_ids:
                    raise HTTPException(status_code=400, detail="No valid course_id provided for individual purchase")

                query = """
                    INSERT INTO UserCoursePurchase (user_id, course_id, payment_id)
                    VALUES (%s, %s, %s)
                """
                exists_query = "SELECT COUNT(*) FROM UserCoursePurchase WHERE user_id=%s AND course_id=%s"
                delete_cart_query = "UPDATE Cart SET Status='Deleted', UpdatedAt=NOW() WHERE UserId=%s AND CourseId=%s AND Status='Active'"
                for cid in course_ids:
                    # Skip duplicate purchases
                    try:
                        cursor.execute(exists_query, (user_id, cid))
                        exists_cnt = cursor.fetchone()[0]
                    except Exception:
                        exists_cnt = 0

                    if exists_cnt and exists_cnt > 0:
                        log_payment_event(payment_id, 'INFO', 'confirm_payment.duplicate_purchase', f'Skipped duplicate purchase for user {user_id} course {cid}')
                        continue

                    # Insert purchase row
                    cursor.execute(query, (user_id, cid, payment_id))
                    log_payment_event(payment_id, 'INFO', 'confirm_payment.purchase_insert', f'Inserted UserCoursePurchase for user {user_id} course {cid}')

                    # Remove from cart (soft delete)
                    try:
                        cursor.execute(delete_cart_query, (user_id, cid))
                        log_payment_event(payment_id, 'INFO', 'confirm_payment.cart_removed', f'Removed cart item for user {user_id} course {cid}')
                    except Exception as e:
                        logger.exception("Failed to remove from cart for user %s course %s: %s", user_id, cid, str(e))
            elif payment_type == 'subscription' and subscription_type:
                # Calculate end_date based on subscription_type
                def add_months(dt: datetime, months: int) -> datetime:
                    month = dt.month - 1 + months
                    year = dt.year + month // 12
                    month = month % 12 + 1
                    day = min(dt.day, calendar.monthrange(year, month)[1])
                    return dt.replace(year=year, month=month, day=day)

                def add_years(dt: datetime, years: int) -> datetime:
                    try:
                        return dt.replace(year=dt.year + years)
                    except ValueError:
                        # handle Feb 29 -> Feb 28 on non-leap years
                        return dt.replace(year=dt.year + years, day=28)

                now = datetime.now()
                end_date = None
                try:
                    if subscription_type == 'S06':
                        end_date = add_months(now, 6)
                    elif subscription_type == 'S12':
                        end_date = add_months(now, 12)
                    elif subscription_type == 'LFT':
                        end_date = add_years(now, 5)
                    else:
                        end_date = now + timedelta(days=30)
                except Exception:
                    # fallback to 30 days if any calculation fails
                    end_date = now + timedelta(days=30)

                query = """
                    INSERT INTO UserSubscription (user_id, subscription_type, payment_id, end_date)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(query, (user_id, subscription_type, payment_id, end_date))
                log_payment_event(payment_id, 'INFO', 'confirm_payment.subscription_insert', f'Inserted UserSubscription for user {user_id} subscription {subscription_type} end_date={end_date}')
            else:
                raise HTTPException(status_code=400, detail="Invalid payment type or missing data.")
            connection.commit()
        finally:
            try:
                cursor.close()
            except Exception:
                pass
        # queue success email after purchases/subscriptions inserted
        try:
            subject = f"[Vidyaroop] Payment Successful — {payment_id}"
            # HTML body (no user id)
            try:
                amount_str = f"Amount: {amount}" if amount is not None else ""
            except Exception:
                amount_str = ""
            body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width:600px;margin:0 auto;padding:20px;border:1px solid #eaeaea;border-radius:8px;">
                  <h2 style="color:#28a745;">Payment Successful</h2>
                  <p>Your payment <strong>{payment_id}</strong> has been processed successfully.</p>
                  <p>{amount_str}</p>
                  <p>Thank you for your purchase. You can access your content at <a href="https://vidyaroop.com">Vidyaroop.com</a>.</p>
                  <hr>
                  <p style="font-size:12px;color:#888;">&copy; Vidyaroop.com</p>
                </div>
              </body>
            </html>
            """
            recipient = _get_user_email(user_id) or ''
            emailService.insert_email(recipient, subject, body, None)
        except Exception:
            pass
        log_payment_event(payment_id, 'INFO', 'confirm_payment.completed', 'Confirm payment completed successfully')
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error confirming payment")
        log_payment_event(payment_id, 'ERROR', 'confirm_payment.exception', str(e))
        try:
            log_exception_to_file(e, context='confirm_payment')
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass

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


