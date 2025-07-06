import jwt as pyjwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, status
from .config import Settings

settings = Settings()

def create_jwt_token(data: Dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(
        to_encode, 
        settings.jwt_secret, 
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt

def verify_jwt_token(token: str) -> Dict:
    """Verify and decode a JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Remove Bearer prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        payload = pyjwt.decode(
            token, 
            settings.jwt_secret, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.JWTError:
        raise credentials_exception