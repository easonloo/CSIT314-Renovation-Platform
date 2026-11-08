from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from projects.models import InteriorDesignProject

from .models import Favourite


class FavouriteControlsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.links = []
        self.current_form = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.current_form = {"attrs": attrs, "inputs": {}}
        elif tag == "input" and self.current_form is not None:
            if attrs.get("name"):
                self.current_form["inputs"][attrs["name"]] = attrs.get("value", "")
        elif tag == "a":
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == "form" and self.current_form is not None:
            self.forms.append(self.current_form)
            self.current_form = None


class FavouriteListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        customer_profile = UserProfile.objects.create(name="Customer")
        cls.customer = User.objects.create_user(username="favourite_filter_customer")
        cls.other_customer = User.objects.create_user(username="favourite_filter_other")
        for user in [cls.customer, cls.other_customer]:
            UserAccount.objects.create(user=user, profile=customer_profile)

        designer_profile = UserProfile.objects.create(name="Interior Designer")
        designer = User.objects.create_user(username="favourite_filter_designer")
        other_designer = User.objects.create_user(username="favourite_filter_designer2")
        for user in [designer, other_designer]:
            UserAccount.objects.create(user=user, profile=designer_profile)
        company = Company.objects.create(user=designer, name="NorthStar Studio")
        other_company = Company.objects.create(user=other_designer, name="Pacific Atelier")

        cls.living = Category.objects.create(name="Living Room")
        cls.kitchen = Category.objects.create(name="Kitchen")
        cls.private_category = Category.objects.create(name="Private Category")
        cls.unused_category = Category.objects.create(name="Unused Category")

        project_specs = [
            ("Sunlit Loft", company, cls.living, "Scandinavian"),
            ("Warm Kitchen", company, cls.kitchen, "Industrial"),
            ("Loft Retreat", other_company, cls.living, "Scandinavian"),
            ("Compact Nook", company, None, "Minimalist"),
        ]
        saved = []
        saved_at = timezone.now() - timedelta(days=4)
        for index, (title, studio, category, style) in enumerate(project_specs):
            project = InteriorDesignProject.objects.create(
                company=studio,
                category=category,
                title=title,
                style=style,
                shortlist_count=1,
            )
            favourite = Favourite.objects.create(user=cls.customer, project=project)
            Favourite.objects.filter(pk=favourite.pk).update(
                created_at=saved_at + timedelta(days=index),
            )
            saved.append(favourite)
        cls.older_living, cls.kitchen_favourite, cls.newer_living, cls.uncategorized = saved
        cls.oldest_order = saved
        cls.newest_order = list(reversed(saved))

        cls.private_project = InteriorDesignProject.objects.create(
            company=other_company,
            category=cls.private_category,
            title="Private Saved Project",
            style="Scandinavian",
            shortlist_count=1,
        )
        Favourite.objects.create(user=cls.other_customer, project=cls.private_project)
        InteriorDesignProject.objects.create(
            company=company,
            category=cls.living,
            title="Unsaved Loft",
            style="Scandinavian",
        )

    def setUp(self):
        self.client.force_login(self.customer)
        self.url = reverse("favourite_list")

    def test_default_page_shows_counts_and_newest_first(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["favourite_count"], 4)
        self.assertEqual(response.context["filtered_count"], 4)
        self.assertEqual(response.context["q"], "")
        self.assertEqual(response.context["category_filter"], "")
        self.assertEqual(response.context["sort_order"], "newest")
        self.assertEqual(list(response.context["favourites"]), self.newest_order)
        self.assertContains(response, 'aria-label="4 saved projects"')
        self.assertContains(response, "<span>4 projects</span>", html=True)

    def test_search_matches_title_company_category_and_style(self):
        searches = [
            ("  LOFT  ", [self.newer_living, self.older_living]),
            ("PACIFIC", [self.newer_living]),
            ("kitchen", [self.kitchen_favourite]),
            ("ScAnDiNaViAn", [self.newer_living, self.older_living]),
        ]
        for query, expected in searches:
            with self.subTest(query=query):
                response = self.client.get(self.url, {"q": query})
                self.assertEqual(list(response.context["favourites"]), expected)

    def test_search_keeps_total_and_filtered_counts_distinct(self):
        response = self.client.get(self.url, {"q": "Loft"})

        self.assertEqual(response.context["favourite_count"], 4)
        self.assertEqual(response.context["filtered_count"], 2)
        self.assertEqual(response.context["q"], "Loft")
        self.assertContains(response, 'value="Loft"')
        self.assertContains(response, "<span>2 projects</span>", html=True)
        self.assertContains(response, "Filtered favourites")

    def test_category_choices_count_only_the_customers_saved_projects(self):
        response = self.client.get(self.url)

        self.assertEqual(
            list(response.context["categories"]),
            [
                {
                    "project__category_id": self.kitchen.pk,
                    "project__category__name": "Kitchen",
                    "count": 1,
                },
                {
                    "project__category_id": self.living.pk,
                    "project__category__name": "Living Room",
                    "count": 2,
                },
            ],
        )
        self.assertNotContains(response, "Private Category")
        self.assertNotContains(response, "Unused Category")

    def test_category_filter_shows_only_matching_saved_projects(self):
        response = self.client.get(self.url, {"category": self.living.pk})

        self.assertEqual(
            list(response.context["favourites"]),
            [self.newer_living, self.older_living],
        )
        self.assertEqual(response.context["category_filter"], str(self.living.pk))
        self.assertEqual(response.context["favourite_count"], 4)
        self.assertEqual(response.context["filtered_count"], 2)

    def test_oldest_sort_uses_the_date_saved(self):
        response = self.client.get(self.url, {"sort": "oldest"})

        self.assertEqual(list(response.context["favourites"]), self.oldest_order)
        self.assertEqual(response.context["sort_order"], "oldest")
        self.assertContains(response, 'value="oldest" selected')

    def test_equal_save_dates_have_a_stable_order(self):
        Favourite.objects.filter(user=self.customer).update(created_at=timezone.now())
        ids = [favourite.pk for favourite in self.oldest_order]

        for sort, expected in [("oldest", ids), ("newest", list(reversed(ids)))]:
            with self.subTest(sort=sort):
                response = self.client.get(self.url, {"sort": sort})
                self.assertEqual(
                    list(response.context["favourites"].values_list("pk", flat=True)),
                    expected,
                )

    def test_search_category_and_sort_work_together(self):
        response = self.client.get(
            self.url,
            {"q": "Scandinavian", "category": self.living.pk, "sort": "oldest"},
        )

        self.assertEqual(
            list(response.context["favourites"]),
            [self.older_living, self.newer_living],
        )
        self.assertEqual(response.context["filtered_count"], 2)
        self.assertEqual(response.context["category_filter"], str(self.living.pk))
        self.assertEqual(response.context["sort_order"], "oldest")

        response = self.client.get(
            self.url,
            {"q": "Industrial", "category": self.living.pk},
        )
        self.assertEqual(list(response.context["favourites"]), [])
        self.assertEqual(response.context["filtered_count"], 0)
        self.assertContains(response, "No matching projects")

    def test_unknown_sort_defaults_to_newest(self):
        response = self.client.get(self.url, {"sort": "unknown"})

        self.assertEqual(response.context["sort_order"], "newest")
        self.assertEqual(list(response.context["favourites"]), self.newest_order)

    def test_invalid_or_unavailable_categories_default_to_all(self):
        categories = [
            "not-a-number",
            "-1",
            str(10 ** 80),
            str(self.private_category.pk),
            str(self.unused_category.pk),
        ]
        for category in categories:
            with self.subTest(category=category):
                response = self.client.get(self.url, {"category": category, "q": "Loft"})
                self.assertEqual(response.context["category_filter"], "")
                self.assertEqual(
                    list(response.context["favourites"]),
                    [self.newer_living, self.older_living],
                )

    def test_user_id_parameter_cannot_expose_another_collection(self):
        response = self.client.get(self.url, {"user_id": self.other_customer.pk})

        self.assertEqual(response.context["favourite_count"], 4)
        self.assertEqual(list(response.context["favourites"]), self.newest_order)
        self.assertNotContains(response, self.private_project.title)
        self.assertNotContains(response, self.private_category.name)

    def test_no_matches_shows_the_search_empty_state_and_clear_link(self):
        response = self.client.get(self.url, {"q": "nothing-matches"})

        self.assertEqual(response.context["favourite_count"], 4)
        self.assertEqual(response.context["filtered_count"], 0)
        self.assertContains(response, "No matching projects")
        self.assertNotContains(response, "Your collection is waiting")
        self.assertContains(response, 'value="nothing-matches"')
        self.assertContains(response, "Clear filters")
        parser = FavouriteControlsParser()
        parser.feed(response.content.decode())
        self.assertTrue(any(link.get("href") == self.url for link in parser.links))

    def test_empty_collection_shows_zero_counts_and_collection_instructions(self):
        self.client.force_login(self.other_customer)
        Favourite.objects.filter(user=self.other_customer).delete()

        response = self.client.get(self.url)

        self.assertEqual(response.context["favourite_count"], 0)
        self.assertEqual(response.context["filtered_count"], 0)
        self.assertEqual(list(response.context["categories"]), [])
        self.assertContains(response, 'aria-label="0 saved projects"')
        self.assertContains(response, "Your collection is waiting")
        self.assertNotContains(response, "No matching projects")

    def test_controls_preserve_search_category_and_sort(self):
        query = "Loft & light"
        response = self.client.get(
            self.url,
            {"q": query, "category": self.living.pk, "sort": "oldest"},
        )
        parser = FavouriteControlsParser()
        parser.feed(response.content.decode())
        for form_class in ["favourites-search", "favourites-sort"]:
            form = next(
                form for form in parser.forms
                if form_class in form["attrs"].get("class", "").split()
            )
            self.assertEqual(form["attrs"].get("action"), self.url)
            self.assertEqual(form["inputs"]["q"], query)
            self.assertEqual(form["inputs"]["category"], str(self.living.pk))
            if form_class == "favourites-search":
                self.assertEqual(form["inputs"]["sort"], "oldest")

        category_links = [
            link for link in parser.links
            if "favourite-chip" in link.get("class", "").split()
        ]
        self.assertEqual(len(category_links), 3)
        for link in category_links:
            params = parse_qs(urlsplit(link["href"]).query)
            self.assertEqual(params["q"], [query])
            self.assertEqual(params["sort"], ["oldest"])
        selected = [link for link in category_links if "is-selected" in link["class"]]
        self.assertEqual(len(selected), 1)
        self.assertEqual(
            parse_qs(urlsplit(selected[0]["href"]).query)["category"],
            [str(self.living.pk)],
        )

    def test_browsing_filters_does_not_change_favourites_or_shortlists(self):
        before_favourites = list(Favourite.objects.order_by("pk").values())
        before_counts = list(
            InteriorDesignProject.objects.order_by("pk").values_list("pk", "shortlist_count")
        )

        for params in [{}, {"q": "Loft"}, {"category": self.living.pk, "sort": "oldest"}]:
            self.client.get(self.url, params)

        self.assertEqual(list(Favourite.objects.order_by("pk").values()), before_favourites)
        self.assertEqual(
            list(InteriorDesignProject.objects.order_by("pk").values_list("pk", "shortlist_count")),
            before_counts,
        )

    def test_blank_search_behaves_like_no_search(self):
        response = self.client.get(self.url, {"q": "   "})

        self.assertEqual(response.context["q"], "")
        self.assertEqual(response.context["filtered_count"], 4)
        self.assertEqual(list(response.context["favourites"]), self.newest_order)
