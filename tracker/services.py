"""
All progress and rollup calculations for the tracker app live here — never in
views or templates (see CLAUDE.md "Conventions").
"""
import calendar as calendar_module
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Sum

from .models import (
    ActivityLog,
    CareerObjective,
    Certification,
    Course,
    KPI,
    MonthlyCommitment,
    MonthlyPlan,
    Pillar,
    SkillDomain,
)


def pillar_progress(pillar_code):
    """Average progress_pct across all KPIs belonging to the given pillar code.

    Returns a float 0-100. A pillar with no KPIs yet returns 0.
    """
    kpis = KPI.objects.filter(pillar__code=pillar_code)
    if not kpis.exists():
        return 0.0
    total = sum(k.progress_pct for k in kpis)
    return total / kpis.count()


def certification_progress():
    """Average progress_pct across all certifications. 0 if none exist."""
    certs = Certification.objects.all()
    if not certs.exists():
        return 0.0
    return sum(c.progress_pct for c in certs) / certs.count()


def overall_progress():
    """
    Weighted overall progress towards the career objective.

    overall = (0.30 * certification_progress)
            + (0.35 * kpi_pillar_b_progress)
            + (0.20 * kpi_pillar_c_progress)
            + (0.15 * kpi_pillar_d_progress)

    The weights are illustrative in BUILD_BRIEF.md but MUST be read from the
    Pillar.weight field (never hardcoded, per CLAUDE.md). Pillar A's weight
    covers "capability" and is represented here by certification_progress
    (certifications earned/in-progress are the clearest capability signal),
    while pillars B, C and D map onto their own KPI sets directly.
    """
    weights = {p.code: p.weight for p in Pillar.objects.all()}
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0

    components = {
        'A': certification_progress(),
        'B': pillar_progress('B'),
        'C': pillar_progress('C'),
        'D': pillar_progress('D'),
    }

    weighted_sum = sum(
        components.get(code, 0.0) * weight for code, weight in weights.items()
    )
    return round(weighted_sum / total_weight, 1)


def certification_summary():
    certs = Certification.objects.all()
    earned = certs.filter(status=Certification.Status.EARNED).count()
    return {'earned': earned, 'total': certs.count()}


def hours_summary():
    """Hours logged to date vs planned hours across all courses + certifications."""
    planned = (Course.objects.aggregate(v=Sum('planned_hours'))['v'] or 0) + (
        Certification.objects.aggregate(v=Sum('planned_hours'))['v'] or 0
    )
    logged = ActivityLog.objects.aggregate(v=Sum('hours'))['v'] or 0
    return {'logged': float(logged), 'planned': planned}


def kpi_summary():
    kpis = KPI.objects.all()
    complete = kpis.filter(status=KPI.Status.COMPLETE).count()
    return {'complete': complete, 'total': kpis.count()}


def current_month_rag():
    """RAG rollup for KPIs relevant to the current calendar month."""
    today = date.today()
    kpis = KPI.objects.filter(
        period=KPI.Period.MONTHLY, period_year=today.year, period_month=today.month,
    )
    if not kpis.exists():
        kpis = KPI.objects.filter(period=KPI.Period.YEARLY, period_year=today.year)
    if not kpis.exists():
        return 'RED'
    rags = [k.rag for k in kpis]
    if all(r == 'GREEN' for r in rags):
        return 'GREEN'
    if any(r == 'RED' for r in rags):
        return 'RED'
    return 'AMBER'


def pillar_health():
    """Weighted RAG summary per pillar, for the dashboard's Pillar Health section."""
    results = []
    for pillar in Pillar.objects.all().order_by('order'):
        kpis = pillar.kpis.all()
        if not kpis.exists():
            rag = 'RED'
            progress = 0
        else:
            progress = round(sum(k.progress_pct for k in kpis) / kpis.count())
            rags = [k.rag for k in kpis]
            if all(r == 'GREEN' for r in rags):
                rag = 'GREEN'
            elif any(r == 'RED' for r in rags):
                rag = 'RED'
            else:
                rag = 'AMBER'
        results.append({
            'pillar': pillar,
            'rag': rag,
            'progress_pct': progress,
            'kpi_count': kpis.count(),
        })
    return results


def monthly_hours_chart_data():
    """Actual vs target hours per MonthlyPlan, ordered chronologically.

    Includes a pre-zipped `rows` list because Django templates cannot index
    two parallel lists by a shared loop counter — the table fallback (Section
    9, BUILD_BRIEF.md) loops over `rows` directly instead.
    """
    plans = MonthlyPlan.objects.all().order_by('year', 'month')
    rows = [
        {'label': plan.period_date.strftime('%b %Y'), 'actual': float(plan.actual_hours), 'target': plan.target_hours}
        for plan in plans
    ]
    return {
        'labels': [r['label'] for r in rows],
        'actual': [r['actual'] for r in rows],
        'target': [r['target'] for r in rows],
        'rows': rows,
    }


def next_commitments(limit=3):
    return list(
        MonthlyCommitment.objects.filter(is_complete=False)
        .select_related('plan', 'pillar')
        .order_by('plan__year', 'plan__month', 'order')[:limit]
    )


def recent_activity(limit=10):
    return list(ActivityLog.objects.select_related('course', 'certification', 'kpi')[:limit])


def skill_radar_data():
    domains = SkillDomain.objects.prefetch_related('skills').order_by('order')
    rows = [
        {'label': d.name, 'code': d.code, 'current': round(d.avg_current_level, 1), 'target': round(d.avg_target_level, 1)}
        for d in domains
    ]
    return {
        'labels': [r['label'] for r in rows],
        'domain_codes': [r['code'] for r in rows],
        'current': [r['current'] for r in rows],
        'target': [r['target'] for r in rows],
        'rows': rows,
    }


def dashboard_context():
    objective = CareerObjective.load()
    return {
        'objective': objective,
        'overall_progress': overall_progress(),
        'certification_summary': certification_summary(),
        'hours_summary': hours_summary(),
        'kpi_summary': kpi_summary(),
        'current_month_rag': current_month_rag(),
        'certifications': Certification.objects.all().order_by('order'),
        'domains': SkillDomain.objects.prefetch_related('skills').order_by('order'),
        'skill_radar_data': skill_radar_data(),
        'pillar_health': pillar_health(),
        'monthly_hours_data': monthly_hours_chart_data(),
        'next_commitments': next_commitments(),
        'recent_activity': recent_activity(),
    }


def activity_summary_strip(today=None):
    """Total hours this week / month / year, plus current streak in days."""
    today = today or date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    def hours_since(start_date):
        return float(
            ActivityLog.objects.filter(date__gte=start_date, date__lte=today)
            .aggregate(v=Sum('hours'))['v'] or 0
        )

    dates_with_activity = set(
        ActivityLog.objects.filter(date__lte=today).values_list('date', flat=True)
    )
    streak = 0
    cursor = today
    while cursor in dates_with_activity:
        streak += 1
        cursor -= timedelta(days=1)

    return {
        'week_hours': hours_since(week_start),
        'month_hours': hours_since(month_start),
        'year_hours': hours_since(year_start),
        'streak_days': streak,
    }


def weekly_hours_chart_data(weeks=12, today=None):
    """Sum of ActivityLog hours per ISO week for the last `weeks` weeks."""
    today = today or date.today()
    current_week_start = today - timedelta(days=today.weekday())
    week_starts = [current_week_start - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]

    totals = defaultdict(float)
    earliest = week_starts[0]
    logs = ActivityLog.objects.filter(date__gte=earliest)
    for log in logs:
        log_week_start = log.date - timedelta(days=log.date.weekday())
        totals[log_week_start] += float(log.hours)

    rows = [{'label': ws.strftime('%d %b'), 'hours': round(totals.get(ws, 0.0), 2)} for ws in week_starts]
    return {
        'labels': [r['label'] for r in rows],
        'hours': [r['hours'] for r in rows],
        'rows': rows,
    }


# ---------------------------------------------------------------------------
# Activity calendar (Year / Month / Day) — Activity Log page.
# Weeks start Monday (calendar.Calendar's default firstweekday=0).
# ---------------------------------------------------------------------------

_CALENDAR = calendar_module.Calendar(firstweekday=0)
WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def _month_bounds_shift(year, month, delta):
    """Return (year, month) shifted by `delta` months, handling year rollover."""
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


def _month_calendar(year, month, today):
    logs = list(
        ActivityLog.objects.filter(date__year=year, date__month=month)
        .select_related('course', 'certification')
        .order_by('date', '-created_at')
    )
    logs_by_date = defaultdict(list)
    for log in logs:
        logs_by_date[log.date].append(log)

    weeks = []
    for week in _CALENDAR.monthdatescalendar(year, month):
        cells = []
        for day in week:
            day_logs = logs_by_date.get(day, [])
            cells.append({
                'date': day,
                'in_month': day.month == month,
                'is_today': day == today,
                'logs': day_logs[:3],
                'extra_count': max(0, len(day_logs) - 3),
                'total_hours': sum((log.hours for log in day_logs), start=0) or 0,
            })
        weeks.append(cells)

    prev_year, prev_month = _month_bounds_shift(year, month, -1)
    next_year, next_month = _month_bounds_shift(year, month, 1)

    return {
        'cal_weeks': weeks,
        'cal_weekday_labels': WEEKDAY_LABELS,
        'cal_month_label': f'{calendar_module.month_name[month]} {year}',
        'cal_prev': {'year': prev_year, 'month': prev_month},
        'cal_next': {'year': next_year, 'month': next_month},
    }


def _year_calendar(year, today):
    rows = (
        ActivityLog.objects.filter(date__year=year)
        .values('date')
        .annotate(hours=Sum('hours'))
    )
    activity_days = {row['date']: row['hours'] for row in rows}

    months = []
    for month in range(1, 13):
        weeks = []
        for week in _CALENDAR.monthdatescalendar(year, month):
            cells = []
            for day in week:
                cells.append({
                    'date': day,
                    'in_month': day.month == month,
                    'is_today': day == today,
                    'has_activity': day in activity_days,
                })
            weeks.append(cells)
        months.append({
            'number': month,
            'name': calendar_module.month_name[month],
            'weeks': weeks,
        })

    return {
        'cal_months': months,
        'cal_weekday_labels': WEEKDAY_LABELS,
        'cal_prev_year': year - 1,
        'cal_next_year': year + 1,
    }


def _day_calendar(day):
    logs = list(
        ActivityLog.objects.filter(date=day)
        .select_related('course', 'certification', 'kpi', 'skill_domain')
        .order_by('-created_at')
    )
    return {
        'cal_day_logs': logs,
        'cal_day_total_hours': sum((log.hours for log in logs), start=0) or 0,
        'cal_prev_day': day - timedelta(days=1),
        'cal_next_day': day + timedelta(days=1),
    }


def activity_calendar_context(view_mode, year, month, day, today):
    """Build the template context for whichever calendar view is active.

    `view_mode` is one of 'month' (default), 'year', 'day'. Invalid/missing
    year, month or day values are the caller's responsibility to normalise
    before calling this (see tracker/views.py:activity_log).
    """
    context = {'cal_view': view_mode, 'cal_year': year, 'cal_month': month, 'cal_date': day, 'cal_today': today}

    if view_mode == 'year':
        context.update(_year_calendar(year, today))
    elif view_mode == 'day':
        context.update(_day_calendar(day))
    else:
        context['cal_view'] = 'month'
        context.update(_month_calendar(year, month, today))

    return context
