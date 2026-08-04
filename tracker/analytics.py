"""Visitor Log analytics — all aggregation/filtering logic for the portfolio
traffic dashboard lives here, never in views or templates (CLAUDE.md
"Conventions"). Kept separate from services.py, which is the original
career-progress domain; this is a distinct, later-added feature area.
"""
from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from .models import CVDownloadLog, VisitorLog

ACTIVE_WINDOW_MINUTES = 5
KPI_CACHE_SECONDS = 60
CHART_ROW_LIMIT = 10

FILTER_CHOICES = [
    ('last30', 'Last 30 Days'),
    ('today', 'Today'),
    ('yesterday', 'Yesterday'),
    ('last7', 'Last 7 Days'),
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly'),
    ('custom', 'Custom Range'),
]


def _day_bounds(d):
    start = timezone.make_aware(datetime.combine(d, time.min))
    return start, start + timedelta(days=1)


def resolve_date_range(params):
    """Turn GET params (filter, year, month, start_date, end_date) into a
    (start, end, label) tuple of timezone-aware datetimes. Defaults to the
    last 30 days when nothing (or something invalid) is supplied — filters
    never raise on bad input, they just fall back to the default range."""
    now = timezone.localtime()
    today = now.date()
    filter_key = params.get('filter', 'last30')

    if filter_key == 'today':
        start, end = _day_bounds(today)
        return start, min(end, now), 'Today'

    if filter_key == 'yesterday':
        start, end = _day_bounds(today - timedelta(days=1))
        return start, end, 'Yesterday'

    if filter_key == 'last7':
        start, _ = _day_bounds(today - timedelta(days=6))
        return start, now, 'Last 7 Days'

    if filter_key == 'monthly':
        try:
            year = int(params.get('year', today.year))
            month = int(params.get('month', today.month))
        except (TypeError, ValueError):
            year, month = today.year, today.month
        start, _ = _day_bounds(today.replace(year=year, month=month, day=1))
        if month == 12:
            end, _ = _day_bounds(today.replace(year=year + 1, month=1, day=1))
        else:
            end, _ = _day_bounds(today.replace(year=year, month=month + 1, day=1))
        return start, min(end, now) if (year, month) == (today.year, today.month) else end, f'{start:%B %Y}'

    if filter_key == 'yearly':
        try:
            year = int(params.get('year', today.year))
        except (TypeError, ValueError):
            year = today.year
        start, _ = _day_bounds(today.replace(year=year, month=1, day=1))
        end, _ = _day_bounds(today.replace(year=year + 1, month=1, day=1))
        return start, min(end, now) if year == today.year else end, str(year)

    if filter_key == 'custom':
        try:
            start_date = datetime.strptime(params.get('start_date', ''), '%Y-%m-%d').date()
            end_date = datetime.strptime(params.get('end_date', ''), '%Y-%m-%d').date()
            start, _ = _day_bounds(start_date)
            _, end = _day_bounds(end_date)
            return start, min(end, now), f'{start_date} to {end_date}'
        except ValueError:
            pass  # fall through to default

    start, _ = _day_bounds(today - timedelta(days=29))
    return start, now, 'Last 30 Days'


def active_visitors_now():
    """Deliberately never cached — this is the one number meant to feel fresh
    on every page load, per the "approximate, refreshes on page load" design
    (no JS polling; see the live-counter decision in conversation)."""
    cutoff = timezone.now() - timedelta(minutes=ACTIVE_WINDOW_MINUTES)
    return VisitorLog.objects.filter(last_seen__gte=cutoff).count()


def kpi_cards():
    """The eight always-on overview cards — deliberately independent of the
    filter dropdown (Today's Visitors always means today, regardless of what
    date range the charts below are currently showing). Cached briefly since
    every dashboard load recomputes eight COUNT queries."""
    data = cache.get('visitor_kpi_cards')
    if data is None:
        now = timezone.localtime()
        today_start, _ = _day_bounds(now.date())
        month_start, _ = _day_bounds(now.date().replace(day=1))
        year_start, _ = _day_bounds(now.date().replace(month=1, day=1))

        visitors = VisitorLog.objects
        downloads = CVDownloadLog.objects

        data = {
            'total_visitors': visitors.count(),
            'today_visitors': visitors.filter(visit_time__gte=today_start).count(),
            'month_visitors': visitors.filter(visit_time__gte=month_start).count(),
            'year_visitors': visitors.filter(visit_time__gte=year_start).count(),
            'total_downloads': downloads.count(),
            'today_downloads': downloads.filter(download_time__gte=today_start).count(),
            'month_downloads': downloads.filter(download_time__gte=month_start).count(),
            'year_downloads': downloads.filter(download_time__gte=year_start).count(),
        }
        cache.set('visitor_kpi_cards', data, KPI_CACHE_SECONDS)

    data = dict(data)
    data['active_now'] = active_visitors_now()
    return data


def _labelled(labels, values):
    """Every chart dict carries labels/values (for Chart.js) *and* a
    pre-zipped rows list, since Django templates can't index two parallel
    lists by a shared loop counter (same convention as services.py's
    monthly_hours_chart_data) — the table fallback loops over rows."""
    return {'labels': labels, 'values': values, 'rows': list(zip(labels, values))}


def daily_visitors_trend(start, end):
    rows = (
        VisitorLog.objects.filter(visit_time__gte=start, visit_time__lt=end)
        .annotate(day=TruncDate('visit_time')).values('day')
        .annotate(count=Count('id')).order_by('day')
    )
    return _labelled([r['day'].strftime('%d %b') for r in rows], [r['count'] for r in rows])


def visitors_by_country(start, end, limit=CHART_ROW_LIMIT):
    rows = (
        VisitorLog.objects.filter(visit_time__gte=start, visit_time__lt=end)
        .exclude(country='').values('country')
        .annotate(count=Count('id')).order_by('-count')[:limit]
    )
    return _labelled([r['country'] for r in rows], [r['count'] for r in rows])


def visitors_by_region(start, end, limit=CHART_ROW_LIMIT):
    rows = (
        VisitorLog.objects.filter(visit_time__gte=start, visit_time__lt=end)
        .exclude(region='').values('region')
        .annotate(count=Count('id')).order_by('-count')[:limit]
    )
    return _labelled([r['region'] for r in rows], [r['count'] for r in rows])


def visitors_by_device(start, end):
    counts = dict(
        VisitorLog.objects.filter(visit_time__gte=start, visit_time__lt=end)
        .values_list('device').annotate(count=Count('id'))
    )
    labels = [label for _, label in VisitorLog.Device.choices]
    keys = [key for key, _ in VisitorLog.Device.choices]
    return _labelled(labels, [counts.get(k, 0) for k in keys])


def visitor_sources(start, end):
    counts = dict(
        VisitorLog.objects.filter(visit_time__gte=start, visit_time__lt=end)
        .values_list('referral_source').annotate(count=Count('id'))
    )
    labels = [label for _, label in VisitorLog.ReferralSource.choices]
    keys = [key for key, _ in VisitorLog.ReferralSource.choices]
    return _labelled(labels, [counts.get(k, 0) for k in keys])


def daily_cv_downloads(start, end):
    rows = (
        CVDownloadLog.objects.filter(download_time__gte=start, download_time__lt=end)
        .annotate(day=TruncDate('download_time')).values('day')
        .annotate(count=Count('id')).order_by('day')
    )
    return _labelled([r['day'].strftime('%d %b') for r in rows], [r['count'] for r in rows])


def monthly_cv_downloads(start, end):
    rows = (
        CVDownloadLog.objects.filter(download_time__gte=start, download_time__lt=end)
        .annotate(month=TruncMonth('download_time')).values('month')
        .annotate(count=Count('id')).order_by('month')
    )
    return _labelled([r['month'].strftime('%b %Y') for r in rows], [r['count'] for r in rows])


def downloads_by_country(start, end, limit=CHART_ROW_LIMIT):
    rows = (
        CVDownloadLog.objects.filter(download_time__gte=start, download_time__lt=end)
        .exclude(country='').values('country')
        .annotate(count=Count('id')).order_by('-count')[:limit]
    )
    return _labelled([r['country'] for r in rows], [r['count'] for r in rows])


def dashboard_charts(start, end):
    return {
        'daily_visitors': daily_visitors_trend(start, end),
        'by_country': visitors_by_country(start, end),
        'by_region': visitors_by_region(start, end),
        'by_device': visitors_by_device(start, end),
        'by_source': visitor_sources(start, end),
        'daily_downloads': daily_cv_downloads(start, end),
        'monthly_downloads': monthly_cv_downloads(start, end),
        'downloads_by_country': downloads_by_country(start, end),
    }


def filter_visitor_logs(start, end, search=''):
    qs = VisitorLog.objects.filter(visit_time__gte=start, visit_time__lt=end)
    if search:
        qs = qs.filter(
            Q(ip_address__icontains=search) | Q(country__icontains=search) | Q(region__icontains=search)
            | Q(city__icontains=search) | Q(browser__icontains=search) | Q(operating_system__icontains=search)
            | Q(landing_page__icontains=search)
        )
    return qs


def filter_cv_downloads(start, end, search=''):
    qs = CVDownloadLog.objects.filter(download_time__gte=start, download_time__lt=end)
    if search:
        qs = qs.filter(
            Q(visitor_ip__icontains=search) | Q(country__icontains=search) | Q(region__icontains=search)
            | Q(city__icontains=search) | Q(browser__icontains=search) | Q(cv_version__icontains=search)
        )
    return qs
