from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from .models import Category


@login_required
@require_http_methods(["GET"])
def category_list(request):
    q = (request.GET.get("q") or "").strip()
    categories = Category.objects.all()
    if q:
        categories = categories.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, "categories/category_list.html", {"categories": categories, "q": q})


@login_required
@require_http_methods(["GET"])
def category_detail(request, pk):
    category = Category.objects.filter(pk=pk).first()
    if category is None:
        raise Http404("Category not found.")
    return render(request, "categories/category_detail.html", {"category": category})


@login_required
@require_http_methods(["GET", "POST"])
def category_create(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        if name:
            category = Category.objects.create(name=name, description=description)
            messages.success(request, "Category created successfully.")
            return redirect("category_detail", pk=category.pk)

    return render(request, "categories/category_form.html", {"action": "Create"})


@login_required
@require_http_methods(["GET", "POST"])
def category_update(request, pk):
    category = Category.objects.filter(pk=pk).first()
    if category is None:
        raise Http404("Category not found.")

    if request.method == "POST":
        category.name = (request.POST.get("name") or "").strip()
        category.description = (request.POST.get("description") or "").strip()
        category.save()
        messages.success(request, "Category updated successfully.")
        return redirect("category_detail", pk=category.pk)

    return render(request, "categories/category_form.html", {"category": category, "action": "Update"})


@login_required
@require_http_methods(["POST"])
def category_delete(request, pk):
    category = Category.objects.filter(pk=pk).first()
    if category is not None:
        category.delete()
        messages.success(request, "Category deleted successfully.")
    return redirect("category_list")
