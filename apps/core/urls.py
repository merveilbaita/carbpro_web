from django.urls import path
from . import views

urlpatterns = [
    path("",                      views.dashboard,             name="dashboard"),
    path("ravitaillement/",       views.ravitaillement_stock,  name="ravitaillement_stock"),
    path("appro-engin/",          views.appro_engin,           name="appro_engin"),
    path("consommation-diverse/", views.consommation_diverse,  name="consommation_diverse"),
    path("historique/",           views.historique,            name="historique"),
    # Historique — édition et suppression
    path("historique/stock/<int:pk>/edit/",    views.edit_operation_stock,      name="edit_operation_stock"),
    path("historique/stock/<int:pk>/delete/",  views.delete_operation_stock,    name="delete_operation_stock"),
    path("historique/rav/<int:pk>/edit/",      views.edit_ravitaillement,       name="edit_ravitaillement"),
    path("historique/rav/<int:pk>/delete/",    views.delete_ravitaillement,     name="delete_ravitaillement"),
    path("historique/diverse/<int:pk>/edit/",  views.edit_consommation_diverse, name="edit_consommation_diverse"),
    path("historique/diverse/<int:pk>/delete/",views.delete_consommation_diverse,name="delete_consommation_diverse"),
    path("export-excel/",         views.export_excel,          name="export_excel"),
    path("import-excel/",         views.import_excel,          name="import_excel"),
    # PWA
    path("sw.js",                 views.service_worker,        name="service_worker"),
    path("offline/",              views.offline,               name="offline"),
    # Gestion utilisateurs
    path("utilisateurs/",                          views.liste_utilisateurs,   name="liste_utilisateurs"),
    path("utilisateurs/creer/",                    views.creer_utilisateur,    name="creer_utilisateur"),
    path("utilisateurs/<int:user_id>/modifier/",   views.modifier_utilisateur, name="modifier_utilisateur"),
    path("utilisateurs/<int:user_id>/toggle/",     views.toggle_utilisateur,   name="toggle_utilisateur"),
    path("utilisateurs/<int:user_id>/supprimer/",  views.supprimer_utilisateur,name="supprimer_utilisateur"),
    # Gestion engins
    path("engins/",                          views.gestion_engins,   name="gestion_engins"),
    path("engins/creer/",                    views.creer_engin,      name="creer_engin"),
    path("engins/<str:id_engin>/modifier/",  views.modifier_engin,   name="modifier_engin"),
    path("engins/<str:id_engin>/toggle/",    views.toggle_engin,     name="toggle_engin"),
    path("engins/<str:id_engin>/supprimer/", views.supprimer_engin,  name="supprimer_engin"),
    # Rapports PDF
    path("rapports/",                  views.rapports,             name="rapports"),
    path("rapports/entrees.pdf",       views.pdf_rapport_entrees,  name="pdf_rapport_entrees"),
    path("rapports/attestation.pdf",   views.pdf_attestation,      name="pdf_attestation"),
    path("rapports/mensuel.pdf",       views.pdf_rapport_mensuel,  name="pdf_rapport_mensuel"),
    # Paramètres
    path("parametres/",          views.parametres,          name="parametres"),
    path("api/parametres/",      views.api_parametres,      name="api_parametres"),
    path("normes/",              views.normes_consommation,  name="normes_consommation"),
    # Web Push Notifications
    path("push/vapid-public-key/", views.push_vapid_public_key, name="push_vapid_public_key"),
    path("push/subscribe/",        views.push_subscribe,        name="push_subscribe"),
    path("push/unsubscribe/",      views.push_unsubscribe,      name="push_unsubscribe"),
]
