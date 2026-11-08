from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile
from favourites.models import Favourite
from projects.models import InteriorDesignProject
from reports.models import ProjectView
from reviews.models import ProjectReview

from .models import Company


class CompanyManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        designer_profile = UserProfile.objects.create(name="Interior Designer")
        cls.designer = get_user_model().objects.create_user(username="company_management_id")
        cls.other_designer = get_user_model().objects.create_user(username="company_management_other")
        for user in [cls.designer, cls.other_designer]:
            UserAccount.objects.create(user=user, profile=designer_profile)
        cls.other_company = Company.objects.create(
            user=cls.other_designer, name="Other Studio",
        )

    def setUp(self):
        self.client.force_login(self.designer)
        self.data = {
            "name": "  My Studio  ",
            "email": "  studio@example.com  ",
            "phone": "  +65 6123 4567  ",
            "website": "  https://studio.example.com  ",
            "address": "  18 Example Road  ",
            "description": "  Designs for every home 家  ",
        }

    def test_create_and_update_preserve_all_company_fields(self):
        response = self.client.post(reverse("company_create"), self.data)
        self.assertRedirects(response, reverse("company_detail"))
        company = Company.objects.get(user=self.designer)
        for field, value in self.data.items():
            self.assertEqual(getattr(company, field), value.strip())

        initial_timestamp = company.updated_at
        changed = {
            "name": "  Updated Studio  ",
            "email": "  updated@example.com  ",
            "phone": "  +65 6999 8888  ",
            "website": "  https://updated.example.com  ",
            "address": "  28 Updated Road  ",
            "description": "  Updated designs for every home 家  ",
        }
        response = self.client.post(reverse("company_update"), changed)
        self.assertRedirects(response, reverse("company_detail"))
        company.refresh_from_db()
        for field, value in changed.items():
            self.assertEqual(getattr(company, field), value.strip())
        self.assertGreater(company.updated_at, initial_timestamp)
        self.assertEqual(company.user_id, self.designer.pk)

    def test_empty_name_does_not_create_a_company(self):
        response = self.client.post(reverse("company_create"), {"name": "   "})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Company.objects.filter(user=self.designer).exists())

    def test_creating_again_keeps_the_existing_company(self):
        company = Company.objects.create(user=self.designer, name="Original Studio")

        response = self.client.post(reverse("company_create"), self.data)

        self.assertRedirects(response, reverse("company_detail"))
        company.refresh_from_db()
        self.assertEqual(company.name, "Original Studio")
        self.assertEqual(Company.objects.filter(user=self.designer).count(), 1)

    def test_update_can_clear_optional_fields(self):
        self.client.post(reverse("company_create"), self.data)

        response = self.client.post(reverse("company_update"), {"name": "Minimal Studio"})

        self.assertRedirects(response, reverse("company_detail"))
        company = Company.objects.get(user=self.designer)
        self.assertEqual(company.name, "Minimal Studio")
        for field in ("email", "phone", "website", "address", "description"):
            self.assertEqual(getattr(company, field), "")

    def test_create_uses_logged_in_designer_instead_of_posted_owner(self):
        response = self.client.post(
            reverse("company_create"),
            {**self.data, "user_id": self.other_designer.pk, "company_id": self.other_company.pk},
        )

        self.assertRedirects(response, reverse("company_detail"))
        self.assertEqual(Company.objects.get(user=self.designer).name, "My Studio")
        self.other_company.refresh_from_db()
        self.assertEqual(self.other_company.name, "Other Studio")

    def test_delete_removes_owned_projects_and_their_related_records(self):
        company = Company.objects.create(user=self.designer, name="My Studio")
        project = InteriorDesignProject.objects.create(company=company, title="My Project")
        customer = get_user_model().objects.create_user(username="company_cascade_customer")
        Favourite.objects.create(user=customer, project=project)
        ProjectView.objects.create(viewer=customer, project=project)
        ProjectReview.objects.create(customer=customer, project=project, rating=4)
        other_project = InteriorDesignProject.objects.create(
            company=self.other_company, title="Keep This Project",
        )

        response = self.client.post(reverse("company_delete"))

        self.assertRedirects(response, reverse("company_detail"))
        self.assertFalse(InteriorDesignProject.objects.filter(pk=project.pk).exists())
        self.assertFalse(Favourite.objects.filter(project_id=project.pk).exists())
        self.assertFalse(ProjectView.objects.filter(project_id=project.pk).exists())
        self.assertFalse(ProjectReview.objects.filter(project_id=project.pk).exists())
        self.assertTrue(InteriorDesignProject.objects.filter(pk=other_project.pk).exists())
