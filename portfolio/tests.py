from datetime import date

import pytest

from portfolio.models import CaseStudy, Experience, Profile


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
