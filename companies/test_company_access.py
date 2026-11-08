from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile

from .models import Company


class CompanyAccessTests(TestCase):
    company_requests = (
        ("get", "company_detail"),
        ("get", "company_create"),
        ("post", "company_create"),
        ("get", "company_update"),
        ("post", "company_update"),
        ("get", "company_delete"),
        ("post", "company_delete"),
        ("get", "company_search"),
    )

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.designer_profile = UserProfile.objects.create(name="Interior Designer")
        cls.designer = User.objects.create_user(username="company_access_id")
        UserAccount.objects.create(
            user=cls.designer,
            profile=cls.designer_profile,
        )
        cls.other_designer = User.objects.create_user(username="company_other_id")
        UserAccount.objects.create(
            user=cls.other_designer,
            profile=cls.designer_profile,
        )
        cls.other_company = Company.objects.create(
            user=cls.other_designer,
            name="Other Designer Studio",
        )
        cls.non_designers = {}
        for index, role in enumerate(
            ["Customer", "User Admin", "Platform Management"], start=1,
        ):
            profile = UserProfile.objects.create(name=role)
            user = User.objects.create_user(username=f"company_other_role_{index}")
            UserAccount.objects.create(user=user, profile=profile)
            cls.non_designers[role] = user
            if role == "Customer":
                cls.customer_profile = profile
        cls.unassigned = User.objects.create_user(username="company_unassigned")

    def setUp(self):
        self.client.force_login(self.designer)
        self.data = {
            "name": "My Design Studio",
            "description": "Residential renovation services",
            "email": "studio@example.com",
            "phone": "+65 6123 4567",
            "website": "https://studio.example.com",
            "address": "18 Example Road",
        }

    def assert_company_requests_forbidden(self):
        before = list(Company.objects.order_by("pk").values())
        for method, route in self.company_requests:
            with self.subTest(method=method, route=route):
                response = getattr(self.client, method)(
                    reverse(route),
                    self.data if method == "post" else {},
                )
                self.assertEqual(response.status_code, 403)
        self.assertEqual(list(Company.objects.order_by("pk").values()), before)

    def assert_company_requests_require_login(self):
        before = list(Company.objects.order_by("pk").values())
        for method, route in self.company_requests:
            with self.subTest(method=method, route=route):
                url = reverse(route)
                response = getattr(self.client, method)(
                    url,
                    self.data if method == "post" else {},
                )
                self.assertRedirects(
                    response,
                    reverse("login") + "?next=" + url,
                    fetch_redirect_response=False,
                )
        self.assertEqual(list(Company.objects.order_by("pk").values()), before)

    def test_active_designer_can_manage_own_company(self):
        self.assertEqual(self.client.get(reverse("company_create")).status_code, 200)

        response = self.client.post(reverse("company_create"), self.data)
        self.assertRedirects(response, reverse("company_detail"))
        company = Company.objects.get(user=self.designer)
        self.assertEqual(company.name, self.data["name"])

        response = self.client.get(reverse("company_detail"))
        self.assertContains(response, self.data["name"])
        self.assertNotContains(response, self.other_company.name)

        response = self.client.post(
            reverse("company_update"),
            {**self.data, "name": "Updated Design Studio"},
        )
        self.assertRedirects(response, reverse("company_detail"))
        company.refresh_from_db()
        self.assertEqual(company.name, "Updated Design Studio")

        response = self.client.post(reverse("company_delete"))
        self.assertRedirects(response, reverse("company_detail"))
        self.assertFalse(Company.objects.filter(user=self.designer).exists())
        self.assertTrue(Company.objects.filter(pk=self.other_company.pk).exists())

    def test_designer_cannot_target_another_designers_company(self):
        target = {
            "company_id": self.other_company.pk,
            "user": self.other_designer.pk,
            "user_id": self.other_designer.pk,
        }
        response = self.client.get(reverse("company_detail"), target)
        self.assertIsNone(response.context["company"])
        self.assertNotContains(response, self.other_company.name)

        response = self.client.post(
            reverse("company_update"),
            {**self.data, **target},
        )
        self.assertRedirects(response, reverse("company_create"))
        response = self.client.post(reverse("company_delete"), target)
        self.assertRedirects(response, reverse("company_detail"))

        self.other_company.refresh_from_db()
        self.assertEqual(self.other_company.name, "Other Designer Studio")
        self.assertFalse(Company.objects.filter(user=self.designer).exists())

    def test_other_roles_cannot_create_companies(self):
        for role, user in self.non_designers.items():
            with self.subTest(role=role):
                self.client.force_login(user)
                response = self.client.post(reverse("company_create"), self.data)
                self.assertEqual(response.status_code, 403)
                self.assertFalse(Company.objects.filter(user=user).exists())

    def test_other_roles_cannot_access_existing_company_records(self):
        for role, user in self.non_designers.items():
            with self.subTest(role=role):
                Company.objects.create(user=user, name=f"Legacy {role} Company")
                self.client.force_login(user)
                self.assert_company_requests_forbidden()

    def test_user_without_an_account_is_forbidden(self):
        self.client.force_login(self.unassigned)
        self.assert_company_requests_forbidden()

    def test_profile_suspension_blocks_an_existing_session(self):
        Company.objects.create(user=self.designer, name="Suspended Profile Studio")
        self.assertEqual(self.client.get(reverse("company_detail")).status_code, 200)
        UserProfile.objects.filter(pk=self.designer_profile.pk).update(is_active=False)

        self.assert_company_requests_forbidden()

    def test_account_suspension_blocks_an_existing_session(self):
        Company.objects.create(user=self.designer, name="Suspended Account Studio")
        self.assertEqual(self.client.get(reverse("company_detail")).status_code, 200)
        get_user_model().objects.filter(pk=self.designer.pk).update(is_active=False)

        self.assert_company_requests_require_login()

    def test_role_change_blocks_an_existing_session(self):
        Company.objects.create(user=self.designer, name="Former Designer Studio")
        self.assertEqual(self.client.get(reverse("company_detail")).status_code, 200)
        UserAccount.objects.filter(user=self.designer).update(
            profile=self.customer_profile,
        )

        self.assert_company_requests_forbidden()

    def test_anonymous_requests_require_login(self):
        self.client.logout()
        self.assert_company_requests_require_login()

    def test_delete_get_displays_confirmation_and_preserves_company(self):
        company = Company.objects.create(user=self.designer, name="Keep This Studio")

        response = self.client.get(reverse("company_delete"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "companies/company_confirm_delete.html")
        self.assertContains(response, company.name)
        self.assertTrue(Company.objects.filter(pk=company.pk).exists())
