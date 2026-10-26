from django.contrib import messages
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import customer_required
from projects.models import InteriorDesignProject

from .forms import ProjectReviewForm
from .models import ProjectReview


@customer_required
@require_http_methods(["GET", "POST"])
def review_create(request, project_id):
    project = get_object_or_404(InteriorDesignProject, pk=project_id)
    review = ProjectReview.objects.filter(
        customer=request.user,
        project=project,
    ).first()
    if review is not None:
        return redirect("review_update", pk=review.pk)

    form = ProjectReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review, created = ProjectReview.objects.get_or_create(
            customer=request.user,
            project=project,
            defaults=form.cleaned_data,
        )
        if not created:
            return redirect("review_update", pk=review.pk)
        messages.success(request, "Your review was submitted.")
        return redirect("idp_detail", pk=project.pk)

    return render(
        request,
        "reviews/review_form.html",
        {"form": form, "project": project, "action": "Create"},
    )


@customer_required
@require_http_methods(["GET", "POST"])
def review_update(request, pk):
    review = get_object_or_404(
        ProjectReview.objects.select_related("project"),
        pk=pk,
        customer=request.user,
    )
    form = ProjectReviewForm(request.POST or None, instance=review)
    if request.method == "POST" and form.is_valid():
        form.save()
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
    review = get_object_or_404(
        ProjectReview,
        pk=pk,
        customer=request.user,
    )
    project_id = review.project_id
    review.delete()
    messages.success(request, "Your review was deleted.")
    return redirect("idp_detail", pk=project_id)
