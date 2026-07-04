import uuid
from django.db import models


class Department(models.Model):
    """A MUST unit/organization that feedback can be routed to.

    e.g. Academics, Hostels/Housing, ICT, Finance, Library, Health Services,
    Examinations, Students' Welfare, Estates & Works, or a student government
    organ (e.g. Faculty Student Council).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=15, unique=True, help_text="Short code e.g. ICT, HOSTEL, ACAD")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def representatives(self):
        return self.staff_members.filter(role="REPRESENTATIVE", is_active_staff=True)
