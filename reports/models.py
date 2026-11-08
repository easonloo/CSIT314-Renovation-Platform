from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from projects.models import InteriorDesignProject

class ProjectView(models.Model):
    project = models.ForeignKey(
        InteriorDesignProject,
        on_delete=models.CASCADE,
        related_name="view_events",
    )
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_view_events",
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at"]

    def __str__(self):
        return f"{self.viewer} viewed {self.project}"

    @classmethod
    def platform_metrics(cls, start_datetime, end_datetime):
        """Read report activity for the half-open interval [start, end)."""
        from favourites.models import Favourite

        User = get_user_model()
        views = cls.objects.filter(
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
