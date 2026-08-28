import httpx
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional

from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate, WebhookUpdate
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class WebhookService:
    @staticmethod
    async def get_webhooks_by_project(project_id: UUID, db: AsyncSession) -> List[Webhook]:
        """Get all webhooks for a project."""
        query = select(Webhook).where(Webhook.project_id == project_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_webhook(webhook_in: WebhookCreate, db: AsyncSession) -> Webhook:
        """Create a new webhook."""
        # Convert HttpUrl to string for database
        webhook_data = webhook_in.model_dump()
        webhook_data["url"] = str(webhook_data["url"])
        
        db_webhook = Webhook(**webhook_data)
        db.add(db_webhook)
        await db.commit()
        await db.refresh(db_webhook)
        return db_webhook

    @staticmethod
    async def update_webhook(webhook_id: UUID, webhook_in: WebhookUpdate, db: AsyncSession) -> Webhook:
        """Update a webhook."""
        query = select(Webhook).where(Webhook.id == webhook_id)
        result = await db.execute(query)
        db_webhook = result.scalar_one_or_none()
        
        if not db_webhook:
            raise NotFoundException("Webhook not found")
            
        update_data = webhook_in.model_dump(exclude_unset=True)
        if "url" in update_data and update_data["url"] is not None:
            update_data["url"] = str(update_data["url"])
            
        for key, value in update_data.items():
            setattr(db_webhook, key, value)
            
        await db.commit()
        await db.refresh(db_webhook)
        return db_webhook

    @staticmethod
    async def delete_webhook(webhook_id: UUID, db: AsyncSession) -> None:
        """Delete a webhook."""
        query = select(Webhook).where(Webhook.id == webhook_id)
        result = await db.execute(query)
        db_webhook = result.scalar_one_or_none()
        
        if not db_webhook:
            raise NotFoundException("Webhook not found")
            
        await db.delete(db_webhook)
        await db.commit()

    @staticmethod
    async def dispatch_lead_webhook(project_id: UUID, lead_data: dict, db: AsyncSession) -> None:
        """
        Background task to dispatch webhook when a lead is created.
        Finds active webhooks for the project and sends a POST request with the lead data.
        """
        webhooks = await WebhookService.get_webhooks_by_project(project_id, db)
        
        active_webhooks = [w for w in webhooks if w.is_active]
        if not active_webhooks:
            return
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            for webhook in active_webhooks:
                try:
                    logger.info(f"Dispatching lead data to webhook {webhook.url}")
                    # In a production app, you'd probably want a retry mechanism or queue
                    response = await client.post(
                        webhook.url,
                        json={"event": "lead.created", "data": lead_data}
                    )
                    response.raise_for_status()
                except Exception as e:
                    logger.error(f"Failed to dispatch webhook to {webhook.url}: {str(e)}")
