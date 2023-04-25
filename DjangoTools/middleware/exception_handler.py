import logging
from http import HTTPStatus

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import set_rollback

logger = logging.getLogger("views")


def api_exc_handler(exc, context):
    logger.exception(exc)
    error = {"code": 0, "data": {}, "message": ""}
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, "auth_header", None):
            headers["WWW-Authenticate"] = exc.auth_header
        if getattr(exc, "wait", None):
            headers["Retry-After"] = "%d" % exc.wait

        if isinstance(exc.detail, list):
            error["data"] = {"detail": exc.detail}
        elif isinstance(exc.detail, dict):
            error["data"] = exc.detail
        else:
            error["data"] = {"detail": [exc.detail]}
        error["code"] = exc.status_code
        error["message"] = HTTPStatus(exc.status_code).phrase
        set_rollback()
        return Response(error, status=exc.status_code, headers=headers)
    else:
        code = 500
        error["code"] = code
        error["message"] = HTTPStatus(code).phrase
        error["data"]["detail"] = [exc.__class__.__qualname__, *exc.args]
        return Response(error, status=code)
