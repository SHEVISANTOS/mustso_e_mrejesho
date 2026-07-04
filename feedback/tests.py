from django.core import mail
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from departments.models import Department
from notifications.models import Notification
from .models import Feedback, FeedbackUpdate


class BaseFeedbackTestCase(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="ICT Department", code="ICT")
        self.other_dept = Department.objects.create(name="Hostels Department", code="HOSTEL")

        self.student = User.objects.create_user(
            username="student1", password="pass12345", role=User.Role.STUDENT,
            registration_number="MUST/2024/001", email="student1@must.ac.tz",
        )
        self.rep = User.objects.create_user(
            username="rep_ict", password="pass12345", role=User.Role.REPRESENTATIVE,
            department=self.dept, email="rep@must.ac.tz",
        )
        self.rep_other = User.objects.create_user(
            username="rep_hostel", password="pass12345", role=User.Role.REPRESENTATIVE,
            department=self.other_dept, email="rep2@must.ac.tz",
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
            is_staff=True, is_superuser=True, email="admin@must.ac.tz",
        )

        self.feedback = Feedback.objects.create(
            submitted_by=self.student, department=self.dept,
            category=Feedback.Category.COMPLAINT,
            subject="WiFi not working in Hostel B",
            description="The WiFi has been down for 3 days.",
        )


class TrackingNumberTests(BaseFeedbackTestCase):
    def test_tracking_number_auto_generated_and_unique(self):
        fb2 = Feedback.objects.create(
            submitted_by=self.student, department=self.dept,
            category=Feedback.Category.SUGGESTION, subject="More study space",
            description="Library is always full.",
        )
        self.assertTrue(self.feedback.tracking_number.startswith("MREJ-"))
        self.assertNotEqual(self.feedback.tracking_number, fb2.tracking_number)


class RoleBasedAccessControlTests(BaseFeedbackTestCase):
    """Objective 2: role-based access control for students, representatives, admins."""

    def test_student_sees_only_own_feedback(self):
        other_student = User.objects.create_user(username="student2", password="pass12345", role=User.Role.STUDENT)
        Feedback.objects.create(
            submitted_by=other_student, department=self.dept,
            category=Feedback.Category.INQUIRY, subject="Fee query", description="...",
        )
        client = Client()
        client.login(username="student1", password="pass12345")
        response = client.get(reverse("feedback:dashboard"))
        self.assertContains(response, "WiFi not working in Hostel B")
        self.assertNotContains(response, "Fee query")

    def test_representative_only_sees_own_department_at_level_1(self):
        client = Client()
        client.login(username="rep_hostel", password="pass12345")
        response = client.get(reverse("feedback:detail", args=[self.feedback.pk]))
        self.assertEqual(response.status_code, 403)  # wrong department

    def test_representative_cannot_view_escalated_case(self):
        self.feedback.escalate(self.rep)
        client = Client()
        client.login(username="rep_ict", password="pass12345")
        response = client.get(reverse("feedback:detail", args=[self.feedback.pk]))
        self.assertEqual(response.status_code, 403)  # escalated past their level

    def test_admin_sees_everything(self):
        client = Client()
        client.login(username="admin1", password="pass12345")
        response = client.get(reverse("feedback:dashboard"))
        self.assertContains(response, "WiFi not working in Hostel B")

    def test_student_cannot_act_on_feedback(self):
        client = Client()
        client.login(username="student1", password="pass12345")
        response = client.get(reverse("feedback:detail", args=[self.feedback.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_act"])


class EscalationAndResolutionTests(BaseFeedbackTestCase):
    """Objective 1: resolution tracking mechanism."""

    def test_escalation_moves_to_admin_level(self):
        result = self.feedback.escalate(self.rep, reason="No response in 48h")
        self.feedback.refresh_from_db()
        self.assertTrue(result)
        self.assertEqual(self.feedback.escalation_level, Feedback.EscalationLevel.ADMIN)
        self.assertEqual(self.feedback.status, Feedback.Status.ESCALATED)

    def test_cannot_escalate_past_admin_level(self):
        self.feedback.escalate(self.rep)
        result = self.feedback.escalate(self.admin)
        self.assertFalse(result)

    def test_mark_resolved_sets_status_and_timestamp(self):
        self.feedback.mark_resolved(self.rep, message="Router replaced.")
        self.feedback.refresh_from_db()
        self.assertEqual(self.feedback.status, Feedback.Status.RESOLVED)
        self.assertIsNotNone(self.feedback.resolved_at)

    def test_audit_trail_records_every_action(self):
        self.feedback.escalate(self.rep, reason="Escalating")
        self.feedback.mark_resolved(self.admin, message="Fixed")
        updates = FeedbackUpdate.objects.filter(feedback=self.feedback)
        self.assertEqual(updates.count(), 2)
        self.assertEqual(updates.first().update_type, FeedbackUpdate.UpdateType.ESCALATION)
        self.assertEqual(updates.last().update_type, FeedbackUpdate.UpdateType.RESOLUTION)


class NotificationTests(BaseFeedbackTestCase):
    """Objective 3: automated notification system (in-app + email)."""

    def test_submitting_feedback_notifies_department_representative(self):
        client = Client()
        client.login(username="student1", password="pass12345")
        client.post(reverse("feedback:submit"), {
            "department": self.dept.id, "category": "COMPLAINT",
            "subject": "Broken projector", "description": "Room B12 projector is broken.",
        })
        notif = Notification.objects.filter(recipient=self.rep, event_type=Notification.EventType.NEW_FEEDBACK)
        self.assertTrue(notif.exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.rep.email, mail.outbox[0].to)

    def test_escalation_notifies_all_admins(self):
        self.feedback.escalate(self.rep)
        notif = Notification.objects.filter(recipient=self.admin, event_type=Notification.EventType.ESCALATED)
        self.assertTrue(notif.exists())

    def test_resolution_notifies_submitting_student(self):
        self.feedback.mark_resolved(self.rep)
        notif = Notification.objects.filter(recipient=self.student, event_type=Notification.EventType.RESOLVED)
        self.assertTrue(notif.exists())

    def test_unread_count_endpoint(self):
        Notification.objects.create(
            recipient=self.student, event_type=Notification.EventType.RESOLVED, message="Test"
        )
        client = Client()
        client.login(username="student1", password="pass12345")
        response = client.get(reverse("notifications:unread_count"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unread_count"], 1)


class LiveDashboardTests(BaseFeedbackTestCase):
    """Objective 1: real-time dashboard data endpoint."""

    def test_dashboard_data_endpoint_returns_correct_counts(self):
        client = Client()
        client.login(username="admin1", password="pass12345")
        response = client.get(reverse("feedback:dashboard_data"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["counts"]["total"], 1)
        self.assertEqual(data["counts"]["submitted"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["tracking_number"], self.feedback.tracking_number)

    def test_dashboard_data_reflects_status_filter(self):
        self.feedback.escalate(self.rep)
        client = Client()
        client.login(username="admin1", password="pass12345")
        response = client.get(reverse("feedback:dashboard_data"), {"status": "ESCALATED"})
        data = response.json()
        self.assertEqual(data["counts"]["total"], 1)
        self.assertEqual(data["items"][0]["status"], "ESCALATED")
