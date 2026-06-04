"""
Authentication Models and Token Management
JWT token handling and authentication data structures
"""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from jose import jwt, JWTError
from app.models.config import get_settings

settings = get_settings()

# Token configuration
TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


class TokenData(BaseModel):
    """Token payload data"""
    email: Optional[str] = None
    user_id: Optional[int] = None
    exp: Optional[datetime] = None


class TokenPayload(BaseModel):
    """Complete token payload"""
    sub: str  # subject (usually user_id or email)
    user_id: int
    email: str
    exp: datetime
    iat: datetime


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    
    Args:
        data: Token payload data
        expires_delta: Custom expiration time delta
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate JWT access token
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData: Decoded token data or None if invalid
        
    Raises:
        JWTError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        
        email: str = payload.get("email")
        user_id: int = payload.get("user_id")
        
        if email is None or user_id is None:
            return None
            
        return TokenData(
            email=email,
            user_id=user_id,
            exp=datetime.fromtimestamp(payload.get("exp"))
        )
        
    except JWTError:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if token is expired
    
    Args:
        token: JWT token string
        
    Returns:
        bool: True if expired, False otherwise
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        exp = payload.get("exp")
        if exp is None:
            return True
        
        return datetime.fromtimestamp(exp) <= datetime.utcnow()
        
    except JWTError:
        return True
