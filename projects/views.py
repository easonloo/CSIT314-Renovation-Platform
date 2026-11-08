from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import interior_designer_required

from .controllers import ProjectAccessDenied, ProjectController
from .forms import InteriorDesignProjectForm
from .models import InteriorDesignProject


@interior_designer_required
@require_http_methods(["GET"])
def idp_list(request):
    context = ProjectController.get_list_data(
        request.user,
        status=request.GET.get("status", ""),
        search_term=request.GET.get("q", ""),
    )
    return render(request, "projects/idp_list.html", context)


@interior_designer_required
@require_http_methods(["GET", "POST"])
def idp_create(request):
    company = ProjectController.get_company(request.user)
    if company is None:
        return redirect("company_create")
    form = InteriorDesignProjectForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        project = ProjectController.create_project(company, **form.cleaned_data)
        messages.success(request, "Project saved successfully.")
        return redirect("idp_detail", pk=project.pk)
    return render(request, "projects/idp_form.html", {"form": form, "action": "Create"})


@login_required
@require_http_methods(["GET"])
def idp_detail(request, pk):
    try:
        context = ProjectController.get_detail_data(request.user, pk)
    except InteriorDesignProject.DoesNotExist as error:
        raise Http404("Project not available to this account.") from error
    except ProjectAccessDenied as error:
        raise PermissionDenied from error
    return render(request, "projects/idp_detail.html", context)


@interior_designer_required
@require_http_methods(["GET", "POST"])
def idp_update(request, pk):
    try:
        project = ProjectController.get_owned_project(request.user, pk)
    except InteriorDesignProject.DoesNotExist as error:
        raise Http404("Project not available to this account.") from error
    form = InteriorDesignProjectForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=project,
    )
    if request.method == "POST" and form.is_valid():
        try:
            project = ProjectController.update_project(request.user, pk, **form.cleaned_data)
        except InteriorDesignProject.DoesNotExist as error:
            raise Http404("Project not available to this account.") from error
        messages.success(request, "Project updated successfully.")
        return redirect("idp_detail", pk=project.pk)
    return render(
        request, "projects/idp_form.html", {"form": form, "project": project, "action": "Update"},
    )


@interior_designer_required
@require_http_methods(["POST"])
def idp_delete(request, pk):
    try:
        ProjectController.delete_project(request.user, pk)
    except InteriorDesignProject.DoesNotExist as error:
        raise Http404("Project not available to this account.") from error
    messages.success(request, "Project deleted successfully.")
    return redirect("idp_list")


@login_required
@require_http_methods(["GET"])
def customer_idp_search(request):
    try:
        context = ProjectController.get_search_data(
            request.user,
            search_term=request.GET.get("q", ""),
            category_id=request.GET.get("category", ""),
            sort_order=request.GET.get("sort", "recommended"),
        )
    except ProjectAccessDenied as error:
        raise PermissionDenied from error
    return render(request, "projects/customer_search.html", context)
