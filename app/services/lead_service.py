"""Lead service for managing qualified leads."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timezone
import uuid

from app.models import Lead, Conversation, Visitor, Project
from app.core.exceptions import NotFoundException, ValidationException


class LeadService:
    """Service for lead operations."""
    
    @staticmethod
    async def create_or_update_lead(
        project_id: uuid.UUID,
        conversation_id: uuid.UUID,
        visitor_id: uuid.UUID,
        lead_data: dict,
        db: AsyncSession,
    ) -> Lead:
        """Create or update a lead from conversation data.
        
        Args:
            project_id: Project ID
            conversation_id: Conversation ID
            visitor_id: Visitor ID
            lead_data: Lead information extracted from AI
            db: Database session
            
        Returns:
            Created or updated lead
            
        Raises:
            NotFoundException: If required entities not found
        """
        # Verify entities exist
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundException("Project", project_id)
        
        # Check if lead already exists for visitor/project
        stmt = (
            select(Lead)
            .where(
                (Lead.project_id == project_id)
                & (Lead.visitor_id == visitor_id)
            )
        )
        result = await db.execute(stmt)
        existing_lead = result.scalar_one_or_none()
        
        if existing_lead:
            # Update existing lead
            existing_lead.conversation_id = conversation_id
            existing_lead.name = lead_data.get("name") or existing_lead.name
            existing_lead.email = lead_data.get("email") or existing_lead.email
            existing_lead.phone = lead_data.get("phone") or existing_lead.phone
            existing_lead.company = lead_data.get("company") or existing_lead.company
            existing_lead.project_type = lead_data.get("project_type") or existing_lead.project_type
            existing_lead.budget = lead_data.get("budget") or existing_lead.budget
            existing_lead.timeline = lead_data.get("timeline") or existing_lead.timeline
            existing_lead.intent_score = lead_data.get("intent_score", existing_lead.intent_score)
            existing_lead.is_qualified = lead_data.get("qualified", existing_lead.is_qualified)
            existing_lead.extraction_data = lead_data
            existing_lead.updated_at = datetime.now(timezone.utc)
            
            db.add(existing_lead)
            await db.commit()
            await db.refresh(existing_lead)
            
            return existing_lead
        else:
            # Create new lead
            lead = Lead(
                id=uuid.uuid4(),
                project_id=project_id,
                conversation_id=conversation_id,
                visitor_id=visitor_id,
                name=lead_data.get("name"),
                email=lead_data.get("email"),
                phone=lead_data.get("phone"),
                company=lead_data.get("company"),
                project_type=lead_data.get("project_type"),
                budget=lead_data.get("budget"),
                timeline=lead_data.get("timeline"),
                intent_score=lead_data.get("intent_score", 0),
                is_qualified=lead_data.get("qualified", False),
                extraction_data=lead_data,
                status="new",
            )
            
            db.add(lead)
            await db.commit()
            await db.refresh(lead)
            
            return lead
    
    @staticmethod
    async def get_lead_by_id(
        lead_id: uuid.UUID,
        db: AsyncSession,
    ) -> Lead:
        """Get lead by ID.
        
        Args:
            lead_id: Lead ID
            db: Database session
            
        Returns:
            Lead
            
        Raises:
            NotFoundException: If lead not found
        """
        stmt = select(Lead).where(Lead.id == lead_id)
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise NotFoundException("Lead", lead_id)
        
        return lead
    
    @staticmethod
    async def get_project_leads(
        project_id: uuid.UUID,
        db: AsyncSession,
        status: str = None,
        qualified_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Lead]:
        """Get leads in a project with optional filters.
        
        Args:
            project_id: Project ID
            db: Database session
            status: Optional status filter (new, contacted, qualified, converted, lost)
            qualified_only: Only return qualified leads
            limit: Number of results
            offset: Results to skip
            
        Returns:
            List of leads
        """
        stmt = select(Lead).where(Lead.project_id == project_id)
        
        if status:
            stmt = stmt.where(Lead.status == status)
        
        if qualified_only:
            stmt = stmt.where(Lead.is_qualified == True)  # noqa: E712
        
        stmt = (
            stmt
            .order_by(Lead.intent_score.desc(), Lead.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def update_lead_status(
        lead_id: uuid.UUID,
        new_status: str,
        db: AsyncSession,
    ) -> Lead:
        """Update lead status.
        
        Args:
            lead_id: Lead ID
            new_status: New status (new, contacted, qualified, converted, lost)
            db: Database session
            
        Returns:
            Updated lead
            
        Raises:
            NotFoundException: If lead not found
            ValidationException: If status is invalid
        """
        valid_statuses = ["new", "contacted", "qualified", "converted", "lost"]
        
        if new_status not in valid_statuses:
            raise ValidationException(
                f"Invalid status '{new_status}'. Must be one of: {', '.join(valid_statuses)}"
            )
        
        lead = await LeadService.get_lead_by_id(lead_id, db)
        
        lead.status = new_status
        lead.updated_at = datetime.now(timezone.utc)
        
        if new_status in ["contacted", "qualified"]:
            lead.last_contacted_at = datetime.now(timezone.utc)
        
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        return lead
    
    @staticmethod
    async def update_lead(
        lead_id: uuid.UUID,
        lead_update: dict,
        db: AsyncSession,
    ) -> Lead:
        """Update lead details.
        
        Args:
            lead_id: Lead ID
            lead_update: Dictionary of fields to update
            db: Database session
            
        Returns:
            Updated lead
            
        Raises:
            NotFoundException: If lead not found
        """
        lead = await LeadService.get_lead_by_id(lead_id, db)
        
        # Update only provided fields
        updateable_fields = [
            "name", "email", "phone", "company",
            "project_type", "budget", "timeline",
            "intent_score", "is_qualified", "notes"
        ]
        
        for field, value in lead_update.items():
            if field in updateable_fields and value is not None:
                setattr(lead, field, value)
        
        lead.updated_at = datetime.now(timezone.utc)
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        return lead
    
    @staticmethod
    async def get_project_lead_stats(
        project_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        """Get lead statistics for a project.
        
        Args:
            project_id: Project ID
            db: Database session
            
        Returns:
            Statistics dictionary
        """
        # Total leads
        stmt = select(func.count(Lead.id)).where(Lead.project_id == project_id)
        result = await db.execute(stmt)
        total = result.scalar() or 0
        
        # Qualified leads
        stmt = (
            select(func.count(Lead.id))
            .where(
                (Lead.project_id == project_id)
                & (Lead.is_qualified == True)  # noqa: E712
            )
        )
        result = await db.execute(stmt)
        qualified = result.scalar() or 0
        
        # By status
        statuses = ["new", "contacted", "qualified", "converted", "lost"]
        status_counts = {}
        
        for status in statuses:
            stmt = (
                select(func.count(Lead.id))
                .where(
                    (Lead.project_id == project_id)
                    & (Lead.status == status)
                )
            )
            result = await db.execute(stmt)
            status_counts[status] = result.scalar() or 0
        
        # Average score
        stmt = (
            select(func.avg(Lead.intent_score))
            .where(Lead.project_id == project_id)
        )
        result = await db.execute(stmt)
        avg_score = float(result.scalar() or 0)
        
        return {
            "total": total,
            "qualified": qualified,
            "conversion_rate": (qualified / total * 100) if total > 0 else 0,
            "by_status": status_counts,
            "average_score": round(avg_score, 2),
        }
