"""
Pydantic Schemas
Request and response schemas for API validation and serialization
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List


# ==================== User Schemas ====================

class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=100, description="User name")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """Schema for user response data"""
    id: int
    email: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Token Schemas ====================

class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: Optional[UserResponse] = Field(None, description="User information")


class TokenData(BaseModel):
    """Schema for token data payload"""
    email: str
    user_id: int
    exp: Optional[int] = None  # Expiration time


# ==================== Conversation Schemas ====================

class ConversationCreate(BaseModel):
    """Schema for creating a conversation"""
    title: str = Field(..., min_length=1, max_length=200, description="Conversation title")


class ConversationResponse(BaseModel):
    """Schema for conversation response"""
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Message Schemas ====================

class MessageCreate(BaseModel):
    """Schema for creating a message"""
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., min_length=1, description="Message content")


class MessageResponse(BaseModel):
    """Schema for message response"""
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Audio/Voice Schemas ====================

class VoiceMessageRequest(BaseModel):
    """Schema for voice message processing"""
    conversation_id: int
    audio_url: Optional[str] = None


class VoiceMessageResponse(BaseModel):
    """Schema for voice message response"""
    user_text: str
    ai_text: str
    audio_file: Optional[str] = None


# ==================== Error Schemas ====================

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
