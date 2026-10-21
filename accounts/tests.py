from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import UserAccount, UserProfile


class ProfileCreationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        profile = UserProfile.objects.create(name="User Admin")
        cls.admin_user = get_user_model().objects.create_user(
            username="profileadmin",
        )
        UserAccount.objects.create(user=cls.admin_user, profile=profile)
        UserProfile.objects.create(name="Customer")

    def test_duplicate_name_displays_error_and_preserves_input(self):
        self.client.force_login(self.admin_user)
        count = UserProfile.objects.count()

        response = self.client.post(
            reverse("profile_create"),
            {"name": "Customer", "description": "My profile description"},
        )

        self.assertContains(response, "A profile with this name already exists.")
        self.assertContains(response, 'value="Customer"')
        self.assertContains(response, "My profile description")
        self.assertEqual(UserProfile.objects.count(), count)


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "TestPassword123!"

        cls.profile = UserProfile.objects.create(
            name="User Admin",
        )

        cls.user = get_user_model().objects.create_user(
            username="testadmin",
            password=cls.password,
        )

        cls.account = UserAccount.objects.create(
            user=cls.user,
            profile=cls.profile,
        )

    def submit_login(self, password=None):
        return self.client.post(
            reverse("login"),
            {
                "username": self.user.username,
                "password": (
                    self.password if password is None else password
                ),
            },
        )

    def assert_login_rejected(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_active_user_can_log_in(self):
        response = self.submit_login()

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(self.user.pk),
        )

    def test_wrong_password_is_rejected(self):
        response = self.submit_login(password="wrong-password")

        self.assert_login_rejected(response)

    def test_suspended_user_is_rejected(self):
        self.user.is_active = False
        self.user.save()

        self.assert_login_rejected(self.submit_login())

    def test_suspended_profile_is_rejected(self):
        self.profile.is_active = False
        self.profile.save()

        self.assert_login_rejected(self.submit_login())

    def test_user_without_account_is_rejected(self):
        self.account.delete()

        self.assert_login_rejected(self.submit_login())

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("dashboard"),
        )

    def test_logged_in_user_loses_access_if_profile_suspended(self):
        self.submit_login()

        self.profile.is_active = False
        self.profile.save()

        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_user_can_log_out(self):
        self.submit_login()

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_profile = UserProfile.objects.create(
            name="User Admin"
        )
        cls.customer_profile = UserProfile.objects.create(
            name="Customer"
        )

        User = get_user_model()

        cls.admin_user = User.objects.create_user(
            username="profileadmin"
        )
        cls.customer = User.objects.create_user(
            username="customer"
        )
        cls.unassigned = User.objects.create_user(
            username="unassigned"
        )

        UserAccount.objects.create(
            user=cls.admin_user,
            profile=cls.admin_profile,
        )
        UserAccount.objects.create(
            user=cls.customer,
            profile=cls.customer_profile,
        )

    def test_admin_can_create_profile(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("profile_create"),
            {
                "name": "Interior Designer",
                "description": "Manages projects",
            },
        )

        self.assertRedirects(response, reverse("profile_list"))
        self.assertTrue(
            UserProfile.objects.filter(
                name="Interior Designer"
            ).exists()
        )

    def test_duplicate_name_is_rejected(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("profile_create"),
            {"name": "Customer"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.context["form"].errors)
        self.assertEqual(
            UserProfile.objects.filter(name="Customer").count(),
            1,
        )

    def test_blank_name_is_rejected(self):
        self.client.force_login(self.admin_user)
        count = UserProfile.objects.count()

        response = self.client.post(
            reverse("profile_create"),
            {"name": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.context["form"].errors)
        self.assertEqual(UserProfile.objects.count(), count)

    def test_customer_is_forbidden(self):
        self.client.force_login(self.customer)

        for route in ["profile_list", "profile_create"]:
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 403)

        response = self.client.post(
            reverse("profile_create"),
            {"name": "Forbidden"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            UserProfile.objects.filter(name="Forbidden").exists()
        )

    def test_suspended_profile_is_forbidden(self):
        self.client.force_login(self.admin_user)

        self.admin_profile.is_active = False
        self.admin_profile.save()

        for route in ["profile_list", "profile_create"]:
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 403)

    def test_unassigned_user_is_forbidden(self):
        self.client.force_login(self.unassigned)

        response = self.client.get(reverse("profile_create"))

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected(self):
        for route in ["profile_list", "profile_create"]:
            url = reverse(route)
            response = self.client.get(url)

            self.assertRedirects(
                response,
                reverse("login") + "?next=" + url,
            )

    def test_admin_can_open_pages(self):
        self.client.force_login(self.admin_user)

        for route in ["dashboard", "profile_list", "profile_create"]:
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("profile_list"))
        self.assertContains(response, "Customer")

    def test_admin_can_view_profile_details(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse(
                "profile_detail",
                args=[self.customer_profile.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/profile_detail.html",
        )
        self.assertEqual(
            response.context["profile"],
            self.customer_profile,
        )
        self.assertContains(response, "Customer")

    def test_profile_list_links_to_details(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("profile_list"))

        self.assertTemplateUsed(response, "accounts/profile_list.html")
        self.assertContains(response, 'href="{}"'.format(reverse("profile_create")))
        for profile in [self.admin_profile, self.customer_profile]:
            self.assertContains(response, profile.name)
            self.assertContains(
                response,
                'href="{}"'.format(
                    reverse("profile_detail", args=[profile.pk])
                ),
            )

    def test_customer_cannot_view_profile_details(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "profile_detail",
                args=[self.customer_profile.pk],
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_missing_profile_returns_404(self):
        self.client.force_login(self.admin_user)

        missing_pk = self.customer_profile.pk + 1000

        response = self.client.get(
            reverse("profile_detail", args=[missing_pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_profile_details_require_login(self):
        url = reverse(
            "profile_detail",
            args=[self.customer_profile.pk],
        )

        response = self.client.get(url)

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + url,
        )

    def test_profile_forms_have_save_button(self):
        self.client.force_login(self.admin_user)
        urls = [
            reverse("profile_create"),
            reverse("profile_update", args=[self.customer_profile.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(
                    response,
                    '<button class="btn btn-primary" type="submit">'
                    'Save profile</button>',
                    html=True,
                )

    def test_admin_can_update_profile(self):
        self.client.force_login(self.admin_user)
        count = UserProfile.objects.count()

        response = self.client.post(
            reverse(
                "profile_update",
                args=[self.customer_profile.pk],
            ),
            {
                "name": "Homeowner",
                "description": "Customers looking for renovation ideas",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "profile_detail",
                args=[self.customer_profile.pk],
            ),
        )

        self.customer_profile.refresh_from_db()

        self.assertEqual(self.customer_profile.name, "Homeowner")
        self.assertEqual(
            self.customer_profile.description,
            "Customers looking for renovation ideas",
        )
        self.assertEqual(UserProfile.objects.count(), count)

    def test_update_rejects_duplicate_name(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                "profile_update",
                args=[self.customer_profile.pk],
            ),
            {"name": "User Admin", "description": ""},
        )

        self.assertContains(
            response,
            "A profile with this name already exists.",
        )

        self.customer_profile.refresh_from_db()
        self.assertEqual(self.customer_profile.name, "Customer")

    def test_update_allows_unchanged_name(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                "profile_update",
                args=[self.customer_profile.pk],
            ),
            {
                "name": "Customer",
                "description": "Updated description",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "profile_detail",
                args=[self.customer_profile.pk],
            ),
        )

        self.customer_profile.refresh_from_db()
        self.assertEqual(
            self.customer_profile.description,
            "Updated description",
        )

    def test_customer_cannot_update_profile(self):
        self.client.force_login(self.customer)

        url = reverse(
            "profile_update",
            args=[self.customer_profile.pk],
        )

        self.assertEqual(self.client.get(url).status_code, 403)

        response = self.client.post(
            url,
            {"name": "Changed", "description": ""},
        )

        self.assertEqual(response.status_code, 403)

        self.customer_profile.refresh_from_db()
        self.assertEqual(self.customer_profile.name, "Customer")

    def test_update_missing_profile_returns_404(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse(
                "profile_update",
                args=[self.customer_profile.pk + 1000],
            )
        )

        self.assertEqual(response.status_code, 404)


    def test_suspend_confirmation_does_not_change_status(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse(
                "profile_suspend",
                args=[self.customer_profile.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/profile_confirm_suspend.html",
        )

        self.customer_profile.refresh_from_db()
        self.assertTrue(self.customer_profile.is_active)

    def test_admin_can_suspend_profile(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                "profile_suspend",
                args=[self.customer_profile.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "profile_detail",
                args=[self.customer_profile.pk],
            ),
        )

        self.customer_profile.refresh_from_db()
        self.assertFalse(self.customer_profile.is_active)

        # Group suspension leaves individual account status unchanged.
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_active)

    def test_customer_cannot_suspend_profile(self):
        self.client.force_login(self.customer)

        url = reverse(
            "profile_suspend",
            args=[self.customer_profile.pk],
        )

        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)

        self.customer_profile.refresh_from_db()
        self.assertTrue(self.customer_profile.is_active)

    def test_suspend_missing_profile_returns_404(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                "profile_suspend",
                args=[self.customer_profile.pk + 1000],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_suspending_own_profile_logs_admin_out(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                "profile_suspend",
                args=[self.admin_profile.pk],
            )
        )

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

        self.admin_profile.refresh_from_db()
        self.assertFalse(self.admin_profile.is_active)


    def test_reactivate_confirmation_does_not_change_status(self):
        self.customer_profile.is_active = False
        self.customer_profile.save()
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse(
                "profile_reactivate",
                args=[self.customer_profile.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/profile_confirm_reactivate.html",
        )

        self.customer_profile.refresh_from_db()
        self.assertFalse(self.customer_profile.is_active)

    def test_profile_detail_shows_correct_status_action(self):
        self.client.force_login(self.admin_user)
        for is_active, action, other_action in [
            (True, "profile_suspend", "profile_reactivate"),
            (False, "profile_reactivate", "profile_suspend"),
        ]:
            with self.subTest(is_active=is_active):
                self.customer_profile.is_active = is_active
                self.customer_profile.save(update_fields=["is_active"])
                response = self.client.get(
                    reverse("profile_detail", args=[self.customer_profile.pk])
                )
                self.assertContains(
                    response,
                    'href="{}"'.format(
                        reverse(action, args=[self.customer_profile.pk])
                    ),
                )
                self.assertNotContains(
                    response,
                    'href="{}"'.format(
                        reverse(other_action, args=[self.customer_profile.pk])
                    ),
                )

    def test_admin_can_reactivate_profile(self):
        self.customer_profile.is_active = False
        self.customer_profile.save()
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                "profile_reactivate",
                args=[self.customer_profile.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "profile_detail",
                args=[self.customer_profile.pk],
            ),
        )

        self.customer_profile.refresh_from_db()
        self.assertTrue(self.customer_profile.is_active)

    def test_reactivation_keeps_individual_account_suspended(self):
        self.customer_profile.is_active = False
        self.customer_profile.save()

        self.customer.is_active = False
        self.customer.save()

        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                "profile_reactivate",
                args=[self.customer_profile.pk],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.customer_profile.refresh_from_db()
        self.customer.refresh_from_db()

        self.assertTrue(self.customer_profile.is_active)
        self.assertFalse(self.customer.is_active)

    def test_customer_cannot_reactivate_profile(self):
        target = UserProfile.objects.create(
            name="Test Profile",
            is_active=False,
        )
        self.client.force_login(self.customer)

        url = reverse("profile_reactivate", args=[target.pk])

        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)

        target.refresh_from_db()
        self.assertFalse(target.is_active)

    def test_reactivate_missing_profile_returns_404(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                "profile_reactivate",
                args=[self.customer_profile.pk + 1000],
            )
        )

        self.assertEqual(response.status_code, 404)


    def test_search_finds_matching_profiles(self):
        self.client.force_login(self.admin_user)

        for term in ["cust", "CUSTOMER", "  Customer  "]:
            with self.subTest(term=term):
                response = self.client.get(
                    reverse("profile_list"),
                    {"q": term},
                )

                self.assertEqual(response.status_code, 200)

                names = [
                    profile.name
                    for profile in response.context["profiles"]
                ]

                self.assertEqual(names, ["Customer"])
                self.assertContains(
                    response,
                    'value="{}"'.format(term.strip()),
                )

    def test_search_with_no_matches(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("profile_list"),
            {"q": "NoMatchingProfile"},
        )

        self.assertEqual(
            list(response.context["profiles"]),
            [],
        )
        self.assertContains(response, "No profiles found.")

    def test_empty_search_shows_all_profiles(self):
        self.client.force_login(self.admin_user)

        for term in ["", "   "]:
            with self.subTest(term=term):
                response = self.client.get(
                    reverse("profile_list"),
                    {"q": term},
                )

                names = [
                    profile.name
                    for profile in response.context["profiles"]
                ]

                self.assertEqual(
                    names,
                    ["Customer", "User Admin"],
                )

    def test_customer_cannot_search_profiles(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("profile_list"),
            {"q": "Customer"},
        )

        self.assertEqual(response.status_code, 403)


class AccountCreationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        admin_profile = UserProfile.objects.create(
            name="User Admin"
        )
        cls.customer_profile = UserProfile.objects.create(
            name="Customer"
        )
        cls.admin_user = get_user_model().objects.create_user(
            username="accountadmin"
        )
        UserAccount.objects.create(
            user=cls.admin_user,
            profile=admin_profile,
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

        self.data = {
            "username": "newcustomer",
            "email": "customer@example.com",
            "first_name": "Alice",
            "last_name": "Tan",
            "password1": "Reno!2026TestPass",
            "password2": "Reno!2026TestPass",
            "profile": self.customer_profile.pk,
        }

    def test_admin_can_create_account(self):
        response = self.client.post(
            reverse("account_create"),
            self.data,
        )

        self.assertRedirects(response, reverse("account_list"))

        user = get_user_model().objects.get(
            username="newcustomer"
        )

        self.assertTrue(user.check_password(self.data["password1"]))
        self.assertNotEqual(user.password, self.data["password1"])
        self.assertEqual(user.account.profile, self.customer_profile)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_duplicate_username_is_rejected(self):
        self.data["username"] = self.admin_user.username
        count = UserAccount.objects.count()

        response = self.client.post(
            reverse("account_create"),
            self.data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(UserAccount.objects.count(), count)

    def test_invalid_passwords_are_rejected(self):
        passwords = [
            ("123", "123"),
            ("Reno!2026TestPass", "Different!2026"),
        ]

        for first, second in passwords:
            with self.subTest(first=first):
                data = dict(
                    self.data,
                    password1=first,
                    password2=second,
                )

                response = self.client.post(
                    reverse("account_create"),
                    data,
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn(
                    "password2",
                    response.context["form"].errors,
                )
                self.assertFalse(
                    get_user_model().objects.filter(
                        username="newcustomer"
                    ).exists()
                )

    def test_suspended_profile_cannot_be_assigned(self):
        self.customer_profile.is_active = False
        self.customer_profile.save()

        response = self.client.post(
            reverse("account_create"),
            self.data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("profile", response.context["form"].errors)
        self.assertFalse(
            get_user_model().objects.filter(
                username="newcustomer"
            ).exists()
        )

    def test_customer_cannot_manage_accounts(self):
        customer = get_user_model().objects.create_user(
            username="existingcustomer"
        )
        UserAccount.objects.create(
            user=customer,
            profile=self.customer_profile,
        )
        self.client.force_login(customer)

        for route in ["account_list", "account_create"]:
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 403)

        response = self.client.post(
            reverse("account_create"),
            self.data,
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            get_user_model().objects.filter(
                username="newcustomer"
            ).exists()
        )


    def test_admin_can_view_account_details(self):
        user = get_user_model().objects.create_user(
            username="viewcustomer",
            first_name="Alice",
            last_name="Tan",
            email="alice@example.com",
            password="SafePassword2026!",
        )

        account = UserAccount.objects.create(
            user=user,
            profile=self.customer_profile,
        )

        response = self.client.get(
            reverse("account_detail", args=[account.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/account_detail.html",
        )
        self.assertEqual(response.context["account"], account)

        self.assertContains(response, "viewcustomer")
        self.assertContains(response, "Alice Tan")
        self.assertContains(response, "alice@example.com")
        self.assertContains(response, "Customer")

        self.assertNotContains(response, "SafePassword2026!")
        self.assertNotContains(response, user.password)

    def test_customer_cannot_view_account_details(self):
        customer = get_user_model().objects.create_user(
            username="detailcustomer"
        )

        UserAccount.objects.create(
            user=customer,
            profile=self.customer_profile,
        )

        self.client.force_login(customer)

        response = self.client.get(
            reverse(
                "account_detail",
                args=[self.admin_user.account.pk],
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_missing_account_returns_404(self):
        response = self.client.get(
            reverse(
                "account_detail",
                args=[self.admin_user.account.pk + 1000],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_account_details_require_login(self):
        self.client.logout()

        url = reverse(
            "account_detail",
            args=[self.admin_user.account.pk],
        )

        response = self.client.get(url)

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + url,
        )

    def test_account_list_has_view_link(self):
        response = self.client.get(reverse("account_list"))

        detail_url = reverse(
            "account_detail",
            args=[self.admin_user.account.pk],
        )

        self.assertContains(
            response,
            'href="{}"'.format(detail_url),
        )


    def make_update_target(self):
        user = get_user_model().objects.create_user(
            username="updatecustomer",
            password="Original!2026Pass",
        )

        return UserAccount.objects.create(
            user=user,
            profile=self.customer_profile,
        )

    def account_update_data(self):
        return {
            "username": "updatedcustomer",
            "first_name": "Alice",
            "last_name": "Tan",
            "email": "updated@example.com",
            "profile": self.customer_profile.pk,
        }

    def test_admin_can_update_account(self):
        account = self.make_update_target()

        user_count = get_user_model().objects.count()
        account_count = UserAccount.objects.count()
        original_password = account.user.password

        new_profile = UserProfile.objects.create(
            name="Interior Designer"
        )

        data = self.account_update_data()
        data["profile"] = new_profile.pk

        response = self.client.post(
            reverse("account_update", args=[account.pk]),
            data,
        )

        self.assertRedirects(
            response,
            reverse("account_detail", args=[account.pk]),
        )

        account.refresh_from_db()

        self.assertEqual(account.user.username, "updatedcustomer")
        self.assertEqual(account.user.email, "updated@example.com")
        self.assertEqual(account.user.get_full_name(), "Alice Tan")
        self.assertEqual(account.profile, new_profile)

        self.assertEqual(account.user.password, original_password)
        self.assertTrue(account.user.is_active)
        self.assertFalse(account.user.is_staff)
        self.assertFalse(account.user.is_superuser)

        self.assertEqual(
            get_user_model().objects.count(),
            user_count,
        )
        self.assertEqual(
            UserAccount.objects.count(),
            account_count,
        )

    def test_account_update_rejects_duplicate_username(self):
        account = self.make_update_target()
        data = self.account_update_data()
        data["username"] = self.admin_user.username.upper()

        response = self.client.post(
            reverse("account_update", args=[account.pk]),
            data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)

        account.user.refresh_from_db()
        self.assertEqual(account.user.username, "updatecustomer")

    def test_account_update_allows_unchanged_username(self):
        account = self.make_update_target()
        data = self.account_update_data()
        data["username"] = account.user.username

        response = self.client.post(
            reverse("account_update", args=[account.pk]),
            data,
        )

        self.assertRedirects(
            response,
            reverse("account_detail", args=[account.pk]),
        )

    def test_customer_cannot_update_accounts(self):
        account = self.make_update_target()
        self.client.force_login(account.user)

        url = reverse("account_update", args=[account.pk])

        self.assertEqual(self.client.get(url).status_code, 403)

        response = self.client.post(
            url,
            self.account_update_data(),
        )

        self.assertEqual(response.status_code, 403)

        account.user.refresh_from_db()
        self.assertEqual(account.user.username, "updatecustomer")

    def test_update_missing_account_returns_404(self):
        response = self.client.get(
            reverse(
                "account_update",
                args=[self.admin_user.account.pk + 1000],
            )
        )

        self.assertEqual(response.status_code, 404)


    def test_account_suspend_confirmation_does_not_change_status(self):
        account = self.make_update_target()

        response = self.client.get(
            reverse("account_suspend", args=[account.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/account_confirm_suspend.html",
        )

        account.user.refresh_from_db()
        self.assertTrue(account.user.is_active)

    def test_admin_can_suspend_account(self):
        account = self.make_update_target()

        response = self.client.post(
            reverse("account_suspend", args=[account.pk])
        )

        self.assertRedirects(
            response,
            reverse("account_detail", args=[account.pk]),
        )

        account.user.refresh_from_db()
        account.profile.refresh_from_db()
        self.admin_user.refresh_from_db()

        self.assertFalse(account.user.is_active)
        self.assertTrue(account.profile.is_active)
        self.assertTrue(self.admin_user.is_active)

    def test_suspended_account_cannot_log_in(self):
        account = self.make_update_target()

        self.client.post(
            reverse("account_suspend", args=[account.pk])
        )
        self.client.logout()

        response = self.client.post(
            reverse("login"),
            {
                "username": account.user.username,
                "password": "Original!2026Pass",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_customer_cannot_suspend_account(self):
        customer_account = self.make_update_target()
        self.client.force_login(customer_account.user)

        url = reverse(
            "account_suspend",
            args=[self.admin_user.account.pk],
        )

        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)

        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)

    def test_suspend_missing_account_returns_404(self):
        response = self.client.post(
            reverse(
                "account_suspend",
                args=[self.admin_user.account.pk + 1000],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_suspending_own_account_logs_admin_out(self):
        response = self.client.post(
            reverse(
                "account_suspend",
                args=[self.admin_user.account.pk],
            )
        )

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

        self.admin_user.refresh_from_db()
        self.assertFalse(self.admin_user.is_active)

    def make_suspended_account(self):
        account = self.make_update_target()
        account.user.is_active = False
        account.user.save(update_fields=["is_active"])
        return account

    def test_account_reactivate_confirmation_does_not_change_status(self):
        account = self.make_suspended_account()

        response = self.client.get(
            reverse("account_reactivate", args=[account.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/account_confirm_reactivate.html",
        )
        self.assertContains(response, "Confirm reactivation")
        account.user.refresh_from_db()
        self.assertFalse(account.user.is_active)

    def test_admin_can_reactivate_account_and_restore_login(self):
        account = self.make_suspended_account()
        original_password = account.user.password
        original_profile_id = account.profile_id

        response = self.client.post(
            reverse("account_reactivate", args=[account.pk])
        )

        self.assertRedirects(
            response,
            reverse("account_detail", args=[account.pk]),
        )
        account.refresh_from_db()
        self.assertTrue(account.user.is_active)
        self.assertEqual(account.user.password, original_password)
        self.assertEqual(account.profile_id, original_profile_id)
        self.assertFalse(account.user.is_staff)
        self.assertFalse(account.user.is_superuser)

        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {
                "username": account.user.username,
                "password": "Original!2026Pass",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(account.user_id),
        )

    def test_account_reactivation_keeps_profile_suspended(self):
        account = self.make_suspended_account()
        self.customer_profile.is_active = False
        self.customer_profile.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("account_reactivate", args=[account.pk])
        )

        self.assertRedirects(
            response,
            reverse("account_detail", args=[account.pk]),
        )
        account.refresh_from_db()
        self.assertTrue(account.user.is_active)
        self.assertFalse(account.profile.is_active)

        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {
                "username": account.user.username,
                "password": "Original!2026Pass",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_customer_cannot_reactivate_account(self):
        account = self.make_suspended_account()
        customer = get_user_model().objects.create_user(
            username="reactivationcustomer"
        )
        UserAccount.objects.create(user=customer, profile=self.customer_profile)
        self.client.force_login(customer)
        url = reverse("account_reactivate", args=[account.pk])

        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)
        account.user.refresh_from_db()
        self.assertFalse(account.user.is_active)

    def test_account_reactivation_requires_login(self):
        account = self.make_suspended_account()
        self.client.logout()
        url = reverse("account_reactivate", args=[account.pk])

        self.assertRedirects(
            self.client.get(url),
            reverse("login") + "?next=" + url,
        )
        self.assertRedirects(
            self.client.post(url),
            reverse("login") + "?next=" + url,
        )
        account.user.refresh_from_db()
        self.assertFalse(account.user.is_active)

    def test_reactivate_missing_account_returns_404(self):
        url = reverse(
            "account_reactivate",
            args=[self.admin_user.account.pk + 1000],
        )

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_account_detail_shows_correct_status_action(self):
        account = self.make_update_target()
        for active, action, other_action in [
            (True, "account_suspend", "account_reactivate"),
            (False, "account_reactivate", "account_suspend"),
        ]:
            with self.subTest(is_active=active):
                account.user.is_active = active
                account.user.save(update_fields=["is_active"])
                response = self.client.get(
                    reverse("account_detail", args=[account.pk])
                )
                self.assertContains(
                    response,
                    'href="{}"'.format(reverse(action, args=[account.pk])),
                )
                self.assertNotContains(
                    response,
                    'href="{}"'.format(reverse(other_action, args=[account.pk])),
                )
