from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import UserAccount, UserProfile


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class RoleAuthenticationUseCaseTests(TestCase):
    password = "TestOnly!RoleLogin2026"

    @classmethod
    def setUpTestData(cls):
        cls.users = []
        for index, role in enumerate([
            "User Admin", "Interior Designer", "Customer", "Platform Management",
        ]):
            profile = UserProfile.objects.create(name=role)
            user = get_user_model().objects.create_user(
                username=f"role_login_{index}", password=cls.password,
            )
            UserAccount.objects.create(user=user, profile=profile)
            cls.users.append(user)

    def test_every_required_role_can_login_and_logout_through_shared_boundaries(self):
        for user in self.users:
            with self.subTest(role=user.account.profile.name):
                response = self.client.post(reverse("login"), {
                    "username": user.username, "password": self.password,
                })
                self.assertRedirects(response, reverse("dashboard"))
                self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))

                response = self.client.post(reverse("logout"))

                self.assertRedirects(response, reverse("login"))
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_each_role_is_denied_login_when_its_profile_is_suspended(self):
        for user in self.users:
            with self.subTest(role=user.account.profile.name):
                UserProfile.objects.filter(pk=user.account.profile_id).update(is_active=False)

                response = self.client.post(reverse("login"), {
                    "username": user.username, "password": self.password,
                })

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Your account is unavailable.")
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_suspended_existing_sessions_can_still_logout(self):
        for user in self.users:
            with self.subTest(role=user.account.profile.name):
                self.client.force_login(user)
                UserProfile.objects.filter(pk=user.account.profile_id).update(is_active=False)

                response = self.client.post(reverse("logout"))

                self.assertRedirects(response, reverse("login"))
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_custom_profiles_keep_their_existing_login_and_logout_behaviour(self):
        profile = UserProfile.objects.create(name="Partners")
        user = get_user_model().objects.create_user(
            username="custom_role_login", password=self.password,
        )
        UserAccount.objects.create(user=user, profile=profile)

        response = self.client.post(reverse("login"), {
            "username": user.username, "password": self.password,
        })

        self.assertRedirects(response, reverse("dashboard"))
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_preserves_post_only_and_csrf_protection(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.users[2])
        self.assertEqual(client.get(reverse("logout")).status_code, 405)
        self.assertEqual(client.post(reverse("logout")).status_code, 403)
        self.assertIn(SESSION_KEY, client.session)

        client.get(reverse("login"))
        response = client.post(
            reverse("logout"), HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn(SESSION_KEY, client.session)
