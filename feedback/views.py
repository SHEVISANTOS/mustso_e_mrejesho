from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView
from django.urls import reverse_lazy

from accounts.models import User
from .models import Feedback, FeedbackUpdate
from .forms import FeedbackSubmitForm, FeedbackUpdateForm, EscalationForm


class SubmitFeedbackView(LoginRequiredMixin, CreateView):
    model = Feedback
    form_class = FeedbackSubmitForm
    template_name = "feedback/submit.html"
    success_url = reverse_lazy("feedback:dashboard")

    def form_valid(self, form):
        form.instance.submitted_by = self.request.user
        response = super().form_valid(form)
        from notifications.services import notify_new_feedback
        notify_new_feedback(self.object)
        messages.success(
            self.request,
            f"Feedback submitted. Your tracking number is {self.object.tracking_number}."
        )
        return response


def _queryset_for_user(user):
    """Role-scoped feedback list, matching the escalation chain."""
    if user.role == User.Role.STUDENT:
        return Feedback.objects.filter(submitted_by=user)

    if user.role == User.Role.REPRESENTATIVE:
        return Feedback.objects.filter(
            department=user.department, escalation_level=Feedback.EscalationLevel.REPRESENTATIVE
        )

    if user.role == User.Role.ADMIN:
        return Feedback.objects.all()

    return Feedback.objects.none()


@login_required
def dashboard(request):
    queryset = _queryset_for_user(request.user)

    status_filter = request.GET.get("status")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    context = {
        "feedback_list": queryset.select_related("department", "submitted_by")[:100],
        "status_choices": Feedback.Status.choices,
        "active_status": status_filter,
        "counts": _counts_for(queryset),
    }
    return render(request, "feedback/dashboard.html", context)


def _counts_for(queryset):
    return {
        "total": queryset.count(),
        "submitted": queryset.filter(status=Feedback.Status.SUBMITTED).count(),
        "in_progress": queryset.filter(status=Feedback.Status.IN_PROGRESS).count(),
        "escalated": queryset.filter(status=Feedback.Status.ESCALATED).count(),
        "resolved": queryset.filter(status=Feedback.Status.RESOLVED).count(),
        "closed": queryset.filter(status=Feedback.Status.CLOSED).count(),
    }


@login_required
def dashboard_data(request):
    """Polled by the dashboard page every few seconds for real-time resolution tracking
    (objective 1) without a full page reload."""
    queryset = _queryset_for_user(request.user)
    status_filter = request.GET.get("status")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    items = [
        {
            "id": str(fb.id),
            "tracking_number": fb.tracking_number,
            "subject": fb.subject,
            "category": fb.get_category_display(),
            "department": fb.department.name,
            "status": fb.status,
            "status_display": fb.get_status_display(),
            "priority": fb.get_priority_display(),
            "created_at": fb.created_at.strftime("%d %b %Y"),
            "url": f"/feedback/{fb.id}/",
        }
        for fb in queryset.select_related("department")[:100]
    ]
    return JsonResponse({"counts": _counts_for(queryset), "items": items})


def _can_view(user, fb):
    if user.role == User.Role.STUDENT:
        return fb.submitted_by_id == user.id
    if user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.REPRESENTATIVE:
        return (
            user.department_id == fb.department_id
            and fb.escalation_level == Feedback.EscalationLevel.REPRESENTATIVE
        )
    return False


def _can_act(user, fb):
    """Can this user comment/escalate/resolve this item right now?"""
    if user.role == User.Role.STUDENT:
        return False
    return _can_view(user, fb)


@login_required
def feedback_detail(request, pk):
    fb = get_object_or_404(Feedback, pk=pk)
    if not _can_view(request.user, fb):
        raise PermissionDenied("You do not have access to this feedback item.")

    can_act = _can_act(request.user, fb)
    comment_form = FeedbackUpdateForm()
    escalation_form = EscalationForm()

    if request.method == "POST" and can_act:
        action = request.POST.get("action")

        if action == "comment":
            comment_form = FeedbackUpdateForm(request.POST)
            if comment_form.is_valid():
                update = comment_form.save(commit=False)
                update.feedback = fb
                update.actor = request.user
                update.update_type = FeedbackUpdate.UpdateType.COMMENT
                update.new_status = fb.status
                update.save()
                if fb.status == Feedback.Status.SUBMITTED:
                    fb.status = Feedback.Status.IN_PROGRESS
                    fb.assigned_to = request.user
                    fb.save()
                from notifications.services import notify_new_comment
                notify_new_comment(fb, request.user)
                messages.success(request, "Comment added.")
                return redirect("feedback:detail", pk=fb.pk)

        elif action == "escalate":
            escalation_form = EscalationForm(request.POST)
            if escalation_form.is_valid():
                if fb.escalate(request.user, escalation_form.cleaned_data.get("reason", "")):
                    messages.success(request, "Feedback escalated.")
                else:
                    messages.warning(request, "This item is already at the highest escalation level.")
                return redirect("feedback:detail", pk=fb.pk)

        elif action == "resolve":
            fb.mark_resolved(request.user, message=request.POST.get("resolution_message", ""))
            messages.success(request, "Feedback marked as resolved.")
            return redirect("feedback:detail", pk=fb.pk)

        elif action == "close":
            fb.status = Feedback.Status.CLOSED
            fb.save()
            FeedbackUpdate.objects.create(
                feedback=fb, actor=request.user,
                update_type=FeedbackUpdate.UpdateType.STATUS_CHANGE,
                message="Case closed.", new_status=fb.status,
            )
            from notifications.services import notify_closed
            notify_closed(fb)
            messages.success(request, "Feedback closed.")
            return redirect("feedback:detail", pk=fb.pk)

    context = {
        "fb": fb,
        "updates": fb.updates.select_related("actor"),
        "can_act": can_act,
        "comment_form": comment_form,
        "escalation_form": escalation_form,
    }
    return render(request, "feedback/detail.html", context)
