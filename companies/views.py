from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import interior_designer_required

from .controllers import (
    CreateCompanyController,
    DeleteCompanyController,
    SearchCompanyInformationController,
    UpdateCompanyController,
    ViewCompanyController,
)


def _company_fields(data):
    return {
        field: (data.get(field) or "").strip()
        for field in ("name", "email", "phone", "website", "address", "description")
    }


@interior_designer_required
@require_http_methods(["GET"])
def company_detail(request):
    company = ViewCompanyController().get_company(request.user)
    return render(request, "companies/company_detail.html", {"company": company})


@interior_designer_required
@require_http_methods(["GET", "POST"])
def company_create(request):
    if ViewCompanyController().get_company(request.user) is not None:
        return redirect("company_detail")

    if request.method == "POST":
        fields = _company_fields(request.POST)
        if fields["name"]:
            CreateCompanyController().create_company(request.user, **fields)
            messages.success(request, "Company information saved successfully.")
            return redirect("company_detail")

    return render(request, "companies/company_form.html", {"action": "Create"})


@interior_designer_required
@require_http_methods(["GET", "POST"])
def company_update(request):
    company = ViewCompanyController().get_company(request.user)

    if company is None:
        return redirect("company_create")

    if request.method == "POST":
        UpdateCompanyController().update_company(company, **_company_fields(request.POST))
        messages.success(request, "Company information updated successfully.")
        return redirect("company_detail")

    return render(request, "companies/company_form.html", {"company": company, "action": "Update"})


@interior_designer_required
@require_http_methods(["GET", "POST"])
def company_delete(request):
    company = ViewCompanyController().get_company(request.user)
    if company is None:
        return redirect("company_detail")
    if request.method == "POST":
        DeleteCompanyController().delete_company(company)
        messages.success(request, "Company information deleted successfully.")
        return redirect("company_detail")
    return render(request, "companies/company_confirm_delete.html", {"company": company})


@interior_designer_required
@require_http_methods(["GET"])
def company_search(request):
    company = ViewCompanyController().get_company(request.user)

    if company is None:
        return redirect("company_create")

    search_term = request.GET.get("q", "").strip()
    results = SearchCompanyInformationController().search_information(company, search_term)

    return render(
        request,
        "companies/company_search.html",
        {
            "company": company,
            "q": search_term,
            "results": results,
        },
    )
