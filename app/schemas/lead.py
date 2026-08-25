"""Lead schemas for request/response validation."""
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from uuid import UUID
from typing import Optional


class LeadBase(BaseModel):
    """Base lead schema."""
    
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=255)


class LeadCreate(LeadBase):
    """Schema for lead creation."""
    
    project_id: UUID
    visitor_id: UUID
    conversation_id: Optional[UUID] = None


class LeadUpdate(BaseModel):
    """Schema for lead updates."""
    
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=255)
    project_type: Optional[str] = Field(None, max_length=100)
    budget: Optional[str] = Field(None, max_length=50)
    timeline: Optional[str] = Field(None, max_length=100)
    intent_score: Optional[int] = Field(None, ge=0, le=100)
    is_qualified: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)


class LeadStatusUpdate(BaseModel):
    """Schema for lead status update."""
    
    status: str = Field(..., description="Lead status")


class LeadResponse(LeadBase):
    """Schema for lead response."""
    
    id: UUID
    project_id: UUID
    visitor_id: UUID
    conversation_id: Optional[UUID] = None
    status: str
    project_type: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    intent_score: int
    is_qualified: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_contacted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LeadDetailResponse(LeadResponse):
    """Detailed lead response."""
    
    extraction_data: Optional[dict] = None
    extra_metadata: Optional[dict] = None


class LeadStatsResponse(BaseModel):
    """Lead statistics response."""
    
    total: int = Field(..., description="Total leads")
    qualified: int = Field(..., description="Number of qualified leads")
    conversion_rate: float = Field(..., description="Conversion rate percentage")
    by_status: dict = Field(..., description="Count by status")
    average_score: float = Field(..., description="Average qualification score")
