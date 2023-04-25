import copy
import json
import sys
from logging import makeLogRecord
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path

from conf import config
from redis import Redis


class RedisLogListener(QueueListener):
    """
    Listener write log file in thread
    """

    def __init__(self, logfile="testredis.log"):
        r = Redis.from_url(config.redis)
        self.log_queue = "log_" + Path(logfile).stem
        hd = RotatingFileHandler(filename=logfile, maxBytes=100 * 1024 * 1024, backupCount=10)
        super().__init__(r, hd)

    def dequeue(self, block: bool):
        # blpop is blocked until rpush an item.
        msg = self.queue.blpop(self.log_queue)
        return makeLogRecord(json.loads(msg[1]))

    def _monitor(self):
        while True:
            try:
                record = self.dequeue(True)
                if record is None:
                    continue
                self.handle(record)
            except BaseException:
                pass

    def enqueue_sentinel(self):
        pass


class RedisLogHandler(QueueHandler):
    # the preforked processes inherit this class, so all processes has same conn instance.
    # each process should have its own connection.
    # Redis has a pool resolution, no matter multiprocessing or threading; others are not so lucky.

    def __init__(self, logfile):
        r = Redis.from_url(config.redis)
        self.log_queue = "log_" + Path(logfile).stem
        super().__init__(r)

    def enqueue(self, record):
        self.queue.rpush(self.log_queue, json.dumps(record.__dict__))

    # python 3.6 has a bug, copy prepare from python3.9
    if sys.version_info < (3, 8):

        def prepare(self, record):
            msg = self.format(record)
            record = copy.copy(record)
            record.message = msg
            record.msg = msg
            record.args = None
            record.exc_info = None
            record.exc_text = None
            return record


if __name__ == "__main__":
    loggerListener = RedisLogListener()
    loggerListener.start()
    loggerListener.stop()
