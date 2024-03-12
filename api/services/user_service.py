from fastapi import HTTPException
from sqlmodel import Session

from api.auth import check_user, get_password_hash
from api.models import User, UserCreate


def create_user(session: Session, user_in: UserCreate) -> User:
    user = check_user(user_in)
    if user:
        raise HTTPException(
            status_code=409, detail="Username already exists",
        )

    new_user = User(
        username=user_in.username, hashed_password=get_password_hash(user_in.password),
    )
    session.add(new_user)
    return new_user
