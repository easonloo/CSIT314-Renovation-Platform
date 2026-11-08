import random
import re
from collections import Counter
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from faker import Faker

from categories.models import Category
from companies.models import Company
from favourites.models import Favourite
from projects.models import InteriorDesignProject
from projects.demo_images import DemoImageController
from reports.models import ProjectView
from reviews.models import ProjectReview

from .models import UserAccount, UserProfile


class DemoDataError(ValueError):
    pass


class DemoDataController:
    """Build an isolated, repeatable synthetic dataset without resetting real data."""

    DEFAULT_PASSWORD = "Demo314!Pass2026"
    ROLE_DESCRIPTIONS = {
        "User Admin": "Manages user accounts and profiles.",
        "Interior Designer": "Manages company information and design projects.",
        "Customer": "Discovers projects and saves favourites.",
        "Platform Management": "Manages categories and platform reports.",
    }
    SPACES = (
        "Living Room", "Kitchen", "Master Bedroom", "Bathroom", "Dining Room",
        "Home Office", "Balcony", "Entryway", "Guest Bedroom", "Children's Room",
        "Laundry Room", "Walk-in Wardrobe", "Study", "Entertainment Room", "Nursery",
        "Reading Nook", "Storage Room", "Patio", "Pantry", "Home Gym",
    )
    PROPERTY_TYPES = ("HDB", "Condominium", "Landed Home", "Studio Apartment", "Commercial")
    STYLES = (
        "Scandinavian", "Contemporary", "Minimalist", "Industrial", "Japandi",
        "Modern Classic", "Coastal", "Eclectic", "Warm Minimalist", "Traditional",
    )
    LOCATIONS = (
        "Tampines", "Bishan", "Queenstown", "Punggol", "Jurong East", "Woodlands",
        "Bedok", "Toa Payoh", "Clementi", "Bukit Timah", "Sengkang", "Yishun",
    )
    COUNT_KEYS = (
        "users", "accounts", "profiles", "companies", "categories", "projects",
        "favourites", "views", "reviews",
    )

    def __init__(self, *, count=100, seed=42, prefix="demo314", password=DEFAULT_PASSWORD):
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1000:
            raise DemoDataError("Count must be an integer between 1 and 1000.")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise DemoDataError("Seed must be an integer.")
        if not isinstance(prefix, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,19}", prefix) is None:
            raise DemoDataError("Prefix must start with a lowercase letter and contain 1–20 lowercase letters, digits or underscores.")
        if not isinstance(password, str) or len(password) < 8:
            raise DemoDataError("The demo password must contain at least 8 characters.")
        self.count = count
        self.seed = seed
        self.prefix = prefix
        self.password = password
        self.now = timezone.now()
        self.today = timezone.localtime(self.now).replace(hour=0, minute=0, second=0, microsecond=0)
        self.fake = Faker("en_US")
        self.fake.seed_instance(seed)
        self.created = dict.fromkeys(self.COUNT_KEYS, 0)
        self.users = []
        self.customers = []
        self.companies = []
        self.projects = []
        self.categories = []

    @classmethod
    def generate(cls, **options):
        return cls(**options).run()

    def _random(self, key):
        return random.Random(f"{self.seed}:{self.prefix}:{key}")

    def _timestamp(self, age_days, key):
        rng = self._random(key)
        timestamp = self.today - timedelta(days=age_days)
        timestamp += timedelta(hours=rng.randrange(24), minutes=rng.randrange(60))
        return min(timestamp, self.now)

    def _user(self, username, profile, index=0):
        User = get_user_model()
        rng = self._random(username)
        age_days = (180, 0, 2, 10)[index] if index < 4 else rng.randint(14, 120)
        first_name, last_name = self.fake.first_name(), self.fake.last_name()
        matches = list(User.objects.filter(username__iexact=username)[:2])
        if len(matches) > 1 or (matches and matches[0].username != username):
            raise DemoDataError(
                f"Username '{username}' conflicts with an existing account ignoring case. "
                "Choose another --prefix; the existing account was not changed."
            )
        user = matches[0] if matches else None
        expected_email = f"{username}@example.test"
        if user is not None:
            account = UserAccount.objects.filter(user=user).first()
            if user.email != expected_email or account is None or account.profile_id != profile.pk:
                raise DemoDataError(
                    f"Username '{username}' conflicts with an existing account. "
                    "Choose another --prefix; the existing account was not changed."
                )
        else:
            user = User.objects.create_user(
                username=username,
                password=self.password,
                email=expected_email,
                first_name=first_name,
                last_name=last_name,
                date_joined=self._timestamp(age_days, username),
                is_active=(index + 1) % 10 != 0,
            )
            UserAccount.objects.create(user=user, profile=profile)
            self.created["users"] += 1
            self.created["accounts"] += 1
        self.users.append(user)
        return user

    def _company(self, designer, index):
        company_name = f"{self.fake.last_name()} & {self.fake.last_name()} Interiors {index + 1:03d}"
        company, created = Company.objects.get_or_create(
            user=designer,
            defaults={
                "name": company_name,
                "email": f"studio{index + 1:03d}.{self.prefix}@example.test",
                "phone": f"+65 6{index + 1:07d}",
                "website": f"https://{self.prefix}-studio-{index + 1:03d}.example.test",
                "address": f"{index + 1} Example Design Avenue, Singapore",
                "description": f"Synthetic demonstration studio specialising in {self.STYLES[index % len(self.STYLES)]} renovations.",
            },
        )
        if created:
            Company.objects.filter(pk=company.pk).update(
                created_at=designer.date_joined, updated_at=designer.date_joined,
            )
            company.refresh_from_db()
            self.created["companies"] += 1
        self.companies.append(company)
        return company

    def _project(self, company, index):
        rng = self._random(f"project:{index}")
        room = self.SPACES[index % len(self.SPACES)]
        title = f"{self.prefix}: {index + 1:03d} {room} Renovation"
        style = rng.choice(self.STYLES)
        description = f"A {style.lower()} {room.lower()} with practical storage, natural light and durable finishes. {self.fake.sentence()}"
        category = self.categories[index % len(self.categories)]
        project, created = InteriorDesignProject.objects.get_or_create(
            company=company,
            title=title,
            defaults={
                "description": description,
                "category": category,
                "location": rng.choice(self.LOCATIONS),
                "style": style,
                "status": InteriorDesignProject.STATUS_CURRENT if index % 2 == 0 else InteriorDesignProject.STATUS_PAST,
                "image": DemoImageController.image_for(category.name, title),
            },
        )
        if created:
            age_days = 0 if index == 0 else 90 if index == 1 else rng.randint(0, 90)
            created_at = max(company.created_at, self._timestamp(age_days, title))
            updated_at = min(self.now, created_at + timedelta(days=rng.randrange(8)))
            InteriorDesignProject.objects.filter(pk=project.pk).update(
                created_at=created_at, updated_at=updated_at,
            )
            project.refresh_from_db()
            self.created["projects"] += 1
        self.projects.append(project)

    def _activity_time(self, project, customer, slot):
        candidates = (
            self.now,
            self.today - timedelta(days=self.today.weekday()),
            self.today.replace(day=1),
            self.now - timedelta(days=35),
            self.now - timedelta(days=75),
        )
        return max(project.created_at, customer.date_joined, candidates[slot % len(candidates)])

    def _favourites(self):
        for index, customer in enumerate(self.customers):
            rng = self._random(f"favourites:{index}")
            projects = rng.sample(self.projects, min(3, len(self.projects)))
            for slot, project in enumerate(projects):
                favourite, created = Favourite.objects.get_or_create(user=customer, project=project)
                if created:
                    Favourite.objects.filter(pk=favourite.pk).update(
                        created_at=self._activity_time(project, customer, index + slot),
                    )
                    self.created["favourites"] += 1

    def _views(self):
        for index, project in enumerate(self.projects):
            existing = dict(
                ProjectView.objects.filter(project=project)
                .order_by()
                .values("viewer_id")
                .annotate(total=Count("pk"))
                .values_list("viewer_id", "total")
            )
            required = Counter()
            for slot in range(5):
                customer = self.customers[(index + slot) % len(self.customers)]
                required[customer.pk] += 1
                if existing.get(customer.pk, 0) >= required[customer.pk]:
                    continue
                event = ProjectView.objects.create(project=project, viewer=customer)
                ProjectView.objects.filter(pk=event.pk).update(
                    viewed_at=self._activity_time(project, customer, slot),
                )
                self.created["views"] += 1

    def _reviews(self):
        for index, project in enumerate(self.projects):
            customer = self.customers[index % len(self.customers)]
            rng = self._random(f"review:{index}")
            review, created = ProjectReview.objects.get_or_create(
                customer=customer,
                project=project,
                defaults={
                    "rating": rng.randint(1, 5),
                    "comment": f"Demonstration review: {rng.choice(('Thoughtful layout', 'Practical storage', 'Beautiful lighting', 'Comfortable finishes', 'Creative use of space'))}. {self.fake.sentence()}",
                },
            )
            if created:
                timestamp = self._activity_time(project, customer, index)
                ProjectReview.objects.filter(pk=review.pk).update(
                    created_at=timestamp, updated_at=timestamp,
                )
                self.created["reviews"] += 1

    def _update_metrics(self):
        for project in self.projects:
            project.view_count = project.view_events.count()
            project.shortlist_count = project.favourited_by.count()
        InteriorDesignProject.objects.bulk_update(
            self.projects, ["view_count", "shortlist_count"], batch_size=200,
        )

    @transaction.atomic
    def run(self):
        profiles = {}
        for name, description in self.ROLE_DESCRIPTIONS.items():
            profiles[name], created = UserProfile.objects.get_or_create(
                name=name, defaults={"description": description},
            )
            self.created["profiles"] += int(created)

        for index in range(self.count):
            name = f"{self.prefix}: {index + 1:03d} {self.PROPERTY_TYPES[(index // len(self.SPACES)) % len(self.PROPERTY_TYPES)]} {self.SPACES[index % len(self.SPACES)]}"
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={"description": "Synthetic renovation category for assignment testing and demonstration."},
            )
            self.categories.append(category)
            self.created["categories"] += int(created)

        for index in range(self.count):
            designer = self._user(
                f"{self.prefix}_designer_{index + 1:03d}", profiles["Interior Designer"], index,
            )
            company = self._company(designer, index)
            self._project(company, index * 2)
            self._project(company, index * 2 + 1)
        for index in range(self.count):
            self.customers.append(self._user(
                f"{self.prefix}_customer_{index + 1:03d}", profiles["Customer"], index,
            ))
        self._user(f"{self.prefix}_admin", profiles["User Admin"])
        self._user(f"{self.prefix}_pm", profiles["Platform Management"])

        self._favourites()
        self._views()
        self._reviews()
        self._update_metrics()
        return {
            "created": dict(self.created),
            "dataset": {
                "users": len(self.users),
                "accounts": len(self.users),
                "profiles": len(profiles),
                "companies": len(self.companies),
                "categories": len(self.categories),
                "projects": len(self.projects),
                "favourites": Favourite.objects.filter(project__in=self.projects).count(),
                "views": ProjectView.objects.filter(project__in=self.projects).count(),
                "reviews": ProjectReview.objects.filter(project__in=self.projects).count(),
            },
            "logins": {
                "User Admin": f"{self.prefix}_admin",
                "Interior Designer": f"{self.prefix}_designer_001",
                "Customer": f"{self.prefix}_customer_001",
                "Platform Management": f"{self.prefix}_pm",
            },
        }
