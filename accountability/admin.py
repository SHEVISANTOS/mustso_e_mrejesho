from django.contrib import admin
from .models import RepresentativeProfile, Promise, PublicDocument


@admin.register(RepresentativeProfile)
class RepresentativeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "updated_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "bio")


@admin.register(Promise)
class PromiseAdmin(admin.ModelAdmin):
    list_display = ("title", "representative", "category", "status", "target_date", "created_at")
    list_filter = ("category", "status")
    search_fields = ("title", "description", "representative__username", "evidence")


@admin.register(PublicDocument)
class PublicDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "uploaded_by", "created_at")
    list_filter = ("document_type",)
    search_fields = ("title", "description", "uploaded_by__username")
