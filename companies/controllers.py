from .models import Company


class CompanyController:
    @staticmethod
    def get_company(user):
        return Company.objects.filter(user=user).first()

    @staticmethod
    def create_company(
        user, *, name, email="", phone="", website="", address="", description="",
    ):
        return Company.objects.create(
            user=user,
            name=name,
            email=email,
            phone=phone,
            website=website,
            address=address,
            description=description,
        )

    @staticmethod
    def update_company(
        company, *, name, email="", phone="", website="", address="", description="",
    ):
        company.name = name
        company.email = email
        company.phone = phone
        company.website = website
        company.address = address
        company.description = description
        company.save(
            update_fields=[
                "name", "email", "phone", "website", "address", "description", "updated_at",
            ],
        )
        return company

    @staticmethod
    def delete_company(company):
        company.delete()

    @staticmethod
    def search_information(company, search_term=""):
        term = (search_term or "").strip().casefold()

        if company is None or not term:
            return []

        details = [
            ("Company name", company.name),
            ("Description", company.description),
            ("Email", company.email),
            ("Phone", company.phone),
            ("Address", company.address),
            ("Website", company.website),
        ]

        return [
            (label, value)
            for label, value in details
            if value and (term in label.casefold() or term in value.casefold())
        ]
