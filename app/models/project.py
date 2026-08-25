"""Project model for AI widget configuration."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime, timezone
from enum import Enum as PyEnum
import uuid

from app.db.base import Base


class ProjectStatus(str, PyEnum):
    """Status of a project."""
    
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Project(Base):
    """Project entity - represents a website/instance getting the widget."""
    
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    website_url = Column(String(500), nullable=False)
    description = Column(Text)
    business_type = Column(String(100))
    ai_instructions = Column(Text)
    welcome_message = Column(Text)
    status = Column(
        Enum(ProjectStatus, name="project_status", create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        default=ProjectStatus.DRAFT,
        nullable=False,
    )
    # API key for widget authentication
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    extra_metadata = Column("metadata", JSON, default={}, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, org_id={self.organization_id})>"
