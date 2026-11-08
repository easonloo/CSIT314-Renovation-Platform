from django.db import transaction
from django.db.models import Count, F, Q
from django.db.models.functions import Greatest

from projects.models import InteriorDesignProject

from .models import Favourite


class FavouriteController:
    @staticmethod
    def is_saved(user, project_id):
        return Favourite.objects.filter(user=user, project_id=project_id).exists()

    @staticmethod
    @transaction.atomic
    def toggle(user, project_id):
        project = InteriorDesignProject.objects.select_for_update().get(pk=project_id)
        favourite = Favourite.objects.filter(user=user, project=project).first()
        if favourite is not None:
            favourite.delete()
            InteriorDesignProject.objects.filter(pk=project.pk).update(
                shortlist_count=Greatest(F("shortlist_count") - 1, 0),
            )
            return False

        Favourite.objects.create(user=user, project=project)
        InteriorDesignProject.objects.filter(pk=project.pk).update(
            shortlist_count=F("shortlist_count") + 1,
        )
        return True

    @staticmethod
    def get_list_data(user, *, search_term="", category_filter="", sort_order="newest"):
        search_term = (search_term or "").strip()
        category_filter = str(category_filter or "").strip()
        sort_order = (sort_order or "newest").strip()
        if sort_order not in {"newest", "oldest"}:
            sort_order = "newest"

        favourites = Favourite.objects.filter(user=user).select_related(
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
