"""OrganizationMember model for user membership in organizations."""
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum as PyEnum
import uuid

from app.db.base import Base


class MemberRole(str, PyEnum):
    """Roles for organization members."""
    
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class OrganizationMember(Base):
    """Membership linking users to organizations with roles."""
    
    __tablename__ = "organization_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        Enum(MemberRole, name="member_role", create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        default=MemberRole.MEMBER,
        nullable=False,
    )
    invited_at = Column(DateTime(timezone=True))
    joined_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
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
    
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )
    
    def __repr__(self):
        return (
            f"<OrganizationMember(org_id={self.organization_id}, "
            f"user_id={self.user_id}, role={self.role})>"
        )
