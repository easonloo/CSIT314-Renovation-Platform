from django.db import models, transaction
from django.db.models import Avg, Count, F, Q

from categories.models import Category
from companies.models import Company


class InteriorDesignProject(models.Model):
    STATUS_CURRENT = "current"
    STATUS_PAST = "past"
    STATUS_CHOICES = [
        (STATUS_CURRENT, "Current"),
        (STATUS_PAST, "Past"),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    location = models.CharField(max_length=200, blank=True, default="")
    style = models.CharField(max_length=100, blank=True, default="")
    image = models.ImageField(upload_to="idp_images/", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CURRENT,
    )
    view_count = models.PositiveIntegerField(default=0)
    shortlist_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    @property
    def display_image(self):
        if self.image and self.image.name:
            return self.image
        return None

    @property
    def is_virtual_image(self):
        return bool(self.image and self.image.name.startswith("demo_idp_catalog/"))

    def __str__(self):
        return self.title

    @classmethod
    def empty(cls):
        return cls.objects.none()

    @classmethod
    def recommended(cls, limit=3):
        return cls.objects.filter(status=cls.STATUS_CURRENT).select_related(
            "company", "category",
        )[:limit]

    @classmethod
    def find(cls, pk):
        return cls.objects.select_related("company", "category").get(pk=pk)

    @classmethod
    def find_owned(cls, user, pk, *, status=None):
        criteria = {"pk": pk, "company__user": user}
        if status is not None:
            criteria["status"] = status
        return cls.objects.select_related("company", "category").get(**criteria)

    @classmethod
    def search_owned(cls, user, *, status="", search_term=""):
        projects = cls.objects.filter(company__user=user)
        if status:
            projects = projects.filter(status=status)
        if search_term:
            projects = projects.filter(
                Q(title__icontains=search_term)
                | Q(description__icontains=search_term)
                | Q(location__icontains=search_term)
                | Q(style__icontains=search_term)
                | Q(category__name__icontains=search_term)
            )
        return projects.select_related("category", "company")

    @classmethod
    def discover(cls, *, search_term="", category_id="", sort_order="recommended"):
        projects = cls.objects.select_related("company", "category").annotate(
            average_rating=Avg("reviews__rating"),
            review_count=Count("reviews"),
        )
        if search_term:
            projects = projects.filter(
                Q(title__icontains=search_term)
                | Q(description__icontains=search_term)
                | Q(style__icontains=search_term)
                | Q(company__name__icontains=search_term)
                | Q(category__name__icontains=search_term)
            )
        if category_id.isdecimal():
            try:
                projects = projects.filter(category_id=int(category_id))
            except ValueError:
                projects = projects.none()
        if sort_order == "rating":
            projects = projects.order_by("-average_rating", "-updated_at")
        elif sort_order == "newest":
            projects = projects.order_by("-created_at")
        else:
            projects = projects.order_by("-average_rating", "-review_count", "-updated_at")
        return {"projects": projects, "project_count": projects.count()}

    @classmethod
    def create_project(
        cls, company, *, title, description="", category=None, location="", style="",
        status=STATUS_CURRENT, image=None,
    ):
        return cls.objects.create(
            company=company, title=title, description=description, category=category,
            location=location, style=style, status=status, image=image or "",
        )

    def update_details(
        self, *, title, description="", category=None, location="", style="",
        status=STATUS_CURRENT, image=None,
    ):
        self.title = title
        self.description = description
        self.category = category
        self.location = location
        self.style = style
        self.status = status
        if image is not None:
            # ClearableFileInput uses False to clear an existing image.
            self.image = image or ""
        self.save()
        return self

    def delete_project(self):
        self.delete()

    @transaction.atomic
    def record_view(self, viewer):
        if self.company.user_id == viewer.pk:
            return
        from reports.models import ProjectView

        ProjectView.objects.create(project=self, viewer=viewer)
        type(self).objects.filter(pk=self.pk).update(view_count=F("view_count") + 1)
        self.view_count += 1

    def number_of_views(self):
        return self.view_count

    def number_of_shortlists(self):
        return self.shortlist_count
