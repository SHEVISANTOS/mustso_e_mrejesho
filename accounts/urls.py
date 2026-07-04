from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.CitizenSignUpView.as_view(), name="register"),
    path("login/", views.MrejeshoLoginView.as_view(), name="login"),
    path("logout/", views.MrejeshoLogoutView.as_view(), name="logout"),
    path("admin-logout/", views.admin_logout, name="admin_logout"),
]
