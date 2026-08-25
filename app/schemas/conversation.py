"""Visitor and conversation schemas for request/response validation."""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional
from enum import Enum


class ConversationStatus(str, Enum):
    """Conversation status options."""
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class MessageRole(str, Enum):
    """Message sender role."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class VisitorBase(BaseModel):
    """Base visitor schema."""
    pass


class VisitorCreate(BaseModel):
    """Schema for visitor session creation (from widget)."""
    
    project_api_key: str = Field(..., description="Project API key from widget")
    extra_metadata: Optional[dict] = Field(None, description="Custom visitor data")


class VisitorResponse(BaseModel):
    """Schema for visitor response."""
    
    id: UUID
    visitor_identifier: str
    project_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """Base conversation schema."""
    pass


class ConversationCreate(BaseModel):
    """Schema for conversation creation."""
    
    project_api_key: str = Field(..., description="Project API key")
    visitor_identifier: str = Field(..., description="Visitor identifier")
    recaptcha_token: Optional[str] = Field(None, description="Google reCAPTCHA token")


class ConversationResponse(BaseModel):
    """Schema for conversation response."""
    
    id: UUID
    project_id: UUID
    visitor_id: UUID
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Schema for message creation."""
    
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    """Schema for message response."""
    
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    """Detailed conversation with messages."""
    
    messages: Optional[list[MessageResponse]] = None
    message_count: Optional[int] = None
