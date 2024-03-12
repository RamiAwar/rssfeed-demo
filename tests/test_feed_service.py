import feedparser
from sqlmodel import Session, select

from api.models import Feed, FeedEntry, ParsedFeed
from api.services import feed_service


def test_update_empty_feed(
    session: Session, base_feed: tuple[Feed, ParsedFeed]
) -> None:
    # Arrange: Create feed
    feed, fetched_feed = base_feed

    # Act: Update feed
    feed_service.update_feed(feed, fetched_feed=fetched_feed, session=session)

    # Assert: Feed metadata is populated
    assert feed.title == fetched_feed.feed.get("title")
    assert feed.hash != ""
    assert feed.published_at is not None
    assert feed.raw is not None


def test_update_existing_feed(
    session: Session, base_feed: tuple[Feed, ParsedFeed], rss_updated_feed: bytes
) -> None:
    # Arrange: Create feed and populate it
    feed, fetched_feed = base_feed
    feed_service.update_feed(feed, fetched_feed=fetched_feed, session=session)
    old_description = feed.description

    # Act: Get slightly different feed with different description
    fetched_feed_updated: ParsedFeed = feedparser.parse(rss_updated_feed)
    feed_service.update_feed(feed, fetched_feed=fetched_feed_updated, session=session)

    # Assert: Feed description is indeed updated even though feed ID is the same
    assert feed.description != old_description


def test_update_or_create_feed_entries(
    session: Session, base_feed: tuple[Feed, ParsedFeed]
) -> None:
    # Arrange: Create feed
    feed, fetched_feed = base_feed

    # Act: Create feed entries
    feed_service.update_or_create_feed_entries(
        feed=feed, fetched_feed=fetched_feed, session=session
    )

    # Assert: Feed entries are created
    statement = select(FeedEntry).where(FeedEntry.feed_id == feed.uuid)
    results = session.exec(statement)
    entries = results.all()
    assert len(entries) > 0
    assert all(entry.title != "" for entry in entries)
    assert all(entry.hash != "" for entry in entries)
    assert all(entry.raw is not None for entry in entries)


def test_update_or_create_feed_entries_updates_existing_entries_when_content_different(
    session: Session, base_feed: tuple[Feed, ParsedFeed], rss_updated_entries: bytes
) -> None:
    # Arrange: Create feed and feed entries
    feed, fetched_feed = base_feed
    feed_service.update_or_create_feed_entries(
        feed=feed, fetched_feed=fetched_feed, session=session
    )
    old_titles = set(entry.title for entry in feed.entries)

    # Act: Update feed entries
    fetched_feed_updated: ParsedFeed = feedparser.parse(rss_updated_entries)
    feed_service.update_or_create_feed_entries(
        feed=feed, fetched_feed=fetched_feed_updated, session=session
    )

    # Assert: Feed entries are updated
    entries = feed.entries
    assert len(entries) > 0
    assert set(entry.title for entry in entries) != old_titles
    assert all(entry.raw is not None for entry in entries)
