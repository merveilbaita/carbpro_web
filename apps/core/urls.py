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
]
