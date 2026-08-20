from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.core.config import settings


# bcrypt only considers the first 72 bytes of a password
BCRYPT_MAX_BYTES = 72


def _encode_password(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(_encode_password(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            _encode_password(plain_password), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            hours=settings.jwt_expiration_hours
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None
