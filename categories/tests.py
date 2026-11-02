from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category


class CategoryFormTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="category_editor",
            password="CategoryEditor2026!",
        )
        self.client.force_login(self.user)

    def test_create_category_form_shows_styled_fields_and_actions(self):
        response = self.client.get(reverse("category_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create IDP Category")
        self.assertContains(response, 'id="category-name"')
        self.assertContains(response, 'id="category-description"')
        self.assertContains(response, "Save category")
        self.assertContains(response, "Cancel")

    def test_create_category_still_saves_and_redirects(self):
        response = self.client.post(
            reverse("category_create"),
            {"name": "Living Room", "description": "Living room projects."},
        )

        category = Category.objects.get(name="Living Room")
        self.assertRedirects(
            response,
            reverse("category_detail", args=[category.pk]),
        )
        self.assertEqual(category.description, "Living room projects.")

    def test_category_list_shows_categories_and_search_results(self):
        matching = Category.objects.create(
            name="Living Room",
            description="Comfortable spaces for families.",
        )
        Category.objects.create(name="Kitchen", description="Cooking spaces.")

        response = self.client.get(
            reverse("category_list"),
            {"q": "comfortable"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All categories")
        self.assertContains(response, matching.name)
        self.assertContains(response, "Comfortable spaces for families.")
        self.assertNotContains(response, "Kitchen")
        self.assertContains(response, "Clear")
