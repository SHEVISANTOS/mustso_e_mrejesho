from django.test import TestCase, Client
from django.urls import reverse
from .models import User


class RoleDefaultsTests(TestCase):
    def test_public_registration_always_creates_student(self):
        """Objective 2: self-registration must never grant elevated roles."""
        client = Client()
        response = client.post(reverse("accounts:register"), {
            "first_name": "Amina", "last_name": "Juma", "email": "amina@must.ac.tz",
            "registration_number": "MUST/2024/010", "phone_number": "0712345678",
            "username": "amina2024", "password1": "StrongPass123!", "password2": "StrongPass123!",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="amina2024")
        self.assertEqual(user.role, User.Role.STUDENT)

    def test_login_required_for_dashboard(self):
        client = Client()
        response = client.get(reverse("feedback:dashboard"))
        self.assertEqual(response.status_code, 302)  # redirected to login

    def test_logout_requires_post_not_get(self):
        """Regression test: Django 5+ LogoutView rejects GET (405)."""
        user = User.objects.create_user(username="rep1", password="pass12345", role=User.Role.REPRESENTATIVE)
        client = Client()
        client.login(username="rep1", password="pass12345")
        get_response = client.get(reverse("accounts:logout"))
        self.assertEqual(get_response.status_code, 405)
        post_response = client.post(reverse("accounts:logout"))
        self.assertEqual(post_response.status_code, 302)
