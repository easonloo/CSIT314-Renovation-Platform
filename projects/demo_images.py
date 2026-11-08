import re
import unicodedata

from django.core.files.storage import default_storage
from django.db import transaction

from .models import InteriorDesignProject


class DemoImageController:
    """Match demo projects to locally stored, clearly labelled virtual room renders."""

    DIRECTORY = "demo_idp_catalog"
    ROOM_IMAGES = {
        "living_room": ("living room", "lounge", "family room"),
        "kitchen": ("kitchen",),
        "master_bedroom": ("master bedroom", "main bedroom", "bedroom"),
        "bathroom": ("bathroom", "ensuite", "washroom"),
        "dining_room": ("dining room", "dining area", "dining"),
        "home_office": ("home office", "office"),
        "balcony": ("balcony",),
        "entryway": ("entryway", "entry hall", "foyer", "entrance"),
        "guest_bedroom": ("guest bedroom", "guest room"),
        "children_room": (
            "children s room", "childrens room", "children room", "kids room", "kid s room",
            "children s bedroom", "childrens bedroom", "children bedroom", "kids bedroom",
        ),
        "laundry_room": ("laundry room", "laundry", "utility room"),
        "walk_in_wardrobe": ("walk in wardrobe", "walk in closet", "dressing room"),
        "study": ("study",),
        "entertainment_room": ("entertainment room", "home cinema", "media room"),
        "nursery": ("nursery", "baby room"),
        "reading_nook": ("reading nook", "reading corner", "library"),
        "storage_room": ("storage room", "storeroom", "storage"),
        "patio": ("patio", "terrace", "courtyard"),
        "pantry": ("pantry",),
        "home_gym": ("home gym", "gym", "fitness room"),
    }
    LEGACY_IMAGES = frozenset(f"sample_idp/sample_{index}.png" for index in range(1, 6))

    @staticmethod
    def _normalize(value):
        value = unicodedata.normalize("NFKC", str(value or "")).casefold()
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    @classmethod
    def room_for(cls, category_name, title=""):
        # Longest matches select 'guest bedroom' before the generic 'bedroom'.
        terms = sorted(
            ((term, room) for room, aliases in cls.ROOM_IMAGES.items() for term in aliases),
            key=lambda pair: len(pair[0]),
            reverse=True,
        )
        for text in (category_name, title):
            normalized = f" {cls._normalize(text)} "
            for term, room in terms:
                if f" {term} " in normalized:
                    return room
        return "living_room"

    @classmethod
    def image_for(cls, category_name, title=""):
        room = cls.room_for(category_name, title)
        name = f"{cls.DIRECTORY}/{room}.png"
        return name if default_storage.exists(name) else ""

    @classmethod
    @transaction.atomic
    def assign_images(cls, *, dry_run=False):
        result = {"updated": 0, "skipped": 0, "missing": 0}
        changed = []
        projects = InteriorDesignProject.objects.select_related("category").order_by("pk")
        for project in projects:
            current = project.image.name or ""
            if current and current not in cls.LEGACY_IMAGES and not current.startswith(f"{cls.DIRECTORY}/"):
                result["skipped"] += 1
                continue
            category_name = project.category.name if project.category_id else ""
            image = cls.image_for(category_name, project.title)
            if not image:
                result["missing"] += 1
                continue
            if current == image:
                result["skipped"] += 1
                continue
            project.image = image
            changed.append(project)
            result["updated"] += 1
        if changed and not dry_run:
            InteriorDesignProject.objects.bulk_update(changed, ["image"], batch_size=200)
        return result
