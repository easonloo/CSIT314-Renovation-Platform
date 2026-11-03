from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import Company


@login_required
@require_http_methods(["GET"])
def company_detail(request):
    company = Company.objects.filter(user=request.user).first()
    return render(request, "companies/company_detail.html", {"company": company})


@login_required
@require_http_methods(["GET", "POST"])
def company_create(request):
    if Company.objects.filter(user=request.user).exists():
        return redirect("company_detail")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            company = Company.objects.create(
                user=request.user,
                name=name,
                email=(request.POST.get("email") or "").strip(),
                phone=(request.POST.get("phone") or "").strip(),
                website=(request.POST.get("website") or "").strip(),
                address=(request.POST.get("address") or "").strip(),
                description=(request.POST.get("description") or "").strip(),
            )
            messages.success(request, "Company information saved successfully.")
            return redirect("company_detail")

    return render(request, "companies/company_form.html", {"action": "Create"})


@login_required
@require_http_methods(["GET", "POST"])
def company_update(request):
    company = Company.objects.filter(user=request.user).first()

    if company is None:
        return redirect("company_create")

    if request.method == "POST":
        company.name = (request.POST.get("name") or "").strip()
        company.email = (request.POST.get("email") or "").strip()
        company.phone = (request.POST.get("phone") or "").strip()
        company.website = (request.POST.get("website") or "").strip()
        company.address = (request.POST.get("address") or "").strip()
        company.description = (request.POST.get("description") or "").strip()
        company.save()
        messages.success(request, "Company information updated successfully.")
        return redirect("company_detail")

    return render(request, "companies/company_form.html", {"company": company, "action": "Update"})


@login_required
@require_http_methods(["POST"])
def company_delete(request):
    company = Company.objects.filter(user=request.user).first()
    if company is not None:
        company.delete()
        messages.success(request, "Company information deleted successfully.")
    return redirect("company_detail")
