from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """The project's user, in place before the first migration.

    Django cannot swap AUTH_USER_MODEL once tables exist, so every project starts
    with its own model. Add fields here (tenant_id, for example) with a migration.
    """
