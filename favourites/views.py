from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from accounts.decorators import customer_required
from projects.models import InteriorDesignProject

from .controllers import (
    SaveFavouriteController,
    SearchFavouritesController,
    ViewFavouriteIDPController,
)
from .models import Favourite


@customer_required
@require_http_methods(["GET"])
def favourite_list(request):
    context = SearchFavouritesController().get_list_data(
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
        is_saved = SaveFavouriteController().toggle(request.user, project_id)
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


@customer_required
@require_http_methods(["GET"])
def favourite_detail(request, project_id):
    try:
        context = ViewFavouriteIDPController().get_detail_data(request.user, project_id)
    except (Favourite.DoesNotExist, InteriorDesignProject.DoesNotExist) as error:
        raise Http404("Saved project not found.") from error
    except PermissionError as error:
        raise PermissionDenied from error
    return render(request, "projects/idp_detail.html", context)
