from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from companies.models import Company
from projects.models import InteriorDesignProject

from .models import Favourite


class FavouriteListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="favourite-customer",
            password="test-password",
        )
        cls.designer = user_model.objects.create_user(
            username="favourite-designer",
            password="test-password",
        )
        cls.company = Company.objects.create(user=cls.designer, name="Studio North")
        cls.residential = Category.objects.create(name="Residential")
        cls.commercial = Category.objects.create(name="Commercial")
        cls.apartment = InteriorDesignProject.objects.create(
            company=cls.company,
            category=cls.residential,
            title="Warm Apartment",
        )
        cls.office = InteriorDesignProject.objects.create(
            company=cls.company,
            category=cls.commercial,
            title="Bright Office",
        )
        cls.apartment_favourite = Favourite.objects.create(
            user=cls.user,
            project=cls.apartment,
        )
        cls.office_favourite = Favourite.objects.create(
            user=cls.user,
            project=cls.office,
        )
        Favourite.objects.filter(pk=cls.apartment_favourite.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_shows_saved_projects_and_category_counts(self):
        response = self.client.get(reverse("favourite_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Warm Apartment")
        self.assertContains(response, "Bright Office")
        self.assertContains(response, "Residential")
        self.assertContains(response, "Commercial")
        self.assertContains(response, "2", html=False)
        self.assertEqual(response.context["favourite_count"], 2)

    def test_search_and_category_filters_can_be_combined(self):
        response = self.client.get(
            reverse("favourite_list"),
            {"q": "studio", "category": str(self.residential.pk)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["favourites"],
            [self.apartment_favourite],
        )

    def test_oldest_sort_orders_saved_projects_ascending(self):
        response = self.client.get(reverse("favourite_list"), {"sort": "oldest"})

        self.assertQuerySetEqual(
            response.context["favourites"],
            [self.apartment_favourite, self.office_favourite],
        )

    def test_invalid_sort_defaults_to_recently_saved(self):
        response = self.client.get(reverse("favourite_list"), {"sort": "invalid"})

        self.assertEqual(response.context["sort_order"], "newest")
        self.assertQuerySetEqual(
            response.context["favourites"],
            [self.office_favourite, self.apartment_favourite],
        )

    def test_add_from_search_returns_to_safe_local_next_url(self):
        project = InteriorDesignProject.objects.create(
            company=self.company,
            category=self.residential,
            title="New Saved Project",
        )
        search_url = f"{reverse('customer_idp_search')}?q=New"

        response = self.client.post(
            reverse("favourite_add", args=[project.pk]),
            {"next": search_url},
        )

        self.assertRedirects(response, search_url)
        self.assertTrue(
            Favourite.objects.filter(user=self.user, project=project).exists()
        )

    def test_add_ignores_external_next_url(self):
        project = InteriorDesignProject.objects.create(
            company=self.company,
            category=self.residential,
            title="Another Saved Project",
        )

        response = self.client.post(
            reverse("favourite_add", args=[project.pk]),
            {"next": "https://example.com/"},
        )

        self.assertRedirects(
            response,
            reverse("idp_detail", args=[project.pk]),
            fetch_redirect_response=False,
        )
