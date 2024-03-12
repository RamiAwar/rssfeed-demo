from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from fastapi.responses import Response
from pydantic import AnyUrl
from sqlmodel import Session

from api.dependencies import get_current_user, session_dep
from api.models import Feed, FeedEntry, FeedEntryRead, FeedRead, User
from api.services import feed_service
from background import tasks

router = APIRouter()


@router.get(
    "/entries", response_model=List[FeedEntryRead], description="List feed entries"
)
def list_feed_entries(
    read: Optional[bool] = Query(None, description="Filter by read/unread status"),
    feed_id: Optional[UUID] = Query(None, description="Filter by feed ID"),
    followed_only: Optional[bool] = Query(
        None, description="Filter by followed feeds only"
    ),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(session_dep),
) -> List[FeedEntry]:
    """List feed filtered entries"""
    entries = feed_service.list_feed_entries(
        session=session,
        user_id=current_user.uuid,
        read=read,
        feed_id=feed_id,
        followed_only=followed_only,
        limit=limit,
        offset=offset,
    )
    return entries


@router.post(
    "/follow", response_model=FeedRead, description="Follow a feed using its URL"
)
def follow_feed(
    feed_url: Annotated[AnyUrl, Body(embed=True)],
    current_user: User = Depends(get_current_user),
    session: Session = Depends(session_dep),
) -> Feed:
    """Follow a feed using its URL"""
    feed = feed_service.follow_feed(
        session=session, user_id=current_user.uuid, feed_url=feed_url
    )
    session.commit()  # Commit early so that task can access the feed

    # Submit job to refresh the feed
    tasks.refresh_feed.delay(feed.uuid)
    return feed


@router.post("/{feed_id}/unfollow", description="Unfollow a feed using it's ID")
def unfollow_feed(
    feed_id: str, current_user: User = Depends(get_current_user)
) -> Response:
    """Unfollow a feed using it's ID"""
    feed_service.unfollow_feed(user_id=current_user.uuid, feed_id=feed_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/entry/{entry_id}", description="Mark a feed entry as read/unread")
def mark_entry_read_unread(
    entry_id: UUID,
    is_read: Annotated[bool, Body(embed=True)],
    current_user: User = Depends(get_current_user),
    session: Session = Depends(session_dep),
) -> Response:
    """Mark a feed entry as read/unread"""
    feed_service.update_feed_entry_user(session, current_user.uuid, entry_id, is_read)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{feed_id}/refresh", description="Trigger a forced feed refresh")
def force_refresh_feed(
    feed_id: str,
    _: User = Depends(get_current_user),
    session: Session = Depends(session_dep),
) -> Response:
    """Trigger a forced feed refresh"""
    feed = session.get(Feed, feed_id)
    if not feed:
        raise Exception("Feed not found.")

    tasks.force_refresh_feed(session, feed_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
