"""Projects API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.database import get_db
from app.services.project_service import ProjectService
from app.services.organization_service import OrganizationService
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse,
)
from app.core.exceptions import NotFoundException, ConflictException
from app.dependencies.auth import get_current_user


router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
    description="Create a new AI widget project",
)
async def create_project(
    project_create: ProjectCreate,
    organization_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project.
    
    Query parameter:
    - **organization_id**: Organization to create project in (user must be a member)
    
    Request body:
    - **name**: Project name
    - **website_url**: Website URL for the widget
    - **description**: Optional project description
    - **business_type**: Optional business type
    - **ai_instructions**: Optional custom AI instructions
    - **welcome_message**: Optional welcome message for visitors
    """
    try:
        # Verify user has access to organization
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, organization_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization",
            )
        
        project = await ProjectService.create_project(
            project_create, organization_id, db, user=current_user
        )
        return ProjectResponse.model_validate(project)
    except ConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List projects",
    description="Get all projects in an organization",
)
async def list_projects(
    organization_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all projects in an organization.
    
    Query parameter:
    - **organization_id**: Organization ID (user must be a member)
    """
    try:
        # Verify user has access to organization
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, organization_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization",
            )
        
        projects = await ProjectService.get_organization_projects(organization_id, db)
        return [ProjectResponse.model_validate(p) for p in projects]
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.get(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Get project details",
    description="Get details of a specific project",
)
async def get_project(
    project_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project details.
    
    User must be a member of the project's organization.
    """
    try:
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
        
        return ProjectDetailResponse.model_validate(project)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
    description="Update project configuration",
)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update project configuration.
    
    User must be a member of the project's organization.
    """
    try:
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
        
        updated = await ProjectService.update_project(project_id, project_update, db)
        return ProjectResponse.model_validate(updated)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Delete a project (soft delete)",
)
async def delete_project(
    project_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project.
    
    User must be a member of the project's organization.
    """
    try:
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
        
        await ProjectService.delete_project(project_id, db)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.post(
    "/{project_id}/regenerate-api-key",
    response_model=ProjectResponse,
    summary="Regenerate API key",
    description="Generate a new API key for the project",
)
async def regenerate_api_key(
    project_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate project API key.
    
    User must be a member of the project's organization.
    """
    try:
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
        
        updated = await ProjectService.regenerate_api_key(project_id, db)
        return ProjectResponse.model_validate(updated)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
