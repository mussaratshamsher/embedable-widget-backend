"""Chat and AI schemas for request/response validation."""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class ChatMessageRequest(BaseModel):
    """Schema for sending a message to AI."""
    
    content: str = Field(..., min_length=1, max_length=5000, description="User message")


class ChatResponseChunk(BaseModel):
    """Schema for a chunk in SSE streaming response."""
    
    chunk: str = Field(..., description="Response text chunk")
    is_final: bool = Field(default=False, description="Whether this is final chunk")


class ChatResponse(BaseModel):
    """Schema for complete chat response."""
    
    message_id: UUID = Field(..., description="Message ID for assistant response")
    conversation_id: UUID = Field(..., description="Conversation ID")
    content: str = Field(..., description="Full response content")
    created_at: datetime = Field(..., description="Timestamp")
    
    class Config:
        from_attributes = True


class AIQualificationResponse(BaseModel):
    """Schema for AI lead qualification result."""
    
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    project_type: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    intent_score: int = Field(0, ge=0, le=100, description="Qualification score 0-100")
    qualified: bool = Field(False, description="Whether lead is qualified")


class ConversationUpdateRequest(BaseModel):
    """Schema for updating conversation."""
    
    status: Optional[str] = Field(None, description="New status")
