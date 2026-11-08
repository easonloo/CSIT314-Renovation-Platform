from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from favourites.models import Favourite
from projects.models import InteriorDesignProject

from .models import ProjectView


class InvalidReportPeriod(ValueError):
    pass


class ReportController:
    @staticmethod
    def get_period_dates(period, today):
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

    @classmethod
    def get_report_data(cls, period):
        start_date, end_date = cls.get_period_dates(period, timezone.localdate())
        start_datetime = timezone.make_aware(
            datetime.combine(start_date, time.min)
        )
        end_datetime = timezone.make_aware(
            datetime.combine(end_date, time.min)
        )
        User = get_user_model()
        views = ProjectView.objects.filter(
            viewed_at__gte=start_datetime,
            viewed_at__lt=end_datetime,
        )
        favourites = Favourite.objects.filter(
            created_at__gte=start_datetime,
            created_at__lt=end_datetime,
        )
        active_user_ids = set(
            views.filter(viewer__is_active=True).values_list("viewer_id", flat=True)
        )
        active_user_ids.update(
            favourites.filter(user__is_active=True).values_list("user_id", flat=True)
        )

        return {
            "period": period,
            "start_date": start_date,
            "end_date": end_date - timedelta(days=1),
            "new_users": User.objects.filter(
                date_joined__gte=start_datetime,
                date_joined__lt=end_datetime,
            ).count(),
            "views": views.count(),
            "shortlists": favourites.count(),
            "new_projects": InteriorDesignProject.objects.filter(
                created_at__gte=start_datetime,
                created_at__lt=end_datetime,
            ).count(),
            "active_users": User.objects.filter(
                pk__in=active_user_ids,
                is_active=True,
            ).count(),
            "total_projects": InteriorDesignProject.objects.count(),
        }
