"""Organization schemas for request/response validation."""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class OrganizationBase(BaseModel):
    """Base organization schema."""
    
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)
    website_url: Optional[str] = Field(None, max_length=500)
    logo_url: Optional[str] = Field(None, max_length=500)


class OrganizationCreate(OrganizationBase):
    """Schema for organization creation."""
    pass


class OrganizationUpdate(BaseModel):
    """Schema for organization updates."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    website_url: Optional[str] = Field(None, max_length=500)
    logo_url: Optional[str] = Field(None, max_length=500)


class OrganizationResponse(OrganizationBase):
    """Schema for organization response."""
    
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrganizationDetailResponse(OrganizationResponse):
    """Detailed organization response with member count."""
    
    member_count: Optional[int] = None
