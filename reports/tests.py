from datetime import datetime, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from favourites.models import Favourite
from projects.models import InteriorDesignProject

from .models import ProjectView
from .views import _create_report_pdf, report, report_download

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
        self.client.force_login(self.manager)

    def test_report_page_renders_period_tabs_and_activity_summary(self):
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
        self.assertContains(response, "Download Monthly PDF")
        self.assertContains(response, "Download Weekly PDF")

    def test_pdf_download_contains_report_period_metrics_and_timestamp(self):
        response = self.client.get("/reports/daily/download/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-1.4"))
        self.assertIn(b"Daily Platform Report", response.content)
        self.assertIn(b"Report dates:", response.content)
        self.assertIn(b"Generated:", response.content)
        self.assertIn(b"New users:", response.content)
        self.assertIn(b"IDP views:", response.content)
        self.assertIn(b"Shortlists:", response.content)
        self.assertIn(b"New projects:", response.content)
        self.assertIn(b"Active users:", response.content)
        self.assertIn(b"Total IDPs:", response.content)

    def test_weekly_pdf_download_has_weekly_filename_and_content(self):
        response = self.client.get("/reports/weekly/download/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("platform-weekly-report-", response["Content-Disposition"])
        self.assertIn(b"Weekly Platform Report", response.content)
        self.assertIn(b"Report dates:", response.content)
        self.assertIn(b"Generated:", response.content)

    def test_pdf_builder_escapes_pdf_text_delimiters(self):
        pdf = _create_report_pdf(["Report (draft)"])

        self.assertIn(b"(Report \\(draft\\)) Tj", pdf)

    def test_non_platform_manager_cannot_download_reports(self):
        request = self.request_factory.get("/reports/daily/download/")
        request.user = self.today_viewer

        with self.assertRaises(PermissionDenied):
            report_download(request, "daily")

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
                with patch("reports.controllers.timezone.localdate", return_value=today):
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

    def test_unknown_period_is_not_found_for_html_and_pdf(self):
        for name in ["report", "report_download"]:
            with self.subTest(view=name):
                response = self.client.get(reverse(name, args=["yearly"]))
                self.assertEqual(response.status_code, 404)
