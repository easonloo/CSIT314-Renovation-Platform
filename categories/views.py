from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import platform_manager_required

from .controllers import (
    CreateIDPCategoryController,
    DeleteIDPCategoryController,
    SearchIDPCategoriesController,
    UpdateIDPCategoryController,
    ViewIDPCategoryController,
)
from .forms import CategoryForm


@platform_manager_required
@require_http_methods(["GET"])
def category_list(request):
    q = (request.GET.get("q") or "").strip()
    categories = SearchIDPCategoriesController().list_categories(q)
    return render(request, "categories/category_list.html", {"categories": categories, "q": q})


@platform_manager_required
@require_http_methods(["GET"])
def category_detail(request, pk):
    category = ViewIDPCategoryController().get_category(pk)
    if category is None:
        raise Http404("Category not found.")
    return render(request, "categories/category_detail.html", {"category": category})


@platform_manager_required
@require_http_methods(["GET", "POST"])
def category_create(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        category = CreateIDPCategoryController().create_category(**form.cleaned_data)
        messages.success(request, "Category created successfully.")
        return redirect("category_detail", pk=category.pk)

    return render(
        request,
        "categories/category_form.html",
        {"action": "Create", "form": form},
    )


@platform_manager_required
@require_http_methods(["GET", "POST"])
def category_update(request, pk):
    category = ViewIDPCategoryController().get_category(pk)
    if category is None:
        raise Http404("Category not found.")

    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        category = UpdateIDPCategoryController().update_category(category, **form.cleaned_data)
        messages.success(request, "Category updated successfully.")
        return redirect("category_detail", pk=category.pk)

    return render(
        request,
        "categories/category_form.html",
        {"category": category, "action": "Update", "form": form},
    )


@platform_manager_required
@require_http_methods(["GET", "POST"])
def category_delete(request, pk):
    category = ViewIDPCategoryController().get_category(pk)
    if category is None:
        if request.method == "POST":
            return redirect("category_list")
        raise Http404("Category not found.")
    if request.method == "POST":
        DeleteIDPCategoryController().delete_category(category)
        messages.success(request, "Category deleted successfully.")
        return redirect("category_list")
    return render(request, "categories/category_confirm_delete.html", {"category": category})
