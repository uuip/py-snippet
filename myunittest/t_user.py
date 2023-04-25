from unittest.mock import patch

import dt.apis.v0_2.views.user as userview
from django.core.cache import cache
from dt.models.user import DtUser
from model_bakery import baker
from rest_framework.test import APITestCase


class TestUser(APITestCase):
    @patch.object(cache, "get", return_value=3)
    def test_check_phone_status_available(self, mock_redis_get):
        user = baker.make(DtUser, phone="13512341234")
        response = self.client.post(
            "/dt/api/v0_2/check_mobile/", {"phone": user.phone, "scene": "login"}
        )
        mock_redis_get.assert_called_once()
        self.assertIn("token", response.data["data"])

    @patch.object(cache, "get", return_value=5)
    def test_check_phone_status_unavailable(self, mock_redis_get):
        user = baker.make(DtUser, phone="13512341234")
        response = self.client.post(
            "/dt/api/v0_2/check_mobile/", {"phone": user.phone, "scene": "login"}
        )
        mock_redis_get.assert_called_once()
        self.assertIsNone(response.data["data"])

    @patch("dt.apis.v0_2.views.user.cache")
    def test_check_phone_status_patch(self, mock_redis):
        user = baker.make(DtUser, phone="13512341234")
        mock_redis.get.return_value = 3
        response = self.client.post(
            "/dt/api/v0_2/check_mobile/", {"phone": user.phone, "scene": "login"}
        )
        mock_redis.get.assert_called_once()
        self.assertIn("token", response.data["data"])

    @patch.object(userview, "check_phone_status")
    def test_check_phone_status_mock_func(self, mock_func):
        user = baker.make(DtUser, phone="13512341234")
        mock_func.return_value = 3
        response = self.client.post(
            "/dt/api/v0_2/check_mobile/", {"phone": user.phone, "scene": "login"}
        )
        mock_func.assert_called_once()
        self.assertIn("token", response.data["data"])

    def test_check_phone_status_notexist(self):
        response = self.client.post(
            "/dt/api/v0_2/check_mobile/", {"phone": "13512341235", "scene": "login"}
        )
        self.assertIsNone(response.data["data"])
