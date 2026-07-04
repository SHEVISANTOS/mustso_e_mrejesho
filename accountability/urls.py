from django.urls import path
from . import views

app_name = "accountability"

urlpatterns = [
    # Promise Tracker & Dashboard
    path("promises/", views.promise_dashboard, name="promise_dashboard"),
    path("promises/new/", views.promise_create, name="promise_create"),
    path("promises/<uuid:pk>/", views.promise_detail, name="promise_detail"),
    path("promises/<uuid:pk>/edit/", views.promise_edit, name="promise_edit"),

    # Public Documents Repository
    path("documents/", views.document_list, name="document_list"),
    path("documents/upload/", views.document_upload, name="document_upload"),

    # Representative Profiles
    path("representatives/", views.rep_list, name="rep_list"),
    path("representatives/<uuid:pk>/", views.rep_detail, name="rep_detail"),
    path("representatives/<uuid:pk>/edit/", views.rep_profile_edit, name="rep_profile_edit"),
]
