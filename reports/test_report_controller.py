from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from companies.models import Company
from favourites.models import Favourite
from projects.models import InteriorDesignProject

from .controllers import InvalidReportPeriod, ReportController
from .models import ProjectView


class ReportControllerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.viewer = User.objects.create_user(username="report_boundary_viewer")
        cls.other_viewer = User.objects.create_user(username="report_boundary_other")
        designer = User.objects.create_user(username="report_boundary_designer")
        cls.company = Company.objects.create(user=designer, name="Boundary Studio")
        User.objects.all().update(
            date_joined=timezone.make_aware(datetime(2000, 1, 1)),
        )

    def create_activity(self, user, at):
        project = InteriorDesignProject.objects.create(
            company=self.company, title=f"Activity at {at.isoformat()}",
        )
        InteriorDesignProject.objects.filter(pk=project.pk).update(created_at=at)
        event = ProjectView.objects.create(project=project, viewer=user)
        ProjectView.objects.filter(pk=event.pk).update(viewed_at=at)
        favourite = Favourite.objects.create(project=project, user=user)
        Favourite.objects.filter(pk=favourite.pk).update(created_at=at)

    def test_report_periods_cover_calendar_and_year_boundaries(self):
        cases = [
            ("daily", date(2026, 11, 2), date(2026, 11, 2), date(2026, 11, 3)),
            ("weekly", date(2026, 11, 1), date(2026, 10, 26), date(2026, 11, 2)),
            ("monthly", date(2024, 2, 29), date(2024, 2, 1), date(2024, 3, 1)),
            ("monthly", date(2026, 12, 31), date(2026, 12, 1), date(2027, 1, 1)),
        ]
        for period, today, expected_start, expected_end in cases:
            with self.subTest(period=period, today=today):
                with patch("reports.controllers.timezone.localdate", return_value=today):
                    data = ReportController.get_report_data(period)
                self.assertEqual(data["start_date"], expected_start)
                self.assertEqual(data["end_date"], expected_end - timedelta(days=1))
                self.assertEqual(data["period"], period)

    def test_daily_metrics_include_start_but_exclude_next_midnight(self):
        today = date(2026, 11, 2)
        with timezone.override("Asia/Singapore"):
            start = timezone.make_aware(datetime.combine(today, time.min))
            end = start + timedelta(days=1)
            for at in [
                start - timedelta(microseconds=1),
                start,
                end - timedelta(microseconds=1),
                end,
            ]:
                self.create_activity(self.viewer, at)
            get_user_model().objects.filter(pk=self.viewer.pk).update(date_joined=start)
            get_user_model().objects.filter(pk=self.other_viewer.pk).update(date_joined=end)

            with patch("reports.controllers.timezone.localdate", return_value=today):
                data = ReportController.get_report_data("daily")

        for metric in ["views", "shortlists", "new_projects"]:
            with self.subTest(metric=metric):
                self.assertEqual(data[metric], 2)
        self.assertEqual(data["new_users"], 1)
        self.assertEqual(data["active_users"], 1)
        self.assertEqual(data["total_projects"], 4)

    def test_active_users_deduplicate_activity_and_exclude_disabled_accounts(self):
        today = date(2026, 11, 2)
        at = timezone.make_aware(datetime.combine(today, time(12)))
        self.create_activity(self.viewer, at)
        self.create_activity(self.viewer, at)
        self.create_activity(self.other_viewer, at)
        get_user_model().objects.filter(pk=self.other_viewer.pk).update(is_active=False)

        with patch("reports.controllers.timezone.localdate", return_value=today):
            data = ReportController.get_report_data("daily")

        self.assertEqual(data["views"], 3)
        self.assertEqual(data["shortlists"], 3)
        self.assertEqual(data["active_users"], 1)

    def test_invalid_period_raises_a_control_layer_error(self):
        with self.assertRaises(InvalidReportPeriod):
            ReportController.get_report_data("yearly")
