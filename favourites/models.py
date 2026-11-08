from django.conf import settings
from django.db import models, transaction
from django.db.models import Count, F, Q
from django.db.models.functions import Greatest

from projects.models import InteriorDesignProject


class Favourite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favourites")
    project = models.ForeignKey(InteriorDesignProject, on_delete=models.CASCADE, related_name="favourited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "project")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} -> {self.project}"

    @classmethod
    def is_saved(cls, user, project_id):
        return cls.objects.filter(user=user, project_id=project_id).exists()

    @classmethod
    def count_for(cls, user):
        return cls.objects.filter(user=user).count()

    @classmethod
    def project_ids(cls, user):
        return cls.objects.filter(user=user).values_list("project_id", flat=True)

    @classmethod
    def saved_project(cls, user, project_id):
        return cls.objects.select_related("project").get(
            user=user, project_id=project_id,
        ).project

    @classmethod
    @transaction.atomic
    def toggle_for(cls, user, project_id):
        project = InteriorDesignProject.objects.select_for_update().get(pk=project_id)
        favourite = cls.objects.filter(user=user, project=project).first()
        if favourite is not None:
            favourite.delete()
            InteriorDesignProject.objects.filter(pk=project.pk).update(
                shortlist_count=Greatest(F("shortlist_count") - 1, 0),
            )
            return False
        cls.objects.create(user=user, project=project)
        InteriorDesignProject.objects.filter(pk=project.pk).update(
            shortlist_count=F("shortlist_count") + 1,
        )
        return True

    @classmethod
    def search_for(cls, user, *, search_term="", category_filter="", sort_order="newest"):
        favourites = cls.objects.filter(user=user).select_related(
            "project", "project__company", "project__category",
        )
        favourite_count = favourites.count()
        categories = list(
            favourites.exclude(project__category__isnull=True)
            .values("project__category_id", "project__category__name")
            .annotate(count=Count("pk"))
            .order_by("project__category__name", "project__category_id")
        )
        available_categories = {
            str(category["project__category_id"]) for category in categories
        }
        if category_filter not in available_categories:
            category_filter = ""
        if search_term:
            favourites = favourites.filter(
                Q(project__title__icontains=search_term)
                | Q(project__company__name__icontains=search_term)
                | Q(project__category__name__icontains=search_term)
                | Q(project__style__icontains=search_term)
            )
        if category_filter:
            favourites = favourites.filter(project__category_id=category_filter)
        if sort_order == "oldest":
            favourites = favourites.order_by("created_at", "pk")
        else:
            favourites = favourites.order_by("-created_at", "-pk")
        return {
            "favourites": favourites,
            "favourite_count": favourite_count,
            "filtered_count": favourites.count(),
            "categories": categories,
            "q": search_term,
            "category_filter": category_filter,
            "sort_order": sort_order,
        }
