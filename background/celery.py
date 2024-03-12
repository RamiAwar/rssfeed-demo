from celery.app.base import Celery
from celery.schedules import crontab

from config import get_settings

app = Celery("tasks", broker=get_settings().REDIS_DSN)

app.conf.beat_schedule = {
    "refresh-every-5-minutes": {
        "task": "background.tasks.refresh_all_feeds",
        "schedule": crontab(minute="*/5"),
    },
}
