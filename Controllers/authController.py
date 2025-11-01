from fastapi import APIRouter, HTTPException, Depends
from Models.authModel import UserRegistration, UserResponse, UserLogin, LoginResponse, ChangePasswordRequest, MessageResponse
from Services.authService import register_user, login_user, change_user_password, create_activation_token_and_queue_email, record_user_login
from Utils.JWT import authenticate_request, create_jwt_token
from DB.db import get_db_connection
import secrets
import string
from pydantic import BaseModel
from typing import Optional
import os
import httpx
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

auth_router = APIRouter()

@auth_router.post("/register", response_model=MessageResponse)
def register(user: UserRegistration):
    """
    Register a new user.
    - For local provider: create activation token, queue email, respond with instruction message.
    - For Google provider: activation not required (Google callback path is preferred anyway).
    """
    try:
        user_id = register_user(user)
        # If local registration, create activation token and queue email
        if (user.provider or "local").lower() == "local":
            try:
                create_activation_token_and_queue_email(user_id, user.email, user.name)
            except Exception as _e:
                # If we fail to queue email, still return an error to let client retry/regenerate
                raise HTTPException(status_code=500, detail=f"Failed to queue activation email: {_e}")
            return MessageResponse(message="Registration successful. Check your email to activate your account.")
        else:
            # Non-local providers (though Google flow should use GoogleCallBack)
            return MessageResponse(message="Registration successful.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/login", response_model=LoginResponse)
def login(user: UserLogin):
    """
    Login a user and return a JWT token.
    """
    try:
        token = login_user(user)
        return LoginResponse(access_token=token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.get("/activate", response_model=MessageResponse)
def activate(token: str):
    """
    Validate activation token and activate the corresponding user if valid and not expired.
    The token is valid for 15 minutes from issuance.
    """
    from DB.db import get_db_connection
    import mysql.connector
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cur = conn.cursor(dictionary=True)
        # Find token that is not used and not expired
        cur.execute(
            """
            SELECT id, user_id, expires_at, used
            FROM UserActivationTokens
            WHERE token = %s
            LIMIT 1
            """,
            (token,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Invalid or expired activation link")
        if int(row.get("used") or 0) == 1:
            raise HTTPException(status_code=400, detail="Activation link already used")

        # Check expiry server-side
        cur.execute("SELECT NOW() < %s AS not_expired", (row["expires_at"],))
        check = cur.fetchone()
        if not check or int(list(check.values())[0]) != 1:
            raise HTTPException(status_code=400, detail="Invalid or expired activation link")

        # Activate user and mark token used
        cur2 = conn.cursor()
        cur2.execute("UPDATE Users SET is_activated = 1 WHERE id = %s", (row["user_id"],))
        cur2.execute("UPDATE UserActivationTokens SET used = 1 WHERE id = %s", (row["id"],))
        conn.commit()
        cur2.close()
        return MessageResponse(message="Your account has been activated. You can now log in.")
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@auth_router.post("/changePassword", response_model=MessageResponse)
def change_password(payload: ChangePasswordRequest, current_user: dict = Depends(authenticate_request)):
    """
    Change the password for the authenticated user.
    - Requires valid Bearer token.
    - Blocks Google sign-in users from changing password.
    - Verifies old password before updating.
    """
    try:
        user_id = int(current_user.get("id"))
        change_user_password(user_id, payload.old_password, payload.new_password)
        return MessageResponse(message="Password changed successfully")
    except Exception as e:
        # Map common error messages to appropriate HTTP codes if needed
        msg = str(e)
        if msg in ("User not found",):
            raise HTTPException(status_code=404, detail=msg)
        if msg in ("Old password is incorrect",):
            raise HTTPException(status_code=400, detail=msg)
        if msg in ("Google sign-in users cannot change password",):
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@auth_router.post("/GoogleCallBack")
async def google_callback(payload: dict):
    """Handle Google callback payload posted by client, create/find user and return internal JWT."""
    # Log incoming payload
    print("[auth/GoogleCallBack] payload:", payload)

    # Try to extract profile/email/name from common shapes
    profile = None
    if isinstance(payload.get("profile"), dict):
        profile = payload.get("profile")
    else:
        # Sometimes frontend may send top-level fields
        profile = payload

    email = profile.get("email") if isinstance(profile, dict) else None
    name = profile.get("name") if isinstance(profile, dict) else None

    # Fallback checks for alternate keys
    if not email:
        email = payload.get("email") or payload.get("emailAddress") or payload.get("user_email")
    if not name:
        name = payload.get("name") or payload.get("given_name") or payload.get("fullName")

    if not email:
        raise HTTPException(status_code=400, detail="Email not found in callback payload")

    # Check DB for existing user
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, role FROM Users WHERE email = %s", (email,))
        db_user = cursor.fetchone()

        if db_user:
            user_id = db_user["id"]
            user_name = db_user.get("name") or name or ""
            user_role = db_user.get("role") or "User"
        else:
            # Create a random password for users created via provider
            rand_pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
            # Use Models.authModel.UserRegistration to register
            from Models.authModel import UserRegistration

            new_user = UserRegistration(
                name=name or email.split("@")[0],
                email=email,
                password=rand_pw,
                phone="",
                provider="google",
                role="User"
            )
            user_id = register_user(new_user)
            user_name = new_user.name
            user_role = new_user.role

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    # Try to extract picture/avatar from payload (common keys and nested structures)
    picture = None
    # Prefer profile.picture when present
    if isinstance(profile, dict):
        picture = profile.get("picture")

    # Fallback top-level keys
    if not picture:
        picture = payload.get("picture") or payload.get("avatar") or payload.get("photoUrl") or payload.get("photo_url")

    # Some providers include photos as a list inside profile
    if not picture and isinstance(profile, dict):
        photos = profile.get("photos") or profile.get("photos[]")
        if isinstance(photos, list) and photos:
            first = photos[0]
            if isinstance(first, dict):
                picture = first.get("value") or first.get("url")
            elif isinstance(first, str):
                picture = first

    # Create internal JWT (include picture if found)
    claims = {"id": user_id, "name": user_name, "email": email, "role": user_role}
    if picture:
        claims["picture"] = picture
    token = create_jwt_token(claims)
    # Record login event for Google sign-in
    try:
        record_user_login(user_id, "google")
    except Exception:
        pass

    return {"access_token": token, "token_type": "bearer"}

