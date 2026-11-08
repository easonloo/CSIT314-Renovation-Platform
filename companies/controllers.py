"""Company use-case controls; Company owns persistence and company behaviour."""

from .models import Company


class CreateCompanyController:
    """User story 15: create the designer's company information."""

    def create_company(self, user, **details):
        return Company.create_for_user(user, **details)


class ViewCompanyController:
    """User story 16: retrieve the designer's own company."""

    def get_company(self, user):
        return Company.find_for_user(user)


class UpdateCompanyController:
    """User story 17: update company information through its entity."""

    def update_company(self, company, **details):
        return company.update_details(**details)


class DeleteCompanyController:
    """User story 18: remove company information through its entity."""

    def delete_company(self, company):
        company.delete_company()


class SearchCompanyInformationController:
    """User story 19: search the fields of the designer's company."""

    def search_information(self, company, search_term=""):
        if company is None:
            return []
        return company.search_information(search_term)


class CompanyController:
    """Compatibility entry points for shared application code and older callers."""

    @staticmethod
    def get_company(user):
        return ViewCompanyController().get_company(user)

    @staticmethod
    def create_company(user, **details):
        return CreateCompanyController().create_company(user, **details)

    @staticmethod
    def update_company(company, **details):
        return UpdateCompanyController().update_company(company, **details)

    @staticmethod
    def delete_company(company):
        return DeleteCompanyController().delete_company(company)

    @staticmethod
    def search_information(company, search_term=""):
        return SearchCompanyInformationController().search_information(company, search_term)
