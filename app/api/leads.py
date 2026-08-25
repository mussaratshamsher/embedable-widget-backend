"""Leads API endpoints for managing qualified leads."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.database import get_db
from app.services.lead_service import LeadService
from app.services.project_service import ProjectService
from app.services.organization_service import OrganizationService
from app.schemas.lead import (
    LeadResponse,
    LeadDetailResponse,
    LeadUpdate,
    LeadStatusUpdate,
    LeadStatsResponse,
)
from app.core.exceptions import NotFoundException, ValidationException
from app.dependencies.auth import get_current_user


router = APIRouter(prefix="/api/leads", tags=["Leads"])


@router.get(
    "",
    response_model=list[LeadResponse],
    summary="List project leads",
    description="Get all leads in a project",
)
async def list_leads(
    project_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lead_status: str = Query(None, description="Filter by status: new, contacted, qualified, converted, lost"),
    qualified_only: bool = Query(False, description="Show only qualified leads"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all leads in a project.
    
    Query parameters:
    - **project_id**: Project ID (user must have access)
    - **lead_status**: Filter by status (new, contacted, qualified, converted, lost)
    - **qualified_only**: Only show qualified leads
    - **limit**: Number of results (default 50, max 500)
    - **offset**: Results to skip (default 0)
    
    User must be a member of the project's organization.
    """
    try:
        # Get project
        project = await ProjectService.get_project_by_id(project_id, db)
        
        # Verify user has access to organization
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, project.organization_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project",
            )
        
        leads = await LeadService.get_project_leads(
            project_id,
            db,
            status=lead_status,
            qualified_only=qualified_only,
            limit=limit,
            offset=offset,
        )
        
        return [LeadResponse.model_validate(lead) for lead in leads]
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


# NOTE: This route MUST come before /{lead_id} to avoid being swallowed by the wildcard.
@router.get(
    "/stats/project/{project_id}",
    response_model=LeadStatsResponse,
    summary="Get lead statistics",
    description="Get statistics for leads in a project",
)
async def get_lead_stats(
    project_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get lead statistics for a project.
    
    Includes total count, qualified count, conversion rate, and breakdown by status.
    
    User must be a member of the project's organization.
    """
    try:
        # Get project
        project = await ProjectService.get_project_by_id(project_id, db)
        
        # Verify user has access to organization
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, project.organization_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project",
            )
        
        stats = await LeadService.get_project_lead_stats(project_id, db)
        
        return LeadStatsResponse(**stats)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.get(
    "/{lead_id}",
    response_model=LeadDetailResponse,
    summary="Get lead details",
    description="Get detailed information about a lead",
)
async def get_lead(
    lead_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get lead details.
    
    User must be a member of the lead's project's organization.
    """
    try:
        lead = await LeadService.get_lead_by_id(lead_id, db)
        
        # Verify user has access to organization
        project = await ProjectService.get_project_by_id(lead.project_id, db)
        
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, project.organization_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this lead",
            )
        
        return LeadDetailResponse.model_validate(lead)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Update lead",
    description="Update lead details",
)
async def update_lead(
    lead_id: UUID,
    lead_update: LeadUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update lead details.
    
    User must be a member of the lead's project's organization.
    """
    try:
        lead = await LeadService.get_lead_by_id(lead_id, db)
        
        # Verify user has access to organization
        project = await ProjectService.get_project_by_id(lead.project_id, db)
        
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, project.organization_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this lead",
            )
        
        update_data = lead_update.model_dump(exclude_unset=True)
        updated_lead = await LeadService.update_lead(lead_id, update_data, db)
        
        return LeadResponse.model_validate(updated_lead)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.post(
    "/{lead_id}/status",
    response_model=LeadResponse,
    summary="Update lead status",
    description="Change lead status",
)
async def update_lead_status(
    lead_id: UUID,
    status_update: LeadStatusUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update lead status.
    
    Valid statuses: new, contacted, qualified, converted, lost
    
    User must be a member of the lead's project's organization.
    """
    try:
        lead = await LeadService.get_lead_by_id(lead_id, db)
        
        # Verify user has access to organization
        project = await ProjectService.get_project_by_id(lead.project_id, db)
        
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, project.organization_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this lead",
            )
        
        updated_lead = await LeadService.update_lead_status(
            lead_id, status_update.status, db
        )
        
        return LeadResponse.model_validate(updated_lead)
    except (NotFoundException, ValidationException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if isinstance(e, ValidationException) else status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
