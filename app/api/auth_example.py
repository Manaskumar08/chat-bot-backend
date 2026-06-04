"""
Authentication API Routes
Complete implementation with models and schemas
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.models.auth import (
    create_access_token,
)

# Models and Schemas
from app.models import (
    User,
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    get_db,
)

TOKEN_EXPIRE_MINUTES = 60  # Token expiration time in minutes

# Security utilities
from app.auth.security import hash_password, verify_password

router = APIRouter()


# ==================== SIGNUP ENDPOINT ====================

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    Args:
        user_data: User registration data (email, name, password)
        db: Database session
        
    Returns:
        TokenResponse: JWT token and user info
        
    Raises:
        HTTPException: If email already exists
    """
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        name=user_data.name,
        password=hash_password(user_data.password),
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate token
    access_token = create_access_token({
        "user_id": new_user.id,
        "email": new_user.email
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(new_user)
    }


# ==================== LOGIN ENDPOINT ====================

@router.post("/login", response_model=TokenResponse)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token
    
    Args:
        credentials: User login credentials (email, password)
        db: Database session
        
    Returns:
        TokenResponse: JWT token and user info
        
    Raises:
        HTTPException: If credentials are invalid
    """
    
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Generate token
    access_token = create_access_token({
        "user_id": user.id,
        "email": user.email
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }


# ==================== GET CURRENT USER DEPENDENCY ====================

async def get_current_user(
    authorization: str = None,
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Dependency to get current authenticated user
    
    Usage in routes:
        @app.get("/profile")
        def get_profile(current_user: UserResponse = Depends(get_current_user)):
            return current_user
    
    Args:
        authorization: Authorization header (Bearer token)
        db: Database session
        
    Returns:
        UserResponse: Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    
    from app.models.auth import decode_access_token
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer token" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode token
    token_data = decode_access_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = db.query(User).filter(User.id == token_data.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return UserResponse.from_orm(user)


# ==================== USER PROFILE ENDPOINT ====================

@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get current user profile
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: User profile data
    """
    return current_user


# ==================== CHANGE PASSWORD ENDPOINT ====================

from pydantic import BaseModel

class ChangePasswordRequest(BaseModel):
    """Schema for password change"""
    old_password: str
    new_password: str


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    
    Args:
        password_data: Old and new password
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If old password is incorrect
    """
    
    # Get user from database
    user = db.query(User).filter(User.id == current_user.id).first()
    
    # Verify old password
    if not verify_password(password_data.old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
    
    # Update password
    user.password = hash_password(password_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


# ==================== LOGOUT ENDPOINT ====================

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Logout user (client should discard token)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
    """
    return {"message": f"User {current_user.email} logged out successfully"}
