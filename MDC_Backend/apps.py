from django.apps import AppConfig


class MdcBackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'MDC_Backend'

    def ready(self):
        try:
            from .views import ensure_notification_scheduler
            ensure_notification_scheduler()
        except Exception as e:
            print(f"Error starting notification scheduler in AppConfig: {e}")

