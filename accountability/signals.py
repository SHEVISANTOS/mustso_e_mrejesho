from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import RepresentativeProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_representative_profile(sender, instance, created, **kwargs):
    """Automatically create a RepresentativeProfile for users with Representative or Admin roles."""
    if instance.role in (User.Role.REPRESENTATIVE, User.Role.ADMIN):
        RepresentativeProfile.objects.get_or_create(user=instance)
