from typing import List
import logging

from DB.db import get_db_connection
import mysql.connector
import base64
import os

logger = logging.getLogger(__name__)


def add_course_to_cart(user_id: int, course_id: int) -> int:
    """
    Insert a cart row for the user if not exists and return the CartId.
    """
    query_check = "SELECT CartId FROM Cart WHERE UserId=%s AND CourseId=%s AND Status='Active'"
    query_insert = "INSERT INTO Cart (UserId, CourseId, CreatedAt, Status) VALUES (%s, %s, NOW(), 'Active')"

    conn = get_db_connection()
    cursor = None
    if not conn:
        raise Exception("Database connection failed")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query_check, (user_id, course_id))
        existing = cursor.fetchone()
        if existing:
            return existing["CartId"]
        cursor.execute(query_insert, (user_id, course_id))
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.Error as e:
        logger.exception("Database error in add_course_to_cart(user_id=%s, course_id=%s): %s", user_id, course_id, str(e))
        raise Exception(f"Database error: {e}")
    finally:
        if cursor:
            cursor.close()
        conn.close()


def get_cart_products_by_user(user_id: int) -> List[dict]:
    """
    Call stored procedure to get cart products for the user and return rows as list[dict].
    """
    conn = get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("GetCartProductsByUser", [user_id])
        rows = []
        for result in cursor.stored_results():
            rows = result.fetchall()
            break
        # Convert datetime objects to ISO strings for Pydantic response validation
        for r in rows:
            if r.get('CreatedAt') is not None:
                try:
                    r['CreatedAt'] = r['CreatedAt'].isoformat()
                except Exception:
                    r['CreatedAt'] = str(r['CreatedAt'])
            if r.get('UpdatedAt') is not None:
                try:
                    r['UpdatedAt'] = r['UpdatedAt'].isoformat()
                except Exception:
                    r['UpdatedAt'] = str(r['UpdatedAt'])
            # Handle BannerImage similar to courseProgressController: prefer BASE_FILE_URL/BASE_FILE_PATH
            banner_path = r.get('BannerImage')
            image_value = None
            base_file_url = os.getenv('BASE_FILE_URL') or os.getenv('BASE_FILE_PATH')
            if banner_path:
                # If banner_path already looks like a URL, use it as-is
                if isinstance(banner_path, str) and (banner_path.startswith('http://') or banner_path.startswith('https://')):
                    image_value = banner_path
                elif base_file_url:
                    # Join carefully to avoid double slashes
                    if base_file_url.endswith('/') and banner_path.startswith('/'):
                        image_value = base_file_url[:-1] + banner_path
                    elif not base_file_url.endswith('/') and not banner_path.startswith('/'):
                        image_value = base_file_url + '/' + banner_path
                    else:
                        image_value = base_file_url + banner_path
                else:
                    # Fallback to embedding base64 if local file exists
                    try:
                        if os.path.isfile('.' + banner_path):
                            with open('.' + banner_path, 'rb') as img_file:
                                image_value = 'data:image/jpeg;base64,' + base64.b64encode(img_file.read()).decode('utf-8')
                    except Exception:
                        image_value = None
            r['BannerImage'] = image_value
        return rows
    except mysql.connector.Error as e:
        logger.exception("Database error in get_cart_products_by_user(user_id=%s): %s", user_id, str(e))
        raise Exception(f"Database error: {e}")
    finally:
        if cursor:
            cursor.close()
        conn.close()


def remove_course_from_cart(user_id: int, course_id: int) -> bool:
    """
    Mark the cart item as deleted (soft delete). Returns True if a row was updated.
    """
    query = "UPDATE Cart SET Status = 'Deleted', UpdatedAt = NOW() WHERE UserId = %s AND CourseId = %s AND Status = 'Active'"
    conn = get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(query, (user_id, course_id))
        affected = cursor.rowcount
        conn.commit()
        return affected > 0
    except mysql.connector.Error as e:
        logger.exception("Database error in remove_course_from_cart(user_id=%s, course_id=%s): %s", user_id, course_id, str(e))
        raise Exception(f"Database error: {e}")
    finally:
        if cursor:
            cursor.close()
        conn.close()
        