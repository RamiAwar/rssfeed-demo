import logging

import feedparser
from sqlmodel import Session

from api.db import get_session
from api.errors import NotFoundError
from api.models import Feed, ParsedFeed
from api.services import feed_service
from background.celery import app
from cache import acquire_lock, release_lock

logger = logging.getLogger(__name__)


def get_refresh_task_identifier(feed_id: str) -> str:
    """Get task identifier for feed refresh job"""
    return f"refresh:{feed_id}"


class RefreshFeedWithRetry(app.Task):  # type: ignore
    retry_jitter = False
    retry_delays = [2, 5, 8]  # Define retry delays in minutes

    def run_refresh_feed(self, feed_id: str) -> None:
        """Run refresh feed task

        Places that need to release the lock:
        - When the task finishes successfully
        - When the task fails and has reached the maximum number of retries
        - If the task will not be retried
        """
        task_identifier = get_refresh_task_identifier(feed_id)
        with get_session() as session:
            # Check if feed exists
            feed = session.get(Feed, feed_id)
            if not feed:
                release_lock(task_identifier)
                raise Exception("Feed not found.")

            # Check if feed has exceeded retry attempts, if so stop and release lock
            if not feed.should_retry:
                release_lock(task_identifier)
                return

            try:
                # Fetch feed
                fetched_feed: ParsedFeed = feedparser.parse(feed.url)

                # Check if any parsing or fetching errors were encountered
                if fetched_feed.bozo:
                    raise Exception(fetched_feed.bozo_exception)

                # Update feed and feed entries
                feed_service.update_feed(feed, fetched_feed, session)
                feed_service.update_or_create_feed_entries(feed, fetched_feed, session)

                session.commit()
                release_lock(task_identifier)

            # If any errors occur, retry the task with a custom delay
            except Exception as e:
                retries = self.request.retries
                max_allowed_retries = len(self.retry_delays)

                # If number of retries exceeds max allowed, revent retrying for this feed
                if retries >= max_allowed_retries:
                    feed.should_retry = False
                    session.add(feed)
                    session.commit()

                    # Release lock so that the task can be scheduled again
                    release_lock(task_identifier)

                # Retry with specific countdown
                if retries < len(self.retry_delays):
                    delay = (
                        self.retry_delays[retries] * 60  # convert to seconds
                        if retries < len(self.retry_delays)
                        else None
                    )
                    raise self.retry(exc=e, countdown=delay)


@app.task(bind=True, base=RefreshFeedWithRetry)
def refresh_feed(self: RefreshFeedWithRetry, feed_id: str) -> None:  # type: ignore
    self.run_refresh_feed(feed_id)


@app.task(bind=True)
def refresh_all_feeds(self) -> None:  # type: ignore
    """Refresh all feeds by submitting a refresh job for each feed"""
    session = get_session()
    feeds = session.query(Feed).all()
    for feed in feeds:
        # Lock feed to prevent multiple refresh jobs from running at the same time
        task_identifier = get_refresh_task_identifier(feed.uuid)
        acquired = acquire_lock(task_identifier)
        if not acquired:
            logger.info(f"{feed.uuid} refresh job is already running.")
            continue
        refresh_feed.delay(feed.uuid)
    session.close()


def force_refresh_feed(session: Session, feed_id: str) -> None:  # type: ignore
    """Force refresh a feed by setting should_retry to True and submitting a refresh job
    Note that this does not acquire a lock, so it is possible for multiple forced refresh jobs to run at the same time
    """
    # Check if feed exists
    feed = session.get(Feed, feed_id)
    if not feed:
        raise NotFoundError("Feed not found.")

    feed.should_retry = True
    session.add(feed)
    session.commit()  # need to commit early so that the task can pick up the change
    refresh_feed.delay(feed_id)
