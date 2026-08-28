"""Webhooks API endpoints for managing external integrations."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.db.database import get_db
from app.services.webhook_service import WebhookService
from app.services.project_service import ProjectService
from app.services.organization_service import OrganizationService
from app.schemas.webhook import WebhookCreate, WebhookUpdate, WebhookResponse
from app.core.exceptions import NotFoundException
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


async def verify_project_access(project_id: UUID, user_id: UUID, db: AsyncSession):
    """Helper to verify user has access to project's organization."""
    try:
        project = await ProjectService.get_project_by_id(project_id, db)
        has_access = await OrganizationService.verify_user_organization_access(
            user_id, project.organization_id, db
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project's webhooks",
            )
        return project
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.get(
    "/project/{project_id}",
    response_model=List[WebhookResponse],
    summary="List webhooks for a project",
)
async def list_webhooks(
    project_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_project_access(project_id, current_user.id, db)
    return await WebhookService.get_webhooks_by_project(project_id, db)


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new webhook",
)
async def create_webhook(
    webhook_in: WebhookCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_project_access(webhook_in.project_id, current_user.id, db)
    return await WebhookService.create_webhook(webhook_in, db)


@router.patch(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update a webhook",
)
async def update_webhook(
    webhook_id: UUID,
    webhook_in: WebhookUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        from sqlalchemy import text
        query = await db.execute(
            text("SELECT project_id FROM webhooks WHERE id = :id"), {"id": webhook_id}
        )
        result = query.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        project_id = result[0]
        await verify_project_access(project_id, current_user.id, db)
        
        return await WebhookService.update_webhook(webhook_id, webhook_in, db)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook",
)
async def delete_webhook(
    webhook_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        from sqlalchemy import text
        query = await db.execute(
            text("SELECT project_id FROM webhooks WHERE id = :id"), {"id": webhook_id}
        )
        result = query.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Webhook not found")
            
        project_id = result[0]
        await verify_project_access(project_id, current_user.id, db)
        
        await WebhookService.delete_webhook(webhook_id, db)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message)
