import secrets
import string

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from larkle.utils.sharding import ShardingMixin, create_model


def make_token():
    sample = string.ascii_letters + string.digits
    return "".join(secrets.choice(sample) for x in range(32))


class User(AbstractUser):
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=False,
        help_text=_("Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."),
        validators=[UnicodeUsernameValidator],
        blank=True,
    )
    email = models.EmailField(_("email address"), blank=False, unique=True)
    role = models.CharField(_("role of Team"), blank=True, max_length=50)
    discord_name = models.CharField(_("Discord Username"), blank=True, max_length=50)
    telegram_name = models.CharField(_("Telegram Username"), blank=True, max_length=50)
    date_joined = models.DateTimeField(auto_now_add=True)


class App(models.Model):
    name = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=50, blank=True)
    enviroment = models.CharField(max_length=50, blank=False)
    network = models.CharField(max_length=50, blank=False)
    is_active = models.BooleanField(default=True)
    auth_token = models.CharField(max_length=32, blank=False, default=make_token())
    time_created = models.DateTimeField(auto_now_add=True)
    qps_limit = models.IntegerField(default=300)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    chain = models.CharField(max_length=20, blank=False, default=None)
    # fcups_limit = models.IntegerField(default=0)
    # concurrent_request_limit = models.IntegerField(default=0)
    # team=
    # whitelisted_addresses=models.ManyToManyField
    # whitelisted_origins
    # whitelisted_ips
    # whitelisted_address_entries
    # whitelisted_origin_entries
    # whitelisted_ip_entries


#
# class Team(models.Model):
#     name = models.CharField(max_length=50, blank=False)
#     time_created = models.DateTimeField(auto_created=True)
#     setup_stage = models.IntegerField()
#     expiry_time = models.DateTimeField()
#     app_limit = models.IntegerField()
#     rate_limit_alert_ack = models.BooleanField(default=False)
#     auth_token = models.CharField(max_length=256)


class Node(models.Model):
    identity = models.IntegerField(blank=True)
    name = models.CharField(max_length=50, blank=True)
    wan = models.CharField(max_length=50)
    lan = models.CharField(max_length=50, blank=True)
    status = models.BooleanField(default=True)
    chain = models.CharField(max_length=50)
    network = models.CharField(max_length=50)


class History(models.Model, ShardingMixin):
    query_time = models.BigIntegerField()
    request = models.JSONField()
    duration = models.FloatField()
    response = models.JSONField()
    response_code = models.IntegerField()
    eth_method = models.CharField(max_length=100, blank=True)
    # A database index is automatically created on the ForeignKey.
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    network = models.CharField(max_length=50)
    func = models.CharField(max_length=100, blank=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)

    SHARDING_TYPE = "precise"
    SHARDING_COUNT = 40

    class Meta:
        abstract = True
        db_table = "history_"
        ordering = ["-query_time"]


for sharding in History.get_sharding_list():
    create_model(History, sharding)
