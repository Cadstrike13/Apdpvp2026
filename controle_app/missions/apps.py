from django.apps import AppConfig


class MissionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "missions"
    verbose_name = "Missions de contrôle"

    def ready(self):
        import missions.signals  # noqa: F401
