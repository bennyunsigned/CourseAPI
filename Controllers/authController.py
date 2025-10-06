from fastapi import APIRouter, HTTPException, Depends
from Models.authModel import UserRegistration, UserResponse, UserLogin, LoginResponse
from Services.authService import register_user, login_user
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

@auth_router.post("/register", response_model=UserResponse)
def register(user: UserRegistration):
    """
    Register a new user.
    """
    try:
        user_id = register_user(user)
        return UserResponse(
            id=user_id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            provider=user.provider,
            role=user.role,
            created_at="Now"  # Replace with actual timestamp from DB if needed
        )
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

    return {"access_token": token, "token_type": "bearer"}

