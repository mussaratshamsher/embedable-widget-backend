"""Organization API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.database import get_db
from app.services.organization_service import OrganizationService
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationDetailResponse,
)
from app.core.exceptions import ConflictException, NotFoundException
from app.dependencies.auth import get_current_user


router = APIRouter(prefix="/api/organizations", tags=["Organizations"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Create a new organization (user becomes owner)",
)
async def create_organization(
    org_create: OrganizationCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization.
    
    - **name**: Organization name
    - **slug**: URL-friendly identifier (lowercase, hyphens only)
    - **description**: Optional description
    - **website_url**: Optional website URL
    - **logo_url**: Optional logo URL
    
    The authenticated user becomes the organization owner.
    """
    try:
        org = await OrganizationService.create_organization(
            org_create, current_user.id, db, user=current_user
        )
        return OrganizationResponse.model_validate(org)
    except ConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


@router.get(
    "",
    response_model=list[OrganizationResponse],
    summary="List user's organizations",
    description="Get all organizations the current user is a member of",
)
async def list_organizations(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all organizations the current user is a member of."""
    orgs = await OrganizationService.get_user_organizations(current_user.id, db)
    return [OrganizationResponse.model_validate(org) for org in orgs]


@router.get(
    "/{org_id}",
    response_model=OrganizationDetailResponse,
    summary="Get organization details",
    description="Get details of a specific organization",
)
async def get_organization(
    org_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get organization details.
    
    User must be a member of the organization.
    """
    try:
        # Verify user has access to organization
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, org_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization",
            )
        
        org = await OrganizationService.get_organization_by_id(org_id, db)
        return OrganizationDetailResponse.model_validate(org)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.patch(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Update organization",
    description="Update organization details",
)
async def update_organization(
    org_id: UUID,
    org_update: OrganizationUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update organization details.
    
    User must be an owner or admin of the organization.
    """
    try:
        # Verify user has access to organization
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, org_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization",
            )
        
        org = await OrganizationService.update_organization(org_id, org_update, db)
        return OrganizationResponse.model_validate(org)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete organization",
    description="Delete an organization (soft delete by setting inactive)",
)
async def delete_organization(
    org_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an organization.
    
    User must be a member/owner of the organization.
    """
    try:
        # Verify user has access to organization
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, org_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization",
            )
        
        await OrganizationService.delete_organization(org_id, db)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

