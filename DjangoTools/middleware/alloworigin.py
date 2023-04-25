from django.http.response import HttpResponse


class Cors:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse()
            response["Access-Control-Allow-Methods"] = "POST, GET, PUT, DELETE"
            response[
                "Access-Control-Allow-Headers"
            ] = "Origin, X-Requested-With, Content-Type,X-CSRFToken"
        else:
            response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = request.headers.get("Origin") or "*"
        response["Access-Control-Max-Age"] = 86400
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Expose-Headers"] = "csrftoken"
        return response
        # settings.py配置如下
        # SESSION_COOKIE_HTTPONLY = False
        # # SESSION_COOKIE_SECURE=False
        # SESSION_COOKIE_SAMESITE = 'None'
        # CSRF_COOKIE_HTTPONLY = False
        # CSRF_COOKIE_SAMESITE = 'None'
