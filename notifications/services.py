import logging
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from .models import Notification

logger = logging.getLogger(__name__)


def _create(recipient, event_type, message, feedback=None):
    if recipient is None:
        return
    notif = Notification.objects.create(
        recipient=recipient, event_type=event_type, message=message, feedback=feedback
    )
    _send_email(recipient, message, feedback)
    _broadcast(recipient)
    return notif


def _broadcast(recipient):
    """Push instant WebSocket updates (objectives 1 & 3). Falls back silently —
    if Channels isn't reachable for any reason, the UI still updates on the
    next fallback poll instead of raising an error."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        from .consumers import DASHBOARD_GROUP

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(DASHBOARD_GROUP, {"type": "dashboard.message"})

        unread_count = recipient.notifications.filter(is_read=False).count()
        async_to_sync(channel_layer.group_send)(
            f"notify_user_{recipient.id}",
            {"type": "notify.message", "unread_count": unread_count},
        )
    except Exception:
        logger.exception("WebSocket broadcast failed; live updates will fall back to polling.")


def _send_email(recipient, message, feedback):
    if not recipient.email:
        return
    subject = "MUST e-Mrejesho: Update on your feedback" if feedback else "MUST e-Mrejesho: Notification"
    body = message
    if feedback:
        body += f"\n\nTracking number: {feedback.tracking_number}"
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@must-mrejesho.ac.tz"),
            recipient_list=[recipient.email],
            fail_silently=True,
        )
    except Exception:
        # Never let a broken/unconfigured mail server break the request-response cycle.
        logger.exception("Failed to send notification email to %s", recipient.email)


def notify_new_feedback(feedback):
    """Alert every active Representative in the target department."""
    for rep in feedback.department.representatives:
        _create(
            rep, Notification.EventType.NEW_FEEDBACK,
            f"New {feedback.get_category_display()} submitted: \"{feedback.subject}\"",
            feedback,
        )


def notify_new_comment(feedback, actor):
    """Notify the other side of the conversation: student <-> handler."""
    if actor.role == actor.Role.STUDENT:
        if feedback.assigned_to:
            _create(
                feedback.assigned_to, Notification.EventType.NEW_COMMENT,
                f"New comment on \"{feedback.subject}\" from the submitter",
                feedback,
            )
    else:
        _create(
            feedback.submitted_by, Notification.EventType.NEW_COMMENT,
            f"New response on your feedback \"{feedback.subject}\"",
            feedback,
        )


def notify_escalation(feedback):
    """Alert all Admins once a case reaches the final escalation level."""
    from accounts.models import User
    for admin in User.objects.filter(role=User.Role.ADMIN, is_active=True):
        _create(
            admin, Notification.EventType.ESCALATED,
            f"Feedback escalated to Admin: \"{feedback.subject}\" ({feedback.department.name})",
            feedback,
        )


def notify_resolution(feedback):
    _create(
        feedback.submitted_by, Notification.EventType.RESOLVED,
        f"Your feedback \"{feedback.subject}\" has been marked resolved",
        feedback,
    )


def notify_closed(feedback):
    _create(
        feedback.submitted_by, Notification.EventType.CLOSED,
        f"Your feedback \"{feedback.subject}\" has been closed",
        feedback,
    )
