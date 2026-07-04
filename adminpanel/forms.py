from django import forms
from django.contrib.auth import get_user_model
from departments.models import Department

User = get_user_model()


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class RepresentativeForm(forms.ModelForm):
    """Admin-only form for provisioning Representative or Admin accounts —
    the only way these elevated roles get created (self-registration is
    always forced to STUDENT, see accounts.forms.CitizenRegistrationForm)."""

    password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "department", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (User.Role.REPRESENTATIVE, "Representative"),
            (User.Role.ADMIN, "Admin"),
        ]
        self.fields["department"].required = False
        self.fields["department"].help_text = "Required for Representatives; leave blank for Admins."

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == User.Role.REPRESENTATIVE and not cleaned.get("department"):
            self.add_error("department", "A department is required for the Representative role.")
        return cleaned
