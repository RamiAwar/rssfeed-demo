from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlmodel import select

from api.db import get_session
from api.models import User, UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_user(username: str) -> User | None:
    """
    Retrieve a user from the database by their username.

    Args:
        username (str): The username of the user to retrieve.

    Returns:
        User | None: The User object corresponding to the given username,
        or None if no such user exists in the database.
    """
    with get_session() as session:
        return session.exec(select(User).where(User.username == username)).first()


def check_user(user: UserCreate) -> User | None:
    """
    Check if a user to be created already exists in the database with the given username.

    Args:
        user (UserCreate): User input to check.

    Returns:
        User | None: The user if found, otherwise None.
    """
    return get_user(user.username)


def authenticate_user(username: str, password: str) -> User | None:
    """
    Authenticates a user by checking if the username and password match a user in the database.

    Args:
        username (str): The username of the user to authenticate.
        password (str): The password of the user to authenticate.

    Returns:
        User | None: The authenticated user object if the username and password match a user in the database,
        otherwise None.
    """
    user = get_user(username)
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
