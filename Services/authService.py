from DB.db import get_db_connection
from Utils.AES import AESCipher
from Utils.JWT import create_jwt_token
from Models.authModel import UserRegistration, UserLogin
import mysql.connector
import secrets
from datetime import datetime, timedelta
import os
from Services import emailService

aes_cipher = AESCipher()

def register_user(user: UserRegistration):
    """Register a new user in the database."""
    encrypted_password = aes_cipher.encrypt(user.password)
    # Mark local users as not activated until they click email link; providers as activated.
    is_activated = 0 if (user.provider or 'local').lower() == 'local' else 1
    query = """
    INSERT INTO Users (name, email, password, phone, provider_id, provider, role, is_activated)
    VALUES (%s, %s, %s, %s, NULL, %s, %s, %s)
    """
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(query, (user.name, user.email, encrypted_password, user.phone, user.provider, user.role, is_activated))
            connection.commit()
            user_id = cursor.lastrowid
            return user_id
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def login_user(user: UserLogin) -> str:
    """
    Authenticate a user and generate a JWT token.
    :param user: UserLogin object containing email and password.
    :return: JWT token if authentication is successful.
    """
    query = "SELECT id, name, email, password, phone, provider, role, is_activated FROM Users WHERE email = %s"
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (user.email,))
            db_user = cursor.fetchone()
            if db_user:
                print(f"Encrypted password from DB: {db_user['password']}")
                decrypted_password = aes_cipher.decrypt(db_user["password"])
                print(f"Decrypted password: {decrypted_password}")
                if decrypted_password == user.password:
                    # Enforce activation for local users only
                    provider = (db_user.get("provider") or "").lower()
                    if provider == 'local' and int(db_user.get("is_activated") or 0) != 1:
                        raise Exception("Account not activated. Please check your email.")
                    claims = {
                        "id": db_user["id"],
                        "name": db_user["name"],
                        "email": db_user["email"],
                        "role": db_user["role"]
                    }
                    token = create_jwt_token(claims)
                    # Record login event
                    try:
                        record_user_login(db_user["id"], provider)
                    except Exception:
                        # Do not block login on logging failure
                        pass
                    return token
                else:
                    raise Exception("Invalid email or password")
            else:
                raise Exception("User not found")
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")


def change_user_password(user_id: int, old_password: str, new_password: str) -> None:
    """
    Change the password for a local-account user after verifying the old password.
    Google sign-in users are not allowed to change password here.
    """
    # Fetch current user
    select_q = "SELECT id, password, provider FROM Users WHERE id = %s"
    update_q = "UPDATE Users SET password = %s WHERE id = %s"

    conn = get_db_connection()
    if not conn:
        raise Exception("Failed to connect to the database.")

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(select_q, (user_id,))
        row = cur.fetchone()
        if not row:
            raise Exception("User not found")

        provider = (row.get("provider") or "").lower()
        if provider == "google":
            raise Exception("Google sign-in users cannot change password")

        # Verify old password
        try:
            current_plain = aes_cipher.decrypt(row["password"]) if row.get("password") else ""
        except Exception:
            # If stored password cannot be decrypted, treat as mismatch
            current_plain = "__invalid__"

        if current_plain != old_password:
            raise Exception("Old password is incorrect")

        # Encrypt and update new password
        new_encrypted = aes_cipher.encrypt(new_password)
        cur2 = conn.cursor()
        cur2.execute(update_q, (new_encrypted, user_id))
        conn.commit()
        cur2.close()
    except mysql.connector.Error as err:
        raise Exception(f"Database error: {err}")
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


def _activation_base_url() -> str:
    """Derive a base URL for activation links from environment.
    Defaults to localhost in development, api.vidyaroop.com in production.
    """
    env = (os.getenv('ENV') or 'Development').lower()
    if env == 'production':
        return os.getenv('PUBLIC_BASE_URL', 'https://api.vidyaroop.com')
    return os.getenv('PUBLIC_BASE_URL', 'http://localhost:8000')


def create_activation_token_and_queue_email(user_id: int, recipient_email: str, name: str | None = None) -> str:
    """Create a 15-minute activation token for the user and queue an email in EmailMaster.
    Returns the token for reference (useful in logs/tests).
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    conn = get_db_connection()
    if not conn:
        raise Exception("Failed to connect to the database.")

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO UserActivationTokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
            (user_id, token, expires_at.strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
    except mysql.connector.Error as err:
        raise Exception(f"Database error: {err}")
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

    # Queue email
    base = _activation_base_url()
    activation_link = f"{base}/auth/activate?token={token}"
    subject = "Activate your Vidyaroop account"
    display_name = name or recipient_email
    body = f"""
    <p>Hi {display_name},</p>
    <p>Thanks for registering on Vidyaroop. Please click the link below to activate your account:</p>
    <p><a href=\"{activation_link}\" target=\"_blank\">Activate my account</a></p>
    <p>This link will expire in <strong>15 minutes</strong>. If you did not sign up, you can ignore this email.</p>
    <p>— Team Vidyaroop</p>
    """
    emailService.insert_email(recipient_email, subject, body)
    return token


def record_user_login(user_id: int, provider: str, ip: str | None = None, user_agent: str | None = None) -> None:
    """Insert a login event into UserLoginLog. Non-critical if it fails."""
    conn = get_db_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO UserLoginLog (UserId, Provider, IP, UserAgent) VALUES (%s, %s, %s, %s)",
            (user_id, (provider or 'local'), ip, user_agent)
        )
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

