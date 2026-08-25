"""Authentication schemas for request/response validation."""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class UserBase(BaseModel):
    """Base user schema."""
    
    email: EmailStr = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration."""
    
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")


class UserLogin(BaseModel):
    """Schema for user login."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(UserBase):
    """Schema for user response."""
    
    id: UUID
    is_active: bool
    is_superadmin: bool = False
    role: str = "user"
    plan: str = "free"
    subscription_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for token response."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse


class TokenData(BaseModel):
    """Schema for JWT token data."""
    
    user_id: UUID
    email: str
    organization_id: Optional[UUID] = None
