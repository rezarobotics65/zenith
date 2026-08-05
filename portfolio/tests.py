from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio.models import CaseStudy, Experience, Profile
from tracker.models import CVDownloadLog, Resume


@pytest.mark.django_db
def test_anonymous_home_returns_200(client):
    response = client.get('/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_unpublished_profile_not_shown(client):
    Profile.objects.update_or_create(pk=1, defaults=dict(
        full_name='Secret Name', headline='H', tagline='T', introduction='I',
        location='L', email='a@b.com', phone='1', years_experience=1, is_published=False,
    ))
    response = client.get('/')
    assert response.status_code == 200
    assert b'Secret Name' not in response.content


@pytest.mark.django_db
def test_unpublished_experience_not_shown(client):
    Profile.objects.update_or_create(pk=1, defaults=dict(
        full_name='Reza', headline='H', tagline='T', introduction='I',
        location='L', email='a@b.com', phone='1', years_experience=1, is_published=True,
    ))
    Experience.objects.create(
        company='Secret Co', title='Secret Title', location='L',
        start_date=date(2020, 1, 1), is_published=False,
    )
    response = client.get('/')
    assert b'Secret Co' not in response.content


@pytest.mark.django_db
def test_unpublished_case_study_not_shown_and_404s(client):
    cs = CaseStudy.objects.create(
        title='Secret Case Study', slug='secret-case-study',
        situation='s', task='t', action='a', result='r', is_published=False,
    )
    home_response = client.get('/')
    assert b'Secret Case Study' not in home_response.content

    detail_response = client.get(f'/case-study/{cs.slug}/')
    assert detail_response.status_code == 404


@pytest.mark.django_db
def test_published_case_study_detail_200(client):
    cs = CaseStudy.objects.create(
        title='Published Case Study', slug='published-case-study',
        situation='s', task='t', action='a', result='r', is_published=True,
    )
    response = client.get(f'/case-study/{cs.slug}/')
    assert response.status_code == 200
    assert b'Published Case Study' in response.content


def _default_resume(tmp_media):
    return Resume.objects.create(
        file=SimpleUploadedFile('resume.pdf', b'%PDF-1.4 test content', content_type='application/pdf'),
        is_default=True,
    )


@pytest.mark.django_db
def test_download_cv_shows_gate_form_when_resume_available(client, tmp_media):
    _default_resume(tmp_media)
    response = client.get('/cv/download/?src=hero')
    assert response.status_code == 200
    assert b'form' in response.content
    assert CVDownloadLog.objects.count() == 0  # nothing logged until the form is submitted


@pytest.mark.django_db
def test_download_cv_logs_and_serves_file_on_valid_submission(client, tmp_media):
    _default_resume(tmp_media)
    response = client.post('/cv/download/', data={
        'name': 'Jane Recruiter', 'organization': 'Acme Corp', 'email': 'jane@acme.example', 'src': 'hero',
    })
    assert response.status_code == 200
    assert response['Content-Disposition'].startswith('attachment')
    assert CVDownloadLog.objects.count() == 1
    log = CVDownloadLog.objects.first()
    assert log.visitor_name == 'Jane Recruiter'
    assert log.organization == 'Acme Corp'
    assert log.email == 'jane@acme.example'
    assert log.download_source == 'hero'
    assert log.cv_version == 'resume.pdf'


@pytest.mark.django_db
def test_download_cv_rejects_incomplete_submission(client, tmp_media):
    _default_resume(tmp_media)
    response = client.post('/cv/download/', data={'name': '', 'email': 'not-an-email'})
    assert response.status_code == 200
    assert CVDownloadLog.objects.count() == 0
    assert 'Content-Disposition' not in response


@pytest.mark.django_db
def test_download_cv_shows_unavailable_message_without_a_default_resume(client):
    response = client.get('/cv/download/')
    assert response.status_code == 200
    assert b'not available' in response.content.lower()
    assert CVDownloadLog.objects.count() == 0


@pytest.mark.django_db
def test_home_hides_download_cv_button_without_default_resume(client):
    Profile.objects.update_or_create(pk=1, defaults=dict(
        full_name='Reza', headline='H', tagline='T', introduction='I', location='L',
        email='a@b.com', phone='1', years_experience=1, is_published=True,
    ))
    response = client.get('/')
    assert b'Download CV' not in response.content


@pytest.mark.django_db
def test_home_shows_download_cv_button_with_default_resume(client, tmp_media):
    Profile.objects.update_or_create(pk=1, defaults=dict(
        full_name='Reza', headline='H', tagline='T', introduction='I', location='L',
        email='a@b.com', phone='1', years_experience=1, is_published=True,
    ))
    _default_resume(tmp_media)
    response = client.get('/')
    assert b'Download CV' in response.content
