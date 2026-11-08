from django.core.management.base import BaseCommand, CommandError

from accounts.demo_data import DemoDataController, DemoDataError


class Command(BaseCommand):
    help = (
        "Generate repeatable synthetic accounts, companies, projects and activity "
        "for the assignment demonstration. Existing records are preserved."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of designers, customers, companies and categories (default: 100).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed used to create reproducible synthetic details (default: 42).",
        )
        parser.add_argument(
            "--prefix",
            default="demo314",
            help="Namespace for generated identities (default: demo314).",
        )
        parser.add_argument(
            "--password",
            default="Demo314!Pass2026",
            help="Initial password for newly created demo accounts only.",
        )

    def handle(self, *args, **options):
        try:
            result = DemoDataController.generate(
                count=options["count"],
                seed=options["seed"],
                prefix=options["prefix"],
                password=options["password"],
            )
        except DemoDataError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write("Generated dataset totals and records created in this run:")
        self.stdout.write(f'{"Record type":<24}{"Dataset total":>15}{"New records":>15}')
        labels = {
            "profiles": "Required role profiles",
            "users": "Users",
            "accounts": "User accounts",
            "companies": "Companies",
            "categories": "Categories",
            "projects": "Projects",
            "favourites": "Favourites",
            "views": "Project views",
            "reviews": "Reviews",
        }
        for key, label in labels.items():
            self.stdout.write(
                f'{label:<24}{result["dataset"][key]:>15}{result["created"][key]:>15}'
            )

        self.stdout.write("")
        self.stdout.write("Demo logins:")
        for role, username in result["logins"].items():
            self.stdout.write(f"  {role}: {username}")
        self.stdout.write(
            f'Initial password for newly created accounts: {options["password"]}'
        )
        self.stdout.write(
            "Reruns reuse generated identities and preserve existing passwords and statuses."
        )
        self.stdout.write(
            "The four required role profiles are reused; existing extra profiles are retained."
        )
