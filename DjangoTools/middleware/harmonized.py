import decimal
import json
from http import HTTPStatus

from rest_framework.response import Response


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)


class FormatResponse:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)  # type:Response
        if response.headers["Content-Type"] == "application/vnd.ms-excel":
            return response
        if not request.path.startswith("/api/"):
            return response
        code = response.status_code
        if code in HTTPStatus.__iter__():
            message = HTTPStatus(code).phrase
        else:
            message = "failed"
        if 200 <= code < 300:
            code = 0
            message = "success"
            if response.status_code in {201, 204}:
                response.status_code = 200

        if isinstance(response, Response):
            data = response.data
        else:
            try:
                data = json.loads(response.content)  # type:dict
            except BaseException:
                data = {}
        if data is None:
            data = {}
        if isinstance(data, dict):
            message = data.get("message") or message

        if isinstance(data, dict) and "code" in data:
            response.content = json.dumps(data, cls=DecimalEncoder, ensure_ascii=False).encode(
                "utf-8"
            )
        else:
            format_data = {"code": code, "data": data, "message": message}
            response.content = json.dumps(
                format_data, cls=DecimalEncoder, ensure_ascii=False
            ).encode("utf-8")

        response.headers["Content-Type"] = "application/json"
        return response
