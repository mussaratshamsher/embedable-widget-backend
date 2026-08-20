"""Project service for project management."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timezone
import uuid
import secrets

from app.models import Project, Organization
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
)
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    """Service for project operations."""
    
    @staticmethod
    def _generate_api_key() -> str:
        """Generate a random API key.
        
        Returns:
            Random API key
        """
        return f"pk_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    async def create_project(
        project_create: ProjectCreate,
        organization_id: uuid.UUID,
        db: AsyncSession,
    ) -> Project:
        """Create a new project.
        
        Args:
            project_create: Project creation data
            organization_id: Organization ID
            db: Database session
            
        Returns:
            Created project
            
        Raises:
            NotFoundException: If organization not found
        """
        # Verify organization exists
        stmt = select(Organization).where(Organization.id == organization_id)
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()
        
        if not org:
            raise NotFoundException("Organization", organization_id)
        
        # Create project with unique API key
        api_key = None
        while api_key is None:
            new_key = ProjectService._generate_api_key()
            stmt = select(Project).where(Project.api_key == new_key)
            result = await db.execute(stmt)
            if result.scalar_one_or_none() is None:
                api_key = new_key
        
        project = Project(
            id=uuid.uuid4(),
            organization_id=organization_id,
            name=project_create.name,
            website_url=project_create.website_url,
            description=project_create.description,
            business_type=project_create.business_type,
            ai_instructions=project_create.ai_instructions,
            welcome_message=project_create.welcome_message,
            api_key=api_key,
            is_active=True,
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        return project
    
    @staticmethod
    async def get_project_by_id(
        project_id: uuid.UUID,
        db: AsyncSession,
    ) -> Project:
        """Get project by ID.
        
        Args:
            project_id: Project ID
            db: Database session
            
        Returns:
            Project
            
        Raises:
            NotFoundException: If project not found
        """
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundException("Project", project_id)
        
        return project
    
    @staticmethod
    async def get_project_by_api_key(
        api_key: str,
        db: AsyncSession,
    ) -> Project:
        """Get project by API key.
        
        Args:
            api_key: Project API key
            db: Database session
            
        Returns:
            Project or None if not found
        """
        stmt = select(Project).where(Project.api_key == api_key)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_organization_projects(
        organization_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[Project]:
        """Get all projects in an organization.
        
        Args:
            organization_id: Organization ID
            db: Database session
            
        Returns:
            List of projects
        """
        stmt = (
            select(Project)
            .where(Project.organization_id == organization_id)
            .order_by(Project.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def update_project(
        project_id: uuid.UUID,
        project_update: ProjectUpdate,
        db: AsyncSession,
    ) -> Project:
        """Update project.
        
        Args:
            project_id: Project ID
            project_update: Project update data
            db: Database session
            
        Returns:
            Updated project
            
        Raises:
            NotFoundException: If project not found
        """
        project = await ProjectService.get_project_by_id(project_id, db)
        
        update_data = project_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(project, key, value)
        
        project.updated_at = datetime.now(timezone.utc)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        return project
    
    @staticmethod
    async def delete_project(
        project_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        """Delete project (soft delete by setting inactive).
        
        Args:
            project_id: Project ID
            db: Database session
            
        Raises:
            NotFoundException: If project not found
        """
        project = await ProjectService.get_project_by_id(project_id, db)
        
        project.is_active = False
        project.updated_at = datetime.now(timezone.utc)
        db.add(project)
        await db.commit()
    
    @staticmethod
    async def regenerate_api_key(
        project_id: uuid.UUID,
        db: AsyncSession,
    ) -> Project:
        """Regenerate project API key.
        
        Args:
            project_id: Project ID
            db: Database session
            
        Returns:
            Updated project
            
        Raises:
            NotFoundException: If project not found
        """
        project = await ProjectService.get_project_by_id(project_id, db)
        
        # Generate new unique API key
        api_key = None
        while api_key is None:
            new_key = ProjectService._generate_api_key()
            stmt = select(Project).where(Project.api_key == new_key)
            result = await db.execute(stmt)
            if result.scalar_one_or_none() is None:
                api_key = new_key
        
        project.api_key = api_key
        project.updated_at = datetime.now(timezone.utc)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        return project
