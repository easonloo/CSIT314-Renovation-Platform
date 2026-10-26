from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from projects.models import InteriorDesignProject

from .models import ProjectReview
from .views import review_update
from projects.views import customer_idp_search, idp_detail
from accounts.views import dashboard


class ProjectReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        cls.designer_profile = UserProfile.objects.create(name="Interior Designer")
        cls.customer = get_user_model().objects.create_user(
            username="review_customer",
            password="CustomerPass123!",
        )
        UserAccount.objects.create(
            user=cls.customer,
            profile=cls.customer_profile,
        )
        designer = get_user_model().objects.create_user(username="review_designer")
        UserAccount.objects.create(user=designer, profile=cls.designer_profile)
        company = Company.objects.create(user=designer, name="Review Studio")
        category = Category.objects.create(name="Review Category")
        cls.past_project = InteriorDesignProject.objects.create(
            company=company,
            category=category,
            title="Completed Review Project",
            status=InteriorDesignProject.STATUS_PAST,
        )
        cls.current_project = InteriorDesignProject.objects.create(
            company=company,
            category=category,
            title="Current Review Project",
            status=InteriorDesignProject.STATUS_CURRENT,
        )

    def setUp(self):
        self.client.force_login(self.customer)
        self.request_factory = RequestFactory()

    def assertRedirectLocation(self, response, url):
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], url)

    def test_customer_can_review_past_project(self):
        response = self.client.post(
            reverse("review_create", args=[self.past_project.pk]),
            {"rating": 5, "comment": "Excellent completed work."},
        )

        review = ProjectReview.objects.get(
            customer=self.customer,
            project=self.past_project,
        )
        self.assertRedirectLocation(
            response,
            reverse("idp_detail", args=[self.past_project.pk]),
        )
        self.assertEqual(review.rating, 5)

    def test_customer_can_review_current_project(self):
        response = self.client.post(
            reverse("review_create", args=[self.current_project.pk]),
            {"rating": 4, "comment": "The work is progressing well."},
        )

        review = ProjectReview.objects.get(
            customer=self.customer,
            project=self.current_project,
        )
        self.assertRedirectLocation(
            response,
            reverse("idp_detail", args=[self.current_project.pk]),
        )
        self.assertEqual(review.rating, 4)

    def test_customer_can_update_and_delete_own_review(self):
        review = ProjectReview.objects.create(
            customer=self.customer,
            project=self.past_project,
            rating=3,
            comment="Initial feedback.",
        )
        response = self.client.post(
            reverse("review_update", args=[review.pk]),
            {"rating": 4, "comment": "Updated feedback."},
        )
        review.refresh_from_db()

        self.assertRedirectLocation(
            response,
            reverse("idp_detail", args=[self.past_project.pk]),
        )
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, "Updated feedback.")

        response = self.client.post(reverse("review_delete", args=[review.pk]))
        self.assertRedirectLocation(
            response,
            reverse("idp_detail", args=[self.past_project.pk]),
        )
        self.assertFalse(ProjectReview.objects.filter(pk=review.pk).exists())

    def test_customer_cannot_update_another_customers_review(self):
        other_customer = get_user_model().objects.create_user(
            username="other_review_customer"
        )
        review = ProjectReview.objects.create(
            customer=other_customer,
            project=self.past_project,
            rating=4,
        )

        request = self.request_factory.get(
            reverse("review_update", args=[review.pk])
        )
        request.user = self.customer
        with self.assertRaises(Http404):
            review_update(request, review.pk)

    def test_customer_sees_review_action_for_current_and_past_idps(self):
        search_request = self.request_factory.get(reverse("customer_idp_search"))
        search_request.user = self.customer
        search_response = customer_idp_search(search_request)
        search_html = search_response.content.decode()

        self.assertIn("Write review", search_html)
        self.assertIn(
            reverse("review_create", args=[self.past_project.pk]),
            search_html,
        )
        self.assertIn(
            reverse("review_create", args=[self.current_project.pk]),
            search_html,
        )

        detail_request = self.request_factory.get(
            reverse("idp_detail", args=[self.current_project.pk])
        )
        detail_request.user = self.customer
        detail_response = idp_detail(detail_request, self.current_project.pk)

        self.assertIn("Write a review", detail_response.content.decode())
        self.assertIn(
            reverse("review_create", args=[self.current_project.pk]),
            detail_response.content.decode(),
        )

    def test_duplicate_review_creation_redirects_to_existing_review(self):
        review = ProjectReview.objects.create(
            customer=self.customer,
            project=self.past_project,
            rating=4,
        )

        response = self.client.post(
            reverse("review_create", args=[self.past_project.pk]),
            {"rating": 5, "comment": "Second review"},
        )

        self.assertRedirectLocation(
            response,
            reverse("review_update", args=[review.pk]),
        )
        self.assertEqual(ProjectReview.objects.count(), 1)

    def test_customer_dashboard_lists_only_the_customers_own_reviews(self):
        review = ProjectReview.objects.create(
            customer=self.customer,
            project=self.current_project,
            rating=4,
            comment="The progress is looking good.",
        )
        other_customer = get_user_model().objects.create_user(
            username="dashboard_other_customer"
        )
        ProjectReview.objects.create(
            customer=other_customer,
            project=self.past_project,
            rating=2,
            comment="Private other customer comment.",
        )

        request = self.request_factory.get(reverse("dashboard"))
        request.user = self.customer
        response = dashboard(request)
        dashboard_html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Your IDP reviews", dashboard_html)
        self.assertIn(self.current_project.title, dashboard_html)
        self.assertIn("The progress is looking good.", dashboard_html)
        self.assertIn(reverse("review_update", args=[review.pk]), dashboard_html)
        self.assertNotIn("Private other customer comment.", dashboard_html)
