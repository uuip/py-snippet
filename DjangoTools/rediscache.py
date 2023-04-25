import json

from django.core.serializers.json import DjangoJSONEncoder
from django_redis.serializers.base import BaseSerializer


class JSONSerializer(BaseSerializer):
    """
    The default JSON serializer of django-redis assumes `decode_responses`
    is disabled, and calls `decode()` and `encode()` on the value.
    This serializer does not.
    """

    def dumps(self, value):
        return json.dumps(value, cls=DjangoJSONEncoder)

    def loads(self, value):
        return json.loads(value)
