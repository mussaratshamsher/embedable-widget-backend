"""
FastAPI application entry point for FastAPI Cloud deployment.
This file allows FastAPI Cloud to easily locate and run the application.
"""
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import the FastAPI application
from app.main import app

# Export for FastAPI Cloud to find
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=4,
        access_log=True,
    )
