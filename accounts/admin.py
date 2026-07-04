from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "role", "department", "registration_number", "is_active_staff")
    list_filter = ("role", "department", "is_active_staff")
    search_fields = ("username", "first_name", "last_name", "registration_number", "email")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("MUST e-Mrejesho", {
            "fields": ("role", "registration_number", "phone_number", "department", "is_active_staff")
        }),
    )
