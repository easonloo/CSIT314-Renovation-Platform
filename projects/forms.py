from django import forms

from categories.models import Category

from .models import InteriorDesignProject


class InteriorDesignProjectForm(forms.ModelForm):
    class Meta:
        model = InteriorDesignProject
        fields = [
            "title",
            "description",
            "category",
            "location",
            "style",
            "status",
            "image",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input"}),
            "description": forms.Textarea(
                attrs={"class": "textarea", "rows": 4}
            ),
            "category": forms.Select(attrs={"class": "select"}),
            "location": forms.TextInput(attrs={"class": "input"}),
            "style": forms.TextInput(attrs={"class": "input"}),
            "status": forms.Select(attrs={"class": "select"}),
            "image": forms.ClearableFileInput(attrs={"class": "input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.order_by("name")
        self.fields["category"].required = False
