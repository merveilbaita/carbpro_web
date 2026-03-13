import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "Crée un superuser par défaut si aucun n'existe"

    def handle(self, *args, **kwargs):
        username = os.environ.get("DJANGO_ADMIN_USER",     "admin")
        password = os.environ.get("DJANGO_ADMIN_PASSWORD", "admin1234")
        email    = os.environ.get("DJANGO_ADMIN_EMAIL",    "admin@carbpro.com")

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"Utilisateur '{username}' existe déjà."))
        else:
            User.objects.create_superuser(username=username, password=password, email=email)
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' créé."))