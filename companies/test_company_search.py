from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile

from .models import Company


class CompanySearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.designer_profile = UserProfile.objects.create(name="Interior Designer")
        customer_profile = UserProfile.objects.create(name="Customer")
        cls.designer = get_user_model().objects.create_user(
            username="company_search_id",
        )
        UserAccount.objects.create(
            user=cls.designer,
            profile=cls.designer_profile,
        )
        cls.customer = get_user_model().objects.create_user(
            username="company_search_customer",
        )
        UserAccount.objects.create(user=cls.customer, profile=customer_profile)
        cls.company = Company.objects.create(
            user=cls.designer,
            name="Own Studio",
            description="Modern renovation services",
            phone="+65 6123 4567",
        )
        other = get_user_model().objects.create_user(username="other_company_id")
        UserAccount.objects.create(user=other, profile=cls.designer_profile)
        Company.objects.create(
            user=other,
            name="Private Other Studio",
            description="Secret details",
        )

    def setUp(self):
        self.client.force_login(self.designer)

    def test_matches_company_values_ignoring_case_and_whitespace(self):
        response = self.client.get(
            reverse("company_search"),
            {"q": "  MODERN  "},
        )

        self.assertEqual(
            response.context["results"],
            [("Description", "Modern renovation services")],
        )
        self.assertContains(response, 'value="MODERN"')
        self.assertContains(
            response,
            'href="{}"'.format(reverse("company_detail")),
        )

    def test_field_name_can_find_a_specific_detail(self):
        response = self.client.get(reverse("company_search"), {"q": "phone"})

        self.assertEqual(
            response.context["results"],
            [("Phone", "+65 6123 4567")],
        )

    def test_search_never_exposes_another_company(self):
        response = self.client.get(reverse("company_search"), {"q": "Secret"})

        self.assertEqual(response.context["results"], [])
        self.assertNotContains(response, "Secret details")
        self.assertNotContains(response, "Private Other Studio")

    def test_unmatched_search_has_a_clear_message(self):
        response = self.client.get(
            reverse("company_search"),
            {"q": "not-found-anywhere"},
        )

        self.assertContains(response, "No matching company information found.")

    def test_empty_search_displays_instructions(self):
        for params in [{}, {"q": ""}, {"q": "   "}]:
            with self.subTest(params=params):
                response = self.client.get(reverse("company_search"), params)
                self.assertEqual(response.context["results"], [])
                self.assertContains(
                    response,
                    "Enter a keyword to search your company information.",
                )

    def test_designer_without_company_is_sent_to_create_one(self):
        self.company.delete()

        response = self.client.get(reverse("company_search"))

        self.assertRedirects(response, reverse("company_create"))

    def test_customer_is_forbidden(self):
        self.client.force_login(self.customer)

        response = self.client.get(reverse("company_search"), {"q": "Modern"})

        self.assertEqual(response.status_code, 403)

    def test_suspended_profile_is_forbidden(self):
        UserProfile.objects.filter(pk=self.designer_profile.pk).update(
            is_active=False,
        )

        response = self.client.get(reverse("company_search"))

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()
        url = reverse("company_search")

        self.assertRedirects(
            self.client.get(url),
            reverse("login") + "?next=" + url,
        )

    def test_company_page_links_to_search(self):
        response = self.client.get(reverse("company_detail"))

        self.assertContains(
            response,
            'href="{}"'.format(reverse("company_search")),
        )

    def test_search_rejects_post_requests(self):
        response = self.client.post(reverse("company_search"), {"q": "Modern"})

        self.assertEqual(response.status_code, 405)
