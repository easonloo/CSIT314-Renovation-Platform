from django.conf import settings
from django.db import models


class Company(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company",
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    website = models.URLField(blank=True, default="")
    address = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @classmethod
    def find_for_user(cls, user):
        """Retrieve the company owned by this user."""
        return cls.objects.filter(user=user).first()

    @classmethod
    def create_for_user(
        cls, user, *, name, email="", phone="", website="", address="", description="",
    ):
        return cls.objects.create(
            user=user,
            name=name,
            email=email,
            phone=phone,
            website=website,
            address=address,
            description=description,
        )

    def update_details(
        self, *, name, email="", phone="", website="", address="", description="",
    ):
        self.name = name
        self.email = email
        self.phone = phone
        self.website = website
        self.address = address
        self.description = description
        self.save(
            update_fields=[
                "name", "email", "phone", "website", "address", "description", "updated_at",
            ],
        )
        return self

    def delete_company(self):
        self.delete()

    def search_information(self, search_term=""):
        term = (search_term or "").strip().casefold()
        if not term:
            return []
        details = [
            ("Company name", self.name),
            ("Description", self.description),
            ("Email", self.email),
            ("Phone", self.phone),
            ("Address", self.address),
            ("Website", self.website),
        ]
        return [
            (label, value)
            for label, value in details
            if value and (term in label.casefold() or term in value.casefold())
        ]
