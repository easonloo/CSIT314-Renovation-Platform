from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import customer_required
from projects.models import InteriorDesignProject

from .controllers import ProjectReviewController
from .forms import ProjectReviewForm
from .models import ProjectReview


@customer_required
@require_http_methods(["GET", "POST"])
def review_create(request, project_id):
    try:
        project = ProjectReviewController.get_project(project_id)
    except InteriorDesignProject.DoesNotExist as error:
        raise Http404("Project not found.") from error
    review = ProjectReviewController.get_customer_review(request.user, project)
    if review is not None:
        return redirect("review_update", pk=review.pk)
    form = ProjectReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review, created = ProjectReviewController.create_review(
            request.user, project, **form.cleaned_data,
        )
        if not created:
            return redirect("review_update", pk=review.pk)
        messages.success(request, "Your review was submitted.")
        return redirect("idp_detail", pk=project.pk)
    return render(
        request, "reviews/review_form.html", {"form": form, "project": project, "action": "Create"},
    )


@customer_required
@require_http_methods(["GET", "POST"])
def review_update(request, pk):
    try:
        review = ProjectReviewController.get_owned_review(request.user, pk)
    except ProjectReview.DoesNotExist as error:
        raise Http404("Review not found.") from error
    form = ProjectReviewForm(request.POST or None, instance=review)
    if request.method == "POST" and form.is_valid():
        try:
            review = ProjectReviewController.update_review(request.user, pk, **form.cleaned_data)
        except ProjectReview.DoesNotExist as error:
            raise Http404("Review not found.") from error
        messages.success(request, "Your review was updated.")
        return redirect("idp_detail", pk=review.project_id)
    return render(
        request,
        "reviews/review_form.html",
        {"form": form, "project": review.project, "action": "Update"},
    )


@customer_required
@require_http_methods(["POST"])
def review_delete(request, pk):
    try:
        project_id = ProjectReviewController.delete_review(request.user, pk)
    except ProjectReview.DoesNotExist as error:
        raise Http404("Review not found.") from error
    messages.success(request, "Your review was deleted.")
    return redirect("idp_detail", pk=project_id)
