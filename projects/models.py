from django.db import models

from categories.models import Category
from companies.models import Company


class InteriorDesignProject(models.Model):
    STATUS_CURRENT = "current"
    STATUS_PAST = "past"
    STATUS_CHOICES = [
        (STATUS_CURRENT, "Current"),
        (STATUS_PAST, "Past"),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    location = models.CharField(max_length=200, blank=True, default="")
    style = models.CharField(max_length=100, blank=True, default="")
    image = models.ImageField(upload_to="idp_images/", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CURRENT,
    )
    view_count = models.PositiveIntegerField(default=0)
    shortlist_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    @property
    def display_image(self):
        if self.image and self.image.name:
            return self.image
        return None

    def __str__(self):
        return self.title
