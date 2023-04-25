import datetime
import time

from django import forms
from django.db.models import Aggregate, FloatField, Count, Func, CharField, Sum, Max
from django.db.models.query import Q
from django_filters.rest_framework import FilterSet, NumberFilter
from geoip.functions import ip2country
from larkle.models import History, App
from larkle.serialize import HistorySerializer, AppSerializer
from larkle.utils.sqlhelper import raw_sql
from rest_framework import generics
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response


class Median(Aggregate):
    function = "PERCENTILE_CONT"
    name = "median"
    output_field = FloatField()
    template = "%(function)s(0.5) WITHIN GROUP (ORDER BY %(expressions)s)"


class StampToDay(Func):
    function = "to_char"
    name = "StampToDay"
    output_field = CharField()
    template = "%(function)s(to_timestamp(%(expressions)s) AT TIME ZONE 'utc',%(format)s)"

    def __init__(self, *expressions, format_str="YYYY-MM-DD", **extra):
        format_str = f"'{format_str}'"
        super().__init__(*expressions, output_field=self.output_field, format=format_str, **extra)


class HistoryFilter(FilterSet):
    response_code = NumberFilter()

    class Meta:
        model = History
        fields = ["response_code"]


class AppStatAPIView(generics.GenericAPIView):
    def initial(self, request, *args, **kwargs):
        response_code = kwargs.get("response_code")
        if response_code:
            try:
                forms.IntegerField(max_value=700, min_value=100).clean(response_code)
            except:
                ValueError("unavailable response_code")
            else:
                request.query_params._mutable = True
                request.query_params["response_code"] = response_code
                request.query_params._mutable = False
        appid = request.query_params.get("app_id")
        app = App.objects.filter(id=appid)
        if not app or app.first().created_by != request.user:
            raise AuthenticationFailed(detail="You don't own this app.")
        self.model = History.shard(appid)  # type: History
        if getattr(self, "filterset_class", None):
            self.filterset_class.Meta.model = self.model
            self.filterset_class._meta.model = self.model
        if getattr(self, "serializer_class", None):
            self.serializer_class.Meta.model = self.model
        setattr(self, "queryset", self.model.objects.filter(app_id=appid))
        return super().initial(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        pass


class AppsStatus(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        apps = request.user.app_set.all()
        now = time.time()
        ret = {}
        for app in apps:
            data = AppSerializer(app).data
            qs = History.shard(app.id).objects.filter(app_id=app.id)
            median_response = qs.filter(query_time__gte=now - 300).aggregate(Median("duration"))[
                "duration__median"
            ]
            total_requests = qs.filter(query_time__gte=now - 24 * 3600).count()
            if total_requests == 0:
                rate_limited = 0
            else:
                rate_limited = (
                    qs.filter(Q(query_time__gte=now - 24 * 3600), Q(response_code=429)).count()
                    / total_requests
                    * 100
                )
            invalid_requests = qs.filter(
                Q(query_time__gte=now - 24 * 3600), ~Q(response_code=200)
            ).count()
            agg = {
                "median_response": median_response,
                "requests_count": total_requests,
                "rate_limited": rate_limited,
                "invalid_requests": invalid_requests,
            }
            data.update(agg)
            ret[data.pop("id")] = data
        return Response(ret)


class DailyLineChart(AppStatAPIView):
    def get(self, request, *args, **kwargs):
        utc_today = datetime.datetime.now(tz=datetime.timezone.utc)
        weeks = [(utc_today - datetime.timedelta(days=d)).strftime("%Y-%m-%d") for d in range(7)]
        select = (
            self.get_queryset()
            .values(day=StampToDay("query_time"))
            .annotate(requests=Count("*"))
            .order_by("-day")[:7]
        )
        select_dict = {x["day"]: x for x in select}
        result = []
        for day in weeks:
            if day in select_dict:
                result.append(select_dict[day])
            else:
                result.append({"day": day, "requests": 0})
        return Response(result)


class OverView(AppStatAPIView):
    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        now = time.time()
        median_response = qs.filter(query_time__gte=now - 300).aggregate(Median("duration"))[
            "duration__median"
        ]
        total_requests = qs.filter(query_time__gte=now - 24 * 3600).count()
        if total_requests == 0:
            rate_limited = 0
        else:
            rate_limited = (
                qs.filter(Q(query_time__gte=now - 24 * 3600), Q(response_code=429)).count()
                / total_requests
                * 100
            )
        invalid_requests = qs.filter(
            Q(query_time__gte=now - 24 * 3600), ~Q(response_code=200)
        ).count()
        return Response(
            {
                "median_response": median_response,
                "requests_count": total_requests,
                "rate_limited": rate_limited,
                "invalid_requests": invalid_requests,
            }
        )


class BoardAggView(AppStatAPIView):
    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        now = time.time()
        compute_units = (
            qs.filter(query_time__gte=now - 300).aggregate(Sum("duration"))["duration__sum"] or 0
        )
        total_1h = qs.filter(Q(query_time__gte=now - 3600)).count()
        total_24h = qs.filter(Q(query_time__gte=now - 24 * 3600)).count()
        success_1h_count = qs.filter(Q(query_time__gte=now - 3600), Q(response_code=200)).count()
        success_24h_count = qs.filter(
            Q(query_time__gte=now - 24 * 3600), Q(response_code=200)
        ).count()
        if total_1h > 0:
            success_1h = success_1h_count / total_1h * 100
        else:
            success_1h = None
        if total_24h > 0:
            success_24h = success_24h_count / total_24h * 100
        else:
            success_24h = None
        # https://www.postgresql.org/docs/current/functions-formatting.html
        conc_requests = (
            qs.filter(query_time__gte=now - 3600)
            .values(day=StampToDay("query_time", format_str="YYYY-MM-DD HH24:MI"))
            .annotate(conc=Count("*"))
            .aggregate(Max("conc"))["conc__max"]
            or 0
        )

        return Response(
            {
                "compute_units": compute_units,
                "success_1h": success_1h,
                "success_24h": success_24h,
                "conc_requests": conc_requests,
            }
        )


class RateLimitedChart(AppStatAPIView):
    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        select = (
            qs.filter(Q(query_time__gte=time.time() - 3600), Q(response_code=429))
            .values(mm=StampToDay("query_time", format_str="YYYY-MM-DD HH12:MI PM"))
            .annotate(requests=Count("*"))
            .order_by("-mm")
        )
        utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        last_hours = [
            (utc_now - datetime.timedelta(minutes=d)).strftime("%I:%M %p") for d in range(60)
        ]
        select_dict = {x["mm"]: x for x in select}
        result = []
        for m in last_hours:
            if m in select_dict:
                result.append(select_dict[m])
            else:
                result.append({"mm": m, "requests": 0})
        return Response(result)


class AppRequests(AppStatAPIView):
    filterset_class = HistoryFilter
    serializer_class = HistorySerializer
    ordering = ["-query_time"]

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class InvalidAppRequests(AppStatAPIView):
    serializer_class = HistorySerializer

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        select = queryset.raw(
            f"select * from {self.model._meta.db_table} where response_code <> ALL(ARRAY[200,429]::INT[]) order by query_time desc limit 10"
        )
        serializer = self.get_serializer(select, many=True)
        return Response(serializer.data)


class DailyRequestsCountry(AppStatAPIView):
    def get(self, request, *args, **kwargs):
        app_id = request.query_params.get("app_id")
        app_id = forms.IntegerField().clean(app_id)
        utc_today = datetime.datetime.now(tz=datetime.timezone.utc)
        utc_tody_timestamp = datetime.datetime(
            utc_today.year, utc_today.month, utc_today.day, tzinfo=datetime.timezone.utc
        ).timestamp()
        qs = self.filter_queryset(self.get_queryset())
        today_clients = (
            qs.filter(Q(query_time__gte=utc_tody_timestamp), Q(client_ip__isnull=False))
            .distinct("client_ip")
            .order_by("client_ip")
            .values_list("client_ip", flat=True)
        )
        ip_country = {}
        for ip in today_clients:
            ip_country[ip] = ip2country(ip)
        sql = f"""
        SELECT
            log.client_ip,
            COUNT ( log.client_ip ),
            CAST (
                ( COUNT ( log.client_ip ) / ( SELECT COUNT ( '*' ) FROM {self.model._meta.db_table} WHERE query_time >= {utc_tody_timestamp} ) :: NUMERIC * 100 ) AS DECIMAL ( 5, 2 ) 
            ) AS rate
        FROM
            {self.model._meta.db_table} AS log
        WHERE
            log.client_ip IS NOT NULL 
            AND log.query_time >= {utc_tody_timestamp}
            AND log.app_id = {app_id} 
        GROUP BY
            log.client_ip
        ORDER BY
        COUNT DESC
        """
        result = raw_sql(sql)
        for x in result:
            x.update(ip_country.get(x["client_ip"]) or {"country_code": "", "country_name": ""})
        return Response(result)
