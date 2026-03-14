from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


ROLES = [
    ("administrateur", "Administrateur"),
    ("operateur",      "Opérateur"),
]


class UserProfile(models.Model):
    """Profil étendu — rôle CarbPro pour chaque utilisateur Django."""
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                 related_name="profile")
    role = models.CharField(max_length=20, choices=ROLES, default="operateur")

    class Meta:
        verbose_name = "Profil utilisateur"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == "administrateur"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """Crée automatiquement un profil à chaque nouvel utilisateur."""
    if created:
        role = "administrateur" if instance.is_superuser else "operateur"
        UserProfile.objects.get_or_create(user=instance, defaults={"role": role})



TYPES_ENGINS = [
    ("camion_benne",    "Camion Benne"),
    ("excavatrice",     "Excavatrice"),
    ("chargeur",        "Chargeur"),
    ("bulldozer",       "Bulldozer"),
    ("niveleuse",       "Niveleuse"),
    ("compacteur",      "Compacteur"),
    ("vehicule",        "Véhicule"),
    ("equipement_fixe", "Équipement Fixe"),
    ("autre",           "Autre"),
]

MODES_APPRO = [
    ("avec_index",  "Avec suivi d'index"),
    ("sans_index",  "Sans suivi d'index"),
]

STATUTS_RAV = [
    ("normal",      "Normal"),
    ("anomalie",    "Anomalie"),
    ("non_verifie", "Non vérifié"),
    ("panne_index", "Panne d'index"),
]

CATEGORIES_DIVERSES = [
    ("Garage",                  "Garage"),
    ("Groupe électrogène",      "Groupe électrogène"),
    ("Bidon",                   "Bidon"),
    ("Fuel Tank",               "Fuel Tank"),
    ("Land Cruiser Direction",  "Land Cruiser Direction"),
    ("Autre",                   "Autre"),
]


# ── Paramètre ─────────────────────────────────────────────────

class Parametre(models.Model):
    cle   = models.CharField(max_length=100, unique=True)
    valeur = models.TextField(default="")

    class Meta:
        verbose_name = "Paramètre"

    def __str__(self):
        return f"{self.cle} = {self.valeur}"

    @classmethod
    def get(cls, cle, defaut=""):
        try:
            return cls.objects.get(cle=cle).valeur
        except cls.DoesNotExist:
            return defaut


# ── Engin ─────────────────────────────────────────────────────

class Engin(models.Model):
    id_engin    = models.CharField(max_length=20, primary_key=True)
    type_engin  = models.CharField(max_length=30, choices=TYPES_ENGINS)
    description = models.CharField(max_length=200, blank=True)
    actif       = models.BooleanField(default=True)
    mode_appro  = models.CharField(max_length=20, choices=MODES_APPRO,
                                    default="avec_index")

    class Meta:
        ordering = ["id_engin"]
        verbose_name = "Engin"

    def __str__(self):
        return f"{self.id_engin} — {self.get_type_engin_display()}"


# ── Stock (entrées / sorties) ──────────────────────────────────

class OperationStock(models.Model):
    TYPES = [("entree", "Entrée"), ("sortie", "Sortie")]

    date        = models.DateField()
    type        = models.CharField(max_length=10, choices=TYPES)
    quantite    = models.FloatField()
    stock_apres = models.FloatField(default=0)
    description = models.CharField(max_length=300, blank=True)
    operateur   = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="operations_stock"
    )
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-cree_le"]
        verbose_name = "Opération Stock"

    def __str__(self):
        return f"{self.date} | {self.type} | {self.quantite} L"


# ── Ravitaillement Engin ───────────────────────────────────────

class RavitaillementEngin(models.Model):
    date             = models.DateField()
    engin            = models.ForeignKey(Engin, on_delete=models.CASCADE,
                                          related_name="ravitaillements")
    index_precedent  = models.FloatField(default=0)
    index_actuel     = models.FloatField(default=0)
    difference_index = models.FloatField(default=0)
    qte_donnee       = models.FloatField()
    taux_reel        = models.FloatField(null=True, blank=True)
    norme_ref        = models.FloatField(null=True, blank=True)
    statut           = models.CharField(max_length=20, choices=STATUTS_RAV,
                                         default="non_verifie")
    commentaire      = models.CharField(max_length=300, blank=True)
    operateur        = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ravitaillements_engins"
    )
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-cree_le"]
        verbose_name = "Ravitaillement Engin"

    def __str__(self):
        return f"{self.date} | {self.engin_id} | {self.qte_donnee} L"


# ── Consommation Diverse ──────────────────────────────────────

class ConsommationDiverse(models.Model):
    date        = models.DateField()
    categorie   = models.CharField(max_length=100, choices=CATEGORIES_DIVERSES)
    quantite    = models.FloatField()
    motif       = models.CharField(max_length=300, blank=True)
    operateur   = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consommations_diverses"
    )
    stock_apres = models.FloatField(default=0)
    cree_le     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-cree_le"]
        verbose_name = "Consommation Diverse"

    def __str__(self):
        return f"{self.date} | {self.categorie} | {self.quantite} L"
