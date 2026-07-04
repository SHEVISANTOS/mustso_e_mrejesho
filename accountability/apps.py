from django.apps import AppConfig


class AccountabilityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accountability'

    def ready(self):
        import accountability.signals
