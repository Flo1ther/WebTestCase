from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Re-enable an administrator account for local development recovery."

    def add_arguments(self, parser):
        parser.add_argument("email", help="Email address of the administrator to restore")

    def handle(self, *args, **options):
        if not settings.DEBUG: raise CommandError("Ця навчальна команда доступна лише в DEBUG-середовищі.")
        try:
            user = User.objects.get(email__iexact=options["email"])
        except User.DoesNotExist as exc:
            raise CommandError("No user exists with that email address.") from exc
        user.is_active = True
        user.role = User.Role.ADMIN
        user.save(update_fields=["is_active", "role"])
        self.stdout.write(self.style.SUCCESS(f"Administrator restored: {user.email}"))
