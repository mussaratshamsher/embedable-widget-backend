"""Authentication service for user management and token handling."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
import uuid
import httpx

from app.models import User
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationException,
    ConflictException,
    NotFoundException,
)
from app.schemas.auth import UserCreate, TokenData


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def _supabase_enabled() -> bool:
        return bool(settings.supabase_url and settings.supabase_publishable_key)
    
    @staticmethod
    async def _supabase_signup(email: str, password: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.supabase_url}/auth/v1/signup",
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Content-Type": "application/json",
                },
                json={"email": email, "password": password},
            )
            if resp.status_code in (400, 422):
                raise ConflictException("Unable to register user")
            resp.raise_for_status()
            data = resp.json()
            return data.get("user") or {}
    
    @staticmethod
    async def _supabase_login(email: str, password: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.supabase_url}/auth/v1/token?grant_type=password",
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Content-Type": "application/json",
                },
                json={"email": email, "password": password},
            )
            if resp.status_code in (400, 401, 404):
                return {}
            resp.raise_for_status()
            data = resp.json()
            return data.get("user") or {}
    
    @staticmethod
    async def _local_register(user_create: UserCreate, db: AsyncSession) -> User:
        email = user_create.email.lower()
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise ConflictException(f"User with email {user_create.email} already exists")
        
        hashed_password = hash_password(user_create.password)
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            is_active=True,
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def _local_authenticate(email: str, password: str, db: AsyncSession) -> User:
        stmt = select(User).where(User.email == email.lower())
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthenticationException("Invalid email or password")
        if not verify_password(password, user.hashed_password):
            raise AuthenticationException("Invalid email or password")
        if not user.is_active:
            raise AuthenticationException("User account is inactive")
        
        user.last_login = datetime.now(timezone.utc)
        db.add(user)
        await db.commit()
        return user
    
    @staticmethod
    async def register_user(user_create: UserCreate, db: AsyncSession) -> User:
        """Register a new user.
        
        Uses Supabase Auth if configured and reachable, otherwise falls back to local auth.
        Also mirrors the user into the local users table.
        """
        email = user_create.email.lower()
        user_id = None
        supabase_user = None
        
        if AuthService._supabase_enabled():
            try:
                supabase_user = await AuthService._supabase_signup(email, user_create.password)
                user_id = uuid.UUID(supabase_user["id"]) if supabase_user.get("id") else None
            except ConflictException:
                raise
            except Exception:
                supabase_user = None
                user_id = None
        
        if not user_id:
            user_id = uuid.uuid4()
            email = user_create.email.lower()
        
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise ConflictException(f"User with email {user_create.email} already exists")
        
        user = User(
            id=user_id,
            email=email,
            hashed_password="" if supabase_user else hash_password(user_create.password),
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            is_active=True,
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def authenticate_user(
        email: str, password: str, db: AsyncSession
    ) -> User:
        """Authenticate a user.
        
        Uses Supabase Auth if configured and reachable, otherwise falls back to local auth.
        """
        if AuthService._supabase_enabled():
            try:
                supabase_user = await AuthService._supabase_login(email.lower(), password)
                user_id = uuid.UUID(supabase_user["id"]) if supabase_user.get("id") else None
                if user_id:
                    user = await AuthService.get_user_by_id(user_id, db)
                    if not user:
                        user = User(
                            id=user_id,
                            email=supabase_user.get("email") or email.lower(),
                            hashed_password="",
                            first_name="",
                            last_name="",
                            is_active=True,
                        )
                        db.add(user)
                        await db.commit()
                        await db.refresh(user)
                    
                    if not user.is_active:
                        raise AuthenticationException("User account is inactive")
                    
                    user.last_login = datetime.now(timezone.utc)
                    db.add(user)
                    await db.commit()
                    return user
            except AuthenticationException:
                raise
            except Exception:
                pass
        
        return await AuthService._local_authenticate(email, password, db)
    
    @staticmethod
    async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession) -> User:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_email(email: str, db: AsyncSession) -> User:
        """Get user by email."""
        stmt = select(User).where(User.email == email.lower())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    def create_token(user: User, organization_id: uuid.UUID = None) -> dict:
        """Create JWT token for user."""
        token_data = {
            "sub": str(user.id),
            "user_id": str(user.id),
            "email": user.email,
            "organization_id": str(organization_id) if organization_id else None,
        }
        
        access_token = create_access_token(token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
