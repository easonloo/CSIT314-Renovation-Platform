from unittest.mock import patch

from django.contrib.auth import SESSION_KEY, get_user_model
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from companies.models import Company
from favourites.models import Favourite
from projects.models import InteriorDesignProject
from reports.models import ProjectView
from reviews.models import ProjectReview

from .models import UserAccount, UserProfile


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class UserAdminDeletionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin_profile = UserProfile.objects.create(name="User Admin")
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        cls.designer_profile = UserProfile.objects.create(name="Interior Designer")
        cls.pm_profile = UserProfile.objects.create(name="Platform Management")
        cls.empty_profile = UserProfile.objects.create(name="Unused Partners")
        cls.admin = User.objects.create_user(username="delete_admin")
        cls.customer = User.objects.create_user(username="delete_customer")
        cls.other_customer = User.objects.create_user(username="delete_other_customer")
        cls.designer = User.objects.create_user(username="delete_designer")
        cls.pm = User.objects.create_user(username="delete_pm")
        cls.unassigned_superuser = User.objects.create_superuser(
            username="delete_unassigned_root", password="TestOnly!2026",
        )
        cls.admin_account = UserAccount.objects.create(user=cls.admin, profile=cls.admin_profile)
        cls.customer_account = UserAccount.objects.create(
            user=cls.customer, profile=cls.customer_profile,
        )
        UserAccount.objects.create(user=cls.other_customer, profile=cls.customer_profile)
        UserAccount.objects.create(user=cls.designer, profile=cls.designer_profile)
        UserAccount.objects.create(user=cls.pm, profile=cls.pm_profile)

    def setUp(self):
        self.client.force_login(self.admin)
        self.account_url = reverse("account_delete", args=[self.customer_account.pk])
        self.profile_url = reverse("profile_delete", args=[self.empty_profile.pk])

    def assert_targets_exist(self):
        self.assertTrue(UserAccount.objects.filter(pk=self.customer_account.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.customer.pk).exists())
        self.assertTrue(UserProfile.objects.filter(pk=self.empty_profile.pk).exists())

    def test_get_displays_confirmation_without_deleting(self):
        for url, target in [
            (self.account_url, self.customer.username),
            (self.profile_url, self.empty_profile.name),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, target)
                self.assertContains(response, "csrfmiddlewaretoken")
                self.assert_targets_exist()

    def test_admin_deletes_account_and_auth_user_and_invalidates_existing_login(self):
        customer_client = Client()
        customer_client.force_login(self.customer)

        response = self.client.post(self.account_url)

        self.assertRedirects(response, reverse("account_list"))
        self.assertFalse(UserAccount.objects.filter(pk=self.customer_account.pk).exists())
        self.assertFalse(get_user_model().objects.filter(pk=self.customer.pk).exists())
        self.assertTrue(UserProfile.objects.filter(pk=self.customer_profile.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.other_customer.pk).exists())
        self.assertRedirects(
            customer_client.get(reverse("dashboard")),
            reverse("login") + "?next=" + reverse("dashboard"),
        )

    def test_deleting_populated_customer_removes_own_activity_and_updates_saved_counts(self):
        company = Company.objects.create(user=self.designer, name="Remaining Design Studio")
        project = InteriorDesignProject.objects.create(
            company=company, title="Remaining Living Room", shortlist_count=2,
            view_count=7,
        )
        zero_project = InteriorDesignProject.objects.create(
            company=company, title="Legacy Zero Counter", shortlist_count=0,
        )
        Favourite.objects.create(user=self.customer, project=project)
        Favourite.objects.create(user=self.customer, project=zero_project)
        other_favourite = Favourite.objects.create(user=self.other_customer, project=project)
        ProjectReview.objects.create(customer=self.customer, project=project, rating=5)
        other_review = ProjectReview.objects.create(
            customer=self.other_customer, project=project, rating=4,
        )
        ProjectView.objects.create(viewer=self.customer, project=project)
        other_view = ProjectView.objects.create(viewer=self.other_customer, project=project)

        response = self.client.post(self.account_url)

        self.assertRedirects(response, reverse("account_list"))
        project.refresh_from_db()
        zero_project.refresh_from_db()
        self.assertEqual(project.shortlist_count, 1)
        self.assertEqual(project.view_count, 7)
        self.assertEqual(zero_project.shortlist_count, 0)
        self.assertFalse(Favourite.objects.filter(user_id=self.customer.pk).exists())
        self.assertFalse(ProjectReview.objects.filter(customer_id=self.customer.pk).exists())
        self.assertFalse(ProjectView.objects.filter(viewer_id=self.customer.pk).exists())
        self.assertTrue(Favourite.objects.filter(pk=other_favourite.pk).exists())
        self.assertTrue(ProjectReview.objects.filter(pk=other_review.pk).exists())
        self.assertTrue(ProjectView.objects.filter(pk=other_view.pk).exists())
        self.assertTrue(Company.objects.filter(pk=company.pk).exists())

    def test_deleting_designer_removes_owned_portfolio_and_preserves_other_users_data(self):
        account = UserAccount.objects.get(user=self.designer)
        company = Company.objects.create(user=self.designer, name="Deleted Portfolio")
        project = InteriorDesignProject.objects.create(company=company, title="Deleted Kitchen")
        favourite = Favourite.objects.create(user=self.customer, project=project)
        review = ProjectReview.objects.create(customer=self.customer, project=project, rating=4)
        view = ProjectView.objects.create(viewer=self.customer, project=project)
        other_designer = get_user_model().objects.create_user(username="remaining_designer")
        UserAccount.objects.create(user=other_designer, profile=self.designer_profile)
        other_company = Company.objects.create(user=other_designer, name="Remaining Portfolio")
        other_project = InteriorDesignProject.objects.create(
            company=other_company, title="Remaining Kitchen", shortlist_count=1,
        )
        other_favourite = Favourite.objects.create(user=self.customer, project=other_project)

        response = self.client.post(reverse("account_delete", args=[account.pk]))

        self.assertRedirects(response, reverse("account_list"))
        for model, pk in [
            (UserAccount, account.pk), (get_user_model(), self.designer.pk),
            (Company, company.pk), (InteriorDesignProject, project.pk),
            (Favourite, favourite.pk), (ProjectReview, review.pk), (ProjectView, view.pk),
        ]:
            with self.subTest(model=model.__name__):
                self.assertFalse(model.objects.filter(pk=pk).exists())
        self.assertTrue(UserAccount.objects.filter(user=self.customer).exists())
        self.assertTrue(UserProfile.objects.filter(pk=self.designer_profile.pk).exists())
        self.assertTrue(Company.objects.filter(pk=other_company.pk).exists())
        self.assertTrue(Favourite.objects.filter(pk=other_favourite.pk).exists())
        other_project.refresh_from_db()
        self.assertEqual(other_project.shortlist_count, 1)

    def test_failed_user_deletion_rolls_back_favourite_counter_changes(self):
        from .controllers import DeleteUserAccountController

        company = Company.objects.create(user=self.designer, name="Atomic Delete Studio")
        project = InteriorDesignProject.objects.create(
            company=company, title="Unchanged Project", shortlist_count=1,
        )
        favourite = Favourite.objects.create(user=self.customer, project=project)

        with patch.object(
            get_user_model(), "delete", side_effect=IntegrityError("Injected delete failure"),
        ):
            with self.assertRaises(IntegrityError):
                DeleteUserAccountController().delete_account(
                    self.customer_account, actor=self.admin,
                )

        project.refresh_from_db()
        self.assertEqual(project.shortlist_count, 1)
        self.assertTrue(Favourite.objects.filter(pk=favourite.pk).exists())
        self.assert_targets_exist()

    def test_admin_cannot_delete_own_account(self):
        url = reverse("account_delete", args=[self.admin_account.pk])
        confirmation = self.client.get(url)
        self.assertContains(confirmation, "You cannot delete your own user account.")
        self.assertNotContains(confirmation, "Confirm deletion")

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You cannot delete your own user account.")
        self.assertTrue(UserAccount.objects.filter(pk=self.admin_account.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.admin.pk).exists())
        self.assertEqual(self.client.session[SESSION_KEY], str(self.admin.pk))

    def test_admin_can_delete_empty_active_and_suspended_profiles(self):
        for active in [True, False]:
            with self.subTest(active=active):
                profile = UserProfile.objects.create(name=f"Unused {active}", is_active=active)

                response = self.client.post(reverse("profile_delete", args=[profile.pk]))

                self.assertRedirects(response, reverse("profile_list"))
                self.assertFalse(UserProfile.objects.filter(pk=profile.pk).exists())
                self.assert_targets_exist()

    def test_assigned_profile_is_not_deleted_and_displays_reassignment_guidance(self):
        response = self.client.post(reverse("profile_delete", args=[self.customer_profile.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "This profile is assigned to user accounts. Reassign or delete those accounts first.",
        )
        self.assertTrue(UserProfile.objects.filter(pk=self.customer_profile.pk).exists())
        self.assertEqual(UserAccount.objects.filter(profile=self.customer_profile).count(), 2)
        self.assert_targets_exist()

    def test_non_admin_roles_and_unassigned_superuser_cannot_view_or_submit_deletion(self):
        for user in [self.customer, self.designer, self.pm, self.unassigned_superuser]:
            self.client.force_login(user)
            for url in [self.account_url, self.profile_url]:
                for method in ["get", "post"]:
                    with self.subTest(user=user.username, url=url, method=method):
                        self.assertEqual(getattr(self.client, method)(url).status_code, 403)
                        self.assert_targets_exist()

    def test_anonymous_requests_redirect_to_login_without_deleting(self):
        self.client.logout()
        for url in [self.account_url, self.profile_url]:
            for method in ["get", "post"]:
                with self.subTest(url=url, method=method):
                    self.assertRedirects(
                        getattr(self.client, method)(url),
                        reverse("login") + "?next=" + url,
                    )
                    self.assert_targets_exist()

    def test_suspended_admin_profile_cannot_delete_from_an_existing_session(self):
        self.assertEqual(self.admin.account.profile.name, "User Admin")
        UserProfile.objects.filter(pk=self.admin_profile.pk).update(is_active=False)
        for url in [self.account_url, self.profile_url]:
            for method in ["get", "post"]:
                with self.subTest(url=url, method=method):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 403)
                    self.assert_targets_exist()

    def test_suspended_admin_user_cannot_delete_from_an_existing_session(self):
        get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
        for url in [self.account_url, self.profile_url]:
            for method in ["get", "post"]:
                with self.subTest(url=url, method=method):
                    self.assertRedirects(
                        getattr(self.client, method)(url),
                        reverse("login") + "?next=" + url,
                    )
                    self.assert_targets_exist()

    def test_control_entry_points_recheck_the_actor_role_from_the_database(self):
        from .controllers import DeleteUserAccountController, DeleteUserProfileController

        self.assertEqual(self.admin.account.profile.name, "User Admin")
        UserAccount.objects.filter(pk=self.admin_account.pk).update(profile=self.customer_profile)

        with self.assertRaises(PermissionDenied):
            DeleteUserAccountController().delete_account(self.customer_account, actor=self.admin)
        with self.assertRaises(PermissionDenied):
            DeleteUserProfileController().delete_profile(self.empty_profile, actor=self.admin)
        self.assert_targets_exist()

    def test_unknown_records_return_404_without_affecting_other_records(self):
        for route in ["account_delete", "profile_delete"]:
            for method in ["get", "post"]:
                with self.subTest(route=route, method=method):
                    self.assertEqual(
                        getattr(self.client, method)(reverse(route, args=[999999])).status_code,
                        404,
                    )
                    self.assert_targets_exist()

    def test_mutating_methods_other_than_post_are_rejected(self):
        for url in [self.account_url, self.profile_url]:
            for method in ["put", "patch", "delete"]:
                with self.subTest(url=url, method=method):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 405)
                    self.assert_targets_exist()

    def test_post_requires_csrf_and_a_valid_confirmation_can_delete(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        for url in [self.account_url, self.profile_url]:
            with self.subTest(url=url):
                self.assertEqual(client.post(url).status_code, 403)
        self.assert_targets_exist()

        for url, redirect in [
            (self.account_url, "account_list"), (self.profile_url, "profile_list"),
        ]:
            with self.subTest(url=url):
                client.get(url)
                response = client.post(url, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
                self.assertRedirects(response, reverse(redirect))
        self.assertFalse(UserAccount.objects.filter(pk=self.customer_account.pk).exists())
        self.assertFalse(UserProfile.objects.filter(pk=self.empty_profile.pk).exists())
