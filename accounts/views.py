from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import CitizenRegistrationForm


class CitizenSignUpView(CreateView):
    form_class = CitizenRegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("feedback:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class MrejeshoLoginView(LoginView):
    template_name = "accounts/login.html"


class MrejeshoLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")

def admin_logout(request):
    """GET-accessible logout for the Jazzmin admin top menu — Jazzmin's base
    template predates Django 5's POST-only LogoutView requirement."""
    logout(request)
    return redirect("/admin/login/")