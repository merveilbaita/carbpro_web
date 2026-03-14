"""
Commande : python manage.py create_default_admin
Crée un superuser par défaut si aucun utilisateur n'existe.
Les identifiants sont lus depuis les variables d'environnement :
  DJANGO_ADMIN_USER     (défaut : admin)
  DJANGO_ADMIN_PASSWORD (défaut : admin1234)
  DJANGO_ADMIN_EMAIL    (défaut : admin@carbpro.com)
"""
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
            self.stdout.write(
                self.style.WARNING(f"Utilisateur '{username}' existe déjà — ignoré.")
            )
        else:
            User.objects.create_superuser(
                username=username,
                password=password,
                email=email
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Superuser '{username}' créé avec succès."
                )
            )
