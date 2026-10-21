from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from django import forms
from django.db.models import Q
from .models import UserAccount, UserProfile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["name", "description"]
        error_messages = {
            "name": {
                "unique": "A profile with this name already exists.",
            },
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "description": forms.Textarea(
                attrs={"class": "input", "rows": 3}
            ),
        }


class AccountLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)



        has_active_profile = UserAccount.objects.filter(
            user=user,
            profile__is_active=True,
        ).exists()

        if not has_active_profile:
            raise ValidationError(
                "Your account is unavailable. "
                "Please contact a user administrator.",
                code="account_unavailable",
            )


class AccountCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    profile = forms.ModelChoiceField(
        queryset=UserProfile.objects.filter(
            is_active=True
        ).order_by("name"),
        empty_label="Select a profile",
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "profile",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "input"



class AccountUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    profile = forms.ModelChoiceField(
        queryset=UserProfile.objects.none()
    )

    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "profile",
        ]

    def __init__(self, *args, account, **kwargs):
        super().__init__(
            *args,
            instance=account.user,
            **kwargs,
        )

        self.fields["profile"].queryset = (
            UserProfile.objects.filter(
                Q(is_active=True) | Q(pk=account.profile_id)
            ).order_by("name")
        )

        self.initial["profile"] = account.profile_id

        for field in self.fields.values():
            field.widget.attrs["class"] = "input"

    def clean_username(self):
        username = self.cleaned_data["username"]

        duplicate = (
            get_user_model().objects.filter(
                username__iexact=username
            )
            .exclude(pk=self.instance.pk)
            .exists()
        )

        if duplicate:
            raise forms.ValidationError(
                "A user with that username already exists."
            )

        return username
