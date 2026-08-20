"""Visitor service for tracking widget users."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
import uuid
import hashlib

from app.models import Visitor, Project
from app.core.exceptions import NotFoundException, ValidationException


class VisitorService:
    """Service for visitor operations."""
    
    @staticmethod
    def _generate_visitor_identifier() -> str:
        """Generate a unique visitor identifier.
        
        Returns:
            Random visitor identifier
        """
        return f"vis_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    async def get_or_create_visitor(
        project_id: uuid.UUID,
        visitor_identifier: str = None,
        metadata: dict = None,
        db: AsyncSession = None,
    ) -> Visitor:
        """Get or create a visitor for a project.
        
        Args:
            project_id: Project ID
            visitor_identifier: Optional visitor identifier
            metadata: Optional visitor metadata
            db: Database session
            
        Returns:
            Visitor
            
        Raises:
            NotFoundException: If project not found
        """
        # Verify project exists
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundException("Project", project_id)
        
        # Check if visitor already exists with this identifier
        if visitor_identifier:
            existing = await VisitorService.get_visitor_by_identifier(
                visitor_identifier, db
            )
            if existing:
                return await VisitorService.update_visitor_last_seen(existing.id, db)
        
        # Generate unique visitor identifier
        if not visitor_identifier:
            visitor_identifier = None
            while visitor_identifier is None:
                new_id = VisitorService._generate_visitor_identifier()
                stmt = select(Visitor).where(Visitor.visitor_identifier == new_id)
                result = await db.execute(stmt)
                if result.scalar_one_or_none() is None:
                    visitor_identifier = new_id
        
        # Create visitor
        visitor = Visitor(
            id=uuid.uuid4(),
            project_id=project_id,
            visitor_identifier=visitor_identifier,
            extra_metadata=metadata or {},
        )
        
        db.add(visitor)
        await db.commit()
        await db.refresh(visitor)
        
        return visitor
    
    @staticmethod
    async def get_visitor_by_identifier(
        visitor_identifier: str,
        db: AsyncSession,
    ) -> Visitor:
        """Get visitor by identifier.
        
        Args:
            visitor_identifier: Visitor identifier
            db: Database session
            
        Returns:
            Visitor or None if not found
        """
        stmt = select(Visitor).where(
            Visitor.visitor_identifier == visitor_identifier
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_visitor_by_id(
        visitor_id: uuid.UUID,
        db: AsyncSession,
    ) -> Visitor:
        """Get visitor by ID.
        
        Args:
            visitor_id: Visitor ID
            db: Database session
            
        Returns:
            Visitor
            
        Raises:
            NotFoundException: If visitor not found
        """
        stmt = select(Visitor).where(Visitor.id == visitor_id)
        result = await db.execute(stmt)
        visitor = result.scalar_one_or_none()
        
        if not visitor:
            raise NotFoundException("Visitor", visitor_id)
        
        return visitor
    
    @staticmethod
    async def update_visitor_last_seen(
        visitor_id: uuid.UUID,
        db: AsyncSession,
    ) -> Visitor:
        """Update visitor's last_seen timestamp.
        
        Args:
            visitor_id: Visitor ID
            db: Database session
            
        Returns:
            Updated visitor
        """
        visitor = await VisitorService.get_visitor_by_id(visitor_id, db)
        visitor.last_seen = datetime.now(timezone.utc)
        db.add(visitor)
        await db.commit()
        await db.refresh(visitor)
        return visitor
