from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse

from .controllers import AccountAccessController
from .models import UserAccount, UserProfile


class AccountAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_profile = UserProfile.objects.create(name="User Admin")
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        cls.user = get_user_model().objects.create_user(username="accessadmin")
        cls.account = UserAccount.objects.create(
            user=cls.user,
            profile=cls.admin_profile,
        )

    def test_active_admin_can_access_and_manage(self):
        self.assertTrue(AccountAccessController.can_access_platform(self.user))
        self.assertTrue(AccountAccessController.can_manage_users(self.user))

    def test_customer_can_access_but_not_manage(self):
        UserAccount.objects.filter(pk=self.account.pk).update(
            profile=self.customer_profile,
        )

        self.assertTrue(AccountAccessController.can_access_platform(self.user))
        self.assertFalse(AccountAccessController.can_manage_users(self.user))

    def test_suspended_account_is_denied_even_with_stale_user(self):
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)

        self.assertTrue(self.user.is_active)
        self.assertFalse(AccountAccessController.can_access_platform(self.user))
        self.assertFalse(AccountAccessController.can_manage_users(self.user))

    def test_suspended_profile_is_denied(self):
        UserProfile.objects.filter(pk=self.admin_profile.pk).update(is_active=False)

        self.assertFalse(AccountAccessController.can_access_platform(self.user))
        self.assertFalse(AccountAccessController.can_manage_users(self.user))

    def test_missing_account_is_denied(self):
        UserAccount.objects.filter(pk=self.account.pk).delete()

        self.assertFalse(AccountAccessController.can_access_platform(self.user))
        self.assertFalse(AccountAccessController.can_manage_users(self.user))

    def test_anonymous_none_and_unsaved_users_are_denied(self):
        users = [
            None,
            AnonymousUser(),
            get_user_model()(username="unsaved"),
        ]

        for user in users:
            with self.subTest(user=user):
                self.assertFalse(AccountAccessController.can_access_platform(user))
                self.assertFalse(AccountAccessController.can_manage_users(user))

    def test_role_change_is_checked_against_database(self):
        self.assertEqual(self.user.account.profile.name, "User Admin")
        UserAccount.objects.filter(pk=self.account.pk).update(
            profile=self.customer_profile,
        )

        self.assertFalse(AccountAccessController.can_manage_users(self.user))

    def test_superuser_without_account_has_no_bypass(self):
        user = get_user_model().objects.create_superuser(
            username="unassignedroot",
            password="TestOnly!2026",
        )

        self.assertFalse(AccountAccessController.can_access_platform(user))
        self.assertFalse(AccountAccessController.can_manage_users(user))

    def test_admin_changing_own_role_loses_management_access(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("account_update", args=[self.account.pk]),
            {
                "username": self.user.username,
                "first_name": "",
                "last_name": "",
                "email": "admin@example.com",
                "profile": self.customer_profile.pk,
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.client.get(reverse("account_list")).status_code, 403)
