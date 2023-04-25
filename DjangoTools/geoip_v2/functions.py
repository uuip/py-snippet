from django.db.models import F

from geoip.models import NetWork


# lookupip='''
# select country_iso_code country_code,country_name
# from geoip2_network net
# left join geoip2_location location on (
#   net.geoname_id = location.geoname_id
# )
# where network >>= '146.243.121.22';
# '''

# ANY('{1,2,3}'::inet[])
# ANY('{1.2.4.8,114.123.35.6}')


def geoip_count_nodes_raw(ipstrs):
    ipstrs = "{" + ipstrs + "}"
    return NetWork.objects.filter(network__containany=ipstrs).distinct("geoname_id").count()


def ip2country(ip):
    return (
        NetWork.objects.filter(network__contains=ip)
        .select_related()
        .values(
            country_code=F("geoname_id__country_iso_code"),
            country_name=F("geoname_id__country_name"),
        )
        .first()
    )
