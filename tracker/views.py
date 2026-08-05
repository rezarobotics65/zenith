import csv
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import analytics
from . import forms as tracker_forms
from . import services
from .models import (
    ActivityLog,
    CareerObjective,
    Certification,
    Course,
    CVDownloadLog,
    KPI,
    MonthlyCommitment,
    MonthlyPlan,
    Pillar,
    Resume,
    Skill,
    SkillDomain,
)

# staff_member_required defaults to redirecting to the admin login page
# ('admin:login'); BUILD_BRIEF.md Section 3 requires /accounts/login/ instead.
tracker_staff_required = staff_member_required(login_url=settings.LOGIN_URL)


@tracker_staff_required
def dashboard(request):
    context = services.dashboard_context()
    return render(request, 'tracker/dashboard.html', context)


MONTH_CHOICES = [
    (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
    (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
    (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
]


@tracker_staff_required
def kpi_timetable(request):
    year = request.GET.get('year', '')
    status = request.GET.get('status', '')
    tier = request.GET.get('tier', '')
    month = request.GET.get('month', '')

    courses = Course.objects.select_related('domain', 'certification').order_by('tier', 'order')
    if status:
        courses = courses.filter(status=status)
    if tier:
        courses = courses.filter(tier=tier)
    if month:
        courses = courses.filter(target_month__month=month)

    certifications = Certification.objects.order_by('order')
    if status:
        certifications = certifications.filter(status=status)
    if month:
        certifications = certifications.filter(target_date__month=month)

    kpis = KPI.objects.select_related('pillar').order_by('pillar__order', 'order')
    if year:
        kpis = kpis.filter(period_year=year)
    if status:
        kpis = kpis.filter(status=status)
    if month:
        # due_date covers both YEARLY and MONTHLY KPIs; period_month is only
        # ever set for MONTHLY-period KPIs and would hide most of the board.
        kpis = kpis.filter(due_date__month=month)

    kpis_by_pillar = {}
    for pillar in Pillar.objects.order_by('order'):
        pillar_kpis = [k for k in kpis if k.pillar_id == pillar.id]
        if pillar_kpis:
            kpis_by_pillar[pillar] = pillar_kpis

    courses_by_tier = {}
    for tier_value, tier_label in Course.Tier.choices:
        tier_courses = [c for c in courses if c.tier == tier_value]
        if tier_courses:
            courses_by_tier[tier_label] = tier_courses

    monthly_plans = MonthlyPlan.objects.prefetch_related('commitments__pillar').order_by('year', 'month')
    if year:
        monthly_plans = monthly_plans.filter(year=year)
    if month:
        monthly_plans = monthly_plans.filter(month=month)

    timetable_rows = _build_timetable(courses, certifications)

    years = sorted(set(KPI.objects.values_list('period_year', flat=True)))

    context = {
        'timetable_rows': timetable_rows['rows'],
        'timetable_months': timetable_rows['months'],
        'courses_by_tier': courses_by_tier,
        'kpis_by_pillar': kpis_by_pillar,
        'monthly_plans': monthly_plans,
        'filter_year': year,
        'filter_status': status,
        'filter_tier': tier,
        'filter_month': month,
        'years': years,
        'status_choices': KPI.Status.choices,
        'course_status_choices': Course.Status.choices,
        'tier_choices': Course.Tier.choices,
        'month_choices': MONTH_CHOICES,
    }
    return render(request, 'tracker/kpi_timetable.html', context)


def _month_range(start, end):
    months = []
    cursor = date(start.year, start.month, 1)
    end_marker = date(end.year, end.month, 1)
    while cursor <= end_marker:
        months.append(cursor)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return months


def _build_timetable(courses, certifications):
    """Month-by-month grid: rows are courses/certs, columns are every month
    present in the data (BUILD_BRIEF.md Section 6.3 — must render any range
    present in the data, not a fixed window)."""
    items = []
    all_months = []

    for course in courses:
        start = course.start_month
        target = course.target_month or course.completed_date
        if start and target:
            items.append({
                'label': course.name,
                'kind': 'course',
                'start': start,
                'end': target,
                'target_month': course.target_month,
                'status': course.get_status_display(),
                'obj': course,
            })
            all_months += [start, target]

    for cert in certifications:
        if cert.target_date:
            start = cert.earned_date or date(cert.target_date.year, cert.target_date.month, 1)
            items.append({
                'label': cert.name,
                'kind': 'certification',
                'start': start,
                'end': cert.target_date,
                'target_month': cert.target_date,
                'status': cert.get_status_display(),
                'obj': cert,
            })
            all_months += [start, cert.target_date]

    if not all_months:
        return {'rows': [], 'months': []}

    range_start = min(all_months)
    range_end = max(all_months)
    months = _month_range(range_start, range_end)

    rows = []
    for item in items:
        cells = []
        for month in months:
            active = item['start'] <= month <= item['end']
            is_target = bool(
                item['target_month']
                and item['target_month'].year == month.year
                and item['target_month'].month == month.month
            )
            cells.append({'active': active, 'is_target': is_target})
        rows.append({'label': item['label'], 'kind': item['kind'], 'status': item['status'], 'cells': cells})

    return {'rows': rows, 'months': months}


@tracker_staff_required
def activity_log(request):
    logs = ActivityLog.objects.select_related('course', 'certification', 'kpi', 'skill_domain')

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    activity_type = request.GET.get('activity_type', '')
    course_id = request.GET.get('course', '')
    certification_id = request.GET.get('certification', '')

    if date_from:
        logs = logs.filter(date__gte=date_from)
    if date_to:
        logs = logs.filter(date__lte=date_to)
    if activity_type:
        logs = logs.filter(activity_type=activity_type)
    if course_id:
        logs = logs.filter(course_id=course_id)
    if certification_id:
        logs = logs.filter(certification_id=certification_id)

    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'summary': services.activity_summary_strip(),
        'weekly_chart_data': services.weekly_hours_chart_data(),
        'activity_types': ActivityLog.ActivityType.choices,
        'courses': Course.objects.order_by('name'),
        'certifications': Certification.objects.order_by('name'),
        'filter_date_from': date_from,
        'filter_date_to': date_to,
        'filter_activity_type': activity_type,
        'filter_course': course_id,
        'filter_certification': certification_id,
    }
    context.update(_build_calendar_context(request))
    return render(request, 'tracker/activity_log.html', context)


def _build_calendar_context(request):
    today = timezone.localdate()

    cal_view = request.GET.get('cal_view', 'month')
    if cal_view not in ('month', 'year', 'day'):
        cal_view = 'month'

    try:
        cal_year = int(request.GET.get('cal_year', today.year))
    except (TypeError, ValueError):
        cal_year = today.year
    cal_year = max(1, min(9999, cal_year))

    try:
        cal_month = int(request.GET.get('cal_month', today.month))
    except (TypeError, ValueError):
        cal_month = today.month
    cal_month = max(1, min(12, cal_month))

    try:
        cal_date = date.fromisoformat(request.GET.get('cal_date', '')) if request.GET.get('cal_date') else today
    except ValueError:
        cal_date = today

    # Links that switch calendar view/period must keep the entry-list
    # filters (date_from, activity_type, ...) intact, and vice versa.
    preserved = request.GET.copy()
    for key in ('cal_view', 'cal_year', 'cal_month', 'cal_date', 'page'):
        preserved.pop(key, None)
    base_qs = preserved.urlencode()

    context = services.activity_calendar_context(cal_view, cal_year, cal_month, cal_date, today)
    context['cal_base_qs'] = base_qs
    return context


# ---------------------------------------------------------------------------
# In-page editing. Django admin remains available and remains the richer
# tool (bulk actions, autocomplete) — these generic views exist so day-to-day
# updates on the Dashboard / KPI & Timetable / Activity Log pages don't
# require a trip to /admin/. One pair of generic views + a registry, rather
# than a hand-written view per model, keeps this from becoming ~30 near-
# identical view functions.
# ---------------------------------------------------------------------------

# slug -> (Model, ModelForm, display name, default redirect url name, allow_add, allow_delete)
CRUD_REGISTRY = {
    'objective': (CareerObjective, tracker_forms.CareerObjectiveForm, 'career objective', 'tracker:dashboard', False, False),
    'skill-domain': (SkillDomain, tracker_forms.SkillDomainForm, 'skill domain', 'tracker:dashboard', True, True),
    'skill': (Skill, tracker_forms.SkillForm, 'skill', 'tracker:dashboard', True, True),
    'certification': (Certification, tracker_forms.CertificationForm, 'certification', 'tracker:kpi_timetable', True, True),
    'course': (Course, tracker_forms.CourseForm, 'course', 'tracker:kpi_timetable', True, True),
    # Pillar delete is disabled: KPI.pillar uses on_delete=PROTECT, and
    # services.overall_progress() hardcodes lookups for codes A/B/C/D — a
    # deleted pillar would silently break the weighted formula rather than
    # error, so it's safer not to offer delete here at all.
    'pillar': (Pillar, tracker_forms.PillarForm, 'pillar', 'tracker:kpi_timetable', True, False),
    'kpi': (KPI, tracker_forms.KPIForm, 'KPI', 'tracker:kpi_timetable', True, True),
    'monthly-plan': (MonthlyPlan, tracker_forms.MonthlyPlanForm, 'monthly plan', 'tracker:kpi_timetable', True, True),
    'commitment': (MonthlyCommitment, tracker_forms.MonthlyCommitmentForm, 'commitment', 'tracker:kpi_timetable', True, True),
    'activity': (ActivityLog, tracker_forms.ActivityLogForm, 'activity entry', 'tracker:activity_log', True, True),
    'resume': (Resume, tracker_forms.ResumeForm, 'CV', 'tracker:cv_list', True, True),
}


def _safe_next(request, fallback_url_name):
    candidate = request.POST.get('next') or request.GET.get('next')
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return candidate
    return reverse(fallback_url_name)


@tracker_staff_required
def edit_object(request, model_slug, pk=None):
    Model, FormClass, display_name, redirect_url_name, allow_add, allow_delete = CRUD_REGISTRY[model_slug]

    if pk is None:
        if not allow_add:
            return redirect(_safe_next(request, redirect_url_name))
        instance = None
    else:
        instance = get_object_or_404(Model, pk=pk)

    next_url = _safe_next(request, redirect_url_name)

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f'Saved {display_name}.')
            return redirect(next_url)
    else:
        form = FormClass(instance=instance)

    context = {
        'form': form,
        'model_slug': model_slug,
        'display_name': display_name,
        'is_new': instance is None,
        'next': next_url,
    }
    return render(request, 'tracker/form.html', context)


@tracker_staff_required
def delete_object(request, model_slug, pk):
    Model, _FormClass, display_name, redirect_url_name, _allow_add, allow_delete = CRUD_REGISTRY[model_slug]
    if not allow_delete:
        return redirect(_safe_next(request, redirect_url_name))

    instance = get_object_or_404(Model, pk=pk)
    next_url = _safe_next(request, redirect_url_name)

    if request.method == 'POST':
        instance.delete()
        messages.success(request, f'Deleted {display_name}.')
        return redirect(next_url)

    context = {'object': instance, 'display_name': display_name, 'next': next_url}
    return render(request, 'tracker/confirm_delete.html', context)


@tracker_staff_required
@require_POST
def toggle_commitment(request, pk):
    commitment = get_object_or_404(MonthlyCommitment, pk=pk)
    commitment.is_complete = not commitment.is_complete
    commitment.completed_date = timezone.localdate() if commitment.is_complete else None
    commitment.save(update_fields=['is_complete', 'completed_date', 'updated_at'])
    return redirect(_safe_next(request, 'tracker:kpi_timetable'))


def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@tracker_staff_required
@require_POST
def quick_update_kpi(request, pk):
    """Inline Status + Current value edit from the KPI & Timetable table.

    Auto-saves on change (static/js/inline-edit.js) — the AJAX path returns
    JSON so the row can update in place without a page reload. A non-AJAX
    POST (JS disabled) still redirects, same as every other tracker view.
    """
    kpi = get_object_or_404(KPI, pk=pk)
    form = tracker_forms.KPIQuickUpdateForm(request.POST, instance=kpi)

    if form.is_valid():
        form.save()
        if _is_ajax(request):
            return JsonResponse({
                'ok': True,
                'progress_pct': kpi.progress_pct,
                'status_display': kpi.get_status_display(),
                'rag': kpi.rag,
            })
        messages.success(request, f'Updated {kpi.code}.')
        return redirect(_safe_next(request, 'tracker:kpi_timetable'))

    if _is_ajax(request):
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
    messages.error(request, f'Could not update {kpi.code} — check the value.')
    return redirect(_safe_next(request, 'tracker:kpi_timetable'))


@tracker_staff_required
@require_POST
def quick_update_course(request, pk):
    """Inline Status edit from the KPI & Timetable Courses table."""
    course = get_object_or_404(Course, pk=pk)
    form = tracker_forms.CourseQuickUpdateForm(request.POST, instance=course)

    if form.is_valid():
        form.save()
        if _is_ajax(request):
            return JsonResponse({
                'ok': True,
                'progress_pct': course.progress_pct,
                'status_display': course.get_status_display(),
            })
        messages.success(request, f'Updated {course.name}.')
        return redirect(_safe_next(request, 'tracker:kpi_timetable'))

    if _is_ajax(request):
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
    messages.error(request, f'Could not update {course.name} — check the value.')
    return redirect(_safe_next(request, 'tracker:kpi_timetable'))


@tracker_staff_required
@require_POST
def quick_set_course_hours(request, pk):
    """Inline "hrs" input from the KPI & Timetable Courses table.

    This sets the total hours logged to exactly what was typed — it does
    not add to it. But Course.hours_logged is a computed sum over
    ActivityLog (never a raw field, and other entries for this course may
    already exist from the Activity Log page or admin), so "setting" it
    means logging an adjustment entry for the difference, rather than
    deleting and replacing history.

    Re-typing a new total for the same course on the same day updates that
    day's adjustment entry in place instead of stacking another one — the
    log should show the final value from a correction session, not every
    intermediate value typed on the way there. Entries from other days, or
    logged manually elsewhere, are never touched.
    """
    course = get_object_or_404(Course, pk=pk)
    raw_hours = (request.POST.get('hours') or '').strip()

    try:
        target_total = Decimal(raw_hours)
    except (InvalidOperation, ValueError):
        target_total = None

    if not raw_hours or target_total is None or target_total < 0:
        if _is_ajax(request):
            return JsonResponse({'ok': False, 'errors': {'hours': ['Enter a number of hours (0 or more).']}}, status=400)
        messages.error(request, 'Enter a number of hours (0 or more).')
        return redirect(_safe_next(request, 'tracker:kpi_timetable'))

    today = timezone.localdate()
    title = f'Hours total set via KPI & Timetable — {course.name}'
    existing = ActivityLog.objects.filter(
        course=course, date=today, activity_type=ActivityLog.ActivityType.STUDY, title=title,
    ).first()

    if existing:
        other_hours = course.hours_logged - existing.hours
        new_delta = target_total - other_hours
        if new_delta == 0:
            existing.delete()
        else:
            existing.hours = new_delta
            existing.save(update_fields=['hours', 'updated_at'])
    else:
        delta = target_total - course.hours_logged
        if delta != 0:
            ActivityLog.objects.create(
                date=today,
                activity_type=ActivityLog.ActivityType.STUDY,
                title=title,
                hours=delta,
                course=course,
            )

    if _is_ajax(request):
        return JsonResponse({
            'ok': True,
            'hours_logged': float(course.hours_logged),
            'planned_hours': course.planned_hours,
            'progress_pct': course.progress_pct,
        })
    messages.success(request, f'Set {course.name} to {target_total}h.')
    return redirect(_safe_next(request, 'tracker:kpi_timetable'))


@tracker_staff_required
def cv_list(request):
    resumes = Resume.objects.all()
    context = {'resumes': resumes}
    return render(request, 'tracker/cv_list.html', context)


@tracker_staff_required
@require_POST
def set_default_resume(request, pk):
    resume = get_object_or_404(Resume, pk=pk)
    resume.is_default = True
    resume.save()  # Resume.save() unsets is_default on every other row.
    messages.success(request, f'{resume.filename} set as default.')
    return redirect(_safe_next(request, 'tracker:cv_list'))


# ---------------------------------------------------------------------------
# Visitor Log — portfolio traffic + CV download analytics.
# ---------------------------------------------------------------------------

VISITOR_SORT_FIELDS = {
    'visit_time', 'ip_address', 'country', 'region', 'city',
    'browser', 'operating_system', 'device', 'referral_source', 'landing_page',
}
DOWNLOAD_SORT_FIELDS = {
    'download_time', 'visitor_name', 'organization', 'email', 'country', 'region', 'city',
    'browser', 'device', 'cv_version',
}


def _apply_sort(qs, sort_param, allowed_fields, default):
    field = (sort_param or default).lstrip('-')
    if field not in allowed_fields:
        return qs.order_by(default)
    return qs.order_by(sort_param if sort_param else default)


def _paginate(request, qs, param_name, per_page=25):
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get(param_name, 1)
    return paginator.get_page(page_number)


def _querystring_without(request, *keys):
    qs = request.GET.copy()
    for key in keys:
        qs.pop(key, None)
    return qs.urlencode()


@tracker_staff_required
def visitor_log(request):
    start, end, range_label = analytics.resolve_date_range(request.GET)
    search = request.GET.get('q', '').strip()

    visitors_qs = _apply_sort(
        analytics.filter_visitor_logs(start, end, search),
        request.GET.get('sort'), VISITOR_SORT_FIELDS, '-visit_time',
    )
    downloads_qs = _apply_sort(
        analytics.filter_cv_downloads(start, end, search),
        request.GET.get('dsort'), DOWNLOAD_SORT_FIELDS, '-download_time',
    )
    visitors_page = _paginate(request, visitors_qs, 'page')
    # Approximate "did this visit lead to a download" by matching IP within
    # the same range — VisitorLog and CVDownloadLog aren't directly linked.
    page_ips = {v.ip_address for v in visitors_page}
    downloaded_ips = set(
        CVDownloadLog.objects.filter(download_time__gte=start, download_time__lt=end, visitor_ip__in=page_ips)
        .values_list('visitor_ip', flat=True)
    ) if page_ips else set()

    context = {
        'kpis': analytics.kpi_cards(),
        'charts': analytics.dashboard_charts(start, end),
        'range_label': range_label,
        'qs_sort_base': _querystring_without(request, 'sort', 'page'),
        'qs_dsort_base': _querystring_without(request, 'dsort', 'dpage'),
        'qs_page_base': _querystring_without(request, 'page'),
        'qs_dpage_base': _querystring_without(request, 'dpage'),
        'current_sort': request.GET.get('sort', '-visit_time'),
        'current_dsort': request.GET.get('dsort', '-download_time'),
        'filter_choices': analytics.FILTER_CHOICES,
        'active_filter': request.GET.get('filter', 'last30'),
        'search': search,
        'visitors_page': visitors_page,
        'downloads_page': _paginate(request, downloads_qs, 'dpage'),
        'downloaded_ips': downloaded_ips,
        'visitor_columns': [
            ('visit_time', 'Date/Time'), ('ip_address', 'IP Address'), ('country', 'Country'),
            ('region', 'Region'), ('city', 'City'), ('browser', 'Browser'), ('operating_system', 'OS'),
            ('device', 'Device'), ('referral_source', 'Referral'), ('landing_page', 'Landing Page'),
        ],
        'download_columns': [
            ('download_time', 'Download Time'), ('visitor_name', 'Name'), ('organization', 'Organization'),
            ('email', 'Email'), ('country', 'Country'), ('region', 'Region'), ('city', 'City'),
            ('browser', 'Browser'), ('device', 'Device'), ('cv_version', 'CV Version'), ('download_source', 'Source'),
        ],
    }
    return render(request, 'tracker/visitor_log.html', context)


def _visitor_export_rows(request):
    start, end, _ = analytics.resolve_date_range(request.GET)
    search = request.GET.get('q', '').strip()
    return analytics.filter_visitor_logs(start, end, search)


def _download_export_rows(request):
    start, end, _ = analytics.resolve_date_range(request.GET)
    search = request.GET.get('q', '').strip()
    return analytics.filter_cv_downloads(start, end, search)


VISITOR_EXPORT_HEADERS = [
    'Date/Time', 'IP Address', 'Country', 'Region', 'City', 'Timezone',
    'Browser', 'OS', 'Device', 'Referral', 'Landing Page', 'Session Duration (s)',
]


def _visitor_export_row(v):
    return [
        timezone.localtime(v.visit_time).strftime('%Y-%m-%d %H:%M:%S'), v.ip_address, v.country, v.region, v.city,
        v.timezone, v.browser, v.operating_system, v.get_device_display(), v.get_referral_source_display(),
        v.landing_page, int(v.session_duration.total_seconds()),
    ]


DOWNLOAD_EXPORT_HEADERS = [
    'Download Time', 'Name', 'Organization', 'Email', 'IP Address', 'Country', 'Region', 'City',
    'Browser', 'Device', 'CV Version', 'Source',
]


def _download_export_row(d):
    return [
        timezone.localtime(d.download_time).strftime('%Y-%m-%d %H:%M:%S'), d.visitor_name, d.organization, d.email,
        d.visitor_ip, d.country, d.region, d.city, d.browser, d.get_device_display(), d.cv_version, d.download_source,
    ]


@tracker_staff_required
def visitor_log_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="visitor-log.csv"'
    writer = csv.writer(response)
    writer.writerow(VISITOR_EXPORT_HEADERS)
    for v in _visitor_export_rows(request):
        writer.writerow(_visitor_export_row(v))
    return response


@tracker_staff_required
def download_log_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="cv-downloads.csv"'
    writer = csv.writer(response)
    writer.writerow(DOWNLOAD_EXPORT_HEADERS)
    for d in _download_export_rows(request):
        writer.writerow(_download_export_row(d))
    return response


def _xlsx_response(filename, headers, rows):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append([str(cell) for cell in row])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@tracker_staff_required
def visitor_log_export_excel(request):
    rows = [_visitor_export_row(v) for v in _visitor_export_rows(request)]
    return _xlsx_response('visitor-log.xlsx', VISITOR_EXPORT_HEADERS, rows)


@tracker_staff_required
def download_log_export_excel(request):
    rows = [_download_export_row(d) for d in _download_export_rows(request)]
    return _xlsx_response('cv-downloads.xlsx', DOWNLOAD_EXPORT_HEADERS, rows)


# --- JSON APIs (staff-only — this is visitor-level data, never public) -----

@tracker_staff_required
def api_visitor_summary(request):
    start, end, range_label = analytics.resolve_date_range(request.GET)
    return JsonResponse({'range': range_label, 'kpis': analytics.kpi_cards(), 'charts': analytics.dashboard_charts(start, end)})


@tracker_staff_required
def api_download_summary(request):
    start, end, range_label = analytics.resolve_date_range(request.GET)
    kpis = analytics.kpi_cards()
    return JsonResponse({
        'range': range_label,
        'total_downloads': kpis['total_downloads'],
        'today_downloads': kpis['today_downloads'],
        'month_downloads': kpis['month_downloads'],
        'year_downloads': kpis['year_downloads'],
        'daily_downloads': analytics.daily_cv_downloads(start, end),
        'monthly_downloads': analytics.monthly_cv_downloads(start, end),
        'by_country': analytics.downloads_by_country(start, end),
    })


@tracker_staff_required
def api_visitor_log(request):
    page = _paginate(request, _visitor_export_rows(request), 'page')
    return JsonResponse({
        'count': page.paginator.count,
        'page': page.number,
        'num_pages': page.paginator.num_pages,
        'results': [
            {
                'visit_time': v.visit_time.isoformat(), 'ip_address': v.ip_address, 'country': v.country,
                'region': v.region, 'city': v.city, 'timezone': v.timezone, 'browser': v.browser,
                'operating_system': v.operating_system, 'device': v.device, 'referral_source': v.referral_source,
                'landing_page': v.landing_page, 'session_duration_seconds': int(v.session_duration.total_seconds()),
            }
            for v in page.object_list
        ],
    })


@tracker_staff_required
def api_download_log(request):
    page = _paginate(request, _download_export_rows(request), 'page')
    return JsonResponse({
        'count': page.paginator.count,
        'page': page.number,
        'num_pages': page.paginator.num_pages,
        'results': [
            {
                'download_time': d.download_time.isoformat(), 'visitor_name': d.visitor_name,
                'organization': d.organization, 'email': d.email, 'visitor_ip': d.visitor_ip,
                'country': d.country, 'region': d.region, 'city': d.city, 'browser': d.browser,
                'device': d.device, 'cv_version': d.cv_version, 'download_source': d.download_source,
            }
            for d in page.object_list
        ],
    })
