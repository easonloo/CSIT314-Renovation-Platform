from django.contrib import admin

from .models import ProjectView

# Register your models here.


@admin.register(ProjectView)
class ProjectViewAdmin(admin.ModelAdmin):
    list_display = ("project", "viewer", "viewed_at")
    list_filter = ("viewed_at",)
    search_fields = ("project__title", "viewer__username")