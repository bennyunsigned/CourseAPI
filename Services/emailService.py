import os
import smtplib
import ssl
from email.message import EmailMessage
import mysql.connector
from DB.db import get_db_connection
import re
import traceback
import sys

# Read SMTP settings from env
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'True').lower() in ('true', '1', 'yes')


def send_email_via_smtp(recipient_email: str, subject: str, body: str, attachments: str = None):
    """Send a single email using SMTP settings from environment.
    attachments: optional JSON/string list - for now ignored or stored as text.
    Returns: (success: bool, error_message: str|None)
    """
    msg = EmailMessage()
    msg['From'] = SMTP_USERNAME or 'no-reply@vidyaroop.com'
    msg['To'] = recipient_email
    msg['Subject'] = subject or ''
    plain = ''
    if body:
        # create a simple plain-text fallback by stripping HTML tags
        plain = re.sub('<[^<]+?>', '', body)
    msg.set_content(plain or (body or ''))
    # attach html alternative if body looks like HTML
    try:
        if body and ('<' in body and '>' in body):
            msg.add_alternative(body, subtype='html')
    except Exception:
        # ignore HTML alternative errors and send plain
        pass

    try:
        if SMTP_USE_TLS:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls(context=context)
                if SMTP_USERNAME and SMTP_PASSWORD:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(), timeout=30) as server:
                if SMTP_USERNAME and SMTP_PASSWORD:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        return True, None
    except Exception as e:
        # Print error details for easier debugging
        try:
            tb = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            print("[emailService] SMTP send error:", file=sys.stderr)
            print(tb, file=sys.stderr)
        except Exception:
            print("[emailService] SMTP send error:", e, file=sys.stderr)
        return False, str(e)


def fetch_active_emails(limit: int = 500):
    """Fetch up to `limit` active emails ordered by EmailId DESC."""
    connection = get_db_connection()
    if not connection:
        return []
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT EmailId, recipient_email, subject, body, attachments, attempts FROM EmailMaster WHERE status = 'Active' ORDER BY EmailId DESC LIMIT %s",
            (limit,)
        )
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error:
        return []
    finally:
        cursor.close()
        connection.close()


def mark_email_sent(email_id: int):
    connection = get_db_connection()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute("UPDATE EmailMaster SET status = 'Sent', attempts = attempts + 1, last_attempt_at = NOW() WHERE EmailId = %s", (email_id,))
        connection.commit()
        return True
    except mysql.connector.Error:
        return False
    finally:
        cursor.close()
        connection.close()


def mark_email_failed(email_id: int):
    connection = get_db_connection()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute("UPDATE EmailMaster SET status = 'Failed', attempts = attempts + 1, last_attempt_at = NOW() WHERE EmailId = %s", (email_id,))
        connection.commit()
        return True
    except mysql.connector.Error:
        return False
    finally:
        cursor.close()
        connection.close()


def insert_email(recipient_email: str, subject: str, body: str, attachments: str = None):
    """Insert a new email record into EmailMaster."""
    connection = get_db_connection()
    if not connection:
        return None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO EmailMaster (recipient_email, subject, body, attachments) VALUES (%s, %s, %s, %s)",
            (recipient_email, subject, body, attachments)
        )
        eid = cursor.lastrowid
        connection.commit()
        return eid
    except mysql.connector.Error:
        return None
    finally:
        cursor.close()
        connection.close()
