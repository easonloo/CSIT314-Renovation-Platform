from django.contrib import admin

from .models import ProjectReview


@admin.register(ProjectReview)
class ProjectReviewAdmin(admin.ModelAdmin):
    list_display = ("project", "customer", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("project__title", "customer__username", "comment")
