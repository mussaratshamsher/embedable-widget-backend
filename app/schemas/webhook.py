from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class WebhookBase(BaseModel):
    url: HttpUrl = Field(..., description="The URL to send the webhook to")
    is_active: bool = Field(True, description="Whether the webhook is active")


class WebhookCreate(WebhookBase):
    project_id: UUID = Field(..., description="The ID of the project this webhook belongs to")


class WebhookUpdate(BaseModel):
    url: Optional[HttpUrl] = Field(None, description="The URL to send the webhook to")
    is_active: Optional[bool] = Field(None, description="Whether the webhook is active")


class WebhookResponse(WebhookBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # ensure pydantic v2 compatible dict conversion for HttpUrl
    class Config:
        from_attributes = True
