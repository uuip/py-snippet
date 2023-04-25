import logging
import os
import sys
from functools import wraps

from celery.app import backends
from celery.app.log import Logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
from django_redis import get_redis_connection
from utils.redislog import RedisLogHandler

from celery import Celery as CeleryOriginal

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "triathon.settings")
os.environ.update(C_FORCE_ROOT="1")
rd = get_redis_connection()


class LoggingWithRotating(Logging):
    def _detect_handler(self, logfile=None):
        """Create handler from filename, an open stream or `None` (stderr)."""
        logfile = sys.__stderr__ if logfile is None else logfile
        if hasattr(logfile, "write"):
            return logging.StreamHandler(logfile)
        if os.getenv("HOOK_CELERY_LOG") == "1":
            return RedisLogHandler(logfile)
        return ConcurrentRotatingFileHandler(
            logfile, encoding="utf-8", maxBytes=100 * 1024 * 1024, backupCount=10
        )


class Celery(CeleryOriginal):
    """
    fix connection leak when using redis as backend. Patch Celery class so we can use 'pip install celery' directly.
    """

    redis_backend = None

    def _get_backend(self):
        backend, url = backends.by_url(self.backend_cls or self.conf.result_backend, self.loader)
        # redis-py always use independent connection for every command, one pool instance is enough
        if isinstance(url, str) and url.startswith("redis"):
            if not self.redis_backend:
                self.redis_backend = backend(app=self, url=url)
            return self.redis_backend
        return backend(app=self, url=url)


app = Celery("triathon", log=LoggingWithRotating)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


# @app.task(bind=True)
# def debug_task(self):
#     print(f'Request: {self.request!r}')

# timeout <= CELERY_TASK_TIME_LIMIT
def task_lock(func=None, timeout=180, waiting_time=10, lock_name=""):
    def decorator(run_func):
        @wraps(run_func)
        def wrapper(*args, **kwargs):
            if lock_name:
                if not lock_name.startswith("CELERY_TASK_LOCK_"):
                    new_lock_name = "CELERY_TASK_LOCK_" + lock_name
                else:
                    new_lock_name = lock_name
            else:
                new_lock_name = f"CELERY_TASK_LOCK_{run_func.__module__}.{run_func.__name__}"
            with rd.lock(new_lock_name, timeout, blocking_timeout=waiting_time):
                return run_func(*args, **kwargs)

        return wrapper

    return decorator(func) if func is not None else decorator
