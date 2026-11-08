from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .controllers import UserAccountController
from .forms import AccountCreationForm
from .models import UserAccount, UserProfile


class AccountCreationConflictTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        admin_profile = UserProfile.objects.create(name="User Admin")
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        cls.admin = get_user_model().objects.create_user(username="conflictadmin")
        UserAccount.objects.create(user=cls.admin, profile=admin_profile)

    def setUp(self):
        self.client.force_login(self.admin)
        self.data = {
            "username": "racingcustomer",
            "email": "new@example.com",
            "first_name": "Alice",
            "last_name": "Tan",
            "password1": "Reno!2026TestPass",
            "password2": "Reno!2026TestPass",
            "profile": self.customer_profile.pk,
        }

    def test_username_taken_after_validation_displays_a_field_error(self):
        original_is_valid = AccountCreationForm.is_valid

        def validate_then_claim_username(form):
            valid = original_is_valid(form)
            if valid:
                get_user_model().objects.create_user(
                    username=form.cleaned_data["username"],
                    email="existing@example.com",
                )
            return valid

        account_count = UserAccount.objects.count()
        with patch.object(
            AccountCreationForm,
            "is_valid",
            new=validate_then_claim_username,
        ):
            response = self.client.post(reverse("account_create"), self.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.assertContains(response, "A user with that username already exists.")
        self.assertContains(response, 'value="racingcustomer"')
        self.assertContains(response, 'value="new@example.com"')
        self.assertEqual(UserAccount.objects.count(), account_count)
        existing = get_user_model().objects.get(username="racingcustomer")
        self.assertEqual(existing.email, "existing@example.com")
        self.assertFalse(UserAccount.objects.filter(user=existing).exists())

    def test_controller_reports_duplicate_username_without_changing_existing_user(self):
        original_password = self.admin.password
        user_count = get_user_model().objects.count()
        account_count = UserAccount.objects.count()

        with self.assertRaises(ValidationError) as caught:
            UserAccountController.create_account(
                username=self.admin.username,
                password="Another!2026Password",
                email="replacement@example.com",
                profile=self.customer_profile,
            )

        self.assertIn("username", caught.exception.message_dict)
        self.assertEqual(get_user_model().objects.count(), user_count)
        self.assertEqual(UserAccount.objects.count(), account_count)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.password, original_password)

    def test_normalized_username_collision_is_a_validation_error(self):
        with self.assertRaises(ValidationError) as caught:
            UserAccountController.create_account(
                username="ｃｏｎｆｌｉｃｔａｄｍｉｎ",
                password="Another!2026Password",
                email="replacement@example.com",
                profile=self.customer_profile,
            )

        self.assertIn("username", caught.exception.message_dict)

    def test_unrelated_account_link_failure_rolls_back_and_is_not_hidden(self):
        account_count = UserAccount.objects.count()
        with patch(
            "accounts.controllers.UserAccount.objects.create",
            side_effect=IntegrityError("Account link failure"),
        ):
            with self.assertRaises(IntegrityError):
                UserAccountController.create_account(
                    username="rollbackcustomer",
                    password="Another!2026Password",
                    email="new@example.com",
                    profile=self.customer_profile,
                )

        self.assertFalse(
            get_user_model().objects.filter(username="rollbackcustomer").exists()
        )
        self.assertEqual(UserAccount.objects.count(), account_count)
