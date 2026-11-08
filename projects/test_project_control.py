from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from reports.models import ProjectView
from reviews.models import ProjectReview

from .controllers import ProjectController
from .models import InteriorDesignProject


class ProjectControlRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        cls.customer = User.objects.create_user(username="project_control_customer")
        UserAccount.objects.create(user=cls.customer, profile=cls.customer_profile)
        cls.non_customer_users = []
        for index, role in enumerate(["Interior Designer", "User Admin", "Platform Management"]):
            profile = UserProfile.objects.create(name=role)
            user = User.objects.create_user(username=f"project_control_role_{index}")
            UserAccount.objects.create(user=user, profile=profile)
            cls.non_customer_users.append(user)
            if role == "Interior Designer":
                cls.designer = user
        cls.company = Company.objects.create(user=cls.designer, name="Project Control Studio")
        cls.category = Category.objects.create(name="Project Control Category")
        cls.project = InteriorDesignProject.objects.create(
            company=cls.company,
            category=cls.category,
            title="Project Control Loft",
            style="Scandinavian",
        )

    def project_data(self, **overrides):
        data = {
            "title": "Updated Loft",
            "description": "Project description",
            "category": self.category.pk,
            "location": "Singapore",
            "style": "Scandinavian",
            "status": InteriorDesignProject.STATUS_CURRENT,
        }
        data.update(overrides)
        return data

    @staticmethod
    def image_upload(name):
        buffer = BytesIO()
        Image.new("RGB", (2, 2), color="blue").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    def test_project_image_can_be_uploaded_kept_replaced_and_cleared(self):
        self.client.force_login(self.designer)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse("idp_create"),
                self.project_data(title="Uploaded Project", image=self.image_upload("first.png")),
            )
            project = InteriorDesignProject.objects.get(title="Uploaded Project")
            self.assertEqual(response.status_code, 302)
            first_name = project.image.name
            self.assertTrue(Path(project.image.path).is_file())
            update_url = reverse("idp_update", args=[project.pk])

            response = self.client.post(update_url, self.project_data())
            self.assertEqual(response.status_code, 302)
            project.refresh_from_db()
            self.assertEqual(project.image.name, first_name)

            response = self.client.post(
                update_url, self.project_data(image=self.image_upload("replacement.png")),
            )
            self.assertEqual(response.status_code, 302)
            project.refresh_from_db()
            self.assertNotEqual(project.image.name, first_name)
            self.assertTrue(Path(project.image.path).is_file())

            response = self.client.post(update_url, self.project_data(**{"image-clear": "on"}))
            self.assertEqual(response.status_code, 302)
            project.refresh_from_db()
            self.assertFalse(project.image)
            self.assertIsNone(project.display_image)

    def test_project_update_cannot_overwrite_owner_or_interest_counts(self):
        self.client.force_login(self.designer)
        InteriorDesignProject.objects.filter(pk=self.project.pk).update(view_count=12, shortlist_count=6)
        response = self.client.post(
            reverse("idp_update", args=[self.project.pk]),
            self.project_data(category="", company=9999, view_count=9999, shortlist_count=9999),
        )
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.company, self.company)
        self.assertIsNone(self.project.category)
        self.assertEqual(self.project.view_count, 12)
        self.assertEqual(self.project.shortlist_count, 6)

    def test_invalid_project_form_does_not_persist_partial_changes(self):
        self.client.force_login(self.designer)
        response = self.client.post(
            reverse("idp_update", args=[self.project.pk]), self.project_data(title=""),
        )
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Project Control Loft")

    def test_suspended_profile_blocks_existing_search_and_detail_session(self):
        self.client.force_login(self.customer)
        search_url = reverse("customer_idp_search")
        detail_url = reverse("idp_detail", args=[self.project.pk])
        self.assertEqual(self.client.get(search_url).status_code, 200)
        self.assertEqual(self.client.get(detail_url).status_code, 200)
        UserProfile.objects.filter(pk=self.customer_profile.pk).update(is_active=False)

        self.assertEqual(self.client.get(search_url).status_code, 403)
        self.assertEqual(self.client.get(detail_url).status_code, 403)
        self.project.refresh_from_db()
        self.assertEqual(self.project.view_count, 1)
        self.assertEqual(ProjectView.objects.filter(project=self.project).count(), 1)

    def test_search_keeps_access_for_each_active_non_customer_role(self):
        for user in self.non_customer_users:
            with self.subTest(username=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse("customer_idp_search"))
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context["can_favourite"])
                self.assertFalse(response.context["can_review"])
                self.assertContains(response, self.project.title)

    def test_search_combines_style_category_and_rating_or_creation_sort(self):
        self.client.force_login(self.customer)
        other = InteriorDesignProject.objects.create(
            company=self.company, category=self.category, title="Newer Loft", style="Scandinavian",
        )
        InteriorDesignProject.objects.filter(pk=self.project.pk).update(
            created_at=timezone.now() - timedelta(days=2),
        )
        ProjectReview.objects.create(customer=self.customer, project=self.project, rating=5)
        ProjectReview.objects.create(customer=self.customer, project=other, rating=3)
        for sort, expected in [
            ("rating", [self.project, other]),
            ("recommended", [self.project, other]),
            ("newest", [other, self.project]),
        ]:
            with self.subTest(sort=sort):
                response = self.client.get(
                    reverse("customer_idp_search"),
                    {"q": "  SCANDINAVIAN  ", "category": self.category.pk, "sort": sort},
                )
                self.assertEqual(list(response.context["projects"]), expected)
                self.assertEqual(response.context["q"], "SCANDINAVIAN")
                self.assertEqual(response.context["selected_category"], str(self.category.pk))

    def test_owner_detail_does_not_record_a_customer_view(self):
        self.client.force_login(self.designer)
        response = self.client.get(reverse("idp_detail", args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project"].view_count, 0)
        self.assertFalse(ProjectView.objects.exists())

    def test_recording_a_view_rolls_back_if_counter_update_fails(self):
        self.client.force_login(self.customer)
        with patch(
            "projects.controllers.InteriorDesignProject.objects.filter",
            side_effect=IntegrityError("Counter update failed"),
        ):
            with self.assertRaises(IntegrityError):
                self.client.get(reverse("idp_detail", args=[self.project.pk]))
        self.assertFalse(ProjectView.objects.exists())
        self.project.refresh_from_db()
        self.assertEqual(self.project.view_count, 0)

    def test_controller_cannot_update_or_delete_another_designers_project(self):
        other_designer = get_user_model().objects.create_user(username="other_project_controller")
        with self.assertRaises(InteriorDesignProject.DoesNotExist):
            ProjectController.update_project(other_designer, self.project.pk, title="Changed")
        with self.assertRaises(InteriorDesignProject.DoesNotExist):
            ProjectController.delete_project(other_designer, self.project.pk)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Project Control Loft")
