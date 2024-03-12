from datetime import datetime, timedelta
from typing import Any, Dict, Generator, Optional

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlmodel import Session

from api.auth import get_user, oauth2_scheme
from api.db import session_engine
from api.models import TokenData, User
from config import get_settings


def session_dep() -> Generator[Session, Any, None]:
    """Dependency for FastAPI routes that require a database session"""
    with Session(session_engine) as session:
        yield session


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token with the given data and expiration time.

    Args:
        data (Dict[str, Any]): The data to include in the token.
        expires_delta (Optional[timedelta]): The expiration time for the token.
            If not provided, the token will expire in 2 days.

    Returns:
        str: The encoded JWT access token.
    """
    # Add arbitrary data we want into jwt
    to_encode = data.copy()

    # Add expiration time to jwt
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=2)
    to_encode.update({"exp": expire})

    # Encode jwt
    secret = get_settings().JWT_SECRET_KEY
    algorithm = get_settings().JWT_ALGORITHM
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=algorithm)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Returns the current user based on the provided authentication token.

    Args:
        token (str): The authentication token.

    Returns:
        User: The user associated with the provided authentication token.

    Raises:
        HTTPException: If the provided token is invalid or the associated user cannot be found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode jwt
    try:
        secret = get_settings().JWT_SECRET_KEY
        algorithm = get_settings().JWT_ALGORITHM
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        username: str = str(payload.get("sub"))  # jwt subject will be user username
        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    # Try to get user from db
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception

    return user
