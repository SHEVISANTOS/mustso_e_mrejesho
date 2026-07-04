import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model for MUST Student Government Accountability & Feedback System.

    Roles form the escalation chain:
    STUDENT          -> submits feedback, tracks resolution
    REPRESENTATIVE   -> first responder, tied to a Department/Organization
    ADMIN            -> final escalation point, university-wide oversight
    """

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        REPRESENTATIVE = "REPRESENTATIVE", "Representative"
        ADMIN = "ADMIN", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    registration_number = models.CharField(
        max_length=30, blank=True, null=True, unique=True,
        help_text="Student registration number or staff ID"
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    department = models.ForeignKey(
        "departments.Department", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="staff_members",
        help_text="Required for Representative role"
    )
    is_active_staff = models.BooleanField(
        default=True, help_text="Toggle off to temporarily suspend a representative from receiving cases"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_handler(self):
        return self.role in (self.Role.REPRESENTATIVE, self.Role.ADMIN)
