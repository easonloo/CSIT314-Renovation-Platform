from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from projects.models import InteriorDesignProject

from .models import Favourite


@login_required
@require_http_methods(["GET"])
def favourite_list(request):
    q = (request.GET.get("q") or "").strip()
    category_filter = (request.GET.get("category") or "").strip()
    sort_order = (request.GET.get("sort") or "newest").strip()
    if sort_order not in {"newest", "oldest"}:
        sort_order = "newest"

    favourites = Favourite.objects.filter(user=request.user).select_related("project", "project__company", "project__category")
    if q:
        favourites = favourites.filter(
            Q(project__title__icontains=q)
            | Q(project__company__name__icontains=q)
            | Q(project__category__name__icontains=q)
        )
    if category_filter.isdigit():
        favourites = favourites.filter(project__category_id=int(category_filter))
    favourites = favourites.order_by(
        "created_at" if sort_order == "oldest" else "-created_at"
    )

    all_favourites = Favourite.objects.filter(user=request.user)
    categories = (
        all_favourites.filter(project__category__isnull=False)
        .values("project__category_id", "project__category__name")
        .annotate(count=Count("pk"))
        .order_by("project__category__name")
    )

    return render(
        request,
        "favourites/favourite_list.html",
        {
            "favourites": favourites,
            "q": q,
            "category_filter": category_filter,
            "sort_order": sort_order,
            "favourite_count": all_favourites.count(),
            "filtered_count": favourites.count(),
            "categories": categories,
        },
    )


@login_required
@require_http_methods(["POST"])
def favourite_add(request, project_id):
    project = InteriorDesignProject.objects.filter(pk=project_id).first()
    if project is None:
        return redirect("customer_idp_search")

    Favourite.objects.get_or_create(user=request.user, project=project)
    messages.success(request, "Project saved to favourites.")
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("idp_detail", pk=project.pk)
