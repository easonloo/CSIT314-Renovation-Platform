from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from accounts.decorators import platform_manager_required
from projects.models import InteriorDesignProject


@login_required
@platform_manager_required
@require_http_methods(["GET"])
def report(request, period="daily"):
    report_data = {
        "period": period,
        "new_users": get_user_model().objects.filter(is_active=True).count(),
        "views": InteriorDesignProject.objects.aggregate(total_views=models.Sum("view_count"))["total_views"] or 0,
        "shortlists": InteriorDesignProject.objects.aggregate(total_shortlists=models.Sum("shortlist_count"))["total_shortlists"] or 0,
        "new_projects": InteriorDesignProject.objects.count(),
        "active_users": get_user_model().objects.filter(is_active=True).count(),
        "total_projects": InteriorDesignProject.objects.count(),
    }
    return render(request, "reports/report.html", {"report": report_data})
