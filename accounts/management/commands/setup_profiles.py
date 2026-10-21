from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import UserAccount, UserProfile


class Command(BaseCommand):
    help = "Create the four initial profiles and optionally assign a User Admin."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-username",
            help="Assign an existing user to the User Admin profile.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["admin_username"]
        user = None
        if username:
            try:
                user = get_user_model().objects.get(username=username)
            except get_user_model().DoesNotExist as exc:
                raise CommandError(
                    f"User '{username}' does not exist. Create the user first."
                ) from exc

        descriptions = {
            "User Admin": "Manages user accounts and profiles.",
            "Interior Designer": "Manages company information and projects.",
            "Customer": "Searches and saves design projects.",
            "Platform Management": "Manages categories and reports.",
        }
        profiles = {}
        for name, description in descriptions.items():
            profiles[name], _ = UserProfile.objects.get_or_create(
                name=name,
                defaults={"description": description},
            )

        if user is not None:
            UserAccount.objects.update_or_create(
                user=user,
                defaults={"profile": profiles["User Admin"]},
            )
            self.stdout.write(
                self.style.SUCCESS(f"Assigned '{username}' to User Admin.")
            )

        self.stdout.write(self.style.SUCCESS("The four initial profiles are ready."))
