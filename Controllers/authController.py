from fastapi import APIRouter, HTTPException,Depends
from Models.authModel import UserRegistration, UserResponse, UserLogin, LoginResponse
from Services.authService import register_user, login_user
from Utils.JWT import authenticate_request


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

