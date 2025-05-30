import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta

SECRET_KEY = "abcd@1234"  # Replace with a secure key
ALGORITHM = "HS256"

security = HTTPBearer()

def create_jwt_token(claims: dict) -> str:
    """
    Create a JWT token with the given claims.
    """
    expiration = datetime.utcnow() + timedelta(hours=1)  # Token valid for 1 hour
    claims.update({"exp": expiration})
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_request(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Validate the JWT token from the Authorization header.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # Return the decoded claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
def authenticate_request_role(credentials: HTTPAuthorizationCredentials = Security(security), required_role: str = None) -> dict:
    """
    Validate the JWT token and optionally check for a required role.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if required_role and payload.get("role") != required_role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")