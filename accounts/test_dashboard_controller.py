from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from companies.models import Company
from favourites.models import Favourite
from projects.models import InteriorDesignProject
from reviews.models import ProjectReview

from .controllers import AccountAccessController, DashboardController
from .models import UserAccount, UserProfile


class DashboardControllerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        cls.designer_profile = UserProfile.objects.create(name="Interior Designer")
        cls.admin_profile = UserProfile.objects.create(name="User Admin")
        cls.customer = User.objects.create_user(username="bce_dashboard_customer")
        cls.other_customer = User.objects.create_user(username="bce_dashboard_other")
        cls.designer = User.objects.create_user(username="bce_dashboard_designer")
        cls.admin = User.objects.create_user(username="bce_dashboard_admin")
        cls.account = UserAccount.objects.create(
            user=cls.customer, profile=cls.customer_profile,
        )
        UserAccount.objects.create(user=cls.other_customer, profile=cls.customer_profile)
        UserAccount.objects.create(user=cls.designer, profile=cls.designer_profile)
        UserAccount.objects.create(user=cls.admin, profile=cls.admin_profile)
        company = Company.objects.create(user=cls.designer, name="Dashboard Studio")
        cls.current_projects = [
            InteriorDesignProject.objects.create(company=company, title=f"Current {index}")
            for index in range(4)
        ]
        cls.past_project = InteriorDesignProject.objects.create(
            company=company,
            title="Completed project",
            status=InteriorDesignProject.STATUS_PAST,
        )
        Favourite.objects.create(user=cls.customer, project=cls.current_projects[0])
        for project in cls.current_projects[1:]:
            Favourite.objects.create(user=cls.other_customer, project=project)
        cls.own_review = ProjectReview.objects.create(
            customer=cls.customer, project=cls.current_projects[0], rating=4,
        )
        cls.public_review = ProjectReview.objects.create(
            customer=cls.other_customer, project=cls.current_projects[0], rating=5,
        )

    def test_customer_dashboard_keeps_public_reviews_and_personal_saved_count(self):
        data = DashboardController.get_dashboard_data(self.customer)

        self.assertCountEqual(
            data["customer_reviews"], [self.own_review, self.public_review],
        )
        self.assertEqual(data["review_count"], 2)
        self.assertEqual(data["favourite_count"], 1)
        recommendations = list(data["recommended_projects"])
        self.assertEqual(len(recommendations), 3)
        self.assertNotIn(self.past_project, recommendations)
        self.assertTrue(all(project.status == "current" for project in recommendations))

    def test_non_customer_dashboard_keeps_customer_sections_empty(self):
        for user in [self.designer, self.admin]:
            with self.subTest(role=user.account.profile.name):
                data = DashboardController.get_dashboard_data(user)

                self.assertEqual(list(data["customer_reviews"]), [])
                self.assertEqual(list(data["recommended_projects"]), [])
                self.assertEqual(data["review_count"], 0)
                self.assertEqual(data["favourite_count"], 0)

    def test_unavailable_users_get_no_dashboard_data(self):
        User = get_user_model()
        unassigned = User.objects.create_user(username="bce_dashboard_unassigned")
        for user in [None, AnonymousUser(), User(username="unsaved"), unassigned]:
            with self.subTest(user=user):
                self.assertIsNone(DashboardController.get_dashboard_data(user))

        UserProfile.objects.filter(pk=self.customer_profile.pk).update(is_active=False)
        self.assertIsNone(DashboardController.get_dashboard_data(self.customer))
        User.objects.filter(pk=self.designer.pk).update(is_active=False)
        self.assertIsNone(DashboardController.get_dashboard_data(self.designer))

    def test_active_account_lookup_refreshes_cached_role_and_suspension(self):
        self.assertEqual(self.customer.account.profile.name, "Customer")
        UserAccount.objects.filter(pk=self.account.pk).update(profile=self.designer_profile)

        account = AccountAccessController.get_active_account(self.customer)

        self.assertEqual(account.profile.name, "Interior Designer")
        UserProfile.objects.filter(pk=self.designer_profile.pk).update(is_active=False)
        self.assertIsNone(AccountAccessController.get_active_account(self.customer))
