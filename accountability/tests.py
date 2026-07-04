from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from departments.models import Department
from feedback.models import Feedback, FeedbackUpdate
from accountability.models import RepresentativeProfile, Promise, PublicDocument


class AccountabilitySignalsTests(TestCase):
    def test_profile_auto_created_for_representative(self):
        dept = Department.objects.create(name="ICT Department", code="ICT")
        user = User.objects.create_user(
            username="rep_test",
            password="password123",
            role=User.Role.REPRESENTATIVE,
            department=dept
        )
        self.assertTrue(RepresentativeProfile.objects.filter(user=user).exists())

    def test_profile_auto_created_for_admin(self):
        user = User.objects.create_user(
            username="admin_test",
            password="password123",
            role=User.Role.ADMIN
        )
        self.assertTrue(RepresentativeProfile.objects.filter(user=user).exists())

    def test_profile_not_created_for_student(self):
        user = User.objects.create_user(
            username="student_test",
            password="password123",
            role=User.Role.STUDENT
        )
        self.assertFalse(RepresentativeProfile.objects.filter(user=user).exists())


class PromiseViewsAccessTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="ICT Department", code="ICT")
        self.student = User.objects.create_user(
            username="student1", password="password123", role=User.Role.STUDENT
        )
        self.rep1 = User.objects.create_user(
            username="rep1", password="password123", role=User.Role.REPRESENTATIVE, department=self.dept
        )
        self.rep2 = User.objects.create_user(
            username="rep2", password="password123", role=User.Role.REPRESENTATIVE, department=self.dept
        )
        self.admin = User.objects.create_user(
            username="admin1", password="password123", role=User.Role.ADMIN
        )
        self.promise1 = Promise.objects.create(
            title="Promise One",
            description="Testing Description",
            representative=self.rep1,
            status=Promise.Status.NOT_STARTED
        )
        self.client = Client()

    def test_public_dashboard_accessible_anonymously(self):
        response = self.client.get(reverse("accountability:promise_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Promise One")

    def test_student_cannot_create_promise(self):
        self.client.login(username="student1", password="password123")
        response = self.client.get(reverse("accountability:promise_create"))
        self.assertEqual(response.status_code, 403)

    def test_representative_can_create_promise(self):
        self.client.login(username="rep1", password="password123")
        response = self.client.get(reverse("accountability:promise_create"))
        self.assertEqual(response.status_code, 200)

    def test_representative_cannot_edit_other_representative_promise(self):
        self.client.login(username="rep2", password="password123")
        response = self.client.get(
            reverse("accountability:promise_edit", args=[self.promise1.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_representative_can_edit_own_promise(self):
        self.client.login(username="rep1", password="password123")
        response = self.client.get(
            reverse("accountability:promise_edit", args=[self.promise1.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_can_edit_any_promise(self):
        self.client.login(username="admin1", password="password123")
        response = self.client.get(
            reverse("accountability:promise_edit", args=[self.promise1.pk])
        )
        self.assertEqual(response.status_code, 200)


class DocumentViewsTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="ICT Department", code="ICT")
        self.rep = User.objects.create_user(
            username="rep1", password="password123", role=User.Role.REPRESENTATIVE, department=self.dept
        )
        self.student = User.objects.create_user(
            username="student1", password="password123", role=User.Role.STUDENT
        )
        self.client = Client()

    def test_anonymous_user_can_view_document_list(self):
        response = self.client.get(reverse("accountability:document_list"))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_upload_document(self):
        self.client.login(username="student1", password="password123")
        response = self.client.get(reverse("accountability:document_upload"))
        self.assertEqual(response.status_code, 403)

    def test_representative_can_upload_document(self):
        self.client.login(username="rep1", password="password123")
        response = self.client.get(reverse("accountability:document_upload"))
        self.assertEqual(response.status_code, 200)


class RepresentativeMetricsTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="ICT Department", code="ICT")
        self.rep = User.objects.create_user(
            username="rep1", password="password123", role=User.Role.REPRESENTATIVE, department=self.dept
        )
        self.student = User.objects.create_user(
            username="student1", password="password123", role=User.Role.STUDENT
        )
        
        # Create campaign promises
        self.promise_done = Promise.objects.create(
            title="Promise Done",
            description="Testing Description",
            representative=self.rep,
            status=Promise.Status.COMPLETED
        )
        self.promise_pending = Promise.objects.create(
            title="Promise Pending",
            description="Testing Description",
            representative=self.rep,
            status=Promise.Status.IN_PROGRESS
        )

        # Create feedback items assigned to rep
        self.feedback_resolved = Feedback.objects.create(
            submitted_by=self.student,
            department=self.dept,
            category=Feedback.Category.COMPLAINT,
            subject="Resolved Feedback",
            description="Description test",
            assigned_to=self.rep,
            status=Feedback.Status.RESOLVED,
            resolved_at=timezone.now()
        )
        # Manually alter created_at for testing avg resolution time (10 hours ago)
        self.feedback_resolved.created_at = timezone.now() - timedelta(hours=10)
        self.feedback_resolved.save()

        self.feedback_open = Feedback.objects.create(
            submitted_by=self.student,
            department=self.dept,
            category=Feedback.Category.COMPLAINT,
            subject="Open Feedback",
            description="Description test",
            assigned_to=self.rep,
            status=Feedback.Status.IN_PROGRESS
        )

        # Create a feedback update comment from rep
        FeedbackUpdate.objects.create(
            feedback=self.feedback_open,
            actor=self.rep,
            update_type=FeedbackUpdate.UpdateType.COMMENT,
            message="Adding a test comment here"
        )
        self.client = Client()

    def test_metrics_calculation_in_rep_detail_view(self):
        self.client.login(username="student1", password="password123")
        response = self.client.get(
            reverse("accountability:rep_detail", args=[self.rep.pk])
        )
        self.assertEqual(response.status_code, 200)
        
        # Check calculated metrics in context
        metrics = response.context["metrics"]
        self.assertEqual(metrics["total_promises"], 2)
        self.assertEqual(metrics["completed_promises"], 1)
        self.assertEqual(metrics["promise_rate"], 50.0) # 50% met
        self.assertEqual(metrics["total_assigned"], 2)
        self.assertEqual(metrics["resolved_count"], 1)
        self.assertEqual(metrics["case_rate"], 50.0) # 50% resolved
        self.assertAlmostEqual(metrics["avg_resolution_hours"], 10.0, places=1)
        self.assertEqual(metrics["comments_count"], 1)
