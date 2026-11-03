from django import forms

from .models import ProjectReview


class ProjectReviewForm(forms.ModelForm):
    class Meta:
        model = ProjectReview
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.RadioSelect(
                choices=[(rating, f"{rating} / 5") for rating in range(1, 6)],
                attrs={"class": "star-rating-input"},
            ),
            "comment": forms.Textarea(
                attrs={"class": "textarea", "rows": 4}
            ),
        }
