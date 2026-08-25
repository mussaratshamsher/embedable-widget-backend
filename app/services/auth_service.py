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
        return bool(settings.supabase_url and (settings.supabase_secret_key or settings.supabase_publishable_key))
    
    @staticmethod
    async def _supabase_signup(email: str, password: str, first_name: str = "", last_name: str = "") -> dict:
        auth_key = settings.supabase_secret_key or settings.supabase_publishable_key
        headers = {
            "apikey": auth_key,
            "Authorization": f"Bearer {auth_key}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # If secret/service key is available, use Admin API to auto-confirm email
            if settings.supabase_secret_key:
                resp = await client.post(
                    f"{settings.supabase_url}/auth/v1/admin/users",
                    headers=headers,
                    json={
                        "email": email,
                        "password": password,
                        "email_confirm": True,
                        "user_metadata": {
                            "first_name": first_name,
                            "last_name": last_name,
                        },
                    },
                )
                if resp.status_code == 200 or resp.status_code == 201:
                    data = resp.json()
                    return data.get("user") or data or {}
                elif resp.status_code in (400, 422):
                    err_data = {}
                    try:
                        err_data = resp.json()
                    except Exception:
                        pass
                    msg = err_data.get("msg") or err_data.get("message") or err_data.get("error_description") or ""
                    if "already" in msg.lower() or "exists" in msg.lower():
                        raise ConflictException(f"User with email {email} already exists in Supabase Auth")
            
            # Fallback to public signup
            resp = await client.post(
                f"{settings.supabase_url}/auth/v1/signup",
                headers={
                    "apikey": settings.supabase_publishable_key or auth_key,
                    "Content-Type": "application/json",
                },
                json={
                    "email": email,
                    "password": password,
                    "data": {"first_name": first_name, "last_name": last_name},
                },
            )
            if resp.status_code in (400, 422):
                err_data = {}
                try:
                    err_data = resp.json()
                except Exception:
                    pass
                msg = err_data.get("msg") or err_data.get("message") or err_data.get("error_description") or "User already registered or invalid registration data"
                if "already" in msg.lower() or "exists" in msg.lower():
                    raise ConflictException(msg)
                return {}
            
            resp.raise_for_status()
            data = resp.json()
            return data.get("user") or {}
    
    @staticmethod
    async def _supabase_login(email: str, password: str) -> dict:
        auth_key = settings.supabase_publishable_key or settings.supabase_secret_key
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.supabase_url}/auth/v1/token?grant_type=password",
                headers={
                    "apikey": auth_key,
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
        clean_email = email.lower().strip()
        
        # Dedicated Admin hardcoded credentials check / auto-provisioning
        if clean_email == "leadforge@gmail.com" and password == "forge123":
            stmt = select(User).where(User.email == clean_email)
            result = await db.execute(stmt)
            admin_user = result.scalar_one_or_none()
            if not admin_user:
                admin_user = User(
                    id=uuid.uuid4(),
                    email=clean_email,
                    hashed_password=hash_password("forge123"),
                    first_name="LeadForge",
                    last_name="Admin",
                    plan="pro",
                    is_active=True,
                    is_superadmin=True,
                )
                db.add(admin_user)
            else:
                admin_user.is_superadmin = True
                admin_user.is_active = True
                admin_user.last_login = datetime.now(timezone.utc)
                db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            return admin_user

        stmt = select(User).where(User.email == clean_email)
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
        
        Always checks the local database first for email uniqueness.
        Syncs with Supabase Auth if configured and reachable.
        Stores the hashed password locally so logins work seamlessly.
        """
        email = user_create.email.lower().strip()
        
        # 1. First check local database
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise ConflictException(f"User with email {user_create.email} already exists")
        
        user_id = None
        supabase_user = None
        
        # 2. Sync with Supabase Auth if enabled
        if AuthService._supabase_enabled():
            try:
                supabase_user = await AuthService._supabase_signup(
                    email,
                    user_create.password,
                    first_name=user_create.first_name or "",
                    last_name=user_create.last_name or "",
                )
                if supabase_user and supabase_user.get("id"):
                    user_id = uuid.UUID(supabase_user["id"])
            except ConflictException:
                # If Supabase reports conflict or invalid, raise
                raise
            except Exception:
                # If network or supabase unreachable, continue with local creation
                supabase_user = None
                user_id = None
        
        if not user_id:
            user_id = uuid.uuid4()
        
        # Always store password hash locally for reliable local & fallback authentication
        hashed = hash_password(user_create.password)
        is_admin = (email == "leadforge@gmail.com")
        
        user = User(
            id=user_id,
            email=email,
            hashed_password=hashed,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            plan="pro" if is_admin else "free",
            is_active=True,
            is_superadmin=is_admin,
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
        clean_email = email.lower().strip()
        if clean_email == "leadforge@gmail.com" and password == "forge123":
            return await AuthService._local_authenticate(clean_email, password, db)

        if AuthService._supabase_enabled():
            try:
                supabase_user = await AuthService._supabase_login(clean_email, password)
                user_id = uuid.UUID(supabase_user["id"]) if supabase_user.get("id") else None
                if user_id:
                    user = await AuthService.get_user_by_id(user_id, db)
                    if not user:
                        user = User(
                            id=user_id,
                            email=supabase_user.get("email") or clean_email,
                            hashed_password="",
                            first_name="",
                            last_name="",
                            is_active=True,
                            is_superadmin=(clean_email == "leadforge@gmail.com"),
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
        
        return await AuthService._local_authenticate(clean_email, password, db)
    
    @staticmethod
    async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession) -> User:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_email(email: str, db: AsyncSession) -> User:
        """Get user by email."""
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    def create_token(user: User, organization_id: uuid.UUID = None) -> dict:
        """Create JWT token for user."""
        is_admin = bool(user.is_superadmin or (user.email and user.email.lower() == "leadforge@gmail.com"))
        token_data = {
            "sub": str(user.id),
            "user_id": str(user.id),
            "email": user.email,
            "role": "admin" if is_admin else "user",
            "is_superadmin": is_admin,
            "organization_id": str(organization_id) if organization_id else None,
        }
        
        access_token = create_access_token(token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    @staticmethod
    async def delete_user(user_id: uuid.UUID, db: AsyncSession) -> None:
        """Delete user account and all owned organizations and data."""
        # 1. Delete from Supabase Auth if configured
        if settings.supabase_url and settings.supabase_secret_key:
            try:
                headers = {
                    "apikey": settings.supabase_secret_key,
                    "Authorization": f"Bearer {settings.supabase_secret_key}",
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.delete(
                        f"{settings.supabase_url}/auth/v1/admin/users/{str(user_id)}",
                        headers=headers,
                    )
            except Exception:
                pass

        # 2. Find and delete organizations where user is owner
        from app.models import Organization, OrganizationMember, MemberRole
        stmt_orgs = (
            select(Organization)
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .where(
                (OrganizationMember.user_id == user_id)
                & (OrganizationMember.role == MemberRole.OWNER)
            )
        )
        result = await db.execute(stmt_orgs)
        owned_orgs = result.scalars().all()
        for org in owned_orgs:
            await db.delete(org)

        # 3. Delete user record from database
        user = await AuthService.get_user_by_id(user_id, db)
        if user:
            await db.delete(user)
            await db.commit()

