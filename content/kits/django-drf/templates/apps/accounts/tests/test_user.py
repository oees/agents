from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from apps.accounts.models import User


def test_the_project_uses_its_own_user_model() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model() is User


def test_staff_manage_users_in_the_admin(admin_client: Client) -> None:
    assert admin_client.get("/admin/accounts/user/").status_code == 200
    assert admin_client.get("/admin/accounts/user/add/").status_code == 200
