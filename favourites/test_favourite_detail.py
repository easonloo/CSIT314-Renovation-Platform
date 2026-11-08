from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile
from companies.models import Company
from projects.models import InteriorDesignProject
from reports.models import ProjectView

from .models import Favourite


class FavouriteDetailTests(TestCase):
    """Story 36 uses the customer's own saved collection before opening an IDP."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        designer_profile = UserProfile.objects.create(name="Interior Designer")
        cls.customer = User.objects.create_user(username="saved_detail_customer")
        cls.other_customer = User.objects.create_user(username="saved_detail_other")
        cls.designer = User.objects.create_user(username="saved_detail_designer")
        UserAccount.objects.create(user=cls.customer, profile=cls.customer_profile)
        UserAccount.objects.create(user=cls.other_customer, profile=cls.customer_profile)
        UserAccount.objects.create(user=cls.designer, profile=designer_profile)
        company = Company.objects.create(user=cls.designer, name="Saved Detail Studio")
        cls.project = InteriorDesignProject.objects.create(company=company, title="Saved Kitchen")
        Favourite.objects.create(user=cls.customer, project=cls.project)

    def setUp(self):
        self.client.force_login(self.customer)
        self.url = reverse("favourite_detail", args=[self.project.pk])

    def test_collection_links_to_saved_detail_and_records_one_view_when_opened(self):
        collection = self.client.get(reverse("favourite_list"))
        self.assertContains(collection, f'href="{self.url}"')
        self.assertFalse(ProjectView.objects.exists())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/idp_detail.html")
        self.assertEqual(response.context["project"], self.project)
        self.assertTrue(response.context["is_favourited"])
        self.assertEqual(response.context["view_count"], 1)
        self.assertEqual(ProjectView.objects.filter(project=self.project, viewer=self.customer).count(), 1)
        self.project.refresh_from_db()
        self.assertEqual(self.project.view_count, 1)

    def test_other_customers_saved_project_cannot_be_opened_through_own_collection(self):
        self.client.force_login(self.other_customer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ProjectView.objects.exists())
        self.assertEqual(Favourite.objects.count(), 1)
        # Public discovery keeps its existing behaviour.
        self.assertEqual(self.client.get(reverse("idp_detail", args=[self.project.pk])).status_code, 200)

    def test_removed_project_is_not_available_through_saved_detail(self):
        Favourite.objects.filter(user=self.customer, project=self.project).delete()

        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertFalse(ProjectView.objects.exists())

    def test_suspended_existing_session_and_designer_cannot_open_customer_collection(self):
        UserProfile.objects.filter(pk=self.customer_profile.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(self.designer)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertFalse(ProjectView.objects.exists())
