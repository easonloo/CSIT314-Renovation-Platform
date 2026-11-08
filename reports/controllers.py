from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import ProjectView


class InvalidReportPeriod(ValueError):
    pass


def report_period_dates(period, today):
    if period == "daily":
        return today, today + timedelta(days=1)
    if period == "weekly":
        start_date = today - timedelta(days=today.weekday())
        return start_date, start_date + timedelta(days=7)
    if period == "monthly":
        start_date = today.replace(day=1)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
        return start_date, end_date
    raise InvalidReportPeriod("Report period not found.")


class _GenerateReportController:
    """Coordinate report dates; the ProjectView entity reads activity metrics."""

    period = None

    def get_report_data(self):
        start_date, end_date = report_period_dates(self.period, timezone.localdate())
        start_datetime = timezone.make_aware(
            datetime.combine(start_date, time.min)
        )
        end_datetime = timezone.make_aware(
            datetime.combine(end_date, time.min)
        )
        return {
            "period": self.period,
            "start_date": start_date,
            "end_date": end_date - timedelta(days=1),
            **ProjectView.platform_metrics(start_datetime, end_datetime),
        }


class GenerateDailyReportController(_GenerateReportController):
    """User story 46: generate the current day's platform report."""

    period = "daily"


class GenerateWeeklyReportController(_GenerateReportController):
    """User story 47: generate the current calendar week's report."""

    period = "weekly"


class GenerateMonthlyReportController(_GenerateReportController):
    """User story 48: generate the current calendar month's report."""

    period = "monthly"


def get_report_controller(period):
    """Select and instantiate the control for the requested report use case."""
    controllers = {
        "daily": GenerateDailyReportController,
        "weekly": GenerateWeeklyReportController,
        "monthly": GenerateMonthlyReportController,
    }
    try:
        return controllers[period]()
    except KeyError as error:
        raise InvalidReportPeriod("Report period not found.") from error


class ReportController:
    """Compatibility entry points for existing report consumers."""

    @staticmethod
    def get_period_dates(period, today):
        return report_period_dates(period, today)

    @staticmethod
    def get_report_data(period):
        return get_report_controller(period).get_report_data()
