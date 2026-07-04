from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class CitizenRegistrationForm(UserCreationForm):
    """Public self-registration — always creates a STUDENT account.
    Staff roles (Representative / Admin) are provisioned by an admin."""

    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    registration_number = forms.CharField(
        max_length=30, required=True, label="Registration/Staff Number"
    )
    phone_number = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = (
            "username", "first_name", "last_name", "email",
            "registration_number", "phone_number", "password1", "password2",
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        if commit:
            user.save()
        return user
