from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile
from companies.models import Company
from projects.models import InteriorDesignProject

from .models import Favourite


class FavouriteAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        cls.customer = User.objects.create_user(username="favourite_access_customer")
        cls.other_customer = User.objects.create_user(username="favourite_other_customer")
        for user in [cls.customer, cls.other_customer]:
            UserAccount.objects.create(user=user, profile=cls.customer_profile)

        cls.non_customers = {}
        for index, role in enumerate(
            ["Interior Designer", "User Admin", "Platform Management"], start=1,
        ):
            profile = UserProfile.objects.create(name=role)
            user = User.objects.create_user(username=f"favourite_other_role_{index}")
            UserAccount.objects.create(user=user, profile=profile)
            cls.non_customers[role] = user
            if role == "Interior Designer":
                cls.designer_profile = profile
                cls.designer = user

        company = Company.objects.create(user=cls.designer, name="Access Test Studio")
        cls.project = InteriorDesignProject.objects.create(
            company=company,
            title="My Saved Project",
        )
        cls.other_project = InteriorDesignProject.objects.create(
            company=company,
            title="Other Customer Private Favourite",
        )
        cls.unassigned = User.objects.create_user(username="favourite_unassigned")

    def setUp(self):
        self.client.force_login(self.customer)

    def favourite_state(self):
        return (
            list(Favourite.objects.order_by("pk").values()),
            list(
                InteriorDesignProject.objects.order_by("pk").values_list(
                    "pk", "shortlist_count",
                )
            ),
        )

    def assert_favourite_requests_forbidden(self):
        before = self.favourite_state()
        requests = (
            ("get", reverse("favourite_list")),
            ("post", reverse("favourite_toggle", args=[self.project.pk])),
        )
        for method, url in requests:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.favourite_state(), before)

    def assert_favourite_requests_require_login(self):
        before = self.favourite_state()
        requests = (
            ("get", reverse("favourite_list")),
            ("post", reverse("favourite_toggle", args=[self.project.pk])),
        )
        for method, url in requests:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertRedirects(
                    response,
                    reverse("login") + "?next=" + url,
                    fetch_redirect_response=False,
                )
        self.assertEqual(self.favourite_state(), before)

    def test_active_customer_saves_and_lists_only_their_own_favourites(self):
        Favourite.objects.create(user=self.other_customer, project=self.other_project)
        InteriorDesignProject.objects.filter(pk=self.other_project.pk).update(
            shortlist_count=1,
        )

        response = self.client.post(
            reverse("favourite_toggle", args=[self.project.pk]),
        )
        self.assertRedirects(
            response,
            reverse("idp_detail", args=[self.project.pk]),
            fetch_redirect_response=False,
        )
        own_favourite = Favourite.objects.get(user=self.customer, project=self.project)
        self.project.refresh_from_db()
        self.assertEqual(self.project.shortlist_count, 1)

        response = self.client.get(reverse("favourite_list"))
        self.assertEqual(list(response.context["favourites"]), [own_favourite])
        self.assertContains(response, self.project.title)
        self.assertNotContains(response, self.other_project.title)

    def test_other_roles_cannot_save_or_increase_shortlists(self):
        for role, user in self.non_customers.items():
            with self.subTest(role=role):
                self.client.force_login(user)
                before = self.favourite_state()

                response = self.client.post(
                    reverse("favourite_toggle", args=[self.project.pk]),
                    {"user": self.customer.pk, "user_id": self.customer.pk},
                )

                self.assertEqual(response.status_code, 403)
                self.assertEqual(self.favourite_state(), before)

    def test_other_roles_cannot_list_legacy_favourites(self):
        for role, user in self.non_customers.items():
            with self.subTest(role=role):
                Favourite.objects.create(user=user, project=self.project)
                self.client.force_login(user)
                self.assert_favourite_requests_forbidden()

    def test_user_without_an_account_is_forbidden(self):
        self.client.force_login(self.unassigned)
        self.assert_favourite_requests_forbidden()

    def test_profile_suspension_blocks_an_existing_session(self):
        self.assertEqual(self.client.get(reverse("favourite_list")).status_code, 200)
        UserProfile.objects.filter(pk=self.customer_profile.pk).update(is_active=False)

        self.assert_favourite_requests_forbidden()

    def test_account_suspension_blocks_an_existing_session(self):
        self.assertEqual(self.client.get(reverse("favourite_list")).status_code, 200)
        get_user_model().objects.filter(pk=self.customer.pk).update(is_active=False)

        self.assert_favourite_requests_require_login()

    def test_role_change_blocks_an_existing_session(self):
        self.assertEqual(self.client.get(reverse("favourite_list")).status_code, 200)
        UserAccount.objects.filter(user=self.customer).update(
            profile=self.designer_profile,
        )

        self.assert_favourite_requests_forbidden()

    def test_anonymous_requests_require_login(self):
        self.client.logout()
        self.assert_favourite_requests_require_login()

    def test_saving_still_requires_post(self):
        before = self.favourite_state()

        response = self.client.get(
            reverse("favourite_toggle", args=[self.project.pk]),
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.favourite_state(), before)
