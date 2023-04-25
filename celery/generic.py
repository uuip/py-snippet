import logging
import os
import platform
import re

import redis
from django_redis import get_redis_connection
from utils.redislog import RedisLogListener

from celery import signals, Task

# Windows can't use prefork
windows = platform.system() == "Windows"
loggert = logging.getLogger()
rd = get_redis_connection()


@signals.task_failure.connect
def exception_handle(sender, task_id, exception, **kwargs):
    if isinstance(exception, redis.exceptions.LockError):
        loggert.warning(f"{sender.name}[{task_id}] can't get lock")
        return
    loggert.exception(
        f"{sender.name}[{task_id}] args={kwargs['args']} kwargs={kwargs['kwargs']} Exception:\n"
    )


@signals.task_success.connect
def task_finish(sender: Task, *args, **kwargs):
    loggert.info(f"{sender.name}[{sender.request.id}] success")


@signals.after_setup_logger.connect
def celery_log(logger, **kwargs):
    check_console(logger, **kwargs)


@signals.after_setup_task_logger.connect
def task_log(logger, **kwargs):
    check_console(logger, **kwargs)


@signals.worker_ready.connect
def clean_lock(**kwargs):
    rd.unlink(*rd.scan_iter("CELERY_TASK_LOCK_*"))
    loggert.info("worker_ready")


@signals.worker_init.connect
def hook_prefork(sender, **kwargs):
    # prefork,gevent,thread
    isprefork = sender.pool_cls.__module__.split(".")[-1] == "prefork"
    # logfile is specified by celery command arg -f
    logfile = sender.logfile
    hook = logfile and isprefork and not windows
    if hook:
        logfile = re.sub(r"%\w", "", logfile)
        if logfile == "":
            logfile = "worker.log"
        sender.logfile = logfile
        sender.options["logfile"] = logfile
        os.environ.update(HOOK_CELERY_LOG=str(int(hook)))
        listener = RedisLogListener(logfile)
        listener.start()


@signals.celeryd_after_setup.connect
def remove_mp_log_env(**kwargs):
    # remove multiprocessing log flag, this env used by 'billiard.spawn._setup_logging_in_child_hack'
    if os.getenv("HOOK_CELERY_LOG") == "1" and os.getenv("_MP_FORK_LOGFILE_"):
        os.environ.pop("_MP_FORK_LOGFILE_")


def check_console(logger, format, **kwargs):
    if not list(filter(lambda x: type(x) is logging.StreamHandler, logger.handlers)):
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(format))
        console.setLevel(logging.INFO)
        logger.addHandler(console)
