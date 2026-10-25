from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import UserAccount, UserProfile
from companies.models import Company
from projects.models import InteriorDesignProject


class SetupProfilesTests(TestCase):
    def test_profiles_are_created_without_duplicates(self):
        for _ in range(2):
            call_command("setup_profiles", stdout=StringIO())

        self.assertSetEqual(
            set(UserProfile.objects.values_list("name", flat=True)),
            {"User Admin", "Interior Designer", "Customer", "Platform Management"},
        )

    def test_demo_designers_have_sample_projects_without_duplicates(self):
        for _ in range(2):
            call_command("setup_profiles", stdout=StringIO())

        self.assertEqual(
            UserAccount.objects.filter(profile__name="Interior Designer").count(),
            6,
        )
        self.assertEqual(Company.objects.count(), 6)
        self.assertEqual(InteriorDesignProject.objects.count(), 18)
        self.assertEqual(
            InteriorDesignProject.objects.filter(status="current").count(),
            12,
        )
        self.assertEqual(
            InteriorDesignProject.objects.filter(status="past").count(),
            6,
        )
        self.assertTrue(
            InteriorDesignProject.objects.filter(
                company__user__username="designer_aurora",
                title="Sunlit Minimalist Living Room",
                image="sample_idp/sample_1.png",
                status="current",
            ).exists()
        )
        self.assertTrue(
            UserAccount.objects.filter(user__username="designer_ember").exists()
        )
        self.assertTrue(
            Company.objects.filter(name="Luna Form Atelier").exists()
        )

    def test_existing_user_can_be_assigned_to_user_admin(self):
        user = get_user_model().objects.create_user(username="teammate")

        for _ in range(2):
            call_command(
                "setup_profiles", admin_username="teammate", stdout=StringIO()
            )

        self.assertEqual(UserAccount.objects.filter(user=user).count(), 1)
        self.assertEqual(user.account.profile.name, "User Admin")
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_unknown_username_does_not_create_partial_setup(self):
        with self.assertRaisesMessage(CommandError, "does not exist"):
            call_command(
                "setup_profiles", admin_username="missing", stdout=StringIO()
            )

        self.assertFalse(UserProfile.objects.exists())
        self.assertFalse(UserAccount.objects.exists())

    def test_existing_profile_and_account_status_are_preserved(self):
        profile = UserProfile.objects.create(
            name="User Admin", description="Existing description", is_active=False
        )
        user = get_user_model().objects.create_user(
            username="teammate", is_active=False
        )

        call_command(
            "setup_profiles", admin_username="teammate", stdout=StringIO()
        )

        profile.refresh_from_db()
        user.refresh_from_db()
        self.assertFalse(profile.is_active)
        self.assertEqual(profile.description, "Existing description")
        self.assertFalse(user.is_active)
