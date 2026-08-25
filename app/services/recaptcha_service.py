import httpx
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def verify_recaptcha_token(token: str) -> bool:
    """Verifies a Google reCAPTCHA v3 token."""
    if not settings.recaptcha_secret_key:
        # If no secret key is configured, bypass verification for local dev
        logger.warning("reCAPTCHA secret key is not configured, skipping verification.")
        return True
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": settings.recaptcha_secret_key,
                    "response": token
                }
            )
            result = response.json()
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Error verifying reCAPTCHA: {e}")
            return False
