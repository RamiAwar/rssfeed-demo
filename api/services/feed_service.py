import json
from typing import List, Optional
from uuid import UUID

from pydantic import AnyUrl
from sqlmodel import Session, and_, or_, select

from api.db import get_session
from api.errors import NotFoundError
from api.models import Feed, FeedEntry, FeedEntryUser, FeedUser, ParsedFeed
from api.utils import get_hash


def follow_feed(session: Session, user_id: UUID, feed_url: AnyUrl) -> Feed:
    # Check if feed already exists
    get_feed_statement = select(Feed).where(Feed.url == feed_url)
    results = session.exec(get_feed_statement)
    feed = results.first()

    if feed:
        # Check if feed is already followed by user
        statement = select(FeedUser).where(
            FeedUser.feed_id == feed.uuid, FeedUser.user_id == user_id
        )
        results = session.exec(statement)  # type: ignore
        exists = results.first()
        if not exists:
            # Add feed to user's feeds
            feed_user = FeedUser(feed_id=feed.uuid, user_id=user_id)
            session.add(feed_user)
    else:
        # Create empty feed with URL
        feed = Feed(url=feed_url)
        session.add(feed)

        # Add feed to user's feeds
        feed_user = FeedUser(feed_id=feed.uuid, user_id=user_id)
        session.add(feed_user)

    return feed


def unfollow_feed(user_id: UUID, feed_id: str) -> None:
    # Check if feed already exists
    with get_session() as session:
        # Check if feed is followed by user
        statement = select(FeedUser).where(
            FeedUser.feed_id == feed_id, FeedUser.user_id == user_id
        )
        results = session.exec(statement)  # type: ignore
        feed_user = results.first()
        if feed_user:
            # Remove feed from user's feeds
            session.delete(feed_user)
            session.commit()
        else:
            raise NotFoundError("Feed not followed by user.")


def update_feed(feed: Feed, fetched_feed: ParsedFeed, session: Session) -> None:
    # Update only if feed has changed
    feed_dict = fetched_feed.feed
    new_hash = get_hash(json.dumps(feed_dict))
    if feed.hash != new_hash:
        feed.update(feed_dict, new_hash)
        session.add(feed)


def update_or_create_feed_entries(
    feed: Feed, fetched_feed: ParsedFeed, session: Session
) -> None:
    # Update or create FeedEntry instances
    entries_for_update: List[FeedEntry] = []
    for entry in fetched_feed.entries:
        # Try to find existing entry based on GUID
        statement = select(FeedEntry).where(FeedEntry.guid == entry.get("guid"))
        results = session.exec(statement)
        existing_entry = results.first()

        # If it exists, compare content hash to see if it needs to be updated
        if existing_entry:
            new_hash = get_hash(json.dumps(entry))

            if existing_entry.hash != new_hash:
                existing_entry.update(entry, new_hash)
                entries_for_update.append(existing_entry)
        else:
            # Does not exist, create new entry
            entries_for_update.append(
                FeedEntry.create_from_dict(feed_id=feed.uuid, entry_dict=entry)
            )

    # Bulk update or create entries
    session.bulk_save_objects(entries_for_update)


def update_feed_entry_user(
    session: Session, user_id: UUID, entry_id: UUID, is_read: bool
) -> None:
    feed_entry = session.get(FeedEntry, entry_id)
    if not feed_entry:
        raise NotFoundError("Feed entry not found.")

    # Get or create and then update with is_read value
    feed_entry_user = session.get(FeedEntryUser, (entry_id, user_id))
    if feed_entry_user:
        feed_entry_user.is_read = is_read
    else:
        feed_entry_user = FeedEntryUser(
            feed_entry_id=entry_id, user_id=user_id, is_read=is_read
        )
    session.add(feed_entry_user)


def list_feed_entries(
    session: Session,
    user_id: UUID,
    read: Optional[bool] = None,
    feed_id: Optional[UUID] = None,
    followed_only: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[FeedEntry]:
    """Fetches a list of filtered feed entries."""
    query = select(FeedEntry)
    # Filter by read/unread status
    if read:
        query = query.join(FeedEntryUser).where(
            FeedEntryUser.is_read == read, FeedEntryUser.user_id == user_id,
        )
    elif read is False:
        # Return FeedEntries that do not have a FeedEntryUser record
        # This generalizes well if other columns were present (ex. is_starred)
        query = query.outerjoin(
            FeedEntryUser,
            # Define ON condition
            and_(
                FeedEntryUser.feed_entry_id == FeedEntry.uuid,
                FeedEntryUser.user_id == user_id,
            ),
        ).where(
            # Fetch all the records that have is_read=False or have no FeedEntryUser record
            # This way we can support FeedEntryUsers with multiple metadata columns
            or_(
                FeedEntryUser.is_read == False,  # noqa
                FeedEntryUser.feed_entry_id == None,  # noqa
            )
        )

    # Filter by feed ID
    if feed_id:
        query = query.where(FeedEntry.feed_id == feed_id)

    # Filter by followed feeds only
    if followed_only:
        query = query.join(
            FeedUser,
            FeedUser.feed_id == FeedEntry.feed_id,
            FeedUser.user_id == user_id,
        )

    # Order by last update of feed entry (not published date, but sync date)
    query = query.order_by(FeedEntry.updated_at.desc())  # type: ignore

    # Limit and offset
    query = query.limit(limit).offset(offset)
    entries = session.exec(query).all()

    return entries
