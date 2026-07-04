from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from departments.models import Department
from feedback.models import Feedback


class AdminPanelAccessTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="ICT Department", code="ICT")
        self.student = User.objects.create_user(username="stu1", password="pass12345", role=User.Role.STUDENT)
        self.rep = User.objects.create_user(
            username="rep1", password="pass12345", role=User.Role.REPRESENTATIVE, department=self.dept
        )
        self.admin = User.objects.create_user(
            username="adm1", password="pass12345", role=User.Role.ADMIN, is_staff=True, is_superuser=True
        )

    def test_student_cannot_access_admin_panel(self):
        client = Client()
        client.login(username="stu1", password="pass12345")
        response = client.get(reverse("adminpanel:analytics"))
        self.assertEqual(response.status_code, 403)

    def test_representative_cannot_access_admin_panel(self):
        client = Client()
        client.login(username="rep1", password="pass12345")
        response = client.get(reverse("adminpanel:analytics"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_admin_panel(self):
        client = Client()
        client.login(username="adm1", password="pass12345")
        response = client.get(reverse("adminpanel:analytics"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirected_to_login(self):
        client = Client()
        response = client.get(reverse("adminpanel:analytics"))
        self.assertEqual(response.status_code, 302)


class AnalyticsDataTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="ICT Department", code="ICT")
        self.student = User.objects.create_user(username="stu1", password="pass12345", role=User.Role.STUDENT)
        self.admin = User.objects.create_user(
            username="adm1", password="pass12345", role=User.Role.ADMIN, is_staff=True, is_superuser=True
        )
        self.fb = Feedback.objects.create(
            submitted_by=self.student, department=self.dept,
            category=Feedback.Category.COMPLAINT, subject="Broken tap", description="Leaking.",
        )
        self.client = Client()
        self.client.login(username="adm1", password="pass12345")

    def test_analytics_data_endpoint_returns_expected_shape(self):
        response = self.client.get(reverse("adminpanel:analytics_data"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        for key in ("by_department", "by_category", "by_status", "trend", "dept_performance"):
            self.assertIn(key, data)
        self.assertEqual(data["by_department"][0]["count"], 1)

    def test_dept_performance_counts_resolved_cases(self):
        self.fb.mark_resolved(self.admin)
        response = self.client.get(reverse("adminpanel:analytics_data"))
        data = response.json()
        dept_row = next(d for d in data["dept_performance"] if d["name"] == self.dept.name)
        self.assertEqual(dept_row["resolved_cases"], 1)


class DepartmentManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="adm1", password="pass12345", role=User.Role.ADMIN, is_staff=True, is_superuser=True
        )
        self.client = Client()
        self.client.login(username="adm1", password="pass12345")

    def test_admin_can_create_department(self):
        response = self.client.post(reverse("adminpanel:department_create"), {
            "name": "Finance Department", "code": "FIN", "description": "", "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Department.objects.filter(code="FIN").exists())

    def test_admin_can_toggle_department_active_state(self):
        dept = Department.objects.create(name="Library", code="LIB")
        self.client.get(reverse("adminpanel:department_toggle", args=[dept.pk]))
        dept.refresh_from_db()
        self.assertFalse(dept.is_active)


class RepresentativeProvisioningTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="ICT Department", code="ICT")
        self.admin = User.objects.create_user(
            username="adm1", password="pass12345", role=User.Role.ADMIN, is_staff=True, is_superuser=True
        )
        self.client = Client()
        self.client.login(username="adm1", password="pass12345")

    def test_admin_can_create_representative_account(self):
        response = self.client.post(reverse("adminpanel:representative_create"), {
            "username": "newrep", "first_name": "Grace", "last_name": "Kileo",
            "email": "grace@must.ac.tz", "role": "REPRESENTATIVE", "department": self.dept.id,
            "password": "StrongPass123!",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newrep")
        self.assertEqual(user.role, User.Role.REPRESENTATIVE)
        self.assertTrue(user.check_password("StrongPass123!"))

    def test_representative_requires_department(self):
        response = self.client.post(reverse("adminpanel:representative_create"), {
            "username": "newrep2", "first_name": "Grace", "last_name": "Kileo",
            "email": "grace2@must.ac.tz", "role": "REPRESENTATIVE", "department": "",
            "password": "StrongPass123!",
        })
        self.assertEqual(response.status_code, 200)  # re-rendered with error
        self.assertFalse(User.objects.filter(username="newrep2").exists())

    def test_admin_can_suspend_a_representative(self):
        rep = User.objects.create_user(
            username="rep2", password="pass12345", role=User.Role.REPRESENTATIVE, department=self.dept
        )
        self.client.get(reverse("adminpanel:user_toggle", args=[rep.pk]))
        rep.refresh_from_db()
        self.assertFalse(rep.is_active_staff)
