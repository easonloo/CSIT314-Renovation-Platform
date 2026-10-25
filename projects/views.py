from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import interior_designer_required
from categories.models import Category
from companies.models import Company

from .models import InteriorDesignProject


@interior_designer_required
@require_http_methods(["GET"])
def idp_list(request):
    status = request.GET.get("status")
    q = (request.GET.get("q") or "").strip()

    projects = InteriorDesignProject.objects.filter(company__user=request.user)
    if status in {"current", "past"}:
        projects = projects.filter(status=status)
    if q:
        projects = projects.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(location__icontains=q)
            | Q(style__icontains=q)
            | Q(category__name__icontains=q)
        )

    return render(
        request,
        "projects/idp_list.html",
        {"projects": projects.select_related("category", "company"), "status": status, "q": q},
    )


@interior_designer_required
@require_http_methods(["GET", "POST"])
def idp_create(request):
    company = Company.objects.filter(user=request.user).first()
    if company is None:
        return redirect("company_create")

    categories = Category.objects.all().order_by("name")

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        if title:
            category_id = request.POST.get("category")
            project = InteriorDesignProject.objects.create(
                company=company,
                category=Category.objects.filter(pk=category_id).first() if category_id else None,
                title=title,
                description=(request.POST.get("description") or "").strip(),
                location=(request.POST.get("location") or "").strip(),
                style=(request.POST.get("style") or "").strip(),
                status=request.POST.get("status") or InteriorDesignProject.STATUS_CURRENT,
            )
            if request.FILES.get("image"):
                project.image = request.FILES["image"]
                project.save(update_fields=["image"])
            messages.success(request, "Project saved successfully.")
            return redirect("idp_detail", pk=project.pk)

    return render(request, "projects/idp_form.html", {"action": "Create", "categories": categories})


@login_required
@require_http_methods(["GET"])
def idp_detail(request, pk):
    project = InteriorDesignProject.objects.select_related("company", "category").filter(pk=pk).first()
    if project is None:
        raise Http404("Interior design project not found.")

    if request.user.is_authenticated and request.user.account.profile.name == "Interior Designer":
        if project.company.user_id != request.user.pk:
            raise Http404("Project not available to this account.")

    return render(request, "projects/idp_detail.html", {"project": project})


@interior_designer_required
@require_http_methods(["GET", "POST"])
def idp_update(request, pk):
    project = InteriorDesignProject.objects.filter(pk=pk, company__user=request.user).first()
    if project is None:
        raise Http404("Project not found.")

    categories = Category.objects.all().order_by("name")

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        if title:
            category_id = request.POST.get("category")
            project.title = title
            project.category = Category.objects.filter(pk=category_id).first() if category_id else None
            project.description = (request.POST.get("description") or "").strip()
            project.location = (request.POST.get("location") or "").strip()
            project.style = (request.POST.get("style") or "").strip()
            project.status = request.POST.get("status") or project.status
            if request.FILES.get("image"):
                project.image = request.FILES["image"]
            project.save()
            messages.success(request, "Project updated successfully.")
            return redirect("idp_detail", pk=project.pk)

    return render(request, "projects/idp_form.html", {"project": project, "action": "Update", "categories": categories})


@interior_designer_required
@require_http_methods(["POST"])
def idp_delete(request, pk):
    project = InteriorDesignProject.objects.filter(pk=pk, company__user=request.user).first()
    if project is not None:
        project.delete()
        messages.success(request, "Project deleted successfully.")
    return redirect("idp_list")


@login_required
@require_http_methods(["GET"])
def customer_idp_search(request):
    q = (request.GET.get("q") or "").strip()
    category_id = request.GET.get("category")
    categories = Category.objects.all().order_by("name")

    projects = InteriorDesignProject.objects.select_related("company", "category").all()
    if q:
        projects = projects.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(style__icontains=q)
            | Q(company__name__icontains=q)
            | Q(category__name__icontains=q)
        )
    if category_id:
        projects = projects.filter(category_id=category_id)

    return render(request, "projects/customer_search.html", {"projects": projects, "categories": categories})
