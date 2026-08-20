import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import AppException
from app.db.database import engine, Base

# Import models to register them with SQLAlchemy
from app.models import (  # noqa: F401
    User,
    Organization,
    OrganizationMember,
    Project,
    Visitor,
    Conversation,
    Message,
    Lead,
)

# Import API routers
from app.api import auth as auth_router
from app.api import organizations as organizations_router
from app.api import projects as projects_router
from app.api import widget as widget_router
from app.api import conversations as conversations_router
from app.api import chat as chat_router
from app.api import leads as leads_router


logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI backend for AI-powered embeddable website widget with lead capture",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router.router)
app.include_router(organizations_router.router)
app.include_router(projects_router.router)
app.include_router(widget_router.router)
app.include_router(conversations_router.router)
app.include_router(chat_router.router)
app.include_router(leads_router.router)


# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details if exc.details else None,
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions without exposing stack traces or secrets."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
            }
        },
    )


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup in development mode."""
    if settings.environment == "development":
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as exc:
            logger.warning("Database startup failed: %s", exc)


# Health check endpoint
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint."""
    return {
        "message": "FlyRank AI Widget Backend",
        "docs": "/docs",
        "version": settings.app_version,
    }


if __name__ == "__main__":
    import uvicorn
    import os
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=settings.environment == "development",
    )
