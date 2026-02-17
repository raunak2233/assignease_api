from django.apps import AppConfig


class AssigneaseappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'AssignEaseApp'

class AssigneaseappConfig(AppConfig):
    name = 'AssignEaseApp'

    def ready(self):
        import AssignEaseApp.signals
