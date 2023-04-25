drop table IF EXISTS geoip2_network;
drop table IF EXISTS geoip2_location;
\copy geoip_location(  geoname_id, locale_code, continent_code, continent_name, country_iso_code, country_name, is_in_european_union) from 'fixtures/GeoLite2-Country-Locations-en.csv' with (format csv, header);
\copy geoip_network(  network, geoname_id, registered_country_geoname_id, represented_country_geoname_id,  is_anonymous_proxy, is_satellite_provider) from 'fixtures/GeoLite2-Country-Blocks-IPv4.csv' with (format csv, header);
\copy geoip_network(  network, geoname_id, registered_country_geoname_id, represented_country_geoname_id,  is_anonymous_proxy, is_satellite_provider) from 'fixtures/GeoLite2-Country-Blocks-IPv6.csv' with (format csv, header);
