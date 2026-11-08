from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg

from projects.models import InteriorDesignProject


class ProjectReview(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_reviews",
    )
    project = models.ForeignKey(
        InteriorDesignProject,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "project"],
                name="unique_customer_project_review",
            ),
            models.CheckConstraint(
                check=models.Q(rating__gte=1, rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
        ]

    def __str__(self):
        return f"{self.customer} rated {self.project} ({self.rating}/5)"

    @classmethod
    def empty(cls):
        return cls.objects.none()

    @classmethod
    def public_reviews(cls):
        return cls.objects.select_related("customer", "project", "project__company")

    @classmethod
    def public_review_count(cls):
        return cls.objects.count()

    @classmethod
    def find_for_customer(cls, customer, project):
        return cls.objects.filter(customer=customer, project=project).first()

    @classmethod
    def find_owned(cls, customer, pk):
        return cls.objects.select_related("project").get(pk=pk, customer=customer)

    @classmethod
    def create_for_customer(cls, customer, project, *, rating, comment=""):
        return cls.objects.get_or_create(
            customer=customer, project=project,
            defaults={"rating": rating, "comment": comment},
        )

    @classmethod
    def project_summary(cls, project, customer=None):
        reviews = cls.objects.filter(project=project).select_related("customer")
        return {
            "reviews": reviews,
            "average_rating": reviews.aggregate(average_rating=Avg("rating"))["average_rating"],
            "customer_review": (
                cls.find_for_customer(customer, project) if customer is not None else None
            ),
        }

    def update_details(self, *, rating, comment=""):
        self.rating = rating
        self.comment = comment
        self.save(update_fields=["rating", "comment", "updated_at"])
        return self

    def delete_review(self):
        project_id = self.project_id
        self.delete()
        return project_id
