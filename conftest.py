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
