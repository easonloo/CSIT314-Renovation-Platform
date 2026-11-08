"""Review use-case controls. ProjectReview owns persistence and queries."""
from projects.models import InteriorDesignProject

from .models import ProjectReview


class ViewProjectReviewsController:
    def get_project(self, project_id):
        return InteriorDesignProject.find(project_id)

    def get_customer_review(self, user, project):
        return ProjectReview.find_for_customer(user, project)

    def get_owned_review(self, user, pk):
        return ProjectReview.find_owned(user, pk)

    def get_project_data(self, project, customer=None):
        return ProjectReview.project_summary(project, customer)


class CreateProjectReviewController:
    def create_review(self, user, project, *, rating, comment=""):
        return ProjectReview.create_for_customer(user, project, rating=rating, comment=comment)


class UpdateProjectReviewController:
    def update_review(self, user, pk, *, rating, comment=""):
        return ProjectReview.find_owned(user, pk).update_details(rating=rating, comment=comment)


class DeleteProjectReviewController:
    def delete_review(self, user, pk):
        return ProjectReview.find_owned(user, pk).delete_review()


class ProjectReviewController:
    """Compatibility API; request boundaries call the use-case classes above."""
    get_project = staticmethod(ViewProjectReviewsController().get_project)
    get_customer_review = staticmethod(ViewProjectReviewsController().get_customer_review)
    get_owned_review = staticmethod(ViewProjectReviewsController().get_owned_review)
    get_project_data = staticmethod(ViewProjectReviewsController().get_project_data)
    create_review = staticmethod(CreateProjectReviewController().create_review)
    update_review = staticmethod(UpdateProjectReviewController().update_review)
    delete_review = staticmethod(DeleteProjectReviewController().delete_review)
