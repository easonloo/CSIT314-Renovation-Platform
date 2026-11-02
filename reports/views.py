from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.decorators import platform_manager_required
from favourites.models import Favourite
from projects.models import InteriorDesignProject
from .models import ProjectView


@platform_manager_required
@require_http_methods(["GET"])
def report(request, period="daily"):
    today = timezone.localdate()
    if period == "daily":
        start_date = today
        end_date = today + timedelta(days=1)
    elif period == "weekly":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=7)
    elif period == "monthly":
        start_date = today.replace(day=1)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
    else:
        raise Http404("Report period not found.")

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

    report_data = {
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
    return render(
        request,
        "reports/report.html",
        {"report": report_data, "period": period},
    )
