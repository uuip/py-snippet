from gevent.monkey import patch_all

patch_all()
from gevent.hub import Hub
import logging


def register_error_handler():
    logger = logging.getLogger("gevent error handler")
    Hub._origin_handle_error = Hub.handle_error

    def custom_handle_error(self, context, type, value, tb):
        logger.exception(
            f"{context._run.__qualname__}: args={context.args}, kwargs={context.kwargs}"
        )
        # self._origin_handle_error(context, type, value, tb)

    Hub.handle_error = custom_handle_error


register_error_handler()
