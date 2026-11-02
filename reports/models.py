from django.conf import settings
from django.db import models

from projects.models import InteriorDesignProject

# Create your models here.


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
