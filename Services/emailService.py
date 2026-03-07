import os
import smtplib
import ssl
from email.message import EmailMessage
import mysql.connector
from DB.db import get_db_connection
import re
import traceback
import sys
import json
import mimetypes
import urllib.request
from Utils.ExceptionHandler import log_exception_to_file

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

    # Handle attachments
    if attachments:
        try:
            # attachments is expected to be a JSON string list of objects: [{"file_url": "...", "file_name": "..."}]
            items = json.loads(attachments)
            if isinstance(items, list):
                for item in items:
                    file_url = item.get('file_url')
                    file_name = item.get('file_name')
                    if not file_url: continue
                    
                    try:
                        # Determine if it's a local file or remote URL
                        # Case-insensitive check for /uploads/ or /Uploads/
                        if file_url.lower().startswith('/uploads/'):
                            # Map to local Uploads directory
                            base_dir = os.path.dirname(os.path.dirname(__file__))
                            # Use the actual folder name on disk
                            local_rel_path = file_url.lstrip('/')
                            local_path = os.path.join(base_dir, local_rel_path)
                            
                            # Try to find the file even if casing differs on disk (though Windows is usually case-insensitive)
                            if not os.path.exists(local_path):
                                # Try matching 'Uploads' instead of 'uploads' if base case failed
                                if local_rel_path.lower().startswith('uploads/'):
                                    local_path = os.path.join(base_dir, 'Uploads', local_rel_path[8:])

                            with open(local_path, 'rb') as f:
                                file_data = f.read()
                            print(f"[emailService] Attached local file: {local_path}")
                        else:
                            # Try to download from full URL
                            # Ensure it's a full URL if it doesn't look like one
                            download_url = file_url
                            if download_url.startswith('//'):
                                download_url = 'https:' + download_url
                            elif not download_url.startswith(('http://', 'https://')):
                                # Fallback for relative paths that escaped the local check
                                download_url = f"https://api.vidyaroop.com/{download_url.lstrip('/')}"
                            
                            with urllib.request.urlopen(download_url, timeout=20) as r:
                                file_data = r.read()
                            print(f"[emailService] Attached remote file: {download_url}")
                        
                        ctype, encoding = mimetypes.guess_type(file_name or file_url)
                        if ctype is None or encoding is not None:
                            ctype = 'application/octet-stream'
                        maintype, subtype = ctype.split('/', 1)
                        
                        msg.add_attachment(
                            file_data,
                            maintype=maintype,
                            subtype=subtype,
                            filename=file_name or os.path.basename(file_url)
                        )
                    except Exception as ae:
                        print(f"[emailService] Failed to attach {file_url}: {ae}", file=sys.stderr)
        except Exception as je:
            print(f"[emailService] Failed to parse attachments JSON: {je}", file=sys.stderr)

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
    if not recipient_email:
        print("[emailService] ERROR: recipient_email is missing. Cannot insert email.")
        return None
        
    print(f"[emailService] Inserting email for {recipient_email}...")
    connection = get_db_connection()
    if not connection:
        print("[emailService] Failed to connect to DB for insert_email")
        return None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO EmailMaster (recipient_email, subject, body, attachments) VALUES (%s, %s, %s, %s)",
            (recipient_email, subject, body, attachments)
        )
        eid = cursor.lastrowid
        connection.commit()
        print(f"[emailService] Email inserted successfully, EmailId={eid}")
        return eid
    except mysql.connector.Error as err:
        print(f"[emailService] Database error during insert_email: {err}")
        log_exception_to_file(err, context='insert_email')
        return None
    finally:
        cursor.close()
        connection.close()

def send_purchase_success_email(user_email: str, user_name: str, payment_id: str, amount: float, item_type: str, item_details: dict):
    """
    Generates and inserts a purchase success email into EmailMaster.
    Supports dynamic templates with placeholders: {{user_name}}, {{payment_id}}, {{amount}}, {{item_name}}.
    """
    subject_template = item_details.get("email_subject") or f"[Vidyaroop] Payment Successful — {payment_id}"
    body_template = item_details.get("email_body")
    item_name = item_details.get("name", "")
    attachments_json = item_details.get("attachments_json")
    is_course_subscription = item_details.get("is_course_subscription", False)

    # If no body template is configured, use a default one
    if not body_template:
        if is_course_subscription:
             # Basic success image for course/subscription
             body_template = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333; text-align: center;">
                <div style="max-width:600px;margin:0 auto;padding:20px;border:1px solid #eaeaea;border-radius:8px;">
                   <h2 style="color:#28a745;">Payment Successful!</h2>
                   <p>Hello {{{{user_name}}}}, your payment for <strong>{{{{item_name}}}}</strong> was successful.</p>
                   <div style="margin: 20px 0;">
                     <img src="https://api.vidyaroop.com/Uploads/success_image.png" alt="Success" style="max-width: 100%; border-radius: 8px;">
                   </div>
                   <p>Payment ID: <strong>{{{{payment_id}}}}</strong></p>
                   <p>You can now access your course at <a href="https://vidyaroop.com/my-courses">Vidyaroop.com</a>.</p>
                   <hr>
                   <p style="font-size:12px;color:#888;">&copy; Vidyaroop.com</p>
                 </div>
               </body>
             </html>
             """
        else:
            description = item_details.get("description", "")
            products_list = item_details.get("products_list", [])
            
            item_info = f"<strong>Item:</strong> {item_name}"
            if description:
                item_info += f"<br><strong>Description:</strong> {description}"
            
            if products_list:
                item_info += "<br><br><strong>Included Products:</strong><ul>"
                for pn in products_list:
                    item_info += f"<li>{pn}</li>"
                item_info += "</ul>"
            
            # Add download links if attachments exist
            if attachments_json:
                try:
                    atts = json.loads(attachments_json)
                    if atts:
                        item_info += "<br><strong>Your Digital Downloads:</strong><ul style='list-style: none; padding: 0;'>"
                        for a in atts:
                            url = a.get('file_url', '')
                            name = a.get('file_name') or os.path.basename(url)
                            if url.lower().startswith('/uploads/'):
                                url = f"https://api.vidyaroop.com/{url.lstrip('/')}"
                            item_info += f"<li style='margin-bottom: 10px; padding: 10px; background: #f0f8ff; border: 1px solid #cce5ff; border-radius: 4px;'><a href='{url}' style='color: #004085; text-decoration: none; font-weight: bold;'>⬇ {name} (Also attached to this email)</a></li>"
                        item_info += "</ul>"
                except: pass
            
            body_template = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <div style="max-width:600px;margin:0 auto;padding:20px;border:1px solid #eaeaea;border-radius:8px;">
                  <h2 style="color:#28a745; text-align: center;">Purchase Confirmation</h2>
                  <p>Hello {{{{user_name}}}}, thank you for your purchase.</p>
                  <div style="margin: 20px 0; padding: 15px; border: 1px solid #eee; border-radius: 4px; background-color: #fdfdfd;">
                    <p style="margin-top: 0;"><strong>Payment ID:</strong> {{{{payment_id}}}}</p>
                    <p><strong>Amount Paid:</strong> ₹{{{{amount}}}}</p>
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee;">
                        {item_info}
                    </div>
                  </div>
                  <p>Thank you for choosing Vidyaroop!</p>
                  <hr>
                  <p style="font-size:12px;color:#888; text-align: center;">&copy; Vidyaroop.com</p>
                </div>
              </body>
            </html>
            """

    # Replace placeholders
    try:
        amt_str = f"{float(amount):.2f}" if amount is not None else "0.00"
    except:
        amt_str = str(amount)

    placeholders = {
        "{{user_name}}": user_name,
        "{{payment_id}}": payment_id,
        "{{amount}}": amt_str,
        "{{item_name}}": item_name
    }
    
    print(f"[emailService] Placeholders: {placeholders}")
    
    final_subject = subject_template
    final_body = body_template
    for placeholder, value in placeholders.items():
        if final_subject: final_subject = final_subject.replace(placeholder, value)
        if final_body: final_body = final_body.replace(placeholder, value)

    insert_email(user_email, final_subject, final_body, attachments_json)
