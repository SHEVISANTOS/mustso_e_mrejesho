import uuid
from django.db import models
from django.conf import settings


class RepresentativeProfile(models.Model):
    """Profile details for representative-role users including bio, goals, and manifesto."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rep_profile"
    )
    bio = models.TextField(blank=True)
    goals = models.TextField(
        blank=True,
        help_text="Key goals or objectives during tenure (use bullet points or newlines)"
    )
    manifesto = models.TextField(blank=True, help_text="Full manifesto text")
    profile_picture = models.FileField(upload_to="rep_profiles/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user}"


class Promise(models.Model):
    """Campaign promises tracking with status, category, target dates, and evidence of progress."""

    class Category(models.TextChoices):
        ACADEMICS = "ACADEMICS", "Academics"
        HOSTELS = "HOSTELS", "Hostels & Housing"
        WELFARE = "WELFARE", "Student Welfare"
        INFRASTRUCTURE = "INFRASTRUCTURE", "Infrastructure & Facilities"
        FINANCE = "FINANCE", "Finance & Budgeting"
        GENERAL = "GENERAL", "General Governance"

    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not Started"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        STALLED = "STALLED", "Stalled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    representative = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="promises"
    )
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.GENERAL
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED
    )
    evidence = models.TextField(
        blank=True,
        help_text="Evidence/notes detailing implementation progress or completion"
    )
    evidence_file = models.FileField(
        upload_to="promise_evidence/",
        blank=True,
        null=True,
        help_text="Upload official proof, photos, or documents confirming resolution"
    )
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class PublicDocument(models.Model):
    """Searchable archive for meeting minutes, legislation, and financial/budget reports."""

    class DocType(models.TextChoices):
        MINUTES = "MINUTES", "Meeting Minutes"
        LEGISLATION = "LEGISLATION", "Legislation & Constitution"
        FINANCIAL = "FINANCIAL", "Financial Report"
        BUDGET = "BUDGET", "Budget Report"
        OTHER = "OTHER", "Other Document"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    document_type = models.CharField(
        max_length=20,
        choices=DocType.choices,
        default=DocType.OTHER
    )
    file = models.FileField(upload_to="public_documents/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_documents"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"
