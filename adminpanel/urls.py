from django.urls import path
from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.analytics_dashboard, name="analytics"),
    path("data/", views.analytics_data, name="analytics_data"),

    path("departments/", views.department_list, name="department_list"),
    path("departments/new/", views.department_create, name="department_create"),
    path("departments/<uuid:pk>/edit/", views.department_edit, name="department_edit"),
    path("departments/<uuid:pk>/toggle/", views.department_toggle_active, name="department_toggle"),

    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.representative_create, name="representative_create"),
    path("users/<uuid:pk>/toggle/", views.user_toggle_active, name="user_toggle"),
]
