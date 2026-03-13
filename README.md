# CarbPro Web — Guide de déploiement

Interface web mobile-friendly pour la saisie terrain du carburant.
Déployée sur **Render.com** avec **PostgreSQL**.

---

## Structure du projet

```
carbpro_web/
├── config/          # Settings, URLs, WSGI
├── apps/core/       # Modèles, vues, formulaires
├── templates/       # HTML (Bootstrap 5, mobile-first)
├── static/          # CSS/JS statiques
├── manage.py
├── requirements.txt
├── Procfile         # Pour Render/Gunicorn
├── render.yaml      # Configuration Render automatique
└── .env.example     # Variables d'environnement
```

---

## 1. Déploiement sur Render.com (première fois)

### Étape 1 — Préparer GitHub
```bash
git init
git add .
git commit -m "Initial commit CarbPro Web"
# Créer un repo sur GitHub puis :
git remote add origin https://github.com/TON_USER/carbpro-web.git
git push -u origin main
```

### Étape 2 — Créer le service sur Render
1. Va sur **render.com** → Se connecter avec GitHub
2. Clic **"New +"** → **"Web Service"**
3. Connecte ton repo GitHub `carbpro-web`
4. Render détecte automatiquement `render.yaml`

### Étape 3 — Variables d'environnement sur Render
Dans l'onglet **Environment** de ton service :

| Variable | Valeur |
|---|---|
| `SECRET_KEY` | Générer une clé ici : https://djecrety.ir |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `carbpro-web.onrender.com` (ton URL Render) |
| `DATABASE_URL` | Copier depuis le service PostgreSQL Render |

### Étape 4 — Créer la base PostgreSQL sur Render
1. **New +** → **PostgreSQL**
2. Nom : `carbpro-db`, Plan : **Free**
3. Copier l'**Internal Database URL** dans la variable `DATABASE_URL`

### Étape 5 — Premier déploiement
Render exécute automatiquement :
```
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
```

### Étape 6 — Créer le superadmin
Dans le shell Render (onglet **Shell**) :
```bash
python manage.py createsuperuser
```

---

## 2. Développement local

### Installation
```bash
# Copier le fichier d'environnement
cp .env.example .env
# Éditer .env avec tes valeurs locales

# Installer les dépendances
pip install -r requirements.txt

# Migrations
python manage.py migrate

# Créer un admin local
python manage.py createsuperuser

# Lancer le serveur
python manage.py runserver
```

Accès : http://127.0.0.1:8000

Pour le dev local, `DATABASE_URL` dans `.env` peut rester en SQLite :
```
DATABASE_URL=sqlite:///db.sqlite3
```

---

## 3. Ajouter les engins

Via l'interface **admin Django** : `/admin/`

Ou via le shell :
```python
python manage.py shell

from apps.core.models import Engin
Engin.objects.create(
    id_engin="CAT01",
    type_engin="excavatrice",
    description="Excavatrice CAT 320",
    mode_appro="avec_index"
)
```

---

## 4. Synchronisation avec l'appli Desktop

1. Dans CarbPro Web → **Historique** → bouton **Export Excel**
2. Dans GestionCarburantPro Desktop → **Import Excel**

L'export génère 3 feuilles compatibles avec l'import desktop :
- `Entrées Stock`
- `Appro Engins`
- `Consommations Diverses`

---

## 5. Mises à jour

```bash
git add .
git commit -m "Description des changements"
git push origin main
```
Render redéploie automatiquement.

---

## Compte par défaut après createsuperuser
- URL admin : `/admin/`
- URL app : `/`
- Login : `/login/`
