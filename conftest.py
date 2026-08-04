import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def staff_user(db):
    User = get_user_model()
    return User.objects.create_user(username='staffer', password='pw', is_staff=True)


@pytest.fixture
def regular_user(db):
    User = get_user_model()
    return User.objects.create_user(username='regular', password='pw', is_staff=False)


@pytest.fixture
def staff_client(client, staff_user):
    client.force_login(staff_user)
    return client


@pytest.fixture
def regular_client(client, regular_user):
    client.force_login(regular_user)
    return client


@pytest.fixture(autouse=True)
def clear_cache():
    """Django's default cache backend (LocMemCache) lives for the whole test
    process, not per-test — without this, analytics.kpi_cards()'s cached
    values leak from one test into the next."""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def tmp_media(settings, tmp_path):
    """FileField.save() writes to disk immediately and isn't rolled back
    with the test DB transaction — redirect MEDIA_ROOT to a throwaway
    directory so file-upload tests never touch the real project media/
    folder. Shared across apps (tracker's Resume, portfolio's CaseStudy
    cover_image/Profile cv_file)."""
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path
