from django import forms
from django.contrib.auth import get_user_model
from .models import Promise, RepresentativeProfile, PublicDocument

User = get_user_model()


class PromiseForm(forms.ModelForm):
    class Meta:
        model = Promise
        fields = [
            "title",
            "description",
            "category",
            "status",
            "target_date",
            "evidence",
            "evidence_file",
            "representative",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "evidence": forms.Textarea(attrs={"rows": 3}),
            "target_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Restrict representative choices to only Representatives and Admins
        self.fields["representative"].queryset = User.objects.filter(
            role__in=[User.Role.REPRESENTATIVE, User.Role.ADMIN]
        )

        # If user is a Representative, fix the field to themselves
        if user and user.role == User.Role.REPRESENTATIVE:
            self.fields["representative"].initial = user
            self.fields["representative"].widget = forms.HiddenInput()
            self.fields["representative"].required = False


class RepresentativeProfileForm(forms.ModelForm):
    class Meta:
        model = RepresentativeProfile
        fields = ["bio", "goals", "manifesto", "profile_picture"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "Brief biographical details..."}),
            "goals": forms.Textarea(attrs={"rows": 4, "placeholder": "1. Goal A\n2. Goal B..."}),
            "manifesto": forms.Textarea(attrs={"rows": 6, "placeholder": "Detailed campaign manifesto..."}),
        }


class PublicDocumentForm(forms.ModelForm):
    class Meta:
        model = PublicDocument
        fields = ["title", "description", "document_type", "file"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Provide a brief description of the document..."}),
        }
