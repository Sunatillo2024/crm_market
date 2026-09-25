from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Superuser akkaunt mavjud bo‘lmasa yaratadi (docker uchun idempotent)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            required=True,
            help="Superuser logini.",
        )
        parser.add_argument(
            "--password",
            required=True,
            help="Superuser paroli.",
        )
        parser.add_argument(
            "--email",
            default="",
            help="Superuser email manzili.",
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        password = options["password"]
        email = (options["email"] or "").strip()

        user = User.objects.filter(
            username__iexact=username,
        ).first()

        if user is not None:
            self.stdout.write(
                f"Superuser '{username}' allaqachon mavjud — o‘zgartirilmadi."
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser '{username}' yaratildi."
            )
        )
