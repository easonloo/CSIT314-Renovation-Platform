from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company

from .models import InteriorDesignProject


class IDPUserStoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.designer_profile = UserProfile.objects.create(name="Interior Designer")
        cls.user = get_user_model().objects.create_user(
            username="story_designer",
            password="StoryPass123!",
            email="story@designer.local",
        )
        UserAccount.objects.create(user=cls.user, profile=cls.designer_profile)
        cls.company = Company.objects.create(user=cls.user, name="Story Studio")
        cls.category = Category.objects.create(name="Residential Story")

    def setUp(self):
        self.client.force_login(self.user)

    def test_as_id_i_can_create_a_current_idp(self):
        response = self.client.post(
            reverse("idp_create"),
            {
                "title": "Current Story Project",
                "description": "A live renovation project being designed right now.",
                "category": self.category.pk,
                "location": "Bukit Timah",
                "style": "Minimal Warm",
                "status": InteriorDesignProject.STATUS_CURRENT,
            },
        )

        project = InteriorDesignProject.objects.get(title="Current Story Project")
        self.assertRedirects(response, reverse("idp_detail", args=[project.pk]))
        self.assertEqual(project.company, self.company)
        self.assertEqual(project.status, InteriorDesignProject.STATUS_CURRENT)

    def test_as_id_i_can_view_a_current_idp(self):
        project = InteriorDesignProject.objects.create(
            company=self.company,
            category=self.category,
            title="Viewing Current Story Project",
            description="Reviewing an active project detail page.",
            location="Kallang",
            style="Contemporary",
            status=InteriorDesignProject.STATUS_CURRENT,
        )

        response = self.client.get(reverse("idp_detail", args=[project.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, project.title)
        self.assertContains(response, project.get_status_display())

    def test_as_id_i_can_delete_a_current_idp(self):
        project = InteriorDesignProject.objects.create(
            company=self.company,
            category=self.category,
            title="Delete Current Story Project",
            description="This current project should be removed.",
            location="Toa Payoh",
            style="Modern Classic",
            status=InteriorDesignProject.STATUS_CURRENT,
        )

        response = self.client.post(reverse("idp_delete", args=[project.pk]))

        self.assertRedirects(response, reverse("idp_list"))
        self.assertFalse(InteriorDesignProject.objects.filter(pk=project.pk).exists())

    def test_as_id_i_can_search_my_past_idps(self):
        project = InteriorDesignProject.objects.create(
            company=self.company,
            category=self.category,
            title="Past Story Search Target",
            description="This completed project should be searchable in the past list.",
            location="Queenstown",
            style="Scandinavian",
            status=InteriorDesignProject.STATUS_PAST,
        )

        response = self.client.get(
            reverse("idp_list"),
            {"status": InteriorDesignProject.STATUS_PAST, "q": "Search Target"},
        )

        self.assertContains(response, project.title)
        self.assertEqual(response.status_code, 200)

    def test_as_id_i_can_delete_a_past_idp(self):
        project = InteriorDesignProject.objects.create(
            company=self.company,
            category=self.category,
            title="Delete Past Story Project",
            description="This finished project should be removed.",
            location="Jurong",
            style="Japandi",
            status=InteriorDesignProject.STATUS_PAST,
        )

        response = self.client.post(reverse("idp_delete", args=[project.pk]))

        self.assertRedirects(response, reverse("idp_list"))
        self.assertFalse(InteriorDesignProject.objects.filter(pk=project.pk).exists())

    def test_as_id_i_can_search_my_current_idps(self):
        project = InteriorDesignProject.objects.create(
            company=self.company,
            category=self.category,
            title="Current Story Search Target",
            description="This live project should be findable in current search results.",
            location="Sembawang",
            style="Minimalist",
            status=InteriorDesignProject.STATUS_CURRENT,
        )

        response = self.client.get(
            reverse("idp_list"),
            {"status": InteriorDesignProject.STATUS_CURRENT, "q": "Search Target"},
        )

        self.assertContains(response, project.title)
        self.assertEqual(response.status_code, 200)

    def test_as_id_i_can_update_a_past_idp(self):
        project = InteriorDesignProject.objects.create(
            company=self.company,
            category=self.category,
            title="Past Story Before Update",
            description="Original completed project details.",
            location="Woodlands",
            style="Classic",
            status=InteriorDesignProject.STATUS_PAST,
        )

        response = self.client.post(
            reverse("idp_update", args=[project.pk]),
            {
                "title": "Past Story After Update",
                "description": "Updated completed project details.",
                "category": self.category.pk,
                "location": "Clementi",
                "style": "Modern Classic",
                "status": InteriorDesignProject.STATUS_PAST,
            },
        )

        project.refresh_from_db()
        self.assertRedirects(response, reverse("idp_detail", args=[project.pk]))
        self.assertEqual(project.title, "Past Story After Update")
        self.assertEqual(project.location, "Clementi")
        self.assertEqual(project.status, InteriorDesignProject.STATUS_PAST)

    def test_as_id_i_can_view_a_past_idp(self):
        project = InteriorDesignProject.objects.create(
            company=self.company,
            category=self.category,
            title="Past Story Detail View",
            description="A completed design project detail page.",
            location="Yishun",
            style="Industrial",
            status=InteriorDesignProject.STATUS_PAST,
        )

        response = self.client.get(reverse("idp_detail", args=[project.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, project.title)
        self.assertContains(response, project.get_status_display())

    def test_as_id_i_can_create_a_past_idp(self):
        response = self.client.post(
            reverse("idp_create"),
            {
                "title": "Past Story Project",
                "description": "A finished renovation project to display in my portfolio.",
                "category": self.category.pk,
                "location": "Pasir Ris",
                "style": "Coastal",
                "status": InteriorDesignProject.STATUS_PAST,
            },
        )

        project = InteriorDesignProject.objects.get(title="Past Story Project")
        self.assertRedirects(response, reverse("idp_detail", args=[project.pk]))
        self.assertEqual(project.company, self.company)
        self.assertEqual(project.status, InteriorDesignProject.STATUS_PAST)

    def test_as_id_i_can_update_a_current_idp(self):
        project = InteriorDesignProject.objects.create(
            company=self.company,
            category=self.category,
            title="Current Story Before Update",
            description="Original active project details.",
            location="Serangoon",
            style="Japanese Minimal",
            status=InteriorDesignProject.STATUS_CURRENT,
        )

        response = self.client.post(
            reverse("idp_update", args=[project.pk]),
            {
                "title": "Current Story After Update",
                "description": "Updated active project details and progress.",
                "category": self.category.pk,
                "location": "Punggol",
                "style": "Warm Minimal",
                "status": InteriorDesignProject.STATUS_CURRENT,
            },
        )

        project.refresh_from_db()
        self.assertRedirects(response, reverse("idp_detail", args=[project.pk]))
        self.assertEqual(project.title, "Current Story After Update")
        self.assertEqual(project.location, "Punggol")
        self.assertEqual(project.status, InteriorDesignProject.STATUS_CURRENT)
