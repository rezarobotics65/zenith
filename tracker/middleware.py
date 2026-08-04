"""VisitorTrackingMiddleware — logs pageviews on the public portfolio into
tracker.models.VisitorLog for the Visitor Log analytics dashboard.

Deliberately excludes the tracker itself, /admin/, /accounts/, and static or
media asset paths — only real visits to the public-facing portfolio pages
are tracked. Never tracks non-GET requests (form posts, AJAX writes).

Tracking must never be able to break or meaningfully slow down the public
site: every step (GeoIP lookup, UA parsing, DB write) is wrapped so a
failure here is logged and swallowed, not raised.
"""
import logging
from urllib.parse import urlparse

from django.utils import timezone

from . import geoip
from .models import VisitorLog

logger = logging.getLogger(__name__)

EXCLUDED_PREFIXES = ('/tracker/', '/admin/', '/accounts/', '/static/', '/media/')

REFERRAL_DOMAIN_MAP = (
    ('google.', VisitorLog.ReferralSource.GOOGLE),
    ('linkedin.', VisitorLog.ReferralSource.LINKEDIN),
    ('github.', VisitorLog.ReferralSource.GITHUB),
)


def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def classify_referral(referrer, request):
    if not referrer:
        return VisitorLog.ReferralSource.DIRECT
    ref_host = urlparse(referrer).netloc.lower()
    own_host = request.get_host().lower()
    if not ref_host or ref_host == own_host:
        return VisitorLog.ReferralSource.DIRECT
    for needle, source in REFERRAL_DOMAIN_MAP:
        if needle in ref_host:
            return source
    return VisitorLog.ReferralSource.OTHER


def parse_user_agent(ua_string):
    try:
        from user_agents import parse
        ua = parse(ua_string or '')
    except Exception:
        return {'browser': '', 'os': '', 'device': VisitorLog.Device.OTHER}

    if ua.is_mobile:
        device = VisitorLog.Device.MOBILE
    elif ua.is_tablet:
        device = VisitorLog.Device.TABLET
    elif ua.is_pc:
        device = VisitorLog.Device.DESKTOP
    else:
        device = VisitorLog.Device.OTHER

    browser = ua.browser.family or ''
    if ua.browser.version_string:
        browser = f'{browser} {ua.browser.version_string}'
    os_name = ua.os.family or ''
    if ua.os.version_string:
        os_name = f'{os_name} {ua.os.version_string}'

    return {'browser': browser.strip(), 'os': os_name.strip(), 'device': device}


class VisitorTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._track(request)
        except Exception:
            logger.warning('Visitor tracking failed', exc_info=True)
        return response

    def _should_track(self, request):
        if request.method != 'GET':
            return False
        if request.path.startswith(EXCLUDED_PREFIXES):
            return False
        return True

    def _track(self, request):
        if not self._should_track(request):
            return

        now = timezone.now()
        session_visitor_id = request.session.get('visitor_log_id')

        if session_visitor_id:
            updated = VisitorLog.objects.filter(pk=session_visitor_id).update(last_seen=now)
            if updated:
                return
            # Session referenced a row that no longer exists — fall through and recreate.

        ip_address = get_client_ip(request)
        if not ip_address:
            return

        ua_info = parse_user_agent(request.META.get('HTTP_USER_AGENT', ''))
        geo = geoip.lookup(ip_address)
        referrer = request.META.get('HTTP_REFERER', '') or ''

        visitor_log = VisitorLog.objects.create(
            visit_time=now,
            last_seen=now,
            ip_address=ip_address,
            country=geo['country'],
            region=geo['region'],
            city=geo['city'],
            timezone=geo['timezone'],
            browser=ua_info['browser'],
            operating_system=ua_info['os'],
            device=ua_info['device'],
            referrer=referrer[:500],
            referral_source=classify_referral(referrer, request),
            landing_page=request.path,
            session_key=request.session.session_key or '',
        )
        request.session['visitor_log_id'] = visitor_log.pk
