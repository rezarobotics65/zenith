from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from django.utils import timezone

from tracker import analytics, services
from tracker.middleware import classify_referral
from tracker.models import (
    ActivityLog,
    CareerObjective,
    Certification,
    Course,
    CVDownloadLog,
    KPI,
    MonthlyPlan,
    Pillar,
    Resume,
    Skill,
    SkillDomain,
    VisitorLog,
)

TRACKER_URLS = ['/tracker/', '/tracker/kpi/', '/tracker/activity/', '/tracker/cv/', '/tracker/visitor-log/']


# ---------------------------------------------------------------------------
# Access control (BUILD_BRIEF.md Section 11 — non-negotiable per CLAUDE.md)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize('url', TRACKER_URLS)
def test_anonymous_tracker_urls_redirect_to_login(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith('/accounts/login/')


@pytest.mark.django_db
def test_non_staff_user_redirected_from_dashboard(regular_client):
    response = regular_client.get('/tracker/')
    assert response.status_code == 302


@pytest.mark.django_db
@pytest.mark.parametrize('url', TRACKER_URLS)
def test_staff_user_can_access_tracker_urls(staff_client, url):
    response = staff_client.get(url)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# seed_roadmap idempotency
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_seed_roadmap_is_idempotent():
    call_command('seed_roadmap')
    counts_first = {
        'domains': SkillDomain.objects.count(),
        'skills': Skill.objects.count(),
        'certifications': Certification.objects.count(),
        'courses': Course.objects.count(),
        'pillars': Pillar.objects.count(),
        'kpis': KPI.objects.count(),
        'plans': MonthlyPlan.objects.count(),
    }

    call_command('seed_roadmap')
    counts_second = {
        'domains': SkillDomain.objects.count(),
        'skills': Skill.objects.count(),
        'certifications': Certification.objects.count(),
        'courses': Course.objects.count(),
        'pillars': Pillar.objects.count(),
        'kpis': KPI.objects.count(),
        'plans': MonthlyPlan.objects.count(),
    }

    assert counts_first == counts_second
    assert counts_first['domains'] == 6
    assert counts_first['pillars'] == 4


# ---------------------------------------------------------------------------
# services.py / model property coverage
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize('current,target,expected', [
    (4, 4, 'NONE'),
    (3, 4, 'MODERATE'),
    (2, 4, 'LARGE'),
    (1, 4, 'CRITICAL'),
])
def test_skill_gap_bands(current, target, expected):
    domain = SkillDomain.objects.create(code='A', name='AI', priority='HIGHEST', order=1)
    skill = Skill.objects.create(
        domain=domain, name='Test skill', current_level=current, target_level=target,
        baseline_level=current, order=1,
    )
    assert skill.gap == expected


@pytest.mark.django_db
def test_course_progress_pct_caps_at_100_and_complete_short_circuits():
    course = Course.objects.create(
        name='Test course', provider='Test', tier='TECHNICAL', status='NOT_STARTED',
        planned_hours=10, order=1,
    )
    ActivityLog.objects.create(date=date.today(), activity_type='STUDY', title='Study', hours=Decimal('15'), course=course)
    assert course.progress_pct == 100

    course.status = 'COMPLETE'
    course.save()
    ActivityLog.objects.filter(course=course).delete()
    assert course.progress_pct == 100


@pytest.mark.django_db
def test_monthly_plan_actual_hours_sums_only_its_month():
    plan = MonthlyPlan.objects.create(year=2026, month=8, theme='Test', target_hours=10)
    ActivityLog.objects.create(date=date(2026, 8, 5), activity_type='STUDY', title='In month A', hours=Decimal('3'))
    ActivityLog.objects.create(date=date(2026, 8, 20), activity_type='STUDY', title='In month B', hours=Decimal('4'))
    ActivityLog.objects.create(date=date(2026, 9, 1), activity_type='STUDY', title='Next month', hours=Decimal('5'))

    assert plan.actual_hours == Decimal('7')


@pytest.mark.django_db
def test_dashboard_overall_progress_known_fixture():
    pillar_a = Pillar.objects.create(code='A', name='Capability', weight=30, order=1)
    pillar_b = Pillar.objects.create(code='B', name='Applied evidence', weight=35, order=2)
    pillar_c = Pillar.objects.create(code='C', name='Visibility', weight=20, order=3)
    pillar_d = Pillar.objects.create(code='D', name='Career outcome', weight=15, order=4)

    Certification.objects.create(name='Earned cert', provider='X', status='EARNED', planned_hours=0, order=1)
    cert2 = Certification.objects.create(name='In progress cert', provider='X', status='STUDYING', planned_hours=20, order=2)
    ActivityLog.objects.create(date=date.today(), activity_type='STUDY', title='Study', hours=Decimal('12'), certification=cert2)
    # certification_progress = avg(100, 60) = 80

    KPI.objects.create(pillar=pillar_b, code='B1', title='B1', target='t', period='YEARLY', period_year=2026,
                        target_value=10, current_value=8, order=1)
    KPI.objects.create(pillar=pillar_b, code='B2', title='B2', target='t', period='YEARLY', period_year=2026,
                        target_value=5, current_value=4, order=2)
    # pillar B progress = avg(80, 80) = 80

    KPI.objects.create(pillar=pillar_c, code='C1', title='C1', target='t', period='YEARLY', period_year=2026,
                        target_value=10, current_value=5, order=1)
    # pillar C progress = 50

    KPI.objects.create(pillar=pillar_d, code='D1', title='D1', target='t', period='YEARLY', period_year=2026,
                        target_value=10, current_value=4, order=1)
    # pillar D progress = 40

    # overall = (30*80 + 35*80 + 20*50 + 15*40) / 100 = 68.0
    assert services.overall_progress() == 68.0


# ---------------------------------------------------------------------------
# In-page CRUD (add/edit/delete) — access control and lifecycle
# ---------------------------------------------------------------------------

CRUD_URLS = [
    '/tracker/add/activity/',
    '/tracker/add/certification/',
    '/tracker/add/course/',
    '/tracker/add/kpi/',
]


@pytest.mark.django_db
@pytest.mark.parametrize('url', CRUD_URLS)
def test_anonymous_crud_urls_redirect_to_login(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith('/accounts/login/')


@pytest.mark.django_db
@pytest.mark.parametrize('url', CRUD_URLS)
def test_non_staff_user_blocked_from_crud_urls(regular_client, url):
    response = regular_client.get(url)
    assert response.status_code == 302


@pytest.mark.django_db
@pytest.mark.parametrize('url', CRUD_URLS)
def test_staff_user_can_open_add_forms(staff_client, url):
    response = staff_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_staff_user_can_create_edit_and_delete_activity_log(staff_client):
    create_response = staff_client.post('/tracker/add/activity/', data={
        'date': '2026-08-10',
        'activity_type': 'STUDY',
        'title': 'Test study session',
        'description': '',
        'hours': '2.5',
        'course': '', 'certification': '', 'kpi': '', 'skill_domain': '',
        'next': '/tracker/activity/',
    })
    assert create_response.status_code == 302
    log = ActivityLog.objects.get(title='Test study session')
    assert log.hours == Decimal('2.5')

    edit_response = staff_client.post(f'/tracker/edit/activity/{log.pk}/', data={
        'date': '2026-08-10',
        'activity_type': 'STUDY',
        'title': 'Test study session (edited)',
        'description': '',
        'hours': '3.0',
        'course': '', 'certification': '', 'kpi': '', 'skill_domain': '',
        'next': '/tracker/activity/',
    })
    assert edit_response.status_code == 302
    log.refresh_from_db()
    assert log.title == 'Test study session (edited)'
    assert log.hours == Decimal('3.0')

    delete_response = staff_client.post(f'/tracker/delete/activity/{log.pk}/', data={'next': '/tracker/activity/'})
    assert delete_response.status_code == 302
    assert not ActivityLog.objects.filter(pk=log.pk).exists()


@pytest.mark.django_db
def test_career_objective_add_and_delete_are_blocked(staff_client):
    CareerObjective.load()
    add_response = staff_client.get('/tracker/add/objective/')
    assert add_response.status_code == 302

    delete_response = staff_client.post('/tracker/delete/objective/1/', data={})
    assert delete_response.status_code == 302
    assert CareerObjective.objects.filter(pk=1).exists()


@pytest.mark.django_db
def test_pillar_delete_is_blocked(staff_client):
    pillar = Pillar.objects.create(code='A', name='Capability', weight=30, order=1)
    response = staff_client.post(f'/tracker/delete/pillar/{pillar.pk}/', data={})
    assert response.status_code == 302
    assert Pillar.objects.filter(pk=pillar.pk).exists()


@pytest.mark.django_db
def test_toggle_commitment(staff_client):
    pillar = Pillar.objects.create(code='A', name='Capability', weight=30, order=1)
    plan = MonthlyPlan.objects.create(year=2026, month=8, theme='Test', target_hours=10)
    from tracker.models import MonthlyCommitment
    commitment = MonthlyCommitment.objects.create(
        plan=plan, pillar=pillar, commitment='Do the thing', done_when='Done', order=1,
    )
    assert commitment.is_complete is False

    response = staff_client.post(f'/tracker/commitment/{commitment.pk}/toggle/', data={'next': '/tracker/kpi/'})
    assert response.status_code == 302
    commitment.refresh_from_db()
    assert commitment.is_complete is True

    staff_client.post(f'/tracker/commitment/{commitment.pk}/toggle/', data={'next': '/tracker/kpi/'})
    commitment.refresh_from_db()
    assert commitment.is_complete is False


@pytest.mark.django_db
def test_quick_set_course_hours_collapses_same_day_edits(staff_client):
    """Re-typing a new total for the same course on the same day should update
    that day's adjustment ActivityLog entry in place, not stack a new one."""
    course = Course.objects.create(name='Test Course', provider='X', tier=Course.Tier.TECHNICAL, order=1)

    staff_client.post(f'/tracker/course/{course.pk}/set-hours/', data={'hours': '0.25', 'next': '/tracker/kpi/'})
    assert course.hours_logged == Decimal('0.25')
    assert ActivityLog.objects.filter(course=course).count() == 1

    staff_client.post(f'/tracker/course/{course.pk}/set-hours/', data={'hours': '0.5', 'next': '/tracker/kpi/'})
    assert course.hours_logged == Decimal('0.5')
    assert ActivityLog.objects.filter(course=course).count() == 1

    staff_client.post(f'/tracker/course/{course.pk}/set-hours/', data={'hours': '0.5', 'next': '/tracker/kpi/'})
    assert course.hours_logged == Decimal('0.5')
    assert ActivityLog.objects.filter(course=course).count() == 1

    staff_client.post(f'/tracker/course/{course.pk}/set-hours/', data={'hours': '0', 'next': '/tracker/kpi/'})
    assert course.hours_logged == Decimal('0')
    assert ActivityLog.objects.filter(course=course).count() == 0


@pytest.mark.django_db
def test_quick_set_course_hours_does_not_touch_other_entries(staff_client):
    """A manual ActivityLog entry (different title, e.g. logged by hand) must
    survive a same-day quick-set adjustment for the same course untouched."""
    course = Course.objects.create(name='Test Course', provider='X', tier=Course.Tier.TECHNICAL, order=1)
    manual = ActivityLog.objects.create(
        date=date.today(), activity_type=ActivityLog.ActivityType.STUDY,
        title='Manual session', hours=Decimal('1.00'), course=course,
    )

    staff_client.post(f'/tracker/course/{course.pk}/set-hours/', data={'hours': '2', 'next': '/tracker/kpi/'})
    assert course.hours_logged == Decimal('2.00')
    manual.refresh_from_db()
    assert manual.hours == Decimal('1.00')

    staff_client.post(f'/tracker/course/{course.pk}/set-hours/', data={'hours': '3', 'next': '/tracker/kpi/'})
    assert course.hours_logged == Decimal('3.00')
    manual.refresh_from_db()
    assert manual.hours == Decimal('1.00')
    assert ActivityLog.objects.filter(course=course).count() == 2


# ---------------------------------------------------------------------------
# CV / Resume
# ---------------------------------------------------------------------------

def _dummy_pdf(name='resume.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 test content', content_type='application/pdf')




@pytest.mark.django_db
def test_resume_only_one_default_at_a_time(tmp_media):
    r1 = Resume.objects.create(file=_dummy_pdf('a.pdf'), is_default=True)
    r2 = Resume.objects.create(file=_dummy_pdf('b.pdf'), is_default=True)

    r1.refresh_from_db()
    r2.refresh_from_db()
    assert r1.is_default is False
    assert r2.is_default is True


@pytest.mark.django_db
def test_resume_upload_via_add_object_view(staff_client, tmp_media):
    response = staff_client.post(
        '/tracker/add/resume/',
        data={'file': _dummy_pdf('uploaded.pdf'), 'next': '/tracker/cv/'},
    )
    assert response.status_code == 302
    assert Resume.objects.filter(file__icontains='uploaded').exists()


@pytest.mark.django_db
def test_set_default_resume_view(staff_client, tmp_media):
    r1 = Resume.objects.create(file=_dummy_pdf('a.pdf'), is_default=True)
    r2 = Resume.objects.create(file=_dummy_pdf('b.pdf'), is_default=False)

    response = staff_client.post(f'/tracker/cv/{r2.pk}/set-default/', data={'next': '/tracker/cv/'})
    assert response.status_code == 302

    r1.refresh_from_db()
    r2.refresh_from_db()
    assert r1.is_default is False
    assert r2.is_default is True


@pytest.mark.django_db
def test_cv_list_shows_uploaded_resumes(staff_client, tmp_media):
    Resume.objects.create(file=_dummy_pdf('my-resume.pdf'), is_default=True)
    response = staff_client.get('/tracker/cv/')
    assert response.status_code == 200
    assert b'my-resume' in response.content
    assert b'Default' in response.content


# ---------------------------------------------------------------------------
# Visitor Log — traffic + CV download analytics
# ---------------------------------------------------------------------------

def _make_visit(**overrides):
    now = timezone.now()
    defaults = dict(visit_time=now, last_seen=now, ip_address='8.8.8.8', country='United States')
    defaults.update(overrides)
    return VisitorLog.objects.create(**defaults)


@pytest.mark.django_db
def test_middleware_tracks_portfolio_visit(client):
    assert VisitorLog.objects.count() == 0
    client.get('/')
    assert VisitorLog.objects.count() == 1
    visit = VisitorLog.objects.first()
    assert visit.landing_page == '/'
    # Django's test client uses 127.0.0.1, a loopback address geoip.lookup()
    # deliberately skips — country/region/city should stay blank, not error.
    assert visit.country == ''


@pytest.mark.django_db
def test_middleware_does_not_track_private_paths(staff_client):
    staff_client.get('/tracker/')
    staff_client.get('/admin/')
    staff_client.get('/accounts/login/')
    assert VisitorLog.objects.count() == 0


@pytest.mark.django_db
def test_middleware_same_session_updates_existing_row(client):
    client.get('/')
    client.get('/')
    client.get('/')
    assert VisitorLog.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize('referrer,expected', [
    ('', VisitorLog.ReferralSource.DIRECT),
    ('https://www.google.com/search?q=reza', VisitorLog.ReferralSource.GOOGLE),
    ('https://www.linkedin.com/feed/', VisitorLog.ReferralSource.LINKEDIN),
    ('https://github.com/rezarobotics65', VisitorLog.ReferralSource.GITHUB),
    ('https://news.ycombinator.com/', VisitorLog.ReferralSource.OTHER),
])
def test_classify_referral(rf, referrer, expected):
    request = rf.get('/')  # RequestFactory defaults HTTP_HOST to 'testserver'
    assert classify_referral(referrer, request) == expected


@pytest.mark.django_db
def test_kpi_cards_counts_are_scoped_to_the_right_period():
    today = timezone.localdate()
    _make_visit(visit_time=timezone.now(), last_seen=timezone.now())
    old_visit_time = timezone.make_aware(timezone.datetime(today.year - 1, 1, 1))
    _make_visit(visit_time=old_visit_time, last_seen=old_visit_time, ip_address='1.1.1.1')

    kpis = analytics.kpi_cards()
    assert kpis['total_visitors'] == 2
    assert kpis['today_visitors'] == 1
    assert kpis['year_visitors'] == 1


@pytest.mark.django_db
@pytest.mark.parametrize('url', [
    '/tracker/api/visitor-log', '/tracker/api/visitor-summary',
    '/tracker/api/download-log', '/tracker/api/download-summary',
])
def test_visitor_api_endpoints_require_staff(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith('/accounts/login/')


@pytest.mark.django_db
def test_visitor_api_endpoints_work_for_staff(staff_client):
    _make_visit()
    response = staff_client.get('/tracker/api/visitor-summary')
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    assert response.json()['kpis']['total_visitors'] == 1


@pytest.mark.django_db
def test_visitor_log_csv_export_requires_staff(client):
    # NB: don't also request staff_client here — that fixture force_logins
    # the *same* underlying `client` object, defeating an anonymous check.
    response = client.get('/tracker/visitor-log/export/csv/')
    assert response.status_code == 302
    assert response.url.startswith('/accounts/login/')


@pytest.mark.django_db
def test_visitor_log_csv_export_returns_csv_for_staff(staff_client):
    _make_visit()
    response = staff_client.get('/tracker/visitor-log/export/csv/')
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv'
    assert b'8.8.8.8' in response.content


@pytest.mark.django_db
def test_visitor_log_excel_export_returns_xlsx(staff_client):
    _make_visit()
    response = staff_client.get('/tracker/visitor-log/export/excel/')
    assert response.status_code == 200
    assert 'spreadsheetml' in response['Content-Type']


@pytest.mark.django_db
def test_visitor_log_page_shows_kpis_and_respects_search(staff_client):
    _make_visit(country='Malaysia', city='Kuala Lumpur')
    _make_visit(ip_address='1.1.1.1', country='Australia', city='Sydney')

    response = staff_client.get('/tracker/visitor-log/')
    assert response.status_code == 200
    assert b'Kuala Lumpur' in response.content
    assert b'Sydney' in response.content

    filtered = staff_client.get('/tracker/visitor-log/?q=Sydney')
    assert b'Sydney' in filtered.content
    assert b'Kuala Lumpur' not in filtered.content


@pytest.mark.django_db
def test_visitor_log_row_shows_cv_download_yes(staff_client):
    _make_visit(ip_address='9.9.9.9')
    CVDownloadLog.objects.create(visitor_ip='9.9.9.9', cv_version='resume.pdf')
    response = staff_client.get('/tracker/visitor-log/')
    assert b'Yes' in response.content
