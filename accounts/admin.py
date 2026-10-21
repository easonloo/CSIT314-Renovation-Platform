from django.contrib import admin

from .models import UserAccount, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name", "description")
    list_filter = ("is_active",)


@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "profile")
    search_fields = ("user__username", "user__email")
    list_filter = ("profile",)