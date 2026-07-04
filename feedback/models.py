import uuid
import random
import string
from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_tracking_number():
    """MREJ-2026-XXXXXX style public tracking code, similar to e-Mrejesho."""
    year = timezone.now().year
    suffix = "".join(random.choices(string.digits, k=6))
    return f"MREJ-{year}-{suffix}"


class Feedback(models.Model):

    class Category(models.TextChoices):
        COMPLAINT = "COMPLAINT", "Malalamiko (Complaint)"
        SUGGESTION = "SUGGESTION", "Mapendekezo (Suggestion)"
        INQUIRY = "INQUIRY", "Maulizo (Inquiry)"
        COMPLIMENT = "COMPLIMENT", "Pongezi (Compliment)"

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        ESCALATED = "ESCALATED", "Escalated"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"
        REJECTED = "REJECTED", "Rejected"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class EscalationLevel(models.IntegerChoices):
        REPRESENTATIVE = 1, "Representative"
        ADMIN = 2, "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_number = models.CharField(
        max_length=20, unique=True, default=generate_tracking_number, editable=False
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submitted_feedback"
    )
    department = models.ForeignKey(
        "departments.Department", on_delete=models.PROTECT, related_name="feedback_items"
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    attachment = models.FileField(upload_to="feedback_attachments/%Y/%m/", blank=True, null=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    escalation_level = models.PositiveSmallIntegerField(
        choices=EscalationLevel.choices, default=EscalationLevel.REPRESENTATIVE
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="assigned_feedback"
    )
    is_anonymous = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(
        null=True, blank=True, help_text="SLA deadline before auto-escalation is due"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tracking_number} - {self.subject}"

    def escalate(self, actor, reason=""):
        """Bump from Representative to Admin — the final escalation level."""
        if self.escalation_level >= self.EscalationLevel.ADMIN:
            return False

        self.escalation_level = self.EscalationLevel.ADMIN
        self.status = self.Status.ESCALATED
        self.assigned_to = None  # picked up by any admin
        self.save()
        FeedbackUpdate.objects.create(
            feedback=self,
            actor=actor,
            update_type=FeedbackUpdate.UpdateType.ESCALATION,
            message=reason or "Escalated to Admin",
            new_status=self.status,
        )
        from notifications.services import notify_escalation
        notify_escalation(self)
        return True

    def mark_resolved(self, actor, message=""):
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save()
        FeedbackUpdate.objects.create(
            feedback=self,
            actor=actor,
            update_type=FeedbackUpdate.UpdateType.RESOLUTION,
            message=message or "Marked as resolved",
            new_status=self.status,
        )
        from notifications.services import notify_resolution
        notify_resolution(self)


class FeedbackUpdate(models.Model):
    """Audit trail: every comment, status change and escalation on a Feedback item."""

    class UpdateType(models.TextChoices):
        COMMENT = "COMMENT", "Comment"
        STATUS_CHANGE = "STATUS_CHANGE", "Status Change"
        ESCALATION = "ESCALATION", "Escalation"
        RESOLUTION = "RESOLUTION", "Resolution"
        ASSIGNMENT = "ASSIGNMENT", "Assignment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name="updates")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    update_type = models.CharField(max_length=20, choices=UpdateType.choices, default=UpdateType.COMMENT)
    message = models.TextField()
    new_status = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.feedback.tracking_number} - {self.get_update_type_display()} by {self.actor}"
