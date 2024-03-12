# Database models (sqlmodel with table=true) as well as pure data models are defined here

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Self
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlmodel import JSON, Field, Relationship, SQLModel

from api.utils import get_hash


class UUIDModel(SQLModel):
    uuid: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )


class AuditModel(SQLModel):
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    hash: Optional[str] = Field(default=None)


class User(UUIDModel, table=True):
    __tablename__ = "users"  # breaking naming convention to avoid reserved word

    username: str
    hashed_password: str = ""


class UserCreate(SQLModel):
    username: str
    password: str


class UserRead(UUIDModel):
    username: str


class Token(SQLModel):
    access_token: str
    token_type: str


class TokenData(SQLModel):
    username: str


class Feed(UUIDModel, AuditModel, table=True):
    # To keep track of user entered URLs as use as a unique identifier for a feed
    # Will still keep UUID as primary key for internal use however
    url: str = Field(index=True, unique=True)

    updated_at: Optional[datetime] = Field()

    # Block retries in case of repetitive failures
    should_retry: bool = Field(default=True)

    # Feed elements (optional to allow for lazy population)
    title: Optional[str] = Field()
    link: Optional[str] = Field()
    description: Optional[str] = Field()
    published_at: Optional[datetime] = Field()
    raw: Optional[dict[str, Any]] = Field(sa_column=Column(JSON))

    entries: List["FeedEntry"] = Relationship(back_populates="feed")

    def update(self, feed_dict: Dict[str, Any], new_hash: str) -> None:
        self.hash = new_hash
        self.title = feed_dict.get("title", "")
        self.link = feed_dict.get("link", "")
        self.description = feed_dict.get("description", "")
        self.updated_at = datetime.now()
        self.raw = feed_dict

        # Transform publish date to datetime
        publish_date = feed_dict.get("updated_parsed", None)
        if publish_date:
            self.published_at = datetime(*publish_date[:6])


class FeedRead(SQLModel):
    uuid: UUID
    url: str
    title: Optional[str]
    link: Optional[str]
    description: Optional[str]
    published_at: Optional[datetime]


class FeedEntry(UUIDModel, AuditModel, table=True):
    feed_id: UUID = Field(foreign_key="feed.uuid")
    feed: Optional[Feed] = Relationship(back_populates="entries")

    # Feed entry elements (optional to allow for lazy population)
    guid: Optional[str] = Field()
    title: Optional[str] = Field()
    link: Optional[str] = Field()
    description: Optional[str] = Field()
    published_at: Optional[datetime] = Field()
    raw: Optional[dict[str, Any]] = Field(sa_column=Column(JSON))

    def update(self, entry: Dict[str, Any], new_hash: str) -> None:
        self.hash = new_hash
        self.title = entry.get("title", "")
        self.guid = entry.get("guid", None)
        self.link = entry.get("link", "")
        self.description = entry.get("description", "")
        self.updated_at = datetime.now()
        self.raw = entry

        # Transform publish date to datetime
        publish_date = entry.get("updated_parsed", None)
        if publish_date:
            self.published_at = datetime(*publish_date[:6])

    @classmethod
    def create_from_dict(cls, feed_id: UUID, entry_dict: Dict[str, Any]) -> Self:
        publish_date = entry_dict.get("updated_parsed", None)
        publish_date = datetime(*publish_date[:6]) if publish_date else None

        return cls(
            feed_id=feed_id,
            title=entry_dict.get("title", ""),
            guid=entry_dict.get("guid", None),
            link=entry_dict.get("link", ""),
            description=entry_dict.get("description", ""),
            published_at=publish_date,
            hash=get_hash(json.dumps(entry_dict)),
            raw=entry_dict,
        )


class FeedEntryRead(SQLModel):
    uuid: UUID
    feed_id: UUID
    title: Optional[str]
    link: Optional[str]
    description: Optional[str]
    published_at: Optional[datetime]


class FeedUser(SQLModel, table=True):
    # Create a link table with a composite primary key
    feed_id: UUID = Field(foreign_key="feed.uuid", primary_key=True)
    user_id: UUID = Field(foreign_key="users.uuid", primary_key=True)


class FeedEntryUser(SQLModel, table=True):
    # Create a link table with a composite primary key
    feed_entry_id: UUID = Field(foreign_key="feedentry.uuid", primary_key=True)
    user_id: UUID = Field(foreign_key="users.uuid", primary_key=True)
    is_read: bool = Field(index=True, default=False)  # Index for faster filtering


@dataclass
class ParsedFeed:
    """Basic dataclass for the output of feedparser.parse"""

    feed: Dict[str, Any]
    entries: List[Dict[str, Any]]
    bozo: bool
    bozo_exception: Optional[Exception]
