from django.db.models import Q

from .models import Category


class CategoryController:
    @staticmethod
    def list_categories(search_term=""):
        categories = Category.objects.all()
        search_term = (search_term or "").strip()
        if search_term:
            categories = categories.filter(
                Q(name__icontains=search_term)
                | Q(description__icontains=search_term)
            )
        return categories

    @staticmethod
    def get_category(pk):
        return Category.objects.filter(pk=pk).first()

    @staticmethod
    def create_category(*, name, description):
        return Category.objects.create(name=name, description=description)

    @staticmethod
    def update_category(category, *, name, description):
        category.name = name
        category.description = description
        category.save()
        return category

    @staticmethod
    def delete_category(category):
        category.delete()
