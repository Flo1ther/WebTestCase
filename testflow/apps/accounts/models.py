from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db.models.functions import Lower
import uuid

class UserManager(DjangoUserManager):
    def create_user(self, username=None, email="", password=None, **extra_fields):
        email=email.strip().lower()
        return super().create_user(username or ("u_"+uuid.uuid4().hex), email, password, **extra_fields)
    def create_superuser(self, username=None, email="", password=None, **extra_fields):
        extra_fields.update(role="ADMIN", email_verified=True)
        return super().create_superuser(username or ("u_"+uuid.uuid4().hex), email.strip().lower(), password, **extra_fields)
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Адміністратор"
        MANAGER = "MANAGER", "Менеджер тестування"
        TESTER = "TESTER", "Тестувальник"

    objects = UserManager()
    email_verified = models.BooleanField(default=True)
    manual_blocked = models.BooleanField(default=False)
    auth_version = models.PositiveIntegerField(default=0)
    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='wtc_email_case_insensitive')]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.TESTER, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.get_full_name() or self.username
