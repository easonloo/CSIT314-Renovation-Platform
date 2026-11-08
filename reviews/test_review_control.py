from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile
from companies.models import Company
from projects.models import InteriorDesignProject

from .controllers import ProjectReviewController
from .models import ProjectReview


class ReviewControlRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        customer_profile = UserProfile.objects.create(name="Customer")
        designer_profile = UserProfile.objects.create(name="Interior Designer")
        cls.customer = User.objects.create_user(username="control_review_customer")
        cls.other_customer = User.objects.create_user(username="control_review_other")
        designer = User.objects.create_user(username="control_review_designer")
        for user in [cls.customer, cls.other_customer]:
            UserAccount.objects.create(user=user, profile=customer_profile)
        UserAccount.objects.create(user=designer, profile=designer_profile)
        company = Company.objects.create(user=designer, name="Review Control Studio")
        cls.project = InteriorDesignProject.objects.create(company=company, title="Review Control Project")

    def setUp(self):
        self.client.force_login(self.customer)

    def test_foreign_review_cannot_be_changed_or_deleted_by_post(self):
        review = ProjectReview.objects.create(
            customer=self.other_customer, project=self.project, rating=4, comment="Keep this review",
        )
        for name in ["review_update", "review_delete"]:
            with self.subTest(action=name):
                response = self.client.post(
                    reverse(name, args=[review.pk]), {"rating": 1, "comment": "Overwrite"},
                )
                self.assertEqual(response.status_code, 404)
                review.refresh_from_db()
                self.assertEqual(review.rating, 4)
                self.assertEqual(review.comment, "Keep this review")

    def test_invalid_rating_does_not_create_or_modify_a_review(self):
        for rating in [0, 6]:
            with self.subTest(action="create", rating=rating):
                response = self.client.post(
                    reverse("review_create", args=[self.project.pk]), {"rating": rating},
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(ProjectReview.objects.exists())
        review = ProjectReview.objects.create(customer=self.customer, project=self.project, rating=4)
        response = self.client.post(reverse("review_update", args=[review.pk]), {"rating": 6})
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)

    def test_duplicate_controller_creation_returns_existing_review_unchanged(self):
        first, created = ProjectReviewController.create_review(
            self.customer, self.project, rating=4, comment="Original",
        )
        self.assertTrue(created)
        second, created = ProjectReviewController.create_review(
            self.customer, self.project, rating=1, comment="Second submission",
        )
        self.assertFalse(created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ProjectReview.objects.count(), 1)
        first.refresh_from_db()
        self.assertEqual(first.rating, 4)
        self.assertEqual(first.comment, "Original")
