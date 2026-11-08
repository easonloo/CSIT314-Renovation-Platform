from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from projects.models import InteriorDesignProject

from .models import Favourite

class FavouriteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        customer_profile = UserProfile.objects.create(name="Customer")
        designer_profile = UserProfile.objects.create(name="Interior Designer")
        cls.customer = get_user_model().objects.create_user(
            username="favourite_customer",
        )
        UserAccount.objects.create(user=cls.customer, profile=customer_profile)
        cls.other_customer = get_user_model().objects.create_user(
            username="favourite_second_customer",
        )
        UserAccount.objects.create(user=cls.other_customer, profile=customer_profile)
        designer = get_user_model().objects.create_user(
            username="favourite_designer",
        )
        UserAccount.objects.create(user=designer, profile=designer_profile)
        company = Company.objects.create(user=designer, name="Favourite Studio")
        category = Category.objects.create(name="Favourite Category")
        cls.project = InteriorDesignProject.objects.create(
            company=company,
            category=category,
            title="Favourite Test Project",
        )

    def setUp(self):
        self.client.force_login(self.customer)
        self.url = reverse("favourite_toggle", args=[self.project.pk])

    def save_project_for(self, user):
        Favourite.objects.create(user=user, project=self.project)
        InteriorDesignProject.objects.filter(pk=self.project.pk).update(
            shortlist_count=Favourite.objects.filter(project=self.project).count(),
        )

    def test_clicking_again_removes_and_a_third_click_saves_again(self):
        for expected_saved, expected_count in [(True, 1), (False, 0), (True, 1)]:
            with self.subTest(saved=expected_saved, count=expected_count):
                response = self.client.post(self.url)

                self.assertRedirects(
                    response,
                    reverse("idp_detail", args=[self.project.pk]),
                    fetch_redirect_response=False,
                )
                self.assertEqual(
                    Favourite.objects.filter(
                        user=self.customer, project=self.project,
                    ).exists(),
                    expected_saved,
                )
                self.project.refresh_from_db()
                self.assertEqual(self.project.shortlist_count, expected_count)

    def test_removing_preserves_another_customers_favourite_and_count(self):
        self.save_project_for(self.customer)
        self.save_project_for(self.other_customer)

        self.client.post(self.url, {"user_id": self.other_customer.pk})

        self.assertFalse(Favourite.objects.filter(user=self.customer).exists())
        self.assertTrue(Favourite.objects.filter(user=self.other_customer).exists())
        self.project.refresh_from_db()
        self.assertEqual(self.project.shortlist_count, 1)

    def test_removing_a_legacy_favourite_does_not_make_the_count_negative(self):
        Favourite.objects.create(user=self.customer, project=self.project)

        self.client.post(self.url)

        self.assertFalse(Favourite.objects.filter(user=self.customer).exists())
        self.project.refresh_from_db()
        self.assertEqual(self.project.shortlist_count, 0)

    def test_counter_update_failure_rolls_back_saving_and_removing(self):
        for initially_saved in [False, True]:
            with self.subTest(initially_saved=initially_saved):
                if initially_saved:
                    self.save_project_for(self.customer)
                with patch(
                    "favourites.controllers.InteriorDesignProject.objects.filter",
                    side_effect=IntegrityError("Counter update failed"),
                ):
                    with self.assertRaises(IntegrityError):
                        self.client.post(self.url)

                self.assertEqual(
                    Favourite.objects.filter(user=self.customer).exists(),
                    initially_saved,
                )
                self.project.refresh_from_db()
                self.assertEqual(self.project.shortlist_count, int(initially_saved))

    def test_return_to_explore_or_favourites_preserves_filters(self):
        for name in ["customer_idp_search", "favourite_list"]:
            with self.subTest(screen=name):
                next_url = reverse(name) + "?q=Living%20Room&category=1&sort=oldest"
                response = self.client.post(self.url, {"next": next_url})

                self.assertRedirects(response, next_url, fetch_redirect_response=False)

    def test_external_return_urls_fall_back_to_project_details(self):
        for next_url in [
            "https://example.com/",
            "//example.com/",
            "javascript:alert(1)",
            "/\\example.com/",
        ]:
            with self.subTest(next_url=next_url):
                response = self.client.post(self.url, {"next": next_url})

                self.assertRedirects(
                    response,
                    reverse("idp_detail", args=[self.project.pk]),
                    fetch_redirect_response=False,
                )

    def test_missing_project_returns_to_explore_without_changing_favourites(self):
        self.save_project_for(self.customer)
        missing_id = self.project.pk + 1000

        response = self.client.post(reverse("favourite_toggle", args=[missing_id]))

        self.assertRedirects(
            response, reverse("customer_idp_search"), fetch_redirect_response=False,
        )
        self.assertEqual(Favourite.objects.count(), 1)
        self.project.refresh_from_db()
        self.assertEqual(self.project.shortlist_count, 1)

    def test_detail_button_reflects_saved_and_removed_states(self):
        detail_url = reverse("idp_detail", args=[self.project.pk])
        response = self.client.get(detail_url)
        self.assertContains(response, "Save to favourites")

        response = self.client.post(self.url, follow=True)
        self.assertContains(response, "Remove from favourites")
        self.assertContains(response, 'aria-pressed="true"')
        self.assertContains(response, "Project saved to favourites.")

        response = self.client.post(self.url, follow=True)
        self.assertContains(response, "Save to favourites")
        self.assertContains(response, 'aria-pressed="false"')
        self.assertContains(response, "Project removed from favourites.")
        self.assertNotContains(response, "Remove from favourites")

    def test_explore_heart_reflects_saved_and_removed_states(self):
        explore_url = reverse("customer_idp_search")
        response = self.client.get(explore_url)
        self.assertContains(response, 'aria-pressed="false"')

        response = self.client.post(self.url, {"next": explore_url}, follow=True)
        self.assertContains(response, 'title="Remove from favourites"')
        self.assertContains(response, 'aria-pressed="true"')

        response = self.client.post(self.url, {"next": explore_url}, follow=True)
        self.assertContains(response, 'title="Save to favourites"')
        self.assertContains(response, 'aria-pressed="false"')

    def test_favourites_heart_removes_project_and_updates_collection_counts(self):
        self.save_project_for(self.customer)
        list_url = reverse("favourite_list")
        response = self.client.get(list_url)
        self.assertContains(response, f'action="{self.url}"')
        self.assertContains(response, 'title="Remove from favourites"')

        response = self.client.post(self.url, {"next": list_url}, follow=True)
        self.assertEqual(response.context["favourite_count"], 0)
        self.assertEqual(response.context["filtered_count"], 0)
        self.assertContains(response, "Your collection is waiting")
        self.assertNotContains(response, f'action="{self.url}"')

    def test_toggle_requires_a_csrf_token(self):
        self.save_project_for(self.customer)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.customer)

        response = client.post(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Favourite.objects.filter(user=self.customer).exists())
        self.project.refresh_from_db()
        self.assertEqual(self.project.shortlist_count, 1)
