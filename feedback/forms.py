from django import forms
from .models import Feedback, FeedbackUpdate


class FeedbackSubmitForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["department", "category", "subject", "description", "attachment", "is_anonymous"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5, "placeholder": "Describe your feedback in detail..."}),
            "subject": forms.TextInput(attrs={"placeholder": "Short summary, e.g. 'No water in Hostel B'"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = self.fields["department"].queryset.filter(is_active=True)


class FeedbackUpdateForm(forms.ModelForm):
    class Meta:
        model = FeedbackUpdate
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3, "placeholder": "Add a comment or response..."}),
        }


class EscalationForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Reason for escalation (optional)"}),
        required=False,
    )
