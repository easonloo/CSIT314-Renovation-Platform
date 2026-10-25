from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from projects.models import InteriorDesignProject

from .models import Favourite


@login_required
@require_http_methods(["GET"])
def favourite_list(request):
    q = (request.GET.get("q") or "").strip()
    favourites = Favourite.objects.filter(user=request.user).select_related("project", "project__company", "project__category")
    if q:
        favourites = favourites.filter(
            Q(project__title__icontains=q)
            | Q(project__company__name__icontains=q)
            | Q(project__category__name__icontains=q)
        )
    return render(request, "favourites/favourite_list.html", {"favourites": favourites})


@login_required
@require_http_methods(["POST"])
def favourite_add(request, project_id):
    project = InteriorDesignProject.objects.filter(pk=project_id).first()
    if project is None:
        return redirect("customer_idp_search")

    Favourite.objects.get_or_create(user=request.user, project=project)
    messages.success(request, "Project saved to favourites.")
    return redirect("idp_detail", pk=project.pk)
