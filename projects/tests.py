from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from reviews.models import ProjectReview

from .models import InteriorDesignProject
from .views import customer_idp_search


class InteriorDesignProjectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.designer_profile = UserProfile.objects.create(
            name="Interior Designer"
        )
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        cls.designer = get_user_model().objects.create_user(
            username="designer",
            password="TestPassword123!",
        )
        UserAccount.objects.create(
            user=cls.designer,
            profile=cls.designer_profile,
        )
        cls.company = Company.objects.create(
            user=cls.designer,
            name="Design Studio",
        )
        cls.category = Category.objects.create(name="Residential")
        cls.current_project = InteriorDesignProject.objects.create(
            company=cls.company,
            category=cls.category,
            title="Current Apartment",
            description="An ongoing apartment renovation",
            location="Singapore",
            style="Modern",
            status=InteriorDesignProject.STATUS_CURRENT,
        )
        cls.past_project = InteriorDesignProject.objects.create(
            company=cls.company,
            category=cls.category,
            title="Completed House",
            description="A finished family home",
            location="Tampines",
            style="Scandinavian",
            status=InteriorDesignProject.STATUS_PAST,
        )

    def setUp(self):
        self.client.force_login(self.designer)

    def test_designer_can_create_current_and_past_projects(self):
        for status in (
            InteriorDesignProject.STATUS_CURRENT,
            InteriorDesignProject.STATUS_PAST,
        ):
            with self.subTest(status=status):
                response = self.client.post(
                    reverse("idp_create"),
                    {
                        "title": f"{status.title()} Sample",
                        "description": "Project description",
                        "category": self.category.pk,
                        "location": "Singapore",
                        "style": "Contemporary",
                        "status": status,
                    },
                )
                project = InteriorDesignProject.objects.get(
                    title=f"{status.title()} Sample"
                )
                self.assertRedirects(
                    response,
                    reverse("idp_detail", args=[project.pk]),
                )
                self.assertEqual(project.company, self.company)
                self.assertEqual(project.status, status)

    def test_create_requires_project_title(self):
        response = self.client.post(
            reverse("idp_create"),
            {},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertEqual(InteriorDesignProject.objects.count(), 2)

    def test_designer_can_view_current_and_past_projects(self):
        for project in (self.current_project, self.past_project):
            with self.subTest(status=project.status):
                response = self.client.get(
                    reverse("idp_detail", args=[project.pk])
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, project.title)
                self.assertContains(response, project.get_status_display())

    def test_update_current_and_past_projects(self):
        for project, new_status in (
            (self.current_project, InteriorDesignProject.STATUS_PAST),
            (self.past_project, InteriorDesignProject.STATUS_CURRENT),
        ):
            with self.subTest(project=project.title):
                updated_title = f"Updated {project.title}"
                response = self.client.post(
                    reverse("idp_update", args=[project.pk]),
                    {
                        "title": updated_title,
                        "description": "Updated project details",
                        "category": self.category.pk,
                        "location": "Updated location",
                        "style": "Updated style",
                        "status": new_status,
                    },
                )
                project.refresh_from_db()
                self.assertRedirects(
                    response,
                    reverse("idp_detail", args=[project.pk]),
                )
                self.assertEqual(project.title, updated_title)
                self.assertEqual(project.description, "Updated project details")
                self.assertEqual(project.status, new_status)

    def test_search_filters_current_and_past_projects(self):
        current_response = self.client.get(
            reverse("idp_list"),
            {"status": "current", "q": "Apartment"},
        )
        past_response = self.client.get(
            reverse("idp_list"),
            {"status": "past", "q": "Apartment"},
        )

        self.assertContains(current_response, "Current Apartment")
        self.assertNotContains(current_response, "Completed House")
        self.assertNotContains(past_response, "Current Apartment")
        self.assertNotContains(past_response, "Completed House")

        past_response = self.client.get(
            reverse("idp_list"),
            {"status": "past", "q": "Scandinavian"},
        )
        self.assertContains(past_response, "Completed House")

    def test_list_filters_current_and_past_projects(self):
        current_response = self.client.get(
            reverse("idp_list"),
            {"status": InteriorDesignProject.STATUS_CURRENT},
        )
        past_response = self.client.get(
            reverse("idp_list"),
            {"status": InteriorDesignProject.STATUS_PAST},
        )

        self.assertContains(current_response, "Current Apartment")
        self.assertNotContains(current_response, "Completed House")
        self.assertContains(past_response, "Completed House")
        self.assertNotContains(past_response, "Current Apartment")

    def test_customer_search_shows_average_rating_for_each_project(self):
        customer_one = get_user_model().objects.create_user(
            username="reviewer-one",
        )
        customer_two = get_user_model().objects.create_user(
            username="reviewer-two",
        )
        ProjectReview.objects.create(
            customer=customer_one,
            project=self.past_project,
            rating=4,
        )
        ProjectReview.objects.create(
            customer=customer_two,
            project=self.past_project,
            rating=5,
        )

        request = RequestFactory().get(reverse("customer_idp_search"))
        request.user = self.designer
        response = customer_idp_search(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("★ 4.5 / 5", response.content.decode())
        self.assertIn("No reviews", response.content.decode())

    def test_designer_can_delete_current_and_past_projects(self):
        for project in (self.current_project, self.past_project):
            with self.subTest(status=project.status):
                response = self.client.post(
                    reverse("idp_delete", args=[project.pk])
                )
                self.assertRedirects(response, reverse("idp_list"))
                self.assertFalse(
                    InteriorDesignProject.objects.filter(pk=project.pk).exists()
                )

    def test_designer_cannot_manage_another_designers_project(self):
        another_designer = get_user_model().objects.create_user(
            username="another-designer",
            password="TestPassword123!",
        )
        UserAccount.objects.create(
            user=another_designer,
            profile=self.designer_profile,
        )
        self.client.force_login(another_designer)

        self.assertEqual(
            self.client.get(
                reverse("idp_detail", args=[self.current_project.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("idp_update", args=[self.current_project.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("idp_delete", args=[self.current_project.pk])
            ).status_code,
            404,
        )
        self.assertTrue(
            InteriorDesignProject.objects.filter(
                pk=self.current_project.pk
            ).exists()
        )

    def test_non_designer_cannot_access_project_management(self):
        customer = get_user_model().objects.create_user(
            username="customer",
            password="TestPassword123!",
        )
        UserAccount.objects.create(user=customer, profile=self.customer_profile)
        self.client.force_login(customer)

        self.assertEqual(
            self.client.get(reverse("idp_list")).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("idp_update", args=[self.current_project.pk])
            ).status_code,
            403,
        )
