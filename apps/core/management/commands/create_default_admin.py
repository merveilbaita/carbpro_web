"""
Commande : python manage.py create_default_admin
- Crée le superuser par défaut si aucun n'existe
- Crée les profils UserProfile manquants pour tous les utilisateurs
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Crée le superuser par défaut et les profils manquants"

    def handle(self, *args, **kwargs):
        from apps.core.models import UserProfile

        # ── 1. Créer les profils manquants ────────────────────
        created_profiles = 0
        for user in User.objects.all():
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": "administrateur" if (user.is_superuser or user.is_staff)
                            else "operateur"
                }
            )
            if created:
                created_profiles += 1

        if created_profiles:
            self.stdout.write(
                self.style.SUCCESS(f"{created_profiles} profil(s) créé(s).")
            )

        # ── 2. Créer le superuser par défaut ──────────────────
        username = os.environ.get("DJANGO_ADMIN_USER",     "admin")
        password = os.environ.get("DJANGO_ADMIN_PASSWORD", "admin1234")
        email    = os.environ.get("DJANGO_ADMIN_EMAIL",    "admin@carbpro.com")

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f"Utilisateur '{username}' existe déjà — ignoré.")
            )
            user = User.objects.get(username=username)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if profile.role != "administrateur":
                profile.role = "administrateur"
                profile.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Profil '{username}' mis à jour → administrateur.")
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
