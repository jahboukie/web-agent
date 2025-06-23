import secrets
from datetime import datetime, timedelta
from typing import Any

import structlog
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_secret_key() -> str:
    """Generate a secure random secret key."""
    return secrets.token_urlsafe(32)


def password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    try:
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed successfully")
        return hashed
    except Exception as e:
        logger.error("Failed to hash password", error=str(e))
        raise


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash using constant-time comparison.

    Args:
        password: Plain text password to verify
        hashed: Hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    try:
        # Use passlib's built-in constant-time verification
        # passlib already implements timing-safe password verification
        is_valid = pwd_context.verify(password, hashed)
        logger.debug("Password verification completed", is_valid=is_valid)
        return is_valid

    except Exception as e:
        logger.error("Failed to verify password", error=str(e))
        return False


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "access"})

    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        logger.debug("Access token created", expires_at=expire.isoformat())
        return encoded_jwt
    except Exception as e:
        logger.error("Failed to create access token", error=str(e))
        raise


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Data to encode in the token

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        logger.debug("Refresh token created", expires_at=expire.isoformat())
        return encoded_jwt
    except Exception as e:
        logger.error("Failed to create refresh token", error=str(e))
        raise


def verify_token(token: str, token_type: str = "access") -> dict[str, Any] | None:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Check token type
        if payload.get("type") != token_type:
            logger.warning(
                "Invalid token type", expected=token_type, actual=payload.get("type")
            )
            return None

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            logger.warning("Token has expired")
            return None

        logger.debug("Token verified successfully", token_type=token_type)
        return payload

    except JWTError as e:
        logger.warning("JWT verification failed", error=str(e))
        return None
    except Exception as e:
        logger.error("Unexpected error during token verification", error=str(e))
        return None


def encrypt_credential(data: str, key: str | None = None) -> str:
    """
    Encrypt sensitive credential data.

    Args:
        data: Data to encrypt
        key: Optional encryption key (uses default if not provided)

    Returns:
        Encrypted data as base64 string
    """
    if key is None:
        # Use a derived key from the secret key for credential encryption
        key = settings.SECRET_KEY[:32].ljust(32, "0")  # Ensure 32 bytes

    try:
        f = Fernet(Fernet.generate_key() if len(key) != 44 else key.encode())
        encrypted_data = f.encrypt(data.encode())
        logger.debug("Credential encrypted successfully")
        return encrypted_data.decode()
    except Exception as e:
        logger.error("Failed to encrypt credential", error=str(e))
        raise


def decrypt_credential(encrypted_data: str, key: str | None = None) -> str:
    """
    Decrypt sensitive credential data.

    Args:
        encrypted_data: Encrypted data to decrypt
        key: Optional encryption key (uses default if not provided)

    Returns:
        Decrypted data as string
    """
    if key is None:
        # Use a derived key from the secret key for credential encryption
        key = settings.SECRET_KEY[:32].ljust(32, "0")  # Ensure 32 bytes

    try:
        f = Fernet(key.encode() if len(key) == 44 else Fernet.generate_key())
        decrypted_data = f.decrypt(encrypted_data.encode())
        logger.debug("Credential decrypted successfully")
        return decrypted_data.decode()
    except Exception as e:
        logger.error("Failed to decrypt credential", error=str(e))
        raise
