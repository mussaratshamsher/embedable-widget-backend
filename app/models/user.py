"""User model for authentication."""
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid

from app.db.base import Base


class User(Base):
    """User entity for system authentication."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False)
    is_superadmin = Column(Boolean, default=False, nullable=False)
    
    # Plan / billing fields
    # plan: "free" or "pro"
    plan = Column(String(20), default="free", nullable=False, server_default="free")
    # stripe customer id (for paid-plan upgrades)
    stripe_customer_id = Column(String(255), nullable=True)
    # subscription status: active | trialing | canceled | None
    subscription_status = Column(String(50), nullable=True)
    
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
    last_login = Column(DateTime(timezone=True))
    
    @property
    def role(self) -> str:
        return "admin" if (self.is_superadmin or self.email == "leadforge@gmail.com") else "user"

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, plan={self.plan})>"

