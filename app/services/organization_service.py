"""Organization service for organization management."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timezone
import uuid

from app.models import Organization, OrganizationMember, MemberRole, User
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ValidationException,
)
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    """Service for organization operations."""
    
    @staticmethod
    async def create_organization(
        org_create: OrganizationCreate,
        owner_id: uuid.UUID,
        db: AsyncSession,
    ) -> Organization:
        """Create a new organization with the user as owner.
        
        Args:
            org_create: Organization creation data
            owner_id: User ID of the organization owner
            db: Database session
            
        Returns:
            Created organization
            
        Raises:
            ConflictException: If slug already exists
        """
        # Check if slug already exists
        stmt = select(Organization).where(Organization.slug == org_create.slug.lower())
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ConflictException(f"Organization slug '{org_create.slug}' already exists")
        
        # Create organization
        organization = Organization(
            id=uuid.uuid4(),
            name=org_create.name,
            slug=org_create.slug.lower(),
            description=org_create.description,
            website_url=org_create.website_url,
            logo_url=org_create.logo_url,
            is_active=True,
        )
        
        db.add(organization)
        await db.flush()  # Flush to get the ID
        
        # Add owner as member
        owner_member = OrganizationMember(
            id=uuid.uuid4(),
            organization_id=organization.id,
            user_id=owner_id,
            role=MemberRole.OWNER,
            joined_at=datetime.now(timezone.utc),
        )
        
        db.add(owner_member)
        await db.commit()
        await db.refresh(organization)
        
        return organization
    
    @staticmethod
    async def get_organization_by_id(
        org_id: uuid.UUID,
        db: AsyncSession,
    ) -> Organization:
        """Get organization by ID.
        
        Args:
            org_id: Organization ID
            db: Database session
            
        Returns:
            Organization
            
        Raises:
            NotFoundException: If organization not found
        """
        stmt = select(Organization).where(Organization.id == org_id)
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()
        
        if not org:
            raise NotFoundException("Organization", org_id)
        
        return org
    
    @staticmethod
    async def get_organization_by_slug(
        slug: str,
        db: AsyncSession,
    ) -> Organization:
        """Get organization by slug.
        
        Args:
            slug: Organization slug
            db: Database session
            
        Returns:
            Organization or None if not found
        """
        stmt = select(Organization).where(Organization.slug == slug.lower())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_organizations(
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[Organization]:
        """Get all organizations a user is a member of.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            List of organizations
        """
        stmt = (
            select(Organization)
            .join(OrganizationMember)
            .where(
                (OrganizationMember.user_id == user_id)
                & (Organization.is_active is True)
            )
            .order_by(Organization.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def update_organization(
        org_id: uuid.UUID,
        org_update: OrganizationUpdate,
        db: AsyncSession,
    ) -> Organization:
        """Update organization.
        
        Args:
            org_id: Organization ID
            org_update: Organization update data
            db: Database session
            
        Returns:
            Updated organization
            
        Raises:
            NotFoundException: If organization not found
        """
        org = await OrganizationService.get_organization_by_id(org_id, db)
        
        update_data = org_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(org, key, value)
        
        org.updated_at = datetime.now(timezone.utc)
        db.add(org)
        await db.commit()
        await db.refresh(org)
        
        return org
    
    @staticmethod
    async def verify_user_organization_access(
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        db: AsyncSession,
    ) -> bool:
        """Verify user has access to organization.
        
        Args:
            user_id: User ID
            org_id: Organization ID
            db: Database session
            
        Returns:
            True if user has access, False otherwise
        """
        stmt = (
            select(OrganizationMember)
            .where(
                (OrganizationMember.user_id == user_id)
                & (OrganizationMember.organization_id == org_id)
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
