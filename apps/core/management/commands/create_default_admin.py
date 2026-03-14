"""
Commande : python manage.py create_default_admin
- Crée le superuser par défaut si aucun n'existe
- Crée les profils UserProfile manquants (si la table existe)
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection


def table_exists(table_name):
    """Vérifie si une table existe dans la base."""
    return table_name in connection.introspection.table_names()


class Command(BaseCommand):
    help = "Crée le superuser par défaut et les profils manquants"

    def handle(self, *args, **kwargs):

        # ── 1. Créer la table UserProfile si elle n'existe pas ─
        if not table_exists("core_userprofile"):
            self.stdout.write(
                self.style.WARNING(
                    "Table core_userprofile absente — "
                    "exécution de migrate --run-syncdb..."
                )
            )
            from django.core.management import call_command
            call_command("migrate", "--run-syncdb", verbosity=0)

        # ── 2. Importer UserProfile après création table ───────
        from apps.core.models import UserProfile

        # ── 3. Créer les profils manquants ─────────────────────
        created_profiles = 0
        for user in User.objects.all():
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": "administrateur"
                    if (user.is_superuser or user.is_staff)
                    else "operateur"
                }
            )
            if created:
                created_profiles += 1

        if created_profiles:
            self.stdout.write(
                self.style.SUCCESS(f"{created_profiles} profil(s) créé(s).")
            )

        # ── 4. Créer le superuser par défaut ───────────────────
        username = os.environ.get("DJANGO_ADMIN_USER",     "admin")
        password = os.environ.get("DJANGO_ADMIN_PASSWORD", "admin1234")
        email    = os.environ.get("DJANGO_ADMIN_EMAIL",    "admin@carbpro.com")

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f"Utilisateur '{username}' existe déjà.")
            )
            # S'assurer que son profil est administrateur
            user = User.objects.get(username=username)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if profile.role != "administrateur":
                profile.role = "administrateur"
                profile.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Profil '{username}' mis à jour → administrateur."
                    )
                )
        else:
            user = User.objects.create_superuser(
                username=username,
                password=password,
                email=email,
            )
            UserProfile.objects.create(user=user, role="administrateur")
            self.stdout.write(
                self.style.SUCCESS(f"Superuser '{username}' créé avec succès.")
            )
