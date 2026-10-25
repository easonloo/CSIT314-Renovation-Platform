import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django


django.setup()

from PIL import Image, ImageDraw
from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from projects.models import InteriorDesignProject


def create_sample_image(path: Path, bg_color, accent_color, label):
    img = Image.new("RGB", (1200, 900), bg_color)
    draw = ImageDraw.Draw(img)

    for i in range(8):
        x = 80 + i * 130
        y = 250 + (i % 2) * 110
        draw.rounded_rectangle(
            [x, y, x + 90, y + 150],
            radius=18,
            fill=accent_color if i % 2 == 0 else (255, 255, 255),
        )

    draw.rounded_rectangle([180, 150, 1020, 700], radius=30, fill=(255, 255, 255, 90))
    draw.rounded_rectangle([220, 220, 980, 640], radius=26, fill=(255, 255, 255, 180))
    draw.rectangle([250, 450, 950, 560], fill=(245, 243, 239))

    draw.text((360, 300), label, fill=(20, 20, 20), font=None)
    draw.text((320, 510), "HouseDesignerz", fill=(80, 80, 80), font=None)
    img.save(path)


def generate_images():
    media_dir = Path(settings.MEDIA_ROOT) / "sample_idp"
    media_dir.mkdir(parents=True, exist_ok=True)

    palette = [
        ((245, 232, 220), (168, 116, 79), "Modern Villa"),
        ((228, 240, 232), (73, 120, 94), "Minimal Loft"),
        ((236, 236, 245), (109, 111, 171), "Warm Residence"),
        ((240, 235, 225), (124, 92, 56), "Coastal Living"),
    ]

    paths = []
    for index, (bg, accent, label) in enumerate(palette, start=1):
        file_path = media_dir / f"sample_{index}.png"
        create_sample_image(file_path, bg, accent, label)
        paths.append(file_path)

    return paths


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

    image_paths = generate_images()
    for title, category_name, description, location in project_specs:
        category = Category.objects.get(name=category_name)
        chosen_image = random.choice(image_paths)
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
        project.image.name = chosen_image.relative_to(settings.MEDIA_ROOT).as_posix()
        project.save()

    print(f"Designer user: {user.username} / password: Designer123!")
    print(f"Company: {company.name}")
    print(f"Images generated in: {settings.MEDIA_ROOT / 'sample_idp'}")
    print("Sample IDPs created.")


if __name__ == "__main__":
    ensure_sample_designer()
