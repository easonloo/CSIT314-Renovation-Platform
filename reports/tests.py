from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile


class ReportPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        profile = UserProfile.objects.create(name="Platform Management")
        cls.user = get_user_model().objects.create_user(
            username="report_manager",
            password="ReportManager2026!",
        )
        UserAccount.objects.create(user=cls.user, profile=profile)

    def test_report_page_renders_period_tabs_and_activity_summary(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("report", args=["daily"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Daily Report")
        self.assertContains(response, "Activity summary")
        self.assertContains(response, 'aria-current="page">Daily</a>')
        self.assertContains(response, reverse("report", args=["weekly"]))
        self.assertContains(response, reverse("report", args=["monthly"]))
        self.assertContains(response, "Active users")
        self.assertContains(response, "Total IDPs")
        self.assertContains(response, "Favourite saves")
