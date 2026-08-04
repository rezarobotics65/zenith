"""Best-effort IP geolocation for VisitorTrackingMiddleware.

Calls the free ip-api.com HTTP API (no key required) with a short timeout.
Every failure mode — private/local IP, network error, timeout, malformed
response — must degrade to an empty result rather than raise, since a
flaky third-party service must never be able to break the public portfolio.
"""
import ipaddress
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

GEOIP_TIMEOUT_SECONDS = 1.5
EMPTY_RESULT = {'country': '', 'region': '', 'city': '', 'timezone': ''}


def lookup(ip_address):
    try:
        addr = ipaddress.ip_address(ip_address)
    except ValueError:
        return dict(EMPTY_RESULT)

    if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
        return dict(EMPTY_RESULT)

    url = f'http://ip-api.com/json/{ip_address}?fields=status,country,regionName,city,timezone'
    try:
        with urllib.request.urlopen(url, timeout=GEOIP_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception:
        logger.warning('GeoIP lookup failed for %s', ip_address, exc_info=True)
        return dict(EMPTY_RESULT)

    if data.get('status') != 'success':
        return dict(EMPTY_RESULT)

    return {
        'country': data.get('country', '') or '',
        'region': data.get('regionName', '') or '',
        'city': data.get('city', '') or '',
        'timezone': data.get('timezone', '') or '',
    }
