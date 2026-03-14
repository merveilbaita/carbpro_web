import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Crée le superuser par défaut"

    def handle(self, *args, **kwargs):
        username = os.environ.get("DJANGO_ADMIN_USER",     "admin")
        password = os.environ.get("DJANGO_ADMIN_PASSWORD", "admin1234")
        email    = os.environ.get("DJANGO_ADMIN_EMAIL",    "admin@carbpro.com")

        # ── Créer la table UserProfile manuellement si absente ─
        tables = connection.introspection.table_names()
        if "core_userprofile" not in tables:
            self.stdout.write("Création manuelle de core_userprofile...")
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS core_userprofile (
                        id      SERIAL PRIMARY KEY,
                        role    VARCHAR(20) NOT NULL DEFAULT 'operateur',
                        user_id INTEGER NOT NULL UNIQUE
                                REFERENCES auth_user(id)
                                ON DELETE CASCADE
                                DEFERRABLE INITIALLY DEFERRED
                    )
                """)
            self.stdout.write(self.style.SUCCESS("Table core_userprofile créée."))

            # Marquer la migration comme appliquée
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO django_migrations (app, name, applied)
                    VALUES ('core', '0001_initial', NOW())
                    ON CONFLICT DO NOTHING
                """)

        # ── Importer UserProfile maintenant que la table existe ─
        from apps.core.models import UserProfile

        # ── Créer les profils manquants ────────────────────────
        for user in User.objects.all():
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": "administrateur"
                    if (user.is_superuser or user.is_staff)
                    else "operateur"
                }
            )

        # ── Créer ou corriger le superuser ─────────────────────
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            self.stdout.write(self.style.WARNING(
                f"Utilisateur '{username}' existe déjà."))
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if profile.role != "administrateur":
                profile.role = "administrateur"
                profile.save()
        else:
            user = User.objects.create_superuser(
                username=username, password=password, email=email)
            UserProfile.objects.create(user=user, role="administrateur")
            self.stdout.write(self.style.SUCCESS(
                f"Superuser '{username}' créé avec succès."))