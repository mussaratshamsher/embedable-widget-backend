"""Authentication dependencies for FastAPI routes."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import AuthenticationException
from app.services.auth_service import AuthService
from app.schemas.auth import TokenData


security = HTTPBearer()
# FIX Bug 5: auto_error=False so missing Authorization header returns None
# instead of raising an HTTP 403 error.
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    # Decode token
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user ID from token
    user_id_str = payload.get("user_id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token data",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    try:
        user = await AuthService.get_user_by_id(user_id, db)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(optional_security),
    db: AsyncSession = Depends(get_db),
):
    """Dependency to optionally get current user (may be None).
    
    Args:
        credentials: HTTP Bearer credentials (optional — no auth header returns None)
        db: Database session
        
    Returns:
        Current user or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_current_admin_user(
    current_user=Depends(get_current_user),
):
    """Dependency to ensure the user has admin privileges.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        The current user if they are an admin
        
    Raises:
        HTTPException: 403 Forbidden if not admin
    """
    is_admin = bool(
        getattr(current_user, "is_superadmin", False)
        or (getattr(current_user, "email", "") and current_user.email.lower() == "leadforge@gmail.com")
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. You do not have permission to access this resource.",
        )
    return current_user
