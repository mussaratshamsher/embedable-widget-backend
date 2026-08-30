"""Project schemas for request/response validation."""
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from uuid import UUID
from typing import Optional
from enum import Enum


class ProjectStatus(str, Enum):
    """Project status options."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ProjectBase(BaseModel):
    """Base project schema."""
    
    name: str = Field(..., min_length=1, max_length=255)
    website_url: str = Field(..., max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    business_type: Optional[str] = Field(None, max_length=100)
    ai_instructions: Optional[str] = Field(None, max_length=5000)
    welcome_message: Optional[str] = Field(None, max_length=1000)
    theme_color: Optional[str] = Field(None, max_length=50)
    allowed_domains: Optional[list[str]] = Field(default_factory=list, description="List of domains allowed to use this widget")


class ProjectCreate(ProjectBase):
    """Schema for project creation."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for project updates."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    website_url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    business_type: Optional[str] = Field(None, max_length=100)
    ai_instructions: Optional[str] = Field(None, max_length=5000)
    welcome_message: Optional[str] = Field(None, max_length=1000)
    theme_color: Optional[str] = Field(None, max_length=50)
    allowed_domains: Optional[list[str]] = Field(None, description="List of domains allowed to use this widget")
    status: Optional[ProjectStatus] = None

class ProjectResponse(ProjectBase):
    """Schema for project response."""
    
    id: UUID
    organization_id: UUID
    status: ProjectStatus
    api_key: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """Detailed project response."""
    
    conversation_count: Optional[int] = None
    lead_count: Optional[int] = None
