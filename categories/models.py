from django.db import models
from django.db.models import Q


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    @property
    def project_count(self):
        return self.projects.count()

    def __str__(self):
        return self.name

    @classmethod
    def search_categories(cls, search_term=""):
        categories = cls.objects.all()
        search_term = (search_term or "").strip()
        if search_term:
            categories = categories.filter(
                Q(name__icontains=search_term)
                | Q(description__icontains=search_term)
            )
        return categories

    @classmethod
    def find_category(cls, pk):
        return cls.objects.filter(pk=pk).first()

    @classmethod
    def create_category(cls, *, name, description):
        return cls.objects.create(name=name, description=description)

    def update_details(self, *, name, description):
        self.name = name
        self.description = description
        self.save()
        return self

    def delete_category(self):
        self.delete()
