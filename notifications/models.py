import uuid
from django.conf import settings
from django.db import models


class Notification(models.Model):
    """In-app notification, optionally mirrored by email (see notifications.services)."""

    class EventType(models.TextChoices):
        NEW_FEEDBACK = "NEW_FEEDBACK", "New Feedback Assigned"
        NEW_COMMENT = "NEW_COMMENT", "New Comment"
        ESCALATED = "ESCALATED", "Feedback Escalated"
        RESOLVED = "RESOLVED", "Feedback Resolved"
        CLOSED = "CLOSED", "Feedback Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    message = models.CharField(max_length=255)
    feedback = models.ForeignKey(
        "feedback.Feedback", on_delete=models.CASCADE, related_name="notifications",
        null=True, blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient} - {self.message[:40]}"
