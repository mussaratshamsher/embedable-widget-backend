"""Visitor model for tracking widget users."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime, timezone
import uuid

from app.db.base import Base


class Visitor(Base):
    """Visitor entity - represents a website visitor using the widget."""
    
    __tablename__ = "visitors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Anonymous visitor identifier
    visitor_identifier = Column(String(255), unique=True, nullable=False, index=True)
    # IP address (anonymized if needed)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    # Custom visitor metadata
    extra_metadata = Column("metadata", JSON, default={}, nullable=False)
    first_seen = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_seen = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
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
        return f"<Visitor(id={self.id}, project_id={self.project_id})>"
