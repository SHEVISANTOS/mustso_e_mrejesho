import logging
from django.core.exceptions import PermissionDenied
from .models import RepresentativeProfile, Promise
from feedback.models import Feedback

logger = logging.getLogger(__name__)

def check_permission(user, obj, role_required):
    """Utility to check if a user has the required role or ownership.
    Raises PermissionDenied if check fails.
    """
    if not user.is_authenticated:
        raise PermissionDenied('Authentication required.')
    # Import User model dynamically to access Role enum
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if user.role == role_required or user.role == User.Role.ADMIN:
        return True
    if hasattr(obj, 'representative') and obj.representative == user:
        return True
    raise PermissionDenied('You do not have permission to perform this action.')

def parse_goals(goals_text):
    """Safely split goals text into a list, handling None values.
    Returns a list of stripped non‑empty lines.
    """
    if not goals_text:
        return []
    return [g.strip() for g in goals_text.split('\n') if g.strip()]

def ensure_representative_profiles(reps):
    """Bulk‑create missing RepresentativeProfile objects for a queryset of users.
    Returns the original queryset after ensuring profiles exist.
    """
    missing_user_ids = []
    existing_profiles = RepresentativeProfile.objects.filter(user__in=reps).values_list('user_id', flat=True)
    for rep in reps:
        if rep.id not in existing_profiles:
            missing_user_ids.append(rep.id)
    # Bulk create profiles for missing users
    RepresentativeProfile.objects.bulk_create([
        RepresentativeProfile(user_id=uid) for uid in missing_user_ids
    ])
    return reps

def calculate_resolution_metrics(resolved_cases):
    """Calculate average resolution time in hours for a queryset of resolved cases.
    Returns a float rounded to one decimal place.
    """
    durations = []
    for case in resolved_cases:
        if case.resolved_at:
            durations.append((case.resolved_at - case.created_at).total_seconds())
    if not durations:
        return 0
    avg_seconds = sum(durations) / len(durations)
    return round(avg_seconds / 3600, 1)
