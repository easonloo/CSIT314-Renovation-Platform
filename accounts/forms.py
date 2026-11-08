from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.views.decorators.debug import sensitive_variables

from .controllers import (
    AssignUserProfileController,
    LoginController,
    UpdateUserAccountController,
)
from .models import UserProfile


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
    @sensitive_variables()
    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if username is not None and password:
            self.user_cache = LoginController().authenticate(
                request=self.request, username=username, password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if not LoginController().can_login(user):
            raise ValidationError(
                "Your account is unavailable. "
                "Please contact a user administrator.",
                code="account_unavailable",
            )


class AccountCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    profile = forms.ModelChoiceField(
        queryset=None,
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
        self.fields["profile"].queryset = AssignUserProfileController().available_for_assignment()

        for field in self.fields.values():
            field.widget.attrs["class"] = "input"


class AccountUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    profile = forms.ModelChoiceField(
        queryset=None,
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
            AssignUserProfileController().available_for_assignment(account.profile_id)
        )

        self.initial["profile"] = account.profile_id

        for field in self.fields.values():
            field.widget.attrs["class"] = "input"

    def clean_username(self):
        username = self.cleaned_data["username"]

        if UpdateUserAccountController().username_exists(
            username, exclude_user_id=self.instance.pk,
        ):
            raise forms.ValidationError(
                "A user with that username already exists."
            )

        return username
