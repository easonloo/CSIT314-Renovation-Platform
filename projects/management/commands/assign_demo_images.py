from django.core.management.base import BaseCommand

from projects.demo_images import DemoImageController


class Command(BaseCommand):
    help = (
        "Assign category-matched virtual images to demo projects and projects "
        "with missing images. Uploaded project photos are preserved."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many project images would change without saving changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        result = DemoImageController.assign_images(dry_run=dry_run)

        if dry_run:
            self.stdout.write("Dry run: no project records were changed.")
            self.stdout.write(f'Images that would be updated: {result["updated"]}')
        else:
            self.stdout.write(self.style.SUCCESS("Demo project images assigned."))
            self.stdout.write(f'Images updated: {result["updated"]}')
        self.stdout.write(f'Projects skipped: {result["skipped"]}')
        self.stdout.write(f'Matching image files missing: {result["missing"]}')
        self.stdout.write("Uploaded project photos are preserved.")
