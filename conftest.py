from typing import Generator

import feedparser
import pytest
from sqlmodel import Session

from api.db import get_session
from api.models import Feed, ParsedFeed


@pytest.fixture(scope="function")
def session() -> Generator[Session, None, None]:
    """Yields an SQLModel/SQLAlchemy session which is rollbacked after the test"""
    with get_session() as session_:
        yield session_
        session_.rollback()


@pytest.fixture(scope="function")
def rss_base() -> bytes:
    # Return rss_example.xml as bytes
    with open("tests/rss_example.xml", "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def rss_updated_feed() -> bytes:
    # Return rss_example_updated_feed.xml as bytes
    with open("tests/rss_example_updated_feed.xml", "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def rss_updated_entries() -> bytes:
    # Return rss_example_updated_entries.xml as bytes
    with open("tests/rss_example_updated_entries.xml", "rb") as f:
        return f.read()


@pytest.fixture(scope="function")
def base_feed(session: Session, rss_base: bytes) -> tuple[Feed, ParsedFeed]:
    fetched_feed: ParsedFeed = feedparser.parse(rss_base)
    feed = Feed(url="whatever")
    session.add(feed)

    return feed, fetched_feed
