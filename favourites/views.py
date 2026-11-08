from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from accounts.decorators import customer_required
from projects.models import InteriorDesignProject

from .controllers import FavouriteController


@customer_required
@require_http_methods(["GET"])
def favourite_list(request):
    context = FavouriteController.get_list_data(
        request.user,
        search_term=request.GET.get("q", ""),
        category_filter=request.GET.get("category", ""),
        sort_order=request.GET.get("sort", "newest"),
    )
    return render(request, "favourites/favourite_list.html", context)


@customer_required
@require_http_methods(["POST"])
def favourite_toggle(request, project_id):
    try:
        is_saved = FavouriteController.toggle(request.user, project_id)
    except InteriorDesignProject.DoesNotExist:
        return redirect("customer_idp_search")

    messages.success(
        request,
        "Project saved to favourites." if is_saved else "Project removed from favourites.",
    )
    next_url = request.POST.get("next", "").strip()
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return HttpResponseRedirect(next_url)
    return redirect("idp_detail", pk=project_id)
