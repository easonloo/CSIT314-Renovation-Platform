from datetime import datetime, timedelta, timezone as datetime_timezone
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from companies.models import Company
from favourites.models import Favourite
from projects.models import InteriorDesignProject
from reports.controllers import ReportController
from reports.models import ProjectView
from reviews.models import ProjectReview

from .demo_data import DemoDataController, DemoDataError
from .models import UserAccount, UserProfile


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DemoDataTests(TestCase):
    models_by_name = {
        "users": get_user_model(),
        "accounts": UserAccount,
        "profiles": UserProfile,
        "companies": Company,
        "categories": Category,
        "projects": InteriorDesignProject,
        "favourites": Favourite,
        "views": ProjectView,
        "reviews": ProjectReview,
    }

    def setUp(self):
        media_root = self.enterContext(TemporaryDirectory())
        self.enterContext(override_settings(MEDIA_ROOT=media_root))

    def snapshot(self):
        return {
            name: list(model.objects.order_by("pk").values())
            for name, model in self.models_by_name.items()
        }

    def assert_interest_counts_match_records(self):
        for project in InteriorDesignProject.objects.all():
            with self.subTest(project=project.pk):
                self.assertEqual(project.view_count, project.view_events.count())
                self.assertEqual(project.shortlist_count, project.favourited_by.count())

    def test_default_dataset_provides_large_volumes_and_valid_relationships(self):
        result = DemoDataController.generate()

        expected = {
            "users": 202,
            "accounts": 202,
            "profiles": 4,
            "companies": 100,
            "categories": 100,
            "projects": 200,
            "favourites": 300,
            "views": 1000,
            "reviews": 200,
        }
        self.assertEqual(result["created"], expected)
        self.assertEqual(result["dataset"], expected)
        for name, count in expected.items():
            with self.subTest(entity=name):
                self.assertEqual(self.models_by_name[name].objects.count(), count)
        self.assertEqual(InteriorDesignProject.objects.filter(status="current").count(), 100)
        self.assertEqual(InteriorDesignProject.objects.filter(status="past").count(), 100)
        self.assertSetEqual(
            set(UserProfile.objects.values_list("name", flat=True)),
            {"User Admin", "Interior Designer", "Customer", "Platform Management"},
        )
        self.assertFalse(Company.objects.exclude(user__account__profile__name="Interior Designer").exists())
        self.assertFalse(Favourite.objects.exclude(user__account__profile__name="Customer").exists())
        self.assertFalse(ProjectView.objects.exclude(viewer__account__profile__name="Customer").exists())
        self.assertFalse(ProjectReview.objects.exclude(customer__account__profile__name="Customer").exists())
        self.assertFalse(ProjectReview.objects.exclude(rating__range=(1, 5)).exists())
        for model in [Company, Category, InteriorDesignProject, ProjectReview]:
            for record in model.objects.all():
                record.full_clean()
        self.assert_interest_counts_match_records()

    def test_smallest_dataset_respects_unique_pairs_and_repeatable_view_events(self):
        result = DemoDataController.generate(count=1)

        self.assertEqual(result["dataset"]["users"], 4)
        self.assertEqual(Favourite.objects.count(), 2)
        self.assertEqual(ProjectReview.objects.count(), 2)
        self.assertEqual(ProjectView.objects.count(), 10)
        self.assertEqual(InteriorDesignProject.objects.filter(status="current").count(), 1)
        self.assertEqual(InteriorDesignProject.objects.filter(status="past").count(), 1)
        before = self.snapshot()
        result = DemoDataController.generate(count=1)
        self.assertTrue(all(value == 0 for value in result["created"].values()))
        self.assertEqual(self.snapshot(), before)

    def test_repeating_generation_does_not_duplicate_or_rewrite_records(self):
        DemoDataController.generate(count=4)
        before = self.snapshot()

        result = DemoDataController.generate(count=4)

        self.assertTrue(all(value == 0 for value in result["created"].values()))
        self.assertEqual(self.snapshot(), before)

    def test_repeating_preserves_edited_content_passwords_and_suspensions(self):
        DemoDataController.generate(count=3)
        customer = get_user_model().objects.get(username="demo314_customer_001")
        customer.first_name = "Edited name"
        customer.is_active = False
        customer.set_password("MyChangedPassword!92")
        customer.save()
        profile = UserProfile.objects.get(name="Interior Designer")
        profile.is_active = False
        profile.description = "Existing profile explanation"
        profile.save()
        company = Company.objects.first()
        company.name = "Edited Studio Name"
        company.description = "Edited company information"
        company.save()
        project = InteriorDesignProject.objects.first()
        project.description = "Edited project description"
        project.status = "past" if project.status == "current" else "current"
        project.save()
        category = Category.objects.first()
        category.description = "Edited category description"
        category.save()
        review = ProjectReview.objects.first()
        review.comment = "Edited review comment"
        review.rating = 5
        review.save()
        before = self.snapshot()

        DemoDataController.generate(count=3, password="AReplacementPassword!95")

        self.assertEqual(self.snapshot(), before)
        customer.refresh_from_db()
        self.assertTrue(customer.check_password("MyChangedPassword!92"))

    def test_unrelated_data_and_existing_profiles_are_unchanged(self):
        User = get_user_model()
        designer_profile = UserProfile.objects.create(
            name="Interior Designer", description="Keep this description", is_active=False,
        )
        UserProfile.objects.create(name="Existing Custom Role")
        designer = User.objects.create_user(username="existing_designer", password="ExistingPass!41")
        UserAccount.objects.create(user=designer, profile=designer_profile)
        company = Company.objects.create(user=designer, name="Existing Studio")
        category = Category.objects.create(name="Existing Category")
        project = InteriorDesignProject.objects.create(
            company=company, category=category, title="Existing Project", view_count=12, shortlist_count=9,
        )
        original_user = User.objects.values().get(pk=designer.pk)
        original_profile = UserProfile.objects.values().get(pk=designer_profile.pk)
        original_project = InteriorDesignProject.objects.values().get(pk=project.pk)
        original_company = Company.objects.values().get(pk=company.pk)

        result = DemoDataController.generate(count=2)

        self.assertEqual(User.objects.values().get(pk=designer.pk), original_user)
        self.assertEqual(UserProfile.objects.values().get(pk=designer_profile.pk), original_profile)
        self.assertEqual(InteriorDesignProject.objects.values().get(pk=project.pk), original_project)
        self.assertEqual(Company.objects.values().get(pk=company.pk), original_company)
        self.assertTrue(UserProfile.objects.filter(name="Existing Custom Role").exists())
        self.assertEqual(result["created"]["profiles"], 3)
        self.assertEqual(result["dataset"]["users"], 6)

    def test_manual_activity_is_preserved_and_included_in_generated_project_counts(self):
        DemoDataController.generate(count=3)
        project = InteriorDesignProject.objects.first()
        customer_profile = UserProfile.objects.get(name="Customer")
        visitor = get_user_model().objects.create_user(username="manual_visitor")
        UserAccount.objects.create(user=visitor, profile=customer_profile)
        favourite = Favourite.objects.create(user=visitor, project=project)
        event = ProjectView.objects.create(viewer=visitor, project=project)
        original_favourite = Favourite.objects.values().get(pk=favourite.pk)
        original_event = ProjectView.objects.values().get(pk=event.pk)

        DemoDataController.generate(count=3)

        self.assertEqual(Favourite.objects.values().get(pk=favourite.pk), original_favourite)
        self.assertEqual(ProjectView.objects.values().get(pk=event.pk), original_event)
        self.assertEqual(Favourite.objects.count(), 10)
        self.assertEqual(ProjectView.objects.count(), 31)
        self.assert_interest_counts_match_records()

    def test_conflicting_existing_username_rolls_back_the_entire_generation(self):
        get_user_model().objects.create_user(
            username="demo314_customer_003", email="real.person@example.com", password="ExistingPass!82",
        )
        before = self.snapshot()

        with self.assertRaises(DemoDataError):
            DemoDataController.generate(count=3)

        self.assertEqual(self.snapshot(), before)

    def test_conflicting_existing_role_does_not_reassign_the_user(self):
        profile = UserProfile.objects.create(name="Customer")
        user = get_user_model().objects.create_user(
            username="demo314_designer_001", email="demo314_designer_001@example.test",
        )
        UserAccount.objects.create(user=user, profile=profile)
        before = self.snapshot()

        with self.assertRaises(DemoDataError):
            DemoDataController.generate(count=2)

        self.assertEqual(self.snapshot(), before)

    def test_case_only_username_collision_is_rejected_without_changing_existing_data(self):
        profile = UserProfile.objects.create(name="Interior Designer")
        user = get_user_model().objects.create_user(
            username="DEMO314_designer_001",
            email="demo314_designer_001@example.test",
            password="KeepExistingPassword!73",
            is_active=False,
        )
        UserAccount.objects.create(user=user, profile=profile)
        before = self.snapshot()

        with self.assertRaises(DemoDataError):
            DemoDataController.generate(count=2)

        self.assertEqual(self.snapshot(), before)
        self.assertEqual(get_user_model().objects.filter(username__iexact=user.username).count(), 1)

    def test_invalid_options_are_rejected_without_writing_rows(self):
        invalid_options = [
            {"count": 0}, {"count": -1}, {"count": 1001},
            {"prefix": ""}, {"prefix": "Uppercase"}, {"prefix": "has-dash"},
            {"prefix": "has space"}, {"prefix": "x" * 21},
            {"password": "short"},
        ]
        before = self.snapshot()
        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(DemoDataError):
                    DemoDataController.generate(**options)
                self.assertEqual(self.snapshot(), before)

    def test_generated_timestamps_are_chronological_and_reports_use_the_periods(self):
        fixed_now = datetime(2026, 11, 5, 12, 30, tzinfo=datetime_timezone.utc)
        with patch("accounts.demo_data.timezone.now", return_value=fixed_now):
            DemoDataController.generate(count=5)

        for company in Company.objects.select_related("user"):
            self.assertLessEqual(company.user.date_joined, company.created_at)
            self.assertLessEqual(company.created_at, company.updated_at)
            self.assertLessEqual(company.updated_at, fixed_now)
        for project in InteriorDesignProject.objects.select_related("company"):
            self.assertLessEqual(project.company.created_at, project.created_at)
            self.assertLessEqual(project.created_at, project.updated_at)
            self.assertLessEqual(project.updated_at, fixed_now)
        for favourite in Favourite.objects.select_related("user", "project"):
            self.assertGreaterEqual(favourite.created_at, favourite.user.date_joined)
            self.assertGreaterEqual(favourite.created_at, favourite.project.created_at)
            self.assertLessEqual(favourite.created_at, fixed_now)
        for review in ProjectReview.objects.select_related("customer", "project"):
            self.assertGreaterEqual(review.created_at, review.customer.date_joined)
            self.assertGreaterEqual(review.created_at, review.project.created_at)
            self.assertLessEqual(review.created_at, review.updated_at)
            self.assertLessEqual(review.updated_at, fixed_now)
        for event in ProjectView.objects.select_related("viewer", "project"):
            self.assertGreaterEqual(event.viewed_at, event.viewer.date_joined)
            self.assertGreaterEqual(event.viewed_at, event.project.created_at)
            self.assertLessEqual(event.viewed_at, fixed_now)

        today = timezone.localtime(fixed_now).date()
        report_data = {}
        with patch("reports.controllers.timezone.localdate", return_value=today):
            for period in ["daily", "weekly", "monthly"]:
                report_data[period] = ReportController.get_report_data(period)
        self.assertGreater(report_data["daily"]["views"], 0)
        self.assertLessEqual(report_data["daily"]["views"], report_data["weekly"]["views"])
        self.assertLessEqual(report_data["weekly"]["views"], report_data["monthly"]["views"])
        self.assertLess(report_data["monthly"]["views"], ProjectView.objects.count())
        self.assertTrue(ProjectView.objects.filter(viewed_at__lt=fixed_now - timedelta(days=31)).exists())

    def test_generated_images_reference_existing_files_or_are_blank(self):
        DemoDataController.generate(count=2)

        for project in InteriorDesignProject.objects.all():
            if project.image:
                self.assertTrue(project.image.storage.exists(project.image.name))

    def test_seed_makes_fresh_data_reproducible(self):
        fixed_now = datetime(2026, 11, 5, 12, 30, tzinfo=datetime_timezone.utc)

        def generated_content():
            return {
                "companies": list(Company.objects.order_by("name").values(
                    "name", "email", "phone", "address", "description",
                )),
                "projects": list(InteriorDesignProject.objects.order_by("title").values(
                    "title", "description", "location", "style", "status", "category__name",
                )),
                "reviews": list(ProjectReview.objects.order_by("project__title").values(
                    "project__title", "customer__username", "rating", "comment",
                )),
            }

        with patch("accounts.demo_data.timezone.now", return_value=fixed_now):
            with transaction.atomic():
                DemoDataController.generate(count=3, seed=18)
                first = generated_content()
                transaction.set_rollback(True)
            DemoDataController.generate(count=3, seed=18)

        self.assertEqual(generated_content(), first)

    def test_all_four_demo_roles_can_log_in_with_the_generated_password(self):
        password = "CustomDemoPassword!246"
        result = DemoDataController.generate(count=2, password=password)
        expected_logins = {
            "User Admin": "demo314_admin",
            "Interior Designer": "demo314_designer_001",
            "Customer": "demo314_customer_001",
            "Platform Management": "demo314_pm",
        }
        self.assertEqual(result["logins"], expected_logins)
        for role, username in expected_logins.items():
            with self.subTest(role=role):
                user = get_user_model().objects.get(username=username)
                self.assertFalse(user.is_staff)
                self.assertFalse(user.is_superuser)
                self.assertEqual(user.account.profile.name, role)
                client = Client()
                response = client.post(reverse("login"), {"username": username, "password": password})
                self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
                self.assertEqual(client.get(reverse("dashboard")).status_code, 200)

    def test_command_supports_a_small_custom_namespace_and_reports_counts(self):
        output = StringIO()

        call_command("generate_demo_data", count=2, seed=19, prefix="test314", stdout=output)

        self.assertEqual(get_user_model().objects.count(), 6)
        self.assertEqual(Company.objects.count(), 2)
        self.assertEqual(InteriorDesignProject.objects.count(), 4)
        self.assertEqual(ProjectView.objects.count(), 20)
        self.assertIn("test314_customer_001", output.getvalue())
        self.assertIn("test314_designer_001", output.getvalue())

    def test_command_reports_invalid_input_as_a_command_error(self):
        with self.assertRaises(CommandError):
            call_command("generate_demo_data", count=0, stdout=StringIO())
        self.assertFalse(get_user_model().objects.exists())
