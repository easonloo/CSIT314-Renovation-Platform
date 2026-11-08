"""Category use-case controls; category entities own database operations."""

from .models import Category


class CreateIDPCategoryController:
    """User story 41: create an IDP category."""

    def create_category(self, *, name, description):
        return Category.create_category(name=name, description=description)


class ViewIDPCategoryController:
    """User story 42: retrieve one category."""

    def get_category(self, pk):
        return Category.find_category(pk)


class UpdateIDPCategoryController:
    """User story 43: update an IDP category."""

    def update_category(self, category, *, name, description):
        return category.update_details(name=name, description=description)


class DeleteIDPCategoryController:
    """User story 44: delete an IDP category."""

    def delete_category(self, category):
        category.delete_category()


class SearchIDPCategoriesController:
    """User story 45: list and search IDP categories."""

    def list_categories(self, search_term=""):
        return Category.search_categories(search_term)


class CategoryController:
    """Compatibility entry points for existing callers."""

    @staticmethod
    def list_categories(search_term=""):
        return SearchIDPCategoriesController().list_categories(search_term)

    @staticmethod
    def get_category(pk):
        return ViewIDPCategoryController().get_category(pk)

    @staticmethod
    def create_category(*, name, description):
        return CreateIDPCategoryController().create_category(name=name, description=description)

    @staticmethod
    def update_category(category, *, name, description):
        return UpdateIDPCategoryController().update_category(
            category, name=name, description=description,
        )

    @staticmethod
    def delete_category(category):
        return DeleteIDPCategoryController().delete_category(category)
