from django.contrib.postgres.indexes import GistIndex
from django.db import models
from django.db.models import GenericIPAddressField, Lookup


@GenericIPAddressField.register_lookup
class ContainedIn(Lookup):
    lookup_name = "contains"

    def as_postgresql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return "%s >>= %s" % (lhs, rhs), params


@GenericIPAddressField.register_lookup
class ContainedInArray(Lookup):
    lookup_name = "containany"

    def as_postgresql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return "%s >>= ANY(%s)" % (lhs, rhs), params


class Location(models.Model):
    geoname_id = models.IntegerField(primary_key=True)
    locale_code = models.TextField()
    continent_code = models.TextField(null=True)
    continent_name = models.TextField(null=True)
    country_iso_code = models.TextField(null=True)
    country_name = models.TextField(null=True)
    is_in_european_union = models.BooleanField(default=False)


class NetWork(models.Model):
    network = models.GenericIPAddressField(db_column="network", db_index=True, primary_key=True)
    geoname_id = models.ForeignKey(
        Location,
        to_field="geoname_id",
        db_column="geoname_id",
        on_delete=models.DO_NOTHING,
        null=True,
    )
    registered_cid = models.ForeignKey(
        Location,
        to_field="geoname_id",
        db_column="registered_country_geoname_id",
        on_delete=models.DO_NOTHING,
        related_name="qcountry",
        null=True,
    )
    represented_country_geoname_id = models.IntegerField(blank=True, null=True)
    is_anonymous_proxy = models.BooleanField(default=False)
    is_satellite_provider = models.BooleanField(default=False)

    class Meta:
        indexes = [GistIndex(fields=["network"], name="network", opclasses=["inet_ops"])]
