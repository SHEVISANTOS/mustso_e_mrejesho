from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from departments.models import Department
from feedback.models import Feedback
from .decorators import admin_required
from .forms import DepartmentForm, RepresentativeForm

User = get_user_model()


@admin_required
def analytics_dashboard(request):
    total = Feedback.objects.count()
    resolved = Feedback.objects.filter(status__in=[Feedback.Status.RESOLVED, Feedback.Status.CLOSED]).count()
    escalated = Feedback.objects.filter(escalation_level=Feedback.EscalationLevel.ADMIN).count()
    resolution_rate = round((resolved / total) * 100, 1) if total else 0

    resolved_qs = Feedback.objects.filter(resolved_at__isnull=False).annotate(
        turnaround=ExpressionWrapper(F("resolved_at") - F("created_at"), output_field=DurationField())
    )
    avg_turnaround = resolved_qs.aggregate(avg=Avg("turnaround"))["avg"]
    avg_hours = round(avg_turnaround.total_seconds() / 3600, 1) if avg_turnaround else None

    context = {
        "kpis": {
            "total": total,
            "resolved": resolved,
            "escalated": escalated,
            "resolution_rate": resolution_rate,
            "avg_hours": avg_hours,
            "departments": Department.objects.filter(is_active=True).count(),
            "representatives": User.objects.filter(role=User.Role.REPRESENTATIVE, is_active_staff=True).count(),
        },
    }
    return render(request, "adminpanel/analytics.html", context)


@admin_required
def analytics_data(request):
    """Chart data for the Admin analytics dashboard — polled/fetched by Chart.js."""
    by_department = list(
        Feedback.objects.values("department__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    by_category = list(
        Feedback.objects.values("category").annotate(count=Count("id")).order_by("-count")
    )
    by_status = list(
        Feedback.objects.values("status").annotate(count=Count("id")).order_by("-count")
    )

    since = timezone.now() - timedelta(days=30)
    trend_qs = (
        Feedback.objects.filter(created_at__gte=since)
        .extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    trend = [{"day": str(row["day"]), "count": row["count"]} for row in trend_qs]

    dept_performance = list(
        Department.objects.filter(is_active=True)
        .annotate(
            total_cases=Count("feedback_items"),
            resolved_cases=Count(
                "feedback_items",
                filter=Q(feedback_items__status__in=["RESOLVED", "CLOSED"]),
            ),
        )
        .values("name", "total_cases", "resolved_cases")
        .order_by("-total_cases")[:10]
    )

    return JsonResponse({
        "by_department": by_department,
        "by_category": by_category,
        "by_status": by_status,
        "trend": trend,
        "dept_performance": dept_performance,
    })


# --- Department management ---

@admin_required
def department_list(request):
    departments = Department.objects.annotate(
        case_count=Count("feedback_items"), rep_count=Count("staff_members")
    ).order_by("name")
    return render(request, "adminpanel/department_list.html", {"departments": departments})


@admin_required
def department_create(request):
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department created.")
            return redirect("adminpanel:department_list")
    else:
        form = DepartmentForm()
    return render(request, "adminpanel/department_form.html", {"form": form, "title": "New Department"})


@admin_required
def department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated.")
            return redirect("adminpanel:department_list")
    else:
        form = DepartmentForm(instance=dept)
    return render(request, "adminpanel/department_form.html", {"form": form, "title": f"Edit {dept.name}"})


@admin_required
def department_toggle_active(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    dept.is_active = not dept.is_active
    dept.save()
    messages.success(request, f"{dept.name} is now {'active' if dept.is_active else 'inactive'}.")
    return redirect("adminpanel:department_list")


# --- User / representative management ---

@admin_required
def user_list(request):
    users = User.objects.exclude(role=User.Role.STUDENT).select_related("department").order_by("role", "username")
    return render(request, "adminpanel/user_list.html", {"users": users})


@admin_required
def representative_create(request):
    if request.method == "POST":
        form = RepresentativeForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, f"{user.get_role_display()} account created for {user.username}.")
            return redirect("adminpanel:user_list")
    else:
        form = RepresentativeForm()
    return render(request, "adminpanel/user_form.html", {"form": form, "title": "New Representative / Admin"})


@admin_required
def user_toggle_active(request, pk):
    target = get_object_or_404(User, pk=pk)
    target.is_active_staff = not target.is_active_staff
    target.save()
    messages.success(request, f"{target.username} is now {'active' if target.is_active_staff else 'suspended'}.")
    return redirect("adminpanel:user_list")
