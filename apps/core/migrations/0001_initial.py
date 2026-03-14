from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Parametre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cle', models.CharField(max_length=100, unique=True)),
                ('valeur', models.TextField(default='')),
            ],
            options={'verbose_name': 'Paramètre'},
        ),
        migrations.CreateModel(
            name='Engin',
            fields=[
                ('id_engin', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('type_engin', models.CharField(choices=[
                    ('camion_benne','Camion Benne'),('excavatrice','Excavatrice'),
                    ('chargeur','Chargeur'),('bulldozer','Bulldozer'),
                    ('niveleuse','Niveleuse'),('compacteur','Compacteur'),
                    ('vehicule','Véhicule'),('equipement_fixe','Équipement Fixe'),
                    ('autre','Autre')], max_length=30)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('actif', models.BooleanField(default=True)),
                ('mode_appro', models.CharField(choices=[
                    ('avec_index','Avec suivi d\'index'),
                    ('sans_index','Sans suivi d\'index')],
                    default='avec_index', max_length=20)),
            ],
            options={'ordering': ['id_engin'], 'verbose_name': 'Engin'},
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[
                    ('administrateur','Administrateur'),
                    ('operateur','Opérateur')],
                    default='operateur', max_length=20)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Profil utilisateur'},
        ),
        migrations.CreateModel(
            name='OperationStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('type', models.CharField(choices=[('entree','Entrée'),('sortie','Sortie')], max_length=10)),
                ('quantite', models.FloatField()),
                ('stock_apres', models.FloatField(default=0)),
                ('description', models.CharField(blank=True, max_length=300)),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
                ('operateur', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='operations_stock',
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', '-cree_le'], 'verbose_name': 'Opération Stock'},
        ),
        migrations.CreateModel(
            name='RavitaillementEngin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('index_precedent', models.FloatField(default=0)),
                ('index_actuel', models.FloatField(default=0)),
                ('difference_index', models.FloatField(default=0)),
                ('qte_donnee', models.FloatField()),
                ('taux_reel', models.FloatField(blank=True, null=True)),
                ('norme_ref', models.FloatField(blank=True, null=True)),
                ('statut', models.CharField(choices=[
                    ('normal','Normal'),('anomalie','Anomalie'),
                    ('non_verifie','Non vérifié'),('panne_index','Panne d\'index')],
                    default='non_verifie', max_length=20)),
                ('commentaire', models.CharField(blank=True, max_length=300)),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
                ('engin', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ravitaillements', to='core.engin')),
                ('operateur', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ravitaillements_engins',
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', '-cree_le'], 'verbose_name': 'Ravitaillement Engin'},
        ),
        migrations.CreateModel(
            name='ConsommationDiverse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('categorie', models.CharField(choices=[
                    ('Garage','Garage'),('Groupe électrogène','Groupe électrogène'),
                    ('Bidon','Bidon'),('Fuel Tank','Fuel Tank'),
                    ('Land Cruiser Direction','Land Cruiser Direction'),('Autre','Autre')],
                    max_length=100)),
                ('quantite', models.FloatField()),
                ('motif', models.CharField(blank=True, max_length=300)),
                ('stock_apres', models.FloatField(default=0)),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
                ('operateur', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='consommations_diverses',
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', '-cree_le'], 'verbose_name': 'Consommation Diverse'},
        ),
    
        migrations.CreateModel(
            name='PushSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endpoint', models.TextField(unique=True)),
                ('p256dh', models.TextField()),
                ('auth', models.TextField()),
                ('user_agent', models.CharField(blank=True, max_length=300)),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='push_subscriptions',
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Abonnement Push'},
        ),
    ]
