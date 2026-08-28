"""Webhook model for external integrations."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid

from app.db.base import Base


class Webhook(Base):
    """Webhook entity - represents external webhook URLs for sending data to external CRMs."""
    
    __tablename__ = "webhooks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    url = Column(String(1024), nullable=False)
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
        return f"<Webhook(id={self.id}, project_id={self.project_id}, url={self.url})>"
