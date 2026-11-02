from datetime import datetime, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from favourites.models import Favourite
from projects.models import InteriorDesignProject

from .models import ProjectView
from .views import report

# Create your tests here.


class PlatformManagerReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager_profile = UserProfile.objects.create(
            name="Platform Management"
        )
        cls.manager = get_user_model().objects.create_user(
            username="report_manager",
            password="ManagerPass123!",
        )
        UserAccount.objects.create(user=cls.manager, profile=cls.manager_profile)
        cls.activity_profile = UserProfile.objects.create(name="Customer")
        cls.today_viewer = get_user_model().objects.create_user(
            username="today_viewer"
        )
        cls.sunday_viewer = get_user_model().objects.create_user(
            username="sunday_viewer"
        )
        cls.october_viewer = get_user_model().objects.create_user(
            username="october_viewer"
        )
        cls.designer = get_user_model().objects.create_user(
            username="report_designer"
        )
        for user in (
            cls.today_viewer,
            cls.sunday_viewer,
            cls.october_viewer,
        ):
            UserAccount.objects.create(user=user, profile=cls.activity_profile)

        cls.company = Company.objects.create(
            user=cls.designer,
            name="Report Studio",
        )
        cls.category = Category.objects.create(name="Report Category")
        cls.projects = [
            InteriorDesignProject.objects.create(
                company=cls.company,
                category=cls.category,
                title=f"Report Project {index}",
            )
            for index in range(1, 5)
        ]

    def setUp(self):
        self.request_factory = RequestFactory()

    def test_daily_weekly_and_monthly_report_metrics_use_their_period(self):
        today = datetime(2026, 11, 2).date()
        dates = {
            "today": today,
            "sunday": datetime(2026, 11, 1).date(),
            "week_end": datetime(2026, 11, 8).date(),
            "october": datetime(2026, 10, 30).date(),
        }

        for user in (
            self.today_viewer,
            self.sunday_viewer,
            self.october_viewer,
            self.designer,
            self.manager,
        ):
            get_user_model().objects.filter(pk=user.pk).update(
                date_joined=timezone.make_aware(
                    datetime.combine(datetime(2025, 1, 1).date(), time.min)
                )
            )

        new_user = get_user_model().objects.create_user(username="new_this_month")
        get_user_model().objects.filter(pk=new_user.pk).update(
            date_joined=timezone.make_aware(datetime.combine(today, time.min))
        )

        viewers = {
            "today": self.today_viewer,
            "sunday": self.sunday_viewer,
            "week_end": self.sunday_viewer,
            "october": self.october_viewer,
        }
        for project, (period_name, date) in zip(
            self.projects,
            dates.items(),
        ):
            timestamp = timezone.make_aware(datetime.combine(date, time(12)))
            InteriorDesignProject.objects.filter(pk=project.pk).update(
                created_at=timestamp
            )
            ProjectView.objects.create(
                project=project,
                viewer=viewers[period_name],
            )
            ProjectView.objects.filter(project=project).update(viewed_at=timestamp)
            Favourite.objects.create(
                user=viewers[period_name],
                project=project,
            )
            Favourite.objects.filter(project=project).update(created_at=timestamp)

        expected = {
            "daily": {"new_users": 1, "views": 1, "shortlists": 1, "new_projects": 1, "active_users": 1},
            "weekly": {"new_users": 1, "views": 2, "shortlists": 2, "new_projects": 2, "active_users": 2},
            "monthly": {"new_users": 1, "views": 3, "shortlists": 3, "new_projects": 3, "active_users": 2},
        }

        for period, metrics in expected.items():
            with self.subTest(period=period):
                request = self.request_factory.get(f"/reports/{period}/")
                request.user = self.manager
                with patch("reports.views.timezone.localdate", return_value=today):
                    with patch("reports.views.render") as render_mock:
                        report(request, period)
                report_context = render_mock.call_args.args[2]["report"]
                for metric, value in metrics.items():
                    self.assertEqual(report_context[metric], value)

    def test_non_platform_manager_cannot_view_reports(self):
        request = self.request_factory.get("/reports/daily/")
        request.user = self.today_viewer

        with self.assertRaises(PermissionDenied):
            report(request, "daily")
