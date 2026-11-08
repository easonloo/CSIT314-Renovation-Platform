from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from categories.models import Category
from companies.models import Company
from favourites.models import Favourite
from projects.models import InteriorDesignProject
from reviews.models import ProjectReview

from .models import UserAccount, UserProfile


class PlatformWorkflowTests(TestCase):
    password = "WorkflowPass!9387"

    @classmethod
    def setUpTestData(cls):
        profile = UserProfile.objects.create(name="User Admin")
        cls.admin = get_user_model().objects.create_user(username="workflow_admin")
        UserAccount.objects.create(user=cls.admin, profile=profile)

    def create_role_and_account(self, role, username):
        response = self.client.post(
            reverse("profile_create"), {"name": role, "description": f"{role} profile"},
        )
        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.get(name=role)
        response = self.client.post(
            reverse("account_create"),
            {
                "username": username,
                "first_name": "Workflow",
                "last_name": role.split()[0],
                "email": f"{username}@example.com",
                "profile": profile.pk,
                "password1": self.password,
                "password2": self.password,
            },
        )
        self.assertRedirects(response, reverse("account_list"), fetch_redirect_response=False)
        client = Client()
        response = client.post(
            reverse("login"), {"username": username, "password": self.password},
        )
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        return profile, client

    def test_all_four_roles_can_complete_a_connected_project_workflow(self):
        self.client.force_login(self.admin)
        _, designer = self.create_role_and_account("Interior Designer", "workflow_designer")
        customer_profile, customer = self.create_role_and_account("Customer", "workflow_customer")
        _, manager = self.create_role_and_account("Platform Management", "workflow_manager")
        response = self.client.get(reverse("account_list"), {"q": "workflow_customer"})
        self.assertEqual(response.context["filtered_count"], 1)

        response = manager.post(
            reverse("category_create"), {"name": "Workflow Living", "description": "Living spaces"},
        )
        self.assertEqual(response.status_code, 302)
        category = Category.objects.get(name="Workflow Living")
        response = designer.post(
            reverse("company_create"),
            {"name": "Workflow Studio", "description": "Workflow renovation designs"},
        )
        self.assertRedirects(response, reverse("company_detail"), fetch_redirect_response=False)
        response = designer.get(reverse("company_search"), {"q": "renovation"})
        self.assertEqual(response.context["results"], [("Description", "Workflow renovation designs")])

        project_data = {
            "title": "Workflow Apartment",
            "description": "A connected renovation project",
            "category": category.pk,
            "location": "Singapore",
            "style": "Scandinavian",
            "status": "current",
        }
        response = designer.post(reverse("idp_create"), project_data)
        self.assertEqual(response.status_code, 302)
        project = InteriorDesignProject.objects.get(title=project_data["title"])
        response = designer.post(
            reverse("idp_update", args=[project.pk]), {**project_data, "status": "past"},
        )
        self.assertEqual(response.status_code, 302)
        response = designer.get(reverse("idp_list"), {"status": "past", "q": "Apartment"})
        self.assertEqual(list(response.context["projects"]), [project])

        response = customer.get(reverse("customer_idp_search"), {"q": "Scandinavian"})
        self.assertEqual(list(response.context["projects"]), [project])
        self.assertEqual(customer.get(reverse("idp_detail", args=[project.pk])).status_code, 200)
        response = customer.post(
            reverse("review_create", args=[project.pk]), {"rating": 5, "comment": "Excellent design"},
        )
        self.assertEqual(response.status_code, 302)
        response = customer.post(reverse("favourite_toggle", args=[project.pk]))
        self.assertEqual(response.status_code, 302)
        response = customer.get(reverse("favourite_list"), {"q": "Scandinavian"})
        self.assertEqual(response.context["filtered_count"], 1)
        response = customer.get(reverse("dashboard"))
        self.assertEqual(response.context["favourite_count"], 1)
        self.assertEqual(response.context["review_count"], 1)

        response = designer.get(reverse("idp_detail", args=[project.pk]))
        self.assertEqual(response.context["project"].view_count, 1)
        self.assertEqual(response.context["project"].shortlist_count, 1)
        self.assertEqual(response.context["average_rating"], 5)
        for period in ["daily", "weekly", "monthly"]:
            with self.subTest(period=period):
                response = manager.get(reverse("report", args=[period]))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["report"]["views"], 1)
                self.assertEqual(response.context["report"]["shortlists"], 1)
                self.assertEqual(response.context["report"]["total_projects"], 1)
                response = manager.get(reverse("report_download", args=[period]))
                self.assertEqual(response["Content-Type"], "application/pdf")
                self.assertTrue(response.content.startswith(b"%PDF-1.4"))

        response = self.client.post(reverse("profile_suspend", args=[customer_profile.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(customer.post(reverse("favourite_toggle", args=[project.pk])).status_code, 403)
        self.assertEqual(Favourite.objects.count(), 1)
        response = self.client.post(reverse("profile_reactivate", args=[customer_profile.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(customer.get(reverse("favourite_list")).status_code, 200)

        response = customer.post(reverse("favourite_toggle", args=[project.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Favourite.objects.count(), 0)
        project.refresh_from_db()
        self.assertEqual(project.shortlist_count, 0)
        review = ProjectReview.objects.get(project=project)
        self.assertEqual(customer.post(reverse("review_delete", args=[review.pk])).status_code, 302)
        self.assertEqual(designer.post(reverse("idp_delete", args=[project.pk])).status_code, 302)
        self.assertEqual(designer.post(reverse("company_delete")).status_code, 302)
        self.assertEqual(manager.post(reverse("category_delete", args=[category.pk])).status_code, 302)
        self.assertFalse(InteriorDesignProject.objects.exists())
        self.assertFalse(Company.objects.exists())
        self.assertFalse(ProjectReview.objects.exists())
        self.assertFalse(Category.objects.exists())
