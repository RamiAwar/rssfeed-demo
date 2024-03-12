from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from api.auth import authenticate_user
from api.dependencies import create_access_token, session_dep
from api.models import Token, User, UserCreate, UserRead
from api.services import user_service
from config import get_settings

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """Login using username and password for access token"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=get_settings().JWT_EXPIRY_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/signup", response_model=UserRead)
def create_new_user(
    user_in: UserCreate, session: Session = Depends(session_dep)
) -> User:
    """Sign up using username and password"""
    user = user_service.create_user(session, user_in)
    session.commit()
    return user
