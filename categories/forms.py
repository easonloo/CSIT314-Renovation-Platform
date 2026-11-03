from django import forms

from .models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "description": forms.Textarea(
                attrs={"class": "textarea", "rows": 4}
            ),
        }
