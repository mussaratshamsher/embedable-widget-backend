"""Admin API endpoints for platform-wide metrics and resource management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.models import User, Organization, OrganizationMember, Project, Lead, Conversation, Message, MemberRole
from app.dependencies.auth import get_current_admin_user
from app.services.organization_service import OrganizationService
from app.services.project_service import ProjectService


router = APIRouter(prefix="/api/admin", tags=["Admin"])


class AdminStatsResponse(BaseModel):
    total_users: int
    total_organizations: int
    total_projects: int
    total_leads: int
    total_conversations: int
    total_messages: int


class AdminOrgItem(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    website_url: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    owner_email: Optional[str] = None
    owner_name: Optional[str] = None
    project_count: int = 0


class AdminProjectItem(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: Optional[str] = None
    name: str
    website_url: str
    description: Optional[str] = None
    business_type: Optional[str] = None
    status: str
    api_key: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    lead_count: int = 0
    conversation_count: int = 0
    owner_email: Optional[str] = None


class AdminUserItem(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_superadmin: bool
    plan: str
    created_at: datetime
    last_login: Optional[datetime] = None


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get platform-wide statistics",
    description="Get platform-wide metrics (Admin only)",
)
async def get_admin_stats(
    admin_user=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve global statistics across all users and organizations."""
    users_count = await db.scalar(select(func.count(User.id))) or 0
    orgs_count = await db.scalar(select(func.count(Organization.id))) or 0
    projects_count = await db.scalar(select(func.count(Project.id))) or 0
    leads_count = await db.scalar(select(func.count(Lead.id))) or 0
    convs_count = await db.scalar(select(func.count(Conversation.id))) or 0
    msgs_count = await db.scalar(select(func.count(Message.id))) or 0

    return AdminStatsResponse(
        total_users=users_count,
        total_organizations=orgs_count,
        total_projects=projects_count,
        total_leads=leads_count,
        total_conversations=convs_count,
        total_messages=msgs_count,
    )


@router.get(
    "/organizations",
    response_model=List[AdminOrgItem],
    summary="Get all platform organizations",
    description="Retrieve all organizations created by any user across the app",
)
async def get_all_organizations(
    admin_user=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all organizations in the platform with owner details and project count."""
    stmt = select(Organization).order_by(Organization.created_at.desc())
    result = await db.execute(stmt)
    orgs = result.scalars().all()

    items: List[AdminOrgItem] = []
    for org in orgs:
        # Find owner
        owner_stmt = (
            select(User)
            .join(OrganizationMember, User.id == OrganizationMember.user_id)
            .where(
                (OrganizationMember.organization_id == org.id)
                & (OrganizationMember.role == MemberRole.OWNER)
            )
        )
        owner_res = await db.execute(owner_stmt)
        owner = owner_res.scalar_one_or_none()

        # Count projects
        p_count = await db.scalar(
            select(func.count(Project.id)).where(Project.organization_id == org.id)
        ) or 0

        items.append(
            AdminOrgItem(
                id=org.id,
                name=org.name,
                slug=org.slug,
                description=org.description,
                website_url=org.website_url,
                logo_url=org.logo_url,
                is_active=org.is_active,
                created_at=org.created_at,
                updated_at=org.updated_at,
                owner_email=owner.email if owner else None,
                owner_name=f"{owner.first_name or ''} {owner.last_name or ''}".strip() if owner else None,
                project_count=p_count,
            )
        )
    return items


@router.get(
    "/projects",
    response_model=List[AdminProjectItem],
    summary="Get all platform projects",
    description="Retrieve all projects created across the entire app",
)
async def get_all_projects(
    admin_user=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all projects across the platform with organization and stats."""
    stmt = select(Project).order_by(Project.created_at.desc())
    result = await db.execute(stmt)
    projects = result.scalars().all()

    items: List[AdminProjectItem] = []
    for p in projects:
        # Organization
        org = await db.get(Organization, p.organization_id)

        # Owner
        owner_email = None
        if org:
            owner_stmt = (
                select(User.email)
                .join(OrganizationMember, User.id == OrganizationMember.user_id)
                .where(
                    (OrganizationMember.organization_id == org.id)
                    & (OrganizationMember.role == MemberRole.OWNER)
                )
            )
            owner_email = await db.scalar(owner_stmt)

        # Leads count
        leads_count = await db.scalar(
            select(func.count(Lead.id)).where(Lead.project_id == p.id)
        ) or 0

        # Conversations count
        convs_count = await db.scalar(
            select(func.count(Conversation.id)).where(Conversation.project_id == p.id)
        ) or 0

        items.append(
            AdminProjectItem(
                id=p.id,
                organization_id=p.organization_id,
                organization_name=org.name if org else "Unknown",
                name=p.name,
                website_url=p.website_url,
                description=p.description,
                business_type=p.business_type,
                status=p.status.value if hasattr(p.status, "value") else str(p.status),
                api_key=p.api_key,
                is_active=p.is_active,
                created_at=p.created_at,
                updated_at=p.updated_at,
                lead_count=leads_count,
                conversation_count=convs_count,
                owner_email=owner_email,
            )
        )
    return items


@router.get(
    "/users",
    response_model=List[AdminUserItem],
    summary="Get all users",
    description="Retrieve all registered users",
)
async def get_all_users(
    admin_user=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all registered users in the platform."""
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    return [
        AdminUserItem(
            id=u.id,
            email=u.email,
            first_name=u.first_name,
            last_name=u.last_name,
            is_active=u.is_active,
            is_superadmin=u.is_superadmin,
            plan=u.plan or "free",
            created_at=u.created_at,
            last_login=u.last_login,
        )
        for u in users
    ]


@router.delete(
    "/organizations/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Admin delete organization",
    description="Administratively delete any organization and its cascading resources",
)
async def admin_delete_organization(
    org_id: UUID,
    admin_user=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an organization as admin."""
    await OrganizationService.delete_organization(org_id, db)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Admin delete project",
    description="Administratively delete any project and its cascading resources",
)
async def admin_delete_project(
    project_id: UUID,
    admin_user=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project as admin."""
    await ProjectService.delete_project(project_id, db)
