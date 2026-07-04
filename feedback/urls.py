from django.urls import path
from . import views

app_name = "feedback"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("data/", views.dashboard_data, name="dashboard_data"),
    path("submit/", views.SubmitFeedbackView.as_view(), name="submit"),
    path("<uuid:pk>/", views.feedback_detail, name="detail"),
]
