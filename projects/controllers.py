"""Use-case controls: coordinate entities without issuing database operations."""
from accounts.controllers import AccountAccessController
from categories.controllers import CategoryController
from companies.controllers import CompanyController
from favourites.models import Favourite
from reviews.controllers import ViewProjectReviewsController

from .models import InteriorDesignProject


class ProjectAccessDenied(PermissionError):
    pass


class IDPFormController:
    def get_company(self, user):
        return CompanyController.get_company(user)

    def get_categories(self):
        return CategoryController.list_categories()


class ViewOwnedIDPController:
    def get_project(self, user, pk):
        return InteriorDesignProject.find_owned(user, pk)


class _StatusIDPController:
    status = None

    def get_project(self, user, pk):
        return InteriorDesignProject.find_owned(user, pk, status=self.status)


class CreateCurrentIDPController(_StatusIDPController):
    """Story 20: create an ongoing project."""
    status = InteriorDesignProject.STATUS_CURRENT

    def create_project(self, company, **details):
        details["status"] = self.status
        return InteriorDesignProject.create_project(company, **details)


class ViewCurrentIDPController(_StatusIDPController):
    """Story 21: view an owned ongoing project."""
    status = InteriorDesignProject.STATUS_CURRENT

    def view_project(self, user, pk):
        return self.get_project(user, pk)


class UpdateCurrentIDPController(_StatusIDPController):
    """Story 22: update a current project, including marking it complete."""
    status = InteriorDesignProject.STATUS_CURRENT

    def update_project(self, user, pk, **details):
        return self.get_project(user, pk).update_details(**details)


class DeleteCurrentIDPController(_StatusIDPController):
    """Story 23: delete an owned ongoing project."""
    status = InteriorDesignProject.STATUS_CURRENT

    def delete_project(self, user, pk):
        self.get_project(user, pk).delete_project()


class SearchCurrentIDPsController(_StatusIDPController):
    """Story 24: search ongoing projects belonging to the designer."""
    status = InteriorDesignProject.STATUS_CURRENT

    def search_projects(self, user, search_term=""):
        return InteriorDesignProject.search_owned(
            user, status=self.status, search_term=(search_term or "").strip(),
        )


class CreatePastIDPController(CreateCurrentIDPController):
    """Story 25: create a completed project."""
    status = InteriorDesignProject.STATUS_PAST


class ViewPastIDPController(ViewCurrentIDPController):
    """Story 26: view an owned completed project."""
    status = InteriorDesignProject.STATUS_PAST


class UpdatePastIDPController(UpdateCurrentIDPController):
    """Story 27: update an owned completed project."""
    status = InteriorDesignProject.STATUS_PAST


class DeletePastIDPController(DeleteCurrentIDPController):
    """Story 28: delete an owned completed project."""
    status = InteriorDesignProject.STATUS_PAST


class SearchPastIDPsController(SearchCurrentIDPsController):
    """Story 29: search completed projects belonging to the designer."""
    status = InteriorDesignProject.STATUS_PAST


class CreateIDPController:
    def create_project(self, company, **details):
        control = (
            CreatePastIDPController()
            if details.get("status") == InteriorDesignProject.STATUS_PAST
            else CreateCurrentIDPController()
        )
        return control.create_project(company, **details)


class UpdateIDPController:
    def update_project(self, user, pk, **details):
        project = ViewOwnedIDPController().get_project(user, pk)
        control = (
            UpdatePastIDPController()
            if project.status == InteriorDesignProject.STATUS_PAST
            else UpdateCurrentIDPController()
        )
        return control.update_project(user, pk, **details)


class DeleteIDPController:
    def delete_project(self, user, pk):
        project = ViewOwnedIDPController().get_project(user, pk)
        control = (
            DeletePastIDPController()
            if project.status == InteriorDesignProject.STATUS_PAST
            else DeleteCurrentIDPController()
        )
        control.delete_project(user, pk)


class SearchOwnedIDPsController:
    def get_list_data(self, user, *, status="", search_term=""):
        status = (status or "").strip()
        if status not in {"", InteriorDesignProject.STATUS_CURRENT, InteriorDesignProject.STATUS_PAST}:
            status = ""
        search_term = (search_term or "").strip()
        if status == InteriorDesignProject.STATUS_CURRENT:
            projects = SearchCurrentIDPsController().search_projects(user, search_term)
        elif status == InteriorDesignProject.STATUS_PAST:
            projects = SearchPastIDPsController().search_projects(user, search_term)
        else:
            projects = InteriorDesignProject.search_owned(user, search_term=search_term)
        return {"projects": projects, "status": status, "q": search_term}


class ViewIDPViewsController:
    """Story 37: let an owner inspect their project's view count."""
    def view_views(self, user, project):
        if project.company.user_id != user.pk:
            raise InteriorDesignProject.DoesNotExist("Project not available to this account.")
        return project.number_of_views()


class ViewIDPShortlistsController:
    """Story 38: let an owner inspect their project's shortlist count."""
    def view_shortlists(self, user, project):
        if project.company.user_id != user.pk:
            raise InteriorDesignProject.DoesNotExist("Project not available to this account.")
        return project.number_of_shortlists()


class ViewIDPController:
    """Story 33 and shared detail boundary; owner requests dispatch to story 21/26."""
    def get_detail_data(self, user, pk):
        project = InteriorDesignProject.find(pk)
        account = AccountAccessController.get_active_account(user)
        if account is None:
            raise ProjectAccessDenied("The account or its profile is unavailable.")
        is_owner = project.company.user_id == user.pk
        if account.profile.name == "Interior Designer" and not is_owner:
            raise InteriorDesignProject.DoesNotExist("Project not available to this account.")
        if is_owner:
            owner_control = (
                ViewPastIDPController()
                if project.status == InteriorDesignProject.STATUS_PAST
                else ViewCurrentIDPController()
            )
            project = owner_control.view_project(user, pk)
        project.record_view(user)
        is_customer = account.profile.name == "Customer"
        return {
            "project": project,
            "is_project_owner": is_owner,
            **ViewProjectReviewsController().get_project_data(project, user if is_customer else None),
            "can_review": is_customer,
            "is_favourited": is_customer and Favourite.is_saved(user, project.pk),
            "view_count": (
                ViewIDPViewsController().view_views(user, project)
                if is_owner else project.number_of_views()
            ),
            "shortlist_count": (
                ViewIDPShortlistsController().view_shortlists(user, project)
                if is_owner else project.number_of_shortlists()
            ),
        }


class SearchIDPsController:
    """Story 32: discover projects using search, category and ranking."""
    def get_search_data(self, user, *, search_term="", category_id="", sort_order="recommended"):
        account = AccountAccessController.get_active_account(user)
        if account is None:
            raise ProjectAccessDenied("The account or its profile is unavailable.")
        search_term = (search_term or "").strip()
        category_id = (category_id or "").strip()
        sort_order = (sort_order or "recommended").strip()
        if sort_order not in {"recommended", "rating", "newest"}:
            sort_order = "recommended"
        is_customer = account.profile.name == "Customer"
        return {
            **InteriorDesignProject.discover(
                search_term=search_term, category_id=category_id, sort_order=sort_order,
            ),
            "categories": IDPFormController().get_categories(),
            "q": search_term,
            "selected_category": category_id,
            "can_review": is_customer,
            "can_favourite": is_customer,
            "favourite_project_ids": Favourite.project_ids(user) if is_customer else (),
            "sort_order": sort_order,
        }


class ProjectController:
    """Compatibility API for existing integrations; boundaries use the specific controls."""
    get_company = staticmethod(IDPFormController().get_company)
    get_categories = staticmethod(IDPFormController().get_categories)
    get_owned_project = staticmethod(ViewOwnedIDPController().get_project)
    get_list_data = staticmethod(SearchOwnedIDPsController().get_list_data)
    create_project = staticmethod(CreateIDPController().create_project)
    update_project = staticmethod(UpdateIDPController().update_project)
    delete_project = staticmethod(DeleteIDPController().delete_project)
    get_detail_data = staticmethod(ViewIDPController().get_detail_data)
    get_search_data = staticmethod(SearchIDPsController().get_search_data)

    @staticmethod
    def record_view(project, viewer):
        return project.record_view(viewer)
