from DB.db import get_db_connection
from Utils.AES import AESCipher
from Utils.JWT import create_jwt_token
from Models.authModel import UserRegistration, UserLogin
import mysql.connector

aes_cipher = AESCipher()

def register_user(user: UserRegistration):
    """Register a new user in the database."""
    encrypted_password = aes_cipher.encrypt(user.password)
    query = """
    INSERT INTO Users (name, email, password, phone, provider_id, provider, role)
    VALUES (%s, %s, %s, %s, NULL, %s, %s)
    """
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(query, (user.name, user.email, encrypted_password, user.phone, user.provider, user.role))
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
    query = "SELECT id, name, email, password, phone, provider, role FROM Users WHERE email = %s"
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
                    claims = {
                        "id": db_user["id"],
                        "name": db_user["name"],
                        "email": db_user["email"],
                        "role": db_user["role"]
                    }
                    return create_jwt_token(claims)
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

