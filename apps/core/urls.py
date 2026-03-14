from django.urls import path
from . import views

urlpatterns = [
    path("",                      views.dashboard,             name="dashboard"),
    path("ravitaillement/",       views.ravitaillement_stock,  name="ravitaillement_stock"),
    path("appro-engin/",          views.appro_engin,           name="appro_engin"),
    path("consommation-diverse/", views.consommation_diverse,  name="consommation_diverse"),
    path("historique/",           views.historique,            name="historique"),
    path("export-excel/",         views.export_excel,          name="export_excel"),
    path("import-excel/",         views.import_excel,          name="import_excel"),
    path("engins/",               views.liste_engins,          name="liste_engins"),
    # PWA
    path("sw.js",                 views.service_worker,        name="service_worker"),
    path("offline/",              views.offline,               name="offline"),
    # Gestion utilisateurs
    path("utilisateurs/",                          views.liste_utilisateurs,   name="liste_utilisateurs"),
    path("utilisateurs/creer/",                    views.creer_utilisateur,    name="creer_utilisateur"),
    path("utilisateurs/<int:user_id>/modifier/",   views.modifier_utilisateur, name="modifier_utilisateur"),
    path("utilisateurs/<int:user_id>/toggle/",     views.toggle_utilisateur,   name="toggle_utilisateur"),
    path("utilisateurs/<int:user_id>/supprimer/",  views.supprimer_utilisateur,name="supprimer_utilisateur"),
    # Web Push Notifications
    path("push/vapid-public-key/", views.push_vapid_public_key, name="push_vapid_public_key"),
    path("push/subscribe/",        views.push_subscribe,        name="push_subscribe"),
    path("push/unsubscribe/",      views.push_unsubscribe,      name="push_unsubscribe"),
]
