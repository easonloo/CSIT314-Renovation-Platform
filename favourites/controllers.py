"""Favourite use-case controls; Favourite encapsulates collection persistence."""
from projects.models import InteriorDesignProject

from .models import Favourite


class SaveFavouriteController:
    """Story 34: save a project; a second click removes the saved project."""
    def toggle(self, user, project_id):
        return Favourite.toggle_for(user, project_id)


class SearchFavouritesController:
    """Story 35: search, filter and order the customer's saved projects."""
    def get_list_data(self, user, *, search_term="", category_filter="", sort_order="newest"):
        search_term = (search_term or "").strip()
        category_filter = str(category_filter or "").strip()
        sort_order = (sort_order or "newest").strip()
        if sort_order not in {"newest", "oldest"}:
            sort_order = "newest"
        return Favourite.search_for(
            user, search_term=search_term, category_filter=category_filter,
            sort_order=sort_order,
        )


class ViewFavouriteIDPController:
    """Story 36: open a project that belongs to this customer's saved list."""
    def get_detail_data(self, user, project_id):
        from projects.controllers import ViewIDPController

        project = Favourite.saved_project(user, project_id)
        return ViewIDPController().get_detail_data(user, project.pk)


class FavouriteController:
    """Compatibility API for existing integrations."""
    toggle = staticmethod(SaveFavouriteController().toggle)
    get_list_data = staticmethod(SearchFavouritesController().get_list_data)

    @staticmethod
    def is_saved(user, project_id):
        return Favourite.is_saved(user, project_id)
