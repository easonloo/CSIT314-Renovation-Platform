from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import UserAccount, UserProfile


class AccountSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        admin_profile = UserProfile.objects.create(name="User Admin")
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        User = get_user_model()

        cls.admin = User.objects.create_user(username="searchadmin")
        cls.admin_account = UserAccount.objects.create(
            user=cls.admin,
            profile=admin_profile,
        )
        cls.alice = User.objects.create_user(
            username="alice",
            email="hello@example.net",
        )
        cls.alice_account = UserAccount.objects.create(
            user=cls.alice,
            profile=cls.customer_profile,
        )
        bob = User.objects.create_user(username="bob", email="bob@example.org")
        cls.bob_account = UserAccount.objects.create(
            user=bob,
            profile=cls.customer_profile,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_username_search_ignores_case_and_surrounding_spaces(self):
        response = self.client.get(reverse("account_list"), {"q": " ALI "})

        self.assertEqual(list(response.context["accounts"]), [self.alice_account])
        self.assertEqual(response.context["q"], "ALI")
        self.assertContains(response, 'value="ALI"')
        detail_url = reverse("account_detail", args=[self.alice_account.pk])
        self.assertContains(response, 'href="{}"'.format(detail_url))
        self.assertContains(
            response,
            'href="{}">Clear</a>'.format(reverse("account_list")),
        )

    def test_email_search_ignores_case(self):
        response = self.client.get(
            reverse("account_list"),
            {"q": "HELLO@EXAMPLE.NET"},
        )

        self.assertEqual(list(response.context["accounts"]), [self.alice_account])

    def test_no_matches_shows_empty_message(self):
        response = self.client.get(
            reverse("account_list"),
            {"q": "nobody-matches-this"},
        )

        self.assertEqual(list(response.context["accounts"]), [])
        self.assertContains(response, "No accounts found.")

    def test_missing_empty_and_whitespace_search_show_all_accounts(self):
        expected = [self.alice_account, self.bob_account, self.admin_account]

        for params in [{}, {"q": ""}, {"q": "   "}]:
            with self.subTest(params=params):
                response = self.client.get(reverse("account_list"), params)
                self.assertEqual(list(response.context["accounts"]), expected)

    def test_suspended_account_and_profile_are_still_searchable(self):
        get_user_model().objects.filter(pk=self.alice.pk).update(is_active=False)
        UserProfile.objects.filter(pk=self.customer_profile.pk).update(
            is_active=False,
        )

        response = self.client.get(reverse("account_list"), {"q": "alice"})

        self.assertEqual(list(response.context["accounts"]), [self.alice_account])
        self.assertContains(response, "Suspended")

    def test_customer_cannot_search_accounts(self):
        self.client.force_login(self.alice)

        response = self.client.get(reverse("account_list"), {"q": "alice"})

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()

        response = self.client.get(reverse("account_list"), {"q": "alice"})

        self.assertEqual(response.status_code, 302)
        destination = urlsplit(response.url)
        self.assertEqual(destination.path, reverse("login"))
        self.assertEqual(
            parse_qs(destination.query)["next"],
            [reverse("account_list") + "?q=alice"],
        )
