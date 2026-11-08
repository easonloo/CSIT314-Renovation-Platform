from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile
from companies.models import Company
from projects.models import InteriorDesignProject

from .models import Category
from .views import category_create, category_detail, category_list

# Create your tests here.


class PlatformManagerCategoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager_profile = UserProfile.objects.create(
            name="Platform Management"
        )
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        cls.manager = get_user_model().objects.create_user(
            username="category_manager",
            password="ManagerPass123!",
        )
        UserAccount.objects.create(user=cls.manager, profile=cls.manager_profile)
        cls.customer = get_user_model().objects.create_user(
            username="category_customer",
        )
        UserAccount.objects.create(user=cls.customer, profile=cls.customer_profile)
        cls.category = Category.objects.create(
            name="Kitchen",
            description="Kitchen renovation projects.",
        )

    def setUp(self):
        self.client.force_login(self.manager)
        self.request_factory = RequestFactory()

    def test_platform_manager_can_log_in_and_log_out(self):
        self.client.logout()
        login_response = self.client.post(
            reverse("login"),
            {"username": "category_manager", "password": "ManagerPass123!"},
        )

        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(self.manager.pk),
        )

        logout_response = self.client.post(reverse("logout"))

        self.assertEqual(logout_response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_platform_manager_can_create_update_view_and_delete_category(self):
        create_response = self.client.post(
            reverse("category_create"),
            {"name": "Bathroom", "description": "Bathroom renovation projects."},
        )
        category = Category.objects.get(name="Bathroom")

        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(
            create_response["Location"],
            reverse("category_detail", args=[category.pk]),
        )

        update_response = self.client.post(
            reverse("category_update", args=[category.pk]),
            {"name": "Bathrooms", "description": "Updated category details."},
        )
        category.refresh_from_db()
        self.assertEqual(update_response.status_code, 302)
        self.assertEqual(category.name, "Bathrooms")
        self.assertEqual(category.description, "Updated category details.")

        request = self.request_factory.get(
            reverse("category_detail", args=[category.pk])
        )
        request.user = self.manager
        detail_response = category_detail(request, category.pk)
        self.assertEqual(detail_response.status_code, 200)
        self.assertIn("Bathrooms", detail_response.content.decode())

        delete_response = self.client.post(
            reverse("category_delete", args=[category.pk])
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_platform_manager_can_search_categories(self):
        request = self.request_factory.get(
            reverse("category_list"),
            {"q": "Kitchen"},
        )
        request.user = self.manager
        response = category_list(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Kitchen", response.content.decode())
        self.assertNotIn("Bathroom", response.content.decode())

    def test_create_category_form_renders_fields_and_actions(self):
        response = self.client.get(reverse("category_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create IDP Category")
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="description"')
        self.assertContains(response, "Save category")
        self.assertContains(response, "Cancel")

    def test_category_list_renders_search_results(self):
        Category.objects.create(
            name="Living Room",
            description="Comfortable spaces for families.",
        )
        Category.objects.create(name="Bedroom", description="Sleeping spaces.")

        response = self.client.get(
            reverse("category_list"),
            {"q": "comfortable"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Living Room")
        self.assertContains(response, "Comfortable spaces for families.")
        self.assertNotContains(response, "Bedroom")

    def test_duplicate_category_name_is_rejected(self):
        request = self.request_factory.post(
            reverse("category_create"),
            {"name": "Kitchen", "description": "Duplicate."},
        )
        request.user = self.manager
        response = category_create(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("already exists", response.content.decode())
        self.assertEqual(Category.objects.filter(name="Kitchen").count(), 1)

    def test_non_platform_manager_cannot_manage_categories(self):
        request = self.request_factory.get(reverse("category_list"))
        request.user = self.customer

        with self.assertRaises(PermissionDenied):
            category_list(request)

    def test_deleting_a_category_keeps_its_projects_uncategorized(self):
        company = Company.objects.create(user=self.customer, name="Category Studio")
        project = InteriorDesignProject.objects.create(
            company=company, category=self.category, title="Keep this project",
        )

        response = self.client.post(
            reverse("category_delete", args=[self.category.pk]),
        )

        self.assertRedirects(response, reverse("category_list"))
        project.refresh_from_db()
        self.assertIsNone(project.category_id)
        self.assertEqual(project.title, "Keep this project")

    def test_updating_to_an_existing_name_shows_errors_without_saving(self):
        Category.objects.create(name="Bedroom")

        response = self.client.post(
            reverse("category_update", args=[self.category.pk]),
            {"name": "Bedroom", "description": "Do not save this change."},
        )

        self.assertContains(response, "already exists")
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Kitchen")
        self.assertEqual(self.category.description, "Kitchen renovation projects.")

    def test_missing_category_detail_and_update_are_404_and_delete_is_safe(self):
        missing_id = self.category.pk + 1000
        for name in ["category_detail", "category_update"]:
            with self.subTest(view=name):
                response = self.client.get(reverse(name, args=[missing_id]))
                self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse("category_delete", args=[missing_id]))

        self.assertRedirects(response, reverse("category_list"))
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
