from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import Notification


@login_required
def notification_list(request):
    # 1. Mark all unread notifications as read FIRST (on the full, unsliced queryset)
    request.user.notifications.filter(is_read=False).update(is_read=True)
    
    # 2. THEN fetch the latest 50 for display
    notifications = request.user.notifications.all()[:50]
    
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.feedback_id:
        return redirect("feedback:detail", pk=notif.feedback_id)
    return redirect("notifications:list")


@login_required
def unread_count(request):
    """Polled by the navbar bell to update the badge without a full page reload."""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"unread_count": count})