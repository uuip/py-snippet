import copy
import logging
import os
import sys
import time
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

import zmq  # pyzmq


class ZmqLogListener(QueueListener):
    """
    call stop() before application exits to make sure zmq server to be killed
    """

    def __init__(self, logfile, port=6677):
        self.port = port
        hd = RotatingFileHandler(filename=logfile, maxBytes=100 * 1024 * 1024, backupCount=10)
        super().__init__(None, hd)

    def _monitor(self):
        self.ctx = zmq.Context.instance()
        queue = self.ctx.socket(zmq.PULL)  # type: zmq.Socket
        queue.bind(f"tcp://*:{self.port}")
        while True:
            record = queue.recv_pyobj()
            if record is None:
                continue
            self.handle(record)

    def enqueue_sentinel(self):
        self.ctx.destroy()


class ZmqPool:
    def __init__(self, port):
        self.port = port
        self.conns = dict()

    def factory(self):
        ctx = zmq.Context.instance()
        sk = ctx.socket(zmq.PUSH)
        sk.connect(f"tcp://localhost:{self.port}")
        return sk

    def __getitem__(self, item):
        if item in self.conns:
            return self.conns[item]
        else:
            conn = self.factory()
            self.conns[item] = conn
            return conn


class ZmqLogHandler(QueueHandler):
    def __init__(self, logfile=None, port=6677):
        logging.Handler.__init__(self)
        self.connections = ZmqPool(port)

    @property
    def queue(self):
        return self.connections[os.getpid()]

    def emit(self, record):
        self.queue.send_pyobj(self.prepare(record))

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
    loggerListener = ZmqLogListener("worker.log")
    loggerListener.start()
    time.sleep(10)
    loggerListener.stop()
