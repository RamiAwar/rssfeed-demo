import logging

import redis

from config import get_settings

redis_client = redis.Redis(
    host=get_settings().REDIS_HOST, port=get_settings().REDIS_PORT
)

logger = logging.getLogger(__name__)


def acquire_lock(lock_name: str) -> bool:
    """Yield true if lock is acquired, false otherwise
    """
    status = redis_client.set(lock_name, "lock", nx=True)
    logger.info(f"Acquired lock {lock_name}: {status}")
    return status is not None


def release_lock(lock_name: str) -> None:
    redis_client.delete(lock_name)
