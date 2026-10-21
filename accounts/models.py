from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account",
    )
    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        related_name="accounts",
    )

    def __str__(self):
        return self.user.get_username()