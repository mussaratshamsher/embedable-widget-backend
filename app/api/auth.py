"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate, UserLogin, UserResponse, TokenResponse
from app.core.exceptions import ConflictException, AuthenticationException
from app.dependencies.auth import get_current_user


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password",
)
async def register(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user.
    
    - **email**: User email address (must be unique)
    - **password**: Password (minimum 8 characters)
    - **first_name**: Optional first name
    - **last_name**: Optional last name
    """
    try:
        # Verify reCAPTCHA if configured and not in development
        if settings.recaptcha_site_key and settings.recaptcha_secret_key and settings.environment != "development":
            if not user_create.recaptcha_token:
                raise AuthenticationException("reCAPTCHA token is required")
            is_valid = await verify_recaptcha_token(user_create.recaptcha_token)
            if not is_valid:
                raise AuthenticationException("Invalid reCAPTCHA token")

        user = await AuthService.register_user(user_create, db)
        token_data = AuthService.create_token(user)
        
        return TokenResponse(
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            user=UserResponse.model_validate(user),
        )
    except ConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


from app.services.recaptcha_service import verify_recaptcha_token
from app.core.config import settings

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate user with email and password",
)
async def login(
    user_login: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT token.
    
    - **email**: User email address
    - **password**: User password
    """
    try:
        # Verify reCAPTCHA if configured and not in development
        if settings.recaptcha_site_key and settings.recaptcha_secret_key and settings.environment != "development":
            if not user_login.recaptcha_token:
                raise AuthenticationException("reCAPTCHA token is required")
            is_valid = await verify_recaptcha_token(user_login.recaptcha_token)
            if not is_valid:
                raise AuthenticationException("Invalid reCAPTCHA token")

        user = await AuthService.authenticate_user(
            user_login.email, user_login.password, db
        )
        token_data = AuthService.create_token(user)
        
        return TokenResponse(
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            user=UserResponse.model_validate(user),
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the authenticated user",
)
async def get_me(
    current_user=Depends(get_current_user),
):
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Logout the current user (client-side token removal)",
)
async def logout(
    current_user=Depends(get_current_user),
):
    """Logout endpoint (token invalidation is client-side).
    
    The client should remove the JWT token from storage.
    """
    return {
        "message": "Successfully logged out",
        "user_id": str(current_user.id),
    }


@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Delete user account",
    description="Delete user account, owned organizations, and all related data",
)
async def delete_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete current authenticated user and all associated data."""
    await AuthService.delete_user(current_user.id, db)
    return {
        "message": "User account and all associated data have been deleted successfully",
        "user_id": str(current_user.id),
    }

