import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django


django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from projects.demo_images import DemoImageController
from projects.models import InteriorDesignProject


def ensure_sample_designer():
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username="housedesignerz",
        defaults={
            "email": "hello@housedesignerz.com",
            "first_name": "House",
            "last_name": "Designerz",
        },
    )
    user.set_password("Designer123!")
    user.save()

    profile, _ = UserProfile.objects.get_or_create(
        name="Interior Designer",
        defaults={"description": "Design studio for bespoke renovation projects."},
    )
    UserAccount.objects.update_or_create(user=user, defaults={"profile": profile})

    company, _ = Company.objects.get_or_create(
        user=user,
        defaults={
            "name": "HouseDesignerz Pte Ltd",
            "email": "hello@housedesignerz.com",
            "phone": "+65 6123 4567",
            "website": "https://housedesignerz.example",
            "address": "18 Orchard Road, Singapore 238840",
            "description": "Luxury residential interior design and renovation studio.",
        },
    )

    for category_name in ["Residential", "Living Room", "Kitchen", "HDB Renovation"]:
        Category.objects.get_or_create(name=category_name)

    project_specs = [
        ("Modern Family Villa", "Residential", "A warm modern family home built around natural light and open-plan living.", "Singapore"),
        ("Bespoke Calm Retreat", "Living Room", "Soft textures and a layered palette create a serene urban living environment.", "Bukit Timah"),
        ("Chef's Kitchen Concept", "Kitchen", "A sophisticated kitchen that balances practicality, storage and statement materials.", "Kallang"),
        ("HDB Smart Redesign", "HDB Renovation", "Compact space planning with elegant finishes and clever storage throughout.", "Toa Payoh"),
    ]

    image_updates = 0
    missing_images = 0
    preserved_uploads = 0
    for title, category_name, description, location in project_specs:
        category = Category.objects.get(name=category_name)
        project, _ = InteriorDesignProject.objects.get_or_create(
            company=company,
            title=title,
            defaults={
                "category": category,
                "description": description,
                "location": location,
                "style": "Contemporary",
                "status": "current",
            },
        )
        project.category = category
        project.description = description
        project.location = location
        project.style = "Contemporary"
        project.status = "current"
        current_image = project.image.name or ""
        if (
            not current_image
            or current_image in DemoImageController.LEGACY_IMAGES
            or current_image.startswith(f"{DemoImageController.DIRECTORY}/")
        ):
            chosen_image = DemoImageController.image_for(category_name, title)
            if chosen_image:
                project.image = chosen_image
                image_updates += int(current_image != chosen_image)
            else:
                missing_images += 1
        else:
            preserved_uploads += 1
        project.save()

    print(f"Designer user: {user.username} / password: Designer123!")
    print(f"Company: {company.name}")
    print(f"Virtual image catalog: {settings.MEDIA_ROOT / DemoImageController.DIRECTORY}")
    print(f"Category-matched images updated: {image_updates}")
    print(f"Custom uploaded photos preserved: {preserved_uploads}")
    if missing_images:
        print(f"Matching catalog images unavailable for {missing_images} projects; existing images retained.")
    print("Sample IDPs created.")


if __name__ == "__main__":
    ensure_sample_designer()
