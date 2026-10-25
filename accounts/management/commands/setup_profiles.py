from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import UserAccount, UserProfile
from categories.models import Category
from companies.models import Company
from projects.models import InteriorDesignProject


class Command(BaseCommand):
    help = "Create the initial profiles, optional User Admin, and sample Interior Designer accounts."

    SAMPLE_DESIGNERS = [
        {
            "username": "designer_aurora",
            "password": "Designer@123",
            "email": "aurora@renovation.local",
            "company_name": "Aurora Nest Studio",
            "phone": "+65 8123 1111",
            "website": "https://auroranest.example",
            "address": "1 Marina Boulevard, Singapore",
            "description": "Modern apartment makeovers and warm minimalist interiors.",
            "projects": [
                (
                    "Sunlit Minimalist Living Room",
                    "Living Room",
                    "An airy living space with natural timber, soft neutral finishes, and generous daylight.",
                    "Bukit Timah",
                    "Warm Minimalist",
                    "sample_idp/sample_1.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
                (
                    "Calm Contemporary Bedroom",
                    "Bedroom",
                    "A restful bedroom renovation combining built-in storage with layered textures.",
                    "Queenstown",
                    "Contemporary",
                    "sample_idp/sample_2.png",
                    InteriorDesignProject.STATUS_PAST,
                ),
                (
                    "Open-Plan Family Kitchen",
                    "Kitchen",
                    "A bright, practical kitchen designed to connect with the home's dining area.",
                    "Tampines",
                    "Scandinavian",
                    "sample_idp/sample_3.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
            ],
        },
        {
            "username": "designer_bloom",
            "password": "Designer@456",
            "email": "bloom@renovation.local",
            "company_name": "Bloom & Form Interiors",
            "phone": "+65 8123 2222",
            "website": "https://bloomandform.example",
            "address": "88 Orchard Road, Singapore",
            "description": "Boutique residential projects with natural textures and soft lighting.",
            "projects": [
                (
                    "Textured City Living Room",
                    "Living Room",
                    "A welcoming apartment lounge with tactile finishes and carefully layered lighting.",
                    "Orchard",
                    "Modern Eclectic",
                    "sample_idp/sample_2.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
                (
                    "Soft-Tone Ensuite Bathroom",
                    "Bathroom",
                    "A compact bathroom refreshed with a light palette and clean, practical detailing.",
                    "Novena",
                    "Contemporary",
                    "sample_idp/sample_3.png",
                    InteriorDesignProject.STATUS_PAST,
                ),
                (
                    "Natural Oak Kitchen",
                    "Kitchen",
                    "A custom kitchen using warm wood tones, durable surfaces, and efficient storage.",
                    "River Valley",
                    "Natural Modern",
                    "sample_idp/sample_4.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
            ],
        },
        {
            "username": "designer_cove",
            "password": "Designer@789",
            "email": "cove@renovation.local",
            "company_name": "Cove Living Co.",
            "phone": "+65 8123 3333",
            "website": "https://coveliving.example",
            "address": "25 Kallang Way, Singapore",
            "description": "Functional family homes and compact urban renovations.",
            "projects": [
                (
                    "Compact HDB Living Space",
                    "Living Room",
                    "A compact HDB living room planned to feel open while providing flexible family storage.",
                    "Toa Payoh",
                    "Modern",
                    "sample_idp/sample_4.png",
                    InteriorDesignProject.STATUS_PAST,
                ),
                (
                    "Family-Friendly Bedroom",
                    "Bedroom",
                    "A comfortable bedroom with practical built-ins and a durable, understated finish.",
                    "Kallang",
                    "Contemporary",
                    "sample_idp/sample_1.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
                (
                    "Small-Space Kitchen Refresh",
                    "Kitchen",
                    "A brighter kitchen layout that makes everyday cooking easier in a smaller home.",
                    "Geylang",
                    "Functional Modern",
                    "sample_idp/sample_2.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
            ],
        },
        {
            "username": "designer_ember",
            "password": "Designer@101",
            "email": "ember@renovation.local",
            "company_name": "Ember & Pine Studio",
            "phone": "+65 8123 4444",
            "website": "https://emberpine.example",
            "address": "30 East Coast Road, Singapore",
            "description": "Warm neutrals, custom joinery, and elevated family living spaces.",
            "projects": [
                (
                    "Coastal Family Lounge",
                    "Living Room",
                    "A soft coastal lounge designed for family gatherings with layered textures and practical storage.",
                    "East Coast",
                    "Coastal Modern",
                    "sample_idp/sample_3.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
                (
                    "Sunset Master Suite",
                    "Bedroom",
                    "A restful master bedroom with layered lighting and calm, organic finishes.",
                    "Upper East Coast",
                    "Soft Contemporary",
                    "sample_idp/sample_5.png",
                    InteriorDesignProject.STATUS_PAST,
                ),
                (
                    "Compact Dining Renewal",
                    "Dining Room",
                    "A dining area reworked to feel brighter and more connected to the open-plan home.",
                    "Katong",
                    "Modern Classic",
                    "sample_idp/sample_1.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
            ],
        },
        {
            "username": "designer_harbor",
            "password": "Designer@202",
            "email": "harbor@renovation.local",
            "company_name": "Harbor & Hearth Designs",
            "phone": "+65 8123 5555",
            "website": "https://harborhearth.example",
            "address": "52 Jalan Besar, Singapore",
            "description": "Luxury and practical lifestyles blended through elevated homes and efficient layouts.",
            "projects": [
                (
                    "Urban Loft Refresh",
                    "Living Room",
                    "An open-plan loft renovation that maximizes light, storage, and visual calm.",
                    "Jalan Besar",
                    "Industrial Minimal",
                    "sample_idp/sample_2.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
                (
                    "Harmonious Guest Suite",
                    "Bedroom",
                    "A guest suite that balances comfort, storage, and tone-on-tone detailing.",
                    "Little India",
                    "Minimal Luxury",
                    "sample_idp/sample_4.png",
                    InteriorDesignProject.STATUS_PAST,
                ),
                (
                    "Calm Kitchen Facelift",
                    "Kitchen",
                    "A kitchen makeover with durable surfaces, quiet materials, and improved circulation.",
                    "Bishan",
                    "Clean Contemporary",
                    "sample_idp/sample_5.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
            ],
        },
        {
            "username": "designer_luna",
            "password": "Designer@303",
            "email": "luna@renovation.local",
            "company_name": "Luna Form Atelier",
            "phone": "+65 8123 6666",
            "website": "https://lunaform.example",
            "address": "17 Clementi Avenue, Singapore",
            "description": "Thoughtful interiors for growing families and compact urban homes.",
            "projects": [
                (
                    "Bright Family Haven",
                    "Living Room",
                    "A warm family lounge designed to feel open, calming, and highly functional.",
                    "Clementi",
                    "Scandinavian Warmth",
                    "sample_idp/sample_1.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
                (
                    "Quiet Reading Nook",
                    "Bedroom",
                    "A cozy bedroom designed around comfortable textures and flexible storage.",
                    "Boon Lay",
                    "Soft Modern",
                    "sample_idp/sample_3.png",
                    InteriorDesignProject.STATUS_PAST,
                ),
                (
                    "Efficient Pantry Makeover",
                    "Kitchen",
                    "A practical kitchen update focused on smooth circulation and clean storage solutions.",
                    "Jurong East",
                    "Functional Scandinavian",
                    "sample_idp/sample_2.png",
                    InteriorDesignProject.STATUS_CURRENT,
                ),
            ],
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-username",
            help="Assign an existing user to the User Admin profile.",
        )
        parser.add_argument(
            "--skip-demo-designers",
            action="store_true",
            help="Skip creating the sample Interior Designer demo accounts.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["admin_username"]
        user = None
        if username:
            try:
                user = get_user_model().objects.get(username=username)
            except get_user_model().DoesNotExist as exc:
                raise CommandError(
                    f"User '{username}' does not exist. Create the user first."
                ) from exc

        descriptions = {
            "User Admin": "Manages user accounts and profiles.",
            "Interior Designer": "Manages company information and projects.",
            "Customer": "Searches and saves design projects.",
            "Platform Management": "Manages categories and reports.",
        }
        profiles = {}
        for name, description in descriptions.items():
            profiles[name], _ = UserProfile.objects.get_or_create(
                name=name,
                defaults={"description": description},
            )

        if user is not None:
            UserAccount.objects.update_or_create(
                user=user,
                defaults={"profile": profiles["User Admin"]},
            )
            self.stdout.write(
                self.style.SUCCESS(f"Assigned '{username}' to User Admin.")
            )

        if not options["skip_demo_designers"]:
            for designer in self.SAMPLE_DESIGNERS:
                user_obj, created = get_user_model().objects.get_or_create(
                    username=designer["username"],
                    defaults={
                        "email": designer["email"],
                        "first_name": designer["company_name"].split()[0],
                    },
                )
                if created:
                    user_obj.set_password(designer["password"])
                    user_obj.save(update_fields=["password"])

                UserAccount.objects.update_or_create(
                    user=user_obj,
                    defaults={"profile": profiles["Interior Designer"]},
                )

                Company.objects.update_or_create(
                    user=user_obj,
                    defaults={
                        "name": designer["company_name"],
                        "email": designer["email"],
                        "phone": designer["phone"],
                        "website": designer["website"],
                        "address": designer["address"],
                        "description": designer["description"],
                    },
                )

                company = user_obj.company
                for (
                    title,
                    category_name,
                    description,
                    location,
                    style,
                    image_name,
                    status,
                ) in designer["projects"]:
                    category, _ = Category.objects.get_or_create(
                        name=category_name,
                    )
                    project, _ = InteriorDesignProject.objects.get_or_create(
                        company=company,
                        title=title,
                        defaults={
                            "category": category,
                            "description": description,
                            "location": location,
                            "style": style,
                            "status": status,
                            "image": image_name,
                        },
                    )
                    if project.status != status:
                        project.status = status
                        project.save(update_fields=["status", "updated_at"])

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Ready demo Interior Designer '{designer['username']}' with company '{designer['company_name']}' "
                        f"(password: {designer['password']})"
                    )
                )

        self.stdout.write(self.style.SUCCESS("The four initial profiles are ready."))
