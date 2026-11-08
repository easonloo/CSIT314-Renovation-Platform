from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from .models import UserAccount, UserProfile


class ProfileControlsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.forms = []
        self.current_link = None
        self.current_form = None
        self.current_button = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.current_link = {**attrs, "text": ""}
        elif tag == "form":
            self.current_form = {"attrs": attrs, "inputs": {}, "buttons": []}
        elif tag == "input" and self.current_form is not None and attrs.get("name"):
            self.current_form["inputs"][attrs["name"]] = attrs.get("value", "")
        elif tag == "button" and self.current_form is not None:
            self.current_button = {**attrs, "text": ""}

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_link["text"] += data
        if self.current_button is not None:
            self.current_button["text"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.current_link is not None:
            self.current_link["text"] = self.current_link["text"].strip()
            self.links.append(self.current_link)
            self.current_link = None
        elif tag == "button" and self.current_button is not None:
            self.current_button["text"] = self.current_button["text"].strip()
            self.current_form["buttons"].append(self.current_button)
            self.current_button = None
        elif tag == "form" and self.current_form is not None:
            self.forms.append(self.current_form)
            self.current_form = None


class ProfileListControlsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_profile = UserProfile.objects.create(name="User Admin")
        cls.customer_profile = UserProfile.objects.create(name="Customer")
        cls.custom_profile = UserProfile.objects.create(name="Design & Build")
        cls.suspended_profile = UserProfile.objects.create(name="Archived Partners", is_active=False)
        cls.empty_profile = UserProfile.objects.create(name="Empty Custom Group")
        cls.admin = get_user_model().objects.create_user(username="profile_controls_admin")
        UserAccount.objects.create(user=cls.admin, profile=cls.admin_profile)

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("profile_list")

    def controls(self, response):
        parser = ProfileControlsParser()
        parser.feed(response.content.decode())
        return parser

    def assert_all_profiles_visible(self, response):
        self.assertEqual(response.status_code, 200)
        profiles = list(response.context["profiles"])
        self.assertCountEqual(profiles, UserProfile.objects.all())
        self.assertEqual(response.context["filtered_count"], 5)
        self.assertEqual(response.context["profile_counts"], {"total": 5, "active": 4, "suspended": 1})
        for profile in profiles:
            self.assertContains(response, escape(profile.name))
            self.assertEqual(profile.user_count, 1 if profile.pk == self.admin_profile.pk else 0)
        self.assertContains(response, "Showing 5 of 5 profiles")

    def test_default_page_includes_custom_suspended_and_empty_profiles(self):
        self.assert_all_profiles_visible(self.client.get(self.url))

    def test_all_link_clears_both_search_and_status_and_restores_every_profile(self):
        response = self.client.get(self.url, {"q": "Archived", "status": "suspended"})
        self.assertEqual(list(response.context["profiles"]), [self.suspended_profile])
        links = [
            link for link in self.controls(response).links
            if "profile-filter" in link.get("class", "").split() and link["text"] == "All"
        ]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["href"], self.url)

        self.assert_all_profiles_visible(self.client.get(links[0]["href"]))

    def test_filtered_results_provide_a_show_all_profiles_reset_link(self):
        response = self.client.get(self.url, {"q": "Design", "status": "active"})
        self.assertEqual(list(response.context["profiles"]), [self.custom_profile])
        links = [link for link in self.controls(response).links if link["text"] == "Show all profiles"]
        self.assertTrue(links)
        self.assertTrue(all(link["href"] == self.url for link in links))

        self.assert_all_profiles_visible(self.client.get(links[0]["href"]))

    def test_no_matches_retains_empty_message_and_has_a_working_reset_link(self):
        response = self.client.get(self.url, {"q": "no-such-profile", "status": "suspended"})
        self.assertContains(response, "No profiles found.")
        self.assertEqual(response.context["filtered_count"], 0)
        links = [link for link in self.controls(response).links if link["text"] == "Show all profiles"]
        self.assertTrue(links)
        self.assertEqual(links[0]["href"], self.url)

        self.assert_all_profiles_visible(self.client.get(links[0]["href"]))

    def test_status_links_preserve_ampersands_in_search_and_mark_current_status(self):
        response = self.client.get(self.url, {"q": "Design & Build", "status": "active"})
        links = self.controls(response).links
        for text, status in [("Active", "active"), ("Suspended", "suspended")]:
            with self.subTest(status=status):
                link = next(
                    link for link in links
                    if "profile-filter" in link.get("class", "").split() and link["text"] == text
                )
                parsed = urlsplit(link["href"])
                self.assertEqual(parsed.path or self.url, self.url)
                self.assertEqual(parse_qs(parsed.query), {"q": ["Design & Build"], "status": [status]})
                self.assertEqual(link.get("aria-current"), "page" if status == "active" else None)
                filtered = self.client.get(urljoin(self.url, link["href"]))
                self.assertEqual(filtered.context["q"], "Design & Build")
                self.assertEqual(filtered.context["status_filter"], status)
                self.assertEqual(
                    list(filtered.context["profiles"]), [self.custom_profile] if status == "active" else [],
                )

    def test_search_form_retains_status_and_has_a_dedicated_search_submit(self):
        response = self.client.get(self.url, {"q": "Archived", "status": "suspended"})
        form = next(form for form in self.controls(response).forms if form["attrs"].get("role") == "search")
        self.assertEqual(form["attrs"].get("method", "").lower(), "get")
        self.assertEqual(form["attrs"]["action"], self.url)
        self.assertEqual(form["inputs"]["q"], "Archived")
        self.assertEqual(form["inputs"]["status"], "suspended")
        self.assertTrue(any(
            button.get("type", "submit") == "submit" and button["text"] == "Search"
            for button in form["buttons"]
        ))
        self.assertFalse(any(button.get("name") == "status" for button in form["buttons"]))

        submitted = self.client.get(form["attrs"]["action"], form["inputs"])
        self.assertEqual(list(submitted.context["profiles"]), [self.suspended_profile])
        self.assertEqual(submitted.context["status_filter"], "suspended")
