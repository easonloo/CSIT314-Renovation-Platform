from django.db.models import Avg

from projects.models import InteriorDesignProject

from .models import ProjectReview


class ProjectReviewController:
    @staticmethod
    def get_project(project_id):
        return InteriorDesignProject.objects.get(pk=project_id)

    @staticmethod
    def get_customer_review(user, project):
        return ProjectReview.objects.filter(customer=user, project=project).first()

    @staticmethod
    def get_owned_review(user, pk):
        return ProjectReview.objects.select_related("project").get(pk=pk, customer=user)

    @staticmethod
    def create_review(user, project, *, rating, comment=""):
        return ProjectReview.objects.get_or_create(
            customer=user,
            project=project,
            defaults={"rating": rating, "comment": comment},
        )

    @classmethod
    def update_review(cls, user, pk, *, rating, comment=""):
        review = cls.get_owned_review(user, pk)
        review.rating = rating
        review.comment = comment
        review.save(update_fields=["rating", "comment", "updated_at"])
        return review

    @classmethod
    def delete_review(cls, user, pk):
        review = cls.get_owned_review(user, pk)
        project_id = review.project_id
        review.delete()
        return project_id

    @classmethod
    def get_project_data(cls, project, customer=None):
        reviews = project.reviews.select_related("customer")
        return {
            "reviews": reviews,
            "average_rating": reviews.aggregate(average_rating=Avg("rating"))["average_rating"],
            "customer_review": (
                cls.get_customer_review(customer, project) if customer is not None else None
            ),
        }
