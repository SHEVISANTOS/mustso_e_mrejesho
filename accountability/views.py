from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model

# Import the custom User model via get_user_model to ensure proper subclass
User = get_user_model()

from feedback.models import Feedback, FeedbackUpdate
from .models import Promise, RepresentativeProfile, PublicDocument
from .forms import PromiseForm, RepresentativeProfileForm, PublicDocumentForm
from .utils import check_permission, parse_goals, ensure_representative_profiles, calculate_resolution_metrics


# ==============================================================================
# Promise Tracker & Dashboard Views
# ==============================================================================

def promise_dashboard(request):
    """Public dashboard showing campaign promises statistics, charts, and lists."""
    queryset = Promise.objects.select_related("representative", "representative__department")

    # Filters
    status_filter = request.GET.get("status")
    category_filter = request.GET.get("category")

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if category_filter:
        queryset = queryset.filter(category=category_filter)

    # Calculate statistics
    all_promises = Promise.objects.all()
    total_count = all_promises.count()
    completed_count = all_promises.filter(status=Promise.Status.COMPLETED).count()
    in_progress_count = all_promises.filter(status=Promise.Status.IN_PROGRESS).count()
    stalled_count = all_promises.filter(status=Promise.Status.STALLED).count()
    not_started_count = all_promises.filter(status=Promise.Status.NOT_STARTED).count()

    completion_rate = round((completed_count / total_count * 100), 1) if total_count > 0 else 0

    context = {
        "promises": queryset[:100],
        "categories": Promise.Category.choices,
        "statuses": Promise.Status.choices,
        "active_status": status_filter,
        "active_category": category_filter,
        "stats": {
            "total": total_count,
            "completed": completed_count,
            "in_progress": in_progress_count,
            "stalled": stalled_count,
            "not_started": not_started_count,
            "completion_rate": completion_rate,
        }
    }
    return render(request, "accountability/promise_dashboard.html", context)


def promise_detail(request, pk):
    """View detail of a campaign promise with evidence."""
    promise = get_object_or_404(Promise, pk=pk)
    can_edit = request.user.is_authenticated and (
        request.user.role == User.Role.ADMIN or request.user == promise.representative
    )
    return render(request, "accountability/promise_detail.html", {"promise": promise, "can_edit": can_edit})


@login_required
def promise_create(request):
    """Allow representatives and admins to create campaign promises."""
    if request.user.role not in [User.Role.REPRESENTATIVE, User.Role.ADMIN]:
        raise PermissionDenied("Only Representatives and Admins can create promises.")

    if request.method == "POST":
        form = PromiseForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            promise = form.save(commit=False)
            if request.user.role == User.Role.REPRESENTATIVE:
                promise.representative = request.user
            promise.save()
            messages.success(request, "Campaign promise created successfully.")
            return redirect("accountability:promise_dashboard")
    else:
        form = PromiseForm(user=request.user)

    return render(request, "accountability/promise_form.html", {"form": form, "title": "Create Promise"})


@login_required
def promise_edit(request, pk):
    """Allow representatives to edit their own promises, or admins to edit any."""
    promise = get_object_or_404(Promise, pk=pk)
    if not (request.user.role == User.Role.ADMIN or request.user == promise.representative):
        raise PermissionDenied("You do not have permission to edit this promise.")

    if request.method == "POST":
        form = PromiseForm(request.POST, request.FILES, instance=promise, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Campaign promise updated successfully.")
            return redirect("accountability:promise_detail", pk=promise.pk)
    else:
        form = PromiseForm(instance=promise, user=request.user)

    return render(request, "accountability/promise_form.html", {"form": form, "title": "Edit Promise", "promise": promise})


# ==============================================================================
# Public Document Repository Views
# ==============================================================================

def document_list(request):
    """Searchable archive of meeting minutes, legislation, and financial reports."""
    queryset = PublicDocument.objects.select_related("uploaded_by")

    # Search & filters
    search_query = request.GET.get("q")
    doc_type_filter = request.GET.get("type")

    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )
    if doc_type_filter:
        queryset = queryset.filter(document_type=doc_type_filter)

    can_upload = request.user.is_authenticated and (
        request.user.role in [User.Role.REPRESENTATIVE, User.Role.ADMIN]
    )

    context = {
        "documents": queryset[:100],
        "doc_types": PublicDocument.DocType.choices,
        "search_query": search_query,
        "active_type": doc_type_filter,
        "can_upload": can_upload,
    }
    return render(request, "accountability/document_list.html", context)


@login_required
def document_upload(request):
    """Upload public documents (staff only)."""
    if request.user.role not in [User.Role.REPRESENTATIVE, User.Role.ADMIN]:
        raise PermissionDenied("Only Representatives and Admins can upload public documents.")

    if request.method == "POST":
        form = PublicDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, f"Document '{doc.title}' uploaded successfully.")
            return redirect("accountability:document_list")
    else:
        form = PublicDocumentForm()

    return render(request, "accountability/document_form.html", {"form": form})


# ==============================================================================
# Representative Profiles & Metrics Views
# ==============================================================================

def rep_list(request):
    """List of all student government representatives and admins with their metrics."""
    representatives = User.objects.filter(role__in=[User.Role.REPRESENTATIVE, User.Role.ADMIN]).select_related("department", "rep_profile")

    # Precalculate summary stats for list cards
    for rep in representatives:
        # Ensure profile exists dynamically if signal missed it
        RepresentativeProfile.objects.get_or_create(user=rep)
        rep.total_promises = rep.promises.count()
        rep.completed_promises = rep.promises.filter(status=Promise.Status.COMPLETED).count()
        rep.resolved_cases = Feedback.objects.filter(assigned_to=rep, status=Feedback.Status.RESOLVED).count()

    return render(request, "accountability/rep_list.html", {"representatives": representatives})


def rep_detail(request, pk):
    """Show representative profile details alongside goals and engagement metrics."""
    rep = get_object_or_404(User, pk=pk)
    if rep.role not in [User.Role.REPRESENTATIVE, User.Role.ADMIN]:
        raise PermissionDenied("This user is not a student government representative.")

    # Ensure profile exists
    profile, created = RepresentativeProfile.objects.get_or_create(user=rep)

    # 1. Promise compliance stats
    promises = rep.promises.all()
    total_promises = promises.count()
    completed_promises = promises.filter(status=Promise.Status.COMPLETED).count()
    promise_completion_rate = round((completed_promises / total_promises * 100), 1) if total_promises > 0 else 0

    # 2. Feedback metrics (assigned cases)
    assigned_cases = Feedback.objects.filter(assigned_to=rep)
    total_assigned = assigned_cases.count()
    resolved_cases = assigned_cases.filter(status=Feedback.Status.RESOLVED)
    resolved_count = resolved_cases.count()
    case_resolution_rate = round((resolved_count / total_assigned * 100), 1) if total_assigned > 0 else 0

    # 3. Average resolution time in hours
    durations = []
    for case in resolved_cases:
        if case.resolved_at:
            durations.append((case.resolved_at - case.created_at).total_seconds())
    avg_seconds = sum(durations) / len(durations) if durations else 0
    avg_resolution_hours = round(avg_seconds / 3600, 1)

    # 4. Department-wide feedback metrics (contextual metrics)
    dept_total = 0
    dept_resolution_rate = 0
    if rep.department:
        dept_cases = Feedback.objects.filter(department=rep.department)
        dept_total = dept_cases.count()
        dept_resolved = dept_cases.filter(status=Feedback.Status.RESOLVED).count()
        dept_resolution_rate = round((dept_resolved / dept_total * 100), 1) if dept_total > 0 else 0

    # 5. Comment communication activity
    comments_count = FeedbackUpdate.objects.filter(
        actor=rep,
        update_type=FeedbackUpdate.UpdateType.COMMENT
    ).count()

    can_edit = request.user.is_authenticated and (
        request.user == rep or request.user.role == User.Role.ADMIN
    )

    # Parse goals by line
    goals_list = parse_goals(profile.goals)

    context = {
        "rep": rep,
        "profile": profile,
        "promises": promises,
        "goals_list": goals_list,
        "can_edit": can_edit,
        "metrics": {
            "total_promises": total_promises,
            "completed_promises": completed_promises,
            "promise_rate": promise_completion_rate,
            "total_assigned": total_assigned,
            "resolved_count": resolved_count,
            "case_rate": case_resolution_rate,
            "avg_resolution_hours": avg_resolution_hours,
            "dept_total": dept_total,
            "dept_rate": dept_resolution_rate,
            "comments_count": comments_count,
        }
    }
    return render(request, "accountability/rep_detail.html", context)


@login_required
def rep_profile_edit(request, pk):
    """Allow representatives to edit their own profile bio/goals."""
    profile = get_object_or_404(RepresentativeProfile, user_id=pk)
    if not (request.user == profile.user or request.user.role == User.Role.ADMIN):
        raise PermissionDenied("You do not have permission to edit this profile.")

    if request.method == "POST":
        form = RepresentativeProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accountability:rep_detail", pk=profile.user.pk)
    else:
        form = RepresentativeProfileForm(instance=profile)

    return render(request, "accountability/rep_profile_form.html", {"form": form, "profile": profile})
