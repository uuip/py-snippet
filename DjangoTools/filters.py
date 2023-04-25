from battle.models import TestResult
from django.contrib.postgres.search import SearchVector
from django_filters.rest_framework import FilterSet, filters
from dungeon.models.auction_models import Detect, Ship, NFTStatus


class TestPoliciesFilter(FilterSet):
    address = filters.CharFilter(field_name="ship__owner", lookup_expr="iexact")
    round = filters.NumberFilter(field_name="round")
    name = filters.CharFilter(field_name="ship__name")
    search = filters.CharFilter(method="fuzzy_search")

    def fuzzy_search(self, queryset, name, value):
        return queryset.annotate(
            search=SearchVector("ship__owner", "ship__name", "ship__token_id")
        ).filter(search=value)

    class Meta:
        model = Detect
        fields = ["address", "round", "search", "name"]


class TestResultFilter(FilterSet):
    address = filters.CharFilter(method="inrounds")

    def inrounds(self, queryset, name, value):
        if value:
            rounds = list(
                Detect.objects.filter(chain=1, ship__owner__iexact=value)
                .order_by("round")
                .distinct("round")
                .values_list("round", flat=True)
            )
            return queryset.filter(round__in=rounds)
        return queryset

    class Meta:
        model = TestResult
        fields = ["address"]


class TestRankingFilter(FilterSet):
    address = filters.CharFilter(field_name="owner")
    search = filters.CharFilter(method="fuzzy_search")
    status = filters.MultipleChoiceFilter(choices=NFTStatus.choices, field_name="status")

    def fuzzy_search(self, queryset, name, value):
        return queryset.annotate(search=SearchVector("owner", "name", "token_id")).filter(
            search=value
        )

    class Meta:
        model = Ship
        fields = ["address", "status", "search"]


class MyShipsFilter(FilterSet):
    address = filters.CharFilter(field_name="owner", lookup_expr="iexact")
    status = filters.MultipleChoiceFilter(choices=NFTStatus.choices, field_name="status")
    round = filters.NumberFilter(field_name="detect__round", lookup_expr="exact")

    class Meta:
        model = Ship
        fields = ["address", "status"]
