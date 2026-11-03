from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from projects.models import InteriorDesignProject

from .models import Favourite

# Create your tests here.


class FavouriteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        customer_profile = UserProfile.objects.create(name="Customer")
        designer_profile = UserProfile.objects.create(name="Interior Designer")
        cls.customer = get_user_model().objects.create_user(
            username="favourite_customer",
        )
        UserAccount.objects.create(user=cls.customer, profile=customer_profile)
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

    def test_saving_a_project_updates_its_shortlist_count_once(self):
        self.client.force_login(self.customer)
        url = reverse("favourite_add", args=[self.project.pk])

        first_response = self.client.post(url)
        second_response = self.client.post(url)

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(
            Favourite.objects.filter(
                user=self.customer,
                project=self.project,
            ).count(),
            1,
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.shortlist_count, 1)