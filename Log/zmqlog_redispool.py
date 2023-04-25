import copy
import os
import sys
import time
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

import zmq  # pyzmq
from redis import ConnectionPool as RPool


class ConnectionPool(RPool):
    def get_connection(self, command_name, *keys, **options):
        self._checkpid()
        with self._lock:
            try:
                connection = self._available_connections.pop()
            except IndexError:
                connection = self.make_connection()
                connection.connect()
            self._in_use_connections.add(connection)

        return connection


class Connection:
    def __init__(self, port):
        self.pid = os.getpid()
        self.port = port
        self.ctx = zmq.Context.instance()
        self.socket = self.ctx.socket(zmq.PUSH)

    def disconnect(self):
        self.socket.close(0)
        self.ctx.destroy(0)

    def connect(self):
        self.socket.connect(f"tcp://localhost:{self.port}")

    def __getattr__(self, item):
        return getattr(self.socket, item)


class ZmqClient:
    def __init__(self, port, single_connection_client=False):
        self.connection_pool = ConnectionPool(connection_class=Connection, port=port)
        self.connection = None
        if single_connection_client:
            self.connection = self.connection_pool.get_connection("_")

    def exec_func(self, func):
        def call_func(*args):
            pool = self.connection_pool
            conn = self.connection or pool.get_connection("_")
            try:
                return getattr(conn, func)(*args)
            finally:
                if not self.connection:
                    pool.release(conn)

        return call_func

    def __getattr__(self, item):
        return self.exec_func(item)


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


class ZmqLogHandler(QueueHandler):
    def __init__(self, logfile=None, port=6677):
        z = ZmqClient(port)
        super().__init__(z)

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
