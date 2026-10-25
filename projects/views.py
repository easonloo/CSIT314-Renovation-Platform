from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import interior_designer_required
from accounts.models import UserAccount
from categories.models import Category
from companies.models import Company

from .forms import InteriorDesignProjectForm
from .models import InteriorDesignProject


@interior_designer_required
@require_http_methods(["GET"])
def idp_list(request):
    status = request.GET.get("status", "").strip()
    if status not in {"", InteriorDesignProject.STATUS_CURRENT, InteriorDesignProject.STATUS_PAST}:
        status = ""
    search_term = request.GET.get("q", "").strip()

    projects = InteriorDesignProject.objects.filter(company__user=request.user)
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

    return render(
        request,
        "projects/idp_list.html",
        {
            "projects": projects.select_related("category", "company"),
            "status": status,
            "q": search_term,
        },
    )


@interior_designer_required
@require_http_methods(["GET", "POST"])
def idp_create(request):
    company = Company.objects.filter(user=request.user).first()
    if company is None:
        return redirect("company_create")

    form = InteriorDesignProjectForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.company = company
        project.save()
        messages.success(request, "Project saved successfully.")
        return redirect("idp_detail", pk=project.pk)

    return render(
        request,
        "projects/idp_form.html",
        {"form": form, "action": "Create"},
    )


@login_required
@require_http_methods(["GET"])
def idp_detail(request, pk):
    project = get_object_or_404(
        InteriorDesignProject.objects.select_related("company", "category"),
        pk=pk,
    )
    account = UserAccount.objects.select_related("profile").filter(
        user=request.user,
        profile__is_active=True,
    ).first()
    if account is None:
        raise PermissionDenied
    if (
        account.profile.name == "Interior Designer"
        and project.company.user_id != request.user.pk
    ):
        raise Http404("Project not available to this account.")

    return render(
        request,
        "projects/idp_detail.html",
        {"project": project, "is_project_owner": project.company.user_id == request.user.pk},
    )


@interior_designer_required
@require_http_methods(["GET", "POST"])
def idp_update(request, pk):
    project = get_object_or_404(
        InteriorDesignProject,
        pk=pk,
        company__user=request.user,
    )
    form = InteriorDesignProjectForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=project,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Project updated successfully.")
        return redirect("idp_detail", pk=project.pk)

    return render(
        request,
        "projects/idp_form.html",
        {"form": form, "project": project, "action": "Update"},
    )


@interior_designer_required
@require_http_methods(["POST"])
def idp_delete(request, pk):
    project = get_object_or_404(
        InteriorDesignProject,
        pk=pk,
        company__user=request.user,
    )
    project.delete()
    messages.success(request, "Project deleted successfully.")
    return redirect("idp_list")


@login_required
@require_http_methods(["GET"])
def customer_idp_search(request):
    search_term = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    categories = Category.objects.order_by("name")
    projects = InteriorDesignProject.objects.select_related(
        "company",
        "category",
    )

    if search_term:
        projects = projects.filter(
            Q(title__icontains=search_term)
            | Q(description__icontains=search_term)
            | Q(style__icontains=search_term)
            | Q(company__name__icontains=search_term)
            | Q(category__name__icontains=search_term)
        )
    if category_id.isdigit():
        projects = projects.filter(category_id=int(category_id))

    return render(
        request,
        "projects/customer_search.html",
        {
            "projects": projects,
            "categories": categories,
            "q": search_term,
            "selected_category": category_id,
        },
    )
