from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.demo_data import DemoDataController
from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from favourites.models import Favourite
from reports.models import ProjectView
from reviews.models import ProjectReview

from .demo_images import DemoImageController
from .models import InteriorDesignProject


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DemoImageTests(TestCase):
    room_images = {
        "Living Room": "living_room.png",
        "Kitchen": "kitchen.png",
        "Master Bedroom": "master_bedroom.png",
        "Bathroom": "bathroom.png",
        "Dining Room": "dining_room.png",
        "Home Office": "home_office.png",
        "Balcony": "balcony.png",
        "Entryway": "entryway.png",
        "Guest Bedroom": "guest_bedroom.png",
        "Children's Room": "children_room.png",
        "Laundry Room": "laundry_room.png",
        "Walk-in Wardrobe": "walk_in_wardrobe.png",
        "Study": "study.png",
        "Entertainment Room": "entertainment_room.png",
        "Nursery": "nursery.png",
        "Reading Nook": "reading_nook.png",
        "Storage Room": "storage_room.png",
        "Patio": "patio.png",
        "Pantry": "pantry.png",
        "Home Gym": "home_gym.png",
    }

    def setUp(self):
        self.media_root = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(override_settings(MEDIA_ROOT=self.media_root))
        catalog = self.media_root / "demo_idp_catalog"
        catalog.mkdir()
        for filename in self.room_images.values():
            Image.new("RGB", (2, 2), color="blue").save(catalog / filename)
        self.designer = get_user_model().objects.create_user(username="image_test_designer")
        self.company = Company.objects.create(user=self.designer, name="Image Test Studio")

    def make_project(self, *, category="Kitchen", image="", title="Image Test Project"):
        category, _ = Category.objects.get_or_create(name=category)
        return InteriorDesignProject.objects.create(
            company=self.company, category=category, title=title, image=image,
            description="Preserve the original description", location="Tampines",
            style="Scandinavian", status="past", view_count=12, shortlist_count=3,
        )

    def snapshot(self, *, exclude_images=False):
        models = (
            get_user_model(), UserProfile, UserAccount, Company, Category,
            InteriorDesignProject, Favourite, ProjectView, ProjectReview,
        )
        result = {}
        for model in models:
            rows = list(model.objects.order_by("pk").values())
            if model is InteriorDesignProject and exclude_images:
                for row in rows:
                    row.pop("image")
            result[model._meta.label] = rows
        return result

    def test_all_twenty_room_categories_resolve_their_own_images(self):
        for index, (room, filename) in enumerate(self.room_images.items(), start=1):
            with self.subTest(room=room):
                expected = f"demo_idp_catalog/{filename}"
                self.assertEqual(DemoImageController.image_for(room), expected)
                self.assertEqual(
                    DemoImageController.image_for(f"demo314: {index:03d} HDB {room}"),
                    expected,
                )

    def test_category_matching_normalizes_case_punctuation_and_room_variants(self):
        for category, filename in (
            ("  condominium KITCHEN  ", "kitchen.png"),
            ("HDB Children’s Room", "children_room.png"),
            ("Children’s Bedroom", "children_room.png"),
            ("HDB Walk in Wardrobe", "walk_in_wardrobe.png"),
            ("Guest Bedroom", "guest_bedroom.png"),
            ("Master Bedroom", "master_bedroom.png"),
            ("Bedroom", "master_bedroom.png"),
        ):
            with self.subTest(category=category):
                self.assertEqual(
                    DemoImageController.image_for(category), f"demo_idp_catalog/{filename}",
                )

    def test_category_takes_precedence_over_an_unrelated_project_title(self):
        self.assertEqual(
            DemoImageController.image_for("Kitchen", "Modern Living Room Renovation"),
            "demo_idp_catalog/kitchen.png",
        )

    def test_generic_categories_use_the_project_title_for_a_specific_room(self):
        for category, title, filename in (
            ("Residential", "Chef's Kitchen Concept", "kitchen.png"),
            ("HDB Renovation", "A Calm Guest Bedroom", "guest_bedroom.png"),
            ("", "Sunny Balcony Refresh", "balcony.png"),
        ):
            with self.subTest(category=category, title=title):
                self.assertEqual(
                    DemoImageController.image_for(category, title), f"demo_idp_catalog/{filename}",
                )

    def test_general_or_unknown_projects_use_the_living_room_image(self):
        for category, title in (("Residential", "Modern Family Villa"), ("Unknown", "Project"), ("", "")):
            with self.subTest(category=category, title=title):
                self.assertEqual(
                    DemoImageController.image_for(category, title), "demo_idp_catalog/living_room.png",
                )

    def test_missing_matching_asset_returns_blank_instead_of_a_broken_image_path(self):
        with TemporaryDirectory() as empty_media, override_settings(MEDIA_ROOT=empty_media):
            self.assertEqual(DemoImageController.image_for("Kitchen"), "")

    def test_assignment_replaces_blank_legacy_and_mismatched_catalog_images(self):
        projects = [
            self.make_project(image=""),
            self.make_project(image=None),
            self.make_project(image="sample_idp/sample_1.png"),
            self.make_project(image="sample_idp/sample_5.png"),
            self.make_project(image="demo_idp_catalog/bathroom.png"),
        ]

        result = DemoImageController.assign_images()

        self.assertEqual(result["updated"], 5)
        self.assertEqual(result["missing"], 0)
        for project in projects:
            project.refresh_from_db()
            self.assertEqual(project.image.name, "demo_idp_catalog/kitchen.png")

    def test_assignment_preserves_custom_uploads_and_unrecognized_sample_files(self):
        projects = [
            self.make_project(image="idp_images/bedroom.jpg"),
            self.make_project(image="idp_images/sample_5.png"),
            self.make_project(image="sample_idp/images.jpg"),
        ]
        before = self.snapshot()

        result = DemoImageController.assign_images()

        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["skipped"], len(projects))
        self.assertEqual(self.snapshot(), before)

    def test_assignment_preserves_business_fields_metrics_and_related_records(self):
        project = self.make_project(image="sample_idp/sample_2.png")
        customer = get_user_model().objects.create_user(username="image_test_customer")
        Favourite.objects.create(user=customer, project=project)
        ProjectView.objects.create(viewer=customer, project=project)
        ProjectReview.objects.create(customer=customer, project=project, rating=4)
        before = self.snapshot(exclude_images=True)

        DemoImageController.assign_images()

        self.assertEqual(self.snapshot(exclude_images=True), before)
        project.refresh_from_db()
        self.assertEqual(project.image.name, "demo_idp_catalog/kitchen.png")

    def test_repeated_assignment_does_not_rewrite_already_matching_images(self):
        self.make_project(image="sample_idp/sample_3.png")
        DemoImageController.assign_images()
        before = self.snapshot()

        result = DemoImageController.assign_images()

        self.assertEqual(result["updated"], 0)
        self.assertEqual(self.snapshot(), before)

    def test_dry_run_reports_changes_without_modifying_any_records(self):
        self.make_project(image="")
        self.make_project(image="sample_idp/sample_4.png")
        before = self.snapshot()

        result = DemoImageController.assign_images(dry_run=True)

        self.assertEqual(result["updated"], 2)
        self.assertEqual(self.snapshot(), before)

    def test_assignment_reports_missing_assets_and_preserves_the_existing_image(self):
        project = self.make_project(image="sample_idp/sample_3.png")
        before = self.snapshot()
        with TemporaryDirectory() as empty_media, override_settings(MEDIA_ROOT=empty_media):
            result = DemoImageController.assign_images()

        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["missing"], 1)
        self.assertEqual(self.snapshot(), before)
        project.refresh_from_db()
        self.assertEqual(project.image.name, "sample_idp/sample_3.png")

    def test_command_applies_images_and_supports_preview_without_writes(self):
        project = self.make_project(image="sample_idp/sample_1.png")
        before = self.snapshot()
        preview = StringIO()

        call_command("assign_demo_images", dry_run=True, stdout=preview)

        self.assertEqual(self.snapshot(), before)
        self.assertTrue(preview.getvalue().strip())
        output = StringIO()
        call_command("assign_demo_images", stdout=output)
        project.refresh_from_db()
        self.assertEqual(project.image.name, "demo_idp_catalog/kitchen.png")
        self.assertTrue(output.getvalue().strip())

    def test_new_demo_projects_receive_images_matching_their_categories(self):
        DemoDataController.generate(count=3)

        projects = InteriorDesignProject.objects.filter(title__startswith="demo314:").select_related("category")
        self.assertEqual(projects.count(), 6)
        for project in projects:
            with self.subTest(project=project.title, category=project.category.name):
                expected = DemoImageController.image_for(project.category.name, project.title)
                self.assertTrue(expected)
                self.assertEqual(project.image.name, expected)

    def test_repeating_demo_generation_preserves_a_subsequently_uploaded_photo(self):
        DemoDataController.generate(count=2)
        project = InteriorDesignProject.objects.first()
        project.image = "idp_images/my_uploaded_photo.jpg"
        project.save(update_fields=["image"])

        DemoDataController.generate(count=2)

        project.refresh_from_db()
        self.assertEqual(project.image.name, "idp_images/my_uploaded_photo.jpg")

    def test_virtual_images_are_labelled_on_customer_and_designer_pages(self):
        designer_profile = UserProfile.objects.create(name="Interior Designer")
        UserAccount.objects.create(user=self.designer, profile=designer_profile)
        customer_profile = UserProfile.objects.create(name="Customer")
        customer = get_user_model().objects.create_user(username="virtual_image_customer")
        UserAccount.objects.create(user=customer, profile=customer_profile)
        project = self.make_project(image="demo_idp_catalog/kitchen.png")
        project.status = "current"
        project.save(update_fields=["status"])
        Favourite.objects.create(user=customer, project=project)

        for image, labelled in [
            ("demo_idp_catalog/kitchen.png", True),
            ("idp_images/uploaded_kitchen.jpg", False),
        ]:
            project.image = image
            project.save(update_fields=["image"])
            self.client.force_login(customer)
            for url in [
                reverse("customer_idp_search"),
                reverse("idp_detail", args=[project.pk]),
                reverse("favourite_list"),
                reverse("dashboard"),
            ]:
                with self.subTest(image=image, url=url):
                    response = self.client.get(url)
                    if labelled:
                        self.assertContains(response, "Virtual demo render")
                    else:
                        self.assertNotContains(response, "Virtual demo render")
            self.client.force_login(self.designer)
            response = self.client.get(reverse("idp_list"))
            if labelled:
                self.assertContains(response, "Virtual demo render")
            else:
                self.assertNotContains(response, "Virtual demo render")
