from django.contrib import admin
from .models import Feedback, FeedbackUpdate


class FeedbackUpdateInline(admin.TabularInline):
    model = FeedbackUpdate
    extra = 0
    readonly_fields = ("actor", "update_type", "message", "new_status", "created_at")
    can_delete = False


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "tracking_number", "subject", "category", "department", "status",
        "priority", "escalation_level", "assigned_to", "created_at",
    )
    list_filter = ("status", "category", "priority", "escalation_level", "department")
    search_fields = ("tracking_number", "subject", "description", "submitted_by__username")
    readonly_fields = ("tracking_number", "created_at", "updated_at")
    inlines = [FeedbackUpdateInline]
