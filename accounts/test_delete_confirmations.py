from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from categories.models import Category
from companies.models import Company
from favourites.models import Favourite
from projects.models import InteriorDesignProject
from reports.models import ProjectView
from reviews.models import ProjectReview

from .models import UserAccount, UserProfile


class ConfirmationControlsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.forms = []
        self.current_form = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs)
        elif tag == "form":
            self.current_form = {**attrs, "inputs": []}
            self.forms.append(self.current_form)
        elif tag == "input" and self.current_form is not None:
            self.current_form["inputs"].append(attrs)

    def handle_endtag(self, tag):
        if tag == "form":
            self.current_form = None


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DeleteConfirmationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        profiles = {
            name: UserProfile.objects.create(name=name)
            for name in ["User Admin", "Interior Designer", "Customer", "Platform Management"]
        }
        cls.admin = User.objects.create_user(username="confirm_admin")
        cls.designer = User.objects.create_user(username="confirm_designer")
        cls.other_designer = User.objects.create_user(username="confirm_other_designer")
        cls.customer = User.objects.create_user(username="confirm_customer")
        cls.other_customer = User.objects.create_user(username="confirm_other_customer")
        cls.manager = User.objects.create_user(username="confirm_manager")
        for user, role in [
            (cls.admin, "User Admin"),
            (cls.designer, "Interior Designer"),
            (cls.other_designer, "Interior Designer"),
            (cls.customer, "Customer"),
            (cls.other_customer, "Customer"),
            (cls.manager, "Platform Management"),
        ]:
            UserAccount.objects.create(user=user, profile=profiles[role])
        cls.category = Category.objects.create(name="Confirmation Kitchens")
        cls.company = Company.objects.create(user=cls.designer, name="Confirmation Studio")
        cls.other_company = Company.objects.create(
            user=cls.other_designer, name="Other Confirmation Studio",
        )
        cls.current = InteriorDesignProject.objects.create(
            company=cls.company, category=cls.category, title="Current Confirmation Kitchen",
            view_count=11, shortlist_count=1,
        )
        cls.past = InteriorDesignProject.objects.create(
            company=cls.company, category=cls.category, title="Past Confirmation Kitchen",
            status=InteriorDesignProject.STATUS_PAST,
        )
        cls.other_project = InteriorDesignProject.objects.create(
            company=cls.other_company, title="Other Portfolio Project",
        )
        cls.review = ProjectReview.objects.create(
            customer=cls.customer, project=cls.current, rating=5,
            comment="Review awaiting deletion confirmation.",
        )
        cls.other_review = ProjectReview.objects.create(
            customer=cls.other_customer, project=cls.current, rating=4,
        )
        Favourite.objects.create(user=cls.customer, project=cls.current)
        ProjectView.objects.create(viewer=cls.customer, project=cls.current)

    def targets(self):
        return [
            (self.designer, reverse("company_delete"), self.company.name,
             reverse("company_detail"), reverse("company_detail")),
            (self.manager, reverse("category_delete", args=[self.category.pk]),
             self.category.name, reverse("category_detail", args=[self.category.pk]),
             reverse("category_list")),
            (self.designer, reverse("idp_delete", args=[self.current.pk]),
             self.current.title, reverse("idp_detail", args=[self.current.pk]),
             reverse("idp_list")),
            (self.designer, reverse("idp_delete", args=[self.past.pk]),
             self.past.title, reverse("idp_detail", args=[self.past.pk]),
             reverse("idp_list")),
            (self.customer, reverse("review_delete", args=[self.review.pk]),
             self.current.title, reverse("idp_detail", args=[self.current.pk]),
             reverse("idp_detail", args=[self.current.pk])),
        ]

    def business_snapshot(self):
        return {
            model._meta.label: list(model.objects.order_by("pk").values())
            for model in [
                Company, Category, InteriorDesignProject, Favourite, ProjectReview, ProjectView,
            ]
        }

    def parse(self, response):
        parser = ConfirmationControlsParser()
        parser.feed(response.content.decode())
        return parser

    def test_opening_each_confirmation_preserves_all_records_and_activity_counts(self):
        before = self.business_snapshot()
        for user, url, title, cancel_url, _ in self.targets():
            with self.subTest(url=url):
                self.client.force_login(user)
                response = self.client.get(url)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, title)
                self.assertContains(response, "Confirm deletion")
                controls = self.parse(response)
                self.assertTrue(any(link.get("href") == cancel_url for link in controls.links))
                forms = [
                    form for form in controls.forms
                    if form.get("method", "get").lower() == "post"
                    and form.get("action", url) == url
                ]
                self.assertTrue(forms)
                self.assertTrue(any(
                    field.get("name") == "csrfmiddlewaretoken"
                    for form in forms for field in form["inputs"]
                ))
                self.assertEqual(self.business_snapshot(), before)

    def test_existing_delete_actions_link_to_confirmation_instead_of_submitting_deletion(self):
        cases = [
            (self.designer, reverse("company_detail"), [reverse("company_delete")]),
            (self.manager, reverse("category_detail", args=[self.category.pk]),
             [reverse("category_delete", args=[self.category.pk])]),
            (self.designer, reverse("idp_detail", args=[self.current.pk]),
             [reverse("idp_delete", args=[self.current.pk])]),
            (self.designer, reverse("idp_list"), [
                reverse("idp_delete", args=[self.current.pk]),
                reverse("idp_delete", args=[self.past.pk]),
            ]),
            (self.customer, reverse("idp_detail", args=[self.current.pk]),
             [reverse("review_delete", args=[self.review.pk])]),
        ]
        for user, page, delete_urls in cases:
            with self.subTest(page=page, user=user.username):
                self.client.force_login(user)
                response = self.client.get(page)
                self.assertEqual(response.status_code, 200)
                controls = self.parse(response)
                for url in delete_urls:
                    self.assertTrue(any(link.get("href") == url for link in controls.links))
                    self.assertFalse(any(
                        form.get("method", "get").lower() == "post"
                        and form.get("action") == url
                        for form in controls.forms
                    ))

    def test_each_confirmation_requires_csrf_and_valid_post_keeps_existing_delete_behaviour(self):
        # Separate transactions let the company cascade and category SET_NULL
        # paths be checked without removing another case's test target.
        from django.db import transaction

        for user, url, _, _, redirect_url in self.targets():
            with self.subTest(url=url), transaction.atomic():
                before = self.business_snapshot()
                client = Client(enforce_csrf_checks=True)
                client.force_login(user)
                self.assertEqual(client.post(url).status_code, 403)
                self.assertEqual(self.business_snapshot(), before)
                self.assertEqual(client.get(url).status_code, 200)

                response = client.post(
                    url, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
                )

                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, redirect_url)
                if url == reverse("company_delete"):
                    self.assertFalse(Company.objects.filter(pk=self.company.pk).exists())
                    self.assertFalse(InteriorDesignProject.objects.filter(pk=self.current.pk).exists())
                    self.assertTrue(InteriorDesignProject.objects.filter(pk=self.other_project.pk).exists())
                elif url == reverse("category_delete", args=[self.category.pk]):
                    self.assertFalse(Category.objects.filter(pk=self.category.pk).exists())
                    self.current.refresh_from_db()
                    self.assertIsNone(self.current.category_id)
                    self.assertEqual(InteriorDesignProject.objects.count(), 3)
                elif url == reverse("review_delete", args=[self.review.pk]):
                    self.assertFalse(ProjectReview.objects.filter(pk=self.review.pk).exists())
                    self.assertTrue(ProjectReview.objects.filter(pk=self.other_review.pk).exists())
                    self.assertTrue(InteriorDesignProject.objects.filter(pk=self.current.pk).exists())
                else:
                    pk = self.current.pk if url == reverse("idp_delete", args=[self.current.pk]) else self.past.pk
                    self.assertFalse(InteriorDesignProject.objects.filter(pk=pk).exists())
                    self.assertTrue(Company.objects.filter(pk=self.company.pk).exists())
                transaction.set_rollback(True)

    def test_confirmation_does_not_bypass_role_or_suspended_profile_checks(self):
        before = self.business_snapshot()
        for user, url, _, _, _ in self.targets():
            for wrong_user in [self.admin, self.designer, self.customer, self.manager]:
                if wrong_user.account.profile_id == user.account.profile_id:
                    continue
                self.client.force_login(wrong_user)
                for method in ["get", "post"]:
                    with self.subTest(url=url, role=wrong_user.username, method=method):
                        self.assertEqual(getattr(self.client, method)(url).status_code, 403)
            self.client.force_login(user)
            UserProfile.objects.filter(pk=user.account.profile_id).update(is_active=False)
            for method in ["get", "post"]:
                with self.subTest(url=url, suspended=True, method=method):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 403)
            UserProfile.objects.filter(pk=user.account.profile_id).update(is_active=True)
        self.assertEqual(self.business_snapshot(), before)

    def test_only_the_owner_can_open_or_confirm_project_and_review_deletion(self):
        before = self.business_snapshot()
        for user, route, target in [
            (self.other_designer, "idp_delete", self.current),
            (self.other_designer, "idp_delete", self.past),
            (self.other_customer, "review_delete", self.review),
        ]:
            self.client.force_login(user)
            for method in ["get", "post"]:
                with self.subTest(route=route, pk=target.pk, method=method):
                    response = getattr(self.client, method)(reverse(route, args=[target.pk]))
                    self.assertEqual(response.status_code, 404)
        self.assertEqual(self.business_snapshot(), before)

    def test_anonymous_requests_require_login_and_other_mutating_methods_are_rejected(self):
        before = self.business_snapshot()
        for user, url, _, _, _ in self.targets():
            self.client.logout()
            for method in ["get", "post"]:
                with self.subTest(url=url, anonymous=True, method=method):
                    response = getattr(self.client, method)(url)
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(response.url, reverse("login") + "?next=" + url)
            self.client.force_login(user)
            for method in ["put", "patch", "delete"]:
                with self.subTest(url=url, method=method):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 405)
        self.assertEqual(self.business_snapshot(), before)
