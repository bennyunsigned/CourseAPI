from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRegistration(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str
    provider: str = "local"
    role: str = "User"

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    provider: str
    role: str
    created_at: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

