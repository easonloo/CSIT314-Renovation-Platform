from django.db import transaction
from django.db.models import Avg, Count, F, Q

from accounts.controllers import AccountAccessController
from categories.controllers import CategoryController
from companies.controllers import CompanyController
from favourites.controllers import FavouriteController
from favourites.models import Favourite
from reports.models import ProjectView
from reviews.controllers import ProjectReviewController

from .models import InteriorDesignProject


class ProjectAccessDenied(PermissionError):
    pass


class ProjectController:
    @staticmethod
    def get_company(user):
        return CompanyController.get_company(user)

    @staticmethod
    def get_categories():
        return CategoryController.list_categories()

    @staticmethod
    def get_owned_project(user, pk):
        return InteriorDesignProject.objects.get(pk=pk, company__user=user)

    @staticmethod
    def get_list_data(user, *, status="", search_term=""):
        status = (status or "").strip()
        if status not in {
            "", InteriorDesignProject.STATUS_CURRENT, InteriorDesignProject.STATUS_PAST,
        }:
            status = ""
        search_term = (search_term or "").strip()
        projects = InteriorDesignProject.objects.filter(company__user=user)
        if status:
            projects = projects.filter(status=status)
        if search_term:
            projects = projects.filter(
                Q(title__icontains=search_term)
                | Q(description__icontains=search_term)
                | Q(location__icontains=search_term)
                | Q(style__icontains=search_term)
                | Q(category__name__icontains=search_term)
            )
        return {
            "projects": projects.select_related("category", "company"),
            "status": status,
            "q": search_term,
        }

    @staticmethod
    def create_project(
        company, *, title, description="", category=None, location="", style="",
        status=InteriorDesignProject.STATUS_CURRENT, image=None,
    ):
        return InteriorDesignProject.objects.create(
            company=company,
            title=title,
            description=description,
            category=category,
            location=location,
            style=style,
            status=status,
            image=image or "",
        )

    @classmethod
    def update_project(
        cls, user, pk, *, title, description="", category=None, location="", style="",
        status=InteriorDesignProject.STATUS_CURRENT, image=None,
    ):
        project = cls.get_owned_project(user, pk)
        project.title = title
        project.description = description
        project.category = category
        project.location = location
        project.style = style
        project.status = status
        if image is not None:
            # ClearableFileInput returns False when the existing image is cleared.
            project.image = image or ""
        project.save()
        return project

    @classmethod
    def delete_project(cls, user, pk):
        cls.get_owned_project(user, pk).delete()

    @staticmethod
    @transaction.atomic
    def record_view(project, viewer):
        if project.company.user_id == viewer.pk:
            return
        ProjectView.objects.create(project=project, viewer=viewer)
        InteriorDesignProject.objects.filter(pk=project.pk).update(
            view_count=F("view_count") + 1,
        )
        project.view_count += 1

    @classmethod
    def get_detail_data(cls, user, pk):
        project = InteriorDesignProject.objects.select_related("company", "category").get(pk=pk)
        account = AccountAccessController.get_active_account(user)
        if account is None:
            raise ProjectAccessDenied("The account or its profile is unavailable.")
        is_project_owner = project.company.user_id == user.pk
        if account.profile.name == "Interior Designer" and not is_project_owner:
            raise InteriorDesignProject.DoesNotExist("Project not available to this account.")
        cls.record_view(project, user)
        is_customer = account.profile.name == "Customer"
        return {
            "project": project,
            "is_project_owner": is_project_owner,
            **ProjectReviewController.get_project_data(project, user if is_customer else None),
            "can_review": is_customer,
            "is_favourited": is_customer and FavouriteController.is_saved(user, project.pk),
        }

    @classmethod
    def get_search_data(cls, user, *, search_term="", category_id="", sort_order="recommended"):
        account = AccountAccessController.get_active_account(user)
        if account is None:
            raise ProjectAccessDenied("The account or its profile is unavailable.")
        search_term = (search_term or "").strip()
        category_id = (category_id or "").strip()
        sort_order = (sort_order or "recommended").strip()
        if sort_order not in {"recommended", "rating", "newest"}:
            sort_order = "recommended"
        projects = InteriorDesignProject.objects.select_related("company", "category").annotate(
            average_rating=Avg("reviews__rating"),
            review_count=Count("reviews"),
        )
        if search_term:
            projects = projects.filter(
                Q(title__icontains=search_term)
                | Q(description__icontains=search_term)
                | Q(style__icontains=search_term)
                | Q(company__name__icontains=search_term)
                | Q(category__name__icontains=search_term)
            )
        if category_id.isdecimal():
            try:
                projects = projects.filter(category_id=int(category_id))
            except ValueError:
                projects = projects.none()
        if sort_order == "rating":
            projects = projects.order_by("-average_rating", "-updated_at")
        elif sort_order == "newest":
            projects = projects.order_by("-created_at")
        else:
            projects = projects.order_by("-average_rating", "-review_count", "-updated_at")
        is_customer = account.profile.name == "Customer"
        return {
            "projects": projects,
            "categories": cls.get_categories(),
            "q": search_term,
            "selected_category": category_id,
            "can_review": is_customer,
            "can_favourite": is_customer,
            "favourite_project_ids": (
                Favourite.objects.filter(user=user).values_list("project_id", flat=True)
                if is_customer else ()
            ),
            "project_count": projects.count(),
            "sort_order": sort_order,
        }
