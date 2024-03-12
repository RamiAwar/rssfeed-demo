from sqlmodel import Session, create_engine

from api import models
from config import get_settings

engine = create_engine(url=get_settings().POSTGRES_DSN, echo=True)
session_engine = create_engine(url=get_settings().POSTGRES_DSN, echo=True)

# Link user-defined SQL models
models.SQLModel.metadata.create_all(engine)  # type: ignore


def get_session() -> Session:
    """Get a database session"""
    return Session(session_engine)
