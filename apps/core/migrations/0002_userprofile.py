"""
Migration manuelle pour créer les profils UserProfile
pour les utilisateurs existants qui n'en ont pas.
"""
from django.db import migrations


def create_profiles(apps, schema_editor):
    User        = apps.get_model("auth", "User")
    UserProfile = apps.get_model("core", "UserProfile")
    for user in User.objects.all():
        if not UserProfile.objects.filter(user=user).exists():
            role = "administrateur" if user.is_superuser or user.is_staff else "operateur"
            UserProfile.objects.create(user=user, role=role)


def reverse_profiles(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_profiles, reverse_profiles),
    ]
