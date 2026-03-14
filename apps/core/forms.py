from django import forms
from django.utils import timezone
from .models import (
    OperationStock, RavitaillementEngin, ConsommationDiverse,
    Engin, CATEGORIES_DIVERSES
)


class RavitaillementStockForm(forms.ModelForm):
    """Formulaire entrée de carburant (ravitaillement stock)."""

    class Meta:
        model  = OperationStock
        fields = ["date", "quantite", "description"]
        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date", "class": "form-control form-control-lg"},
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "placeholder": "Ex : 1500",
                    "step": "0.01", "min": "0.01",
                }
            ),
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Fournisseur, numéro BL… (optionnel)",
                }
            ),
        }
        labels = {
            "date":        "Date *",
            "quantite":    "Quantité (L) *",
            "description": "Description",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.localdate()


class ApproEnginForm(forms.ModelForm):
    """Formulaire ravitaillement engin — adaptatif selon mode_appro."""

    premier_plein = forms.BooleanField(
        required=False,
        label="Premier plein (initialisation index)",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )
    panne_index = forms.BooleanField(
        required=False,
        label="Compteur en panne (panne d'index)",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    class Meta:
        model  = RavitaillementEngin
        fields = ["date", "engin", "index_precedent", "index_actuel",
                  "qte_donnee", "commentaire"]
        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date", "class": "form-control form-control-lg"},
            ),
            "engin": forms.Select(
                attrs={"class": "form-select form-select-lg", "id": "id_engin"}
            ),
            "index_precedent": forms.NumberInput(
                attrs={
                    "class": "form-control", "step": "0.1", "min": "0",
                    "placeholder": "Index précédent",
                }
            ),
            "index_actuel": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "step": "0.1", "min": "0",
                    "placeholder": "Index actuel (km ou h)",
                }
            ),
            "qte_donnee": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "step": "0.01", "min": "0.01",
                    "placeholder": "Quantité (L)",
                }
            ),
            "commentaire": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Commentaire (obligatoire si anomalie ou panne)",
                }
            ),
        }
        labels = {
            "date":             "Date *",
            "engin":            "Engin *",
            "index_precedent":  "Index précédent",
            "index_actuel":     "Index actuel",
            "qte_donnee":       "Quantité servie (L) *",
            "commentaire":      "Commentaire / Motif",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.localdate()
        self.fields["engin"].queryset = Engin.objects.filter(actif=True).order_by("id_engin")
        self.fields["index_precedent"].required = False
        self.fields["index_actuel"].required    = False
        self.fields["commentaire"].required     = False

    def clean(self):
        cleaned = super().clean()
        engin        = cleaned.get("engin")
        panne        = cleaned.get("panne_index")
        premier      = cleaned.get("premier_plein")
        index_act    = cleaned.get("index_actuel")
        index_prec   = cleaned.get("index_precedent")
        commentaire  = cleaned.get("commentaire", "")

        if not engin:
            return cleaned

        mode = engin.mode_appro

        # Mode avec_index : index obligatoire sauf panne ou premier plein
        if mode == "avec_index" and not panne and not premier:
            if index_act is None:
                self.add_error("index_actuel", "Index actuel obligatoire.")
            if index_prec is None:
                self.add_error("index_precedent", "Index précédent obligatoire.")
            if index_act and index_prec and index_act < index_prec:
                self.add_error("index_actuel",
                               "L'index actuel doit être ≥ à l'index précédent.")

        # Panne d'index : commentaire obligatoire
        if panne and not commentaire:
            self.add_error("commentaire",
                           "Le commentaire est obligatoire en cas de panne d'index.")

        return cleaned




# ── Formulaires Gestion Utilisateurs ─────────────────────────

class CreerUtilisateurForm(forms.Form):
    """Formulaire création d'un nouvel utilisateur."""
    username   = forms.CharField(
        max_length=50, label="Identifiant *",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Ex : operateur1",
            "autocomplete": "off",
        })
    )
    nom_complet = forms.CharField(
        max_length=100, label="Nom complet *",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Ex : Jean Mukendi",
        })
    )
    email = forms.EmailField(
        required=False, label="Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "optionnel",
        })
    )
    role = forms.ChoiceField(
        choices=[("operateur", "Opérateur"), ("administrateur", "Administrateur")],
        label="Rôle *",
        widget=forms.Select(attrs={"class": "form-select form-select-lg"})
    )
    password1 = forms.CharField(
        label="Mot de passe *", min_length=4,
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Min. 4 caractères",
            "autocomplete": "new-password",
        })
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe *",
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Répéter le mot de passe",
            "autocomplete": "new-password",
        })
    )

    def clean_username(self):
        from django.contrib.auth.models import User
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Cet identifiant est déjà utilisé.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Les mots de passe ne correspondent pas.")
        return cleaned


class ModifierUtilisateurForm(forms.Form):
    """Formulaire modification d'un utilisateur existant."""
    nom_complet = forms.CharField(
        max_length=100, label="Nom complet *",
        widget=forms.TextInput(attrs={"class": "form-control form-control-lg"})
    )
    email = forms.EmailField(
        required=False, label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    role = forms.ChoiceField(
        choices=[("operateur", "Opérateur"), ("administrateur", "Administrateur")],
        label="Rôle *",
        widget=forms.Select(attrs={"class": "form-select form-select-lg"})
    )
    password_nouveau = forms.CharField(
        required=False, label="Nouveau mot de passe",
        min_length=4,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Laisser vide pour ne pas changer",
            "autocomplete": "new-password",
        })
    )
    password_confirm = forms.CharField(
        required=False, label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        })
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password_nouveau")
        p2 = cleaned.get("password_confirm")
        if p1 and p1 != p2:
            self.add_error("password_confirm", "Les mots de passe ne correspondent pas.")
        return cleaned

    """Formulaire consommation diverse (garage, groupe élec…)."""

    class Meta:
        model  = ConsommationDiverse
        fields = ["date", "categorie", "quantite", "motif"]
        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date", "class": "form-control form-control-lg"},
            ),
            "categorie": forms.Select(
                attrs={"class": "form-select form-select-lg"}
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "step": "0.01", "min": "0.01",
                    "placeholder": "Ex : 50",
                }
            ),
            "motif": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Détail / motif (optionnel)",
                }
            ),
        }
        labels = {
            "date":      "Date *",
            "categorie": "Catégorie *",
            "quantite":  "Quantité (L) *",
            "motif":     "Motif / Détail",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.localdate()
        self.fields["motif"].required = False


class ConsommationDiverseForm(forms.ModelForm):
    """Formulaire consommation diverse (garage, groupe élec…)."""

    class Meta:
        model  = ConsommationDiverse
        fields = ["date", "categorie", "quantite", "motif"]
        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date", "class": "form-control form-control-lg"},
            ),
            "categorie": forms.Select(
                attrs={"class": "form-select form-select-lg"}
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "step": "0.01", "min": "0.01",
                    "placeholder": "Ex : 50",
                }
            ),
            "motif": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Détail / motif (optionnel)",
                }
            ),
        }
        labels = {
            "date":      "Date *",
            "categorie": "Catégorie *",
            "quantite":  "Quantité (L) *",
            "motif":     "Motif / Détail",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.localdate()
        self.fields["motif"].required = False
