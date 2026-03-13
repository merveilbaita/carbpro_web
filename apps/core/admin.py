from django.contrib import admin
from .models import Engin, OperationStock, RavitaillementEngin, ConsommationDiverse, Parametre

@admin.register(Engin)
class EnginAdmin(admin.ModelAdmin):
    list_display  = ["id_engin", "type_engin", "mode_appro", "actif"]
    list_filter   = ["type_engin", "mode_appro", "actif"]
    search_fields = ["id_engin", "description"]

@admin.register(OperationStock)
class OperationStockAdmin(admin.ModelAdmin):
    list_display = ["date", "type", "quantite", "stock_apres", "operateur"]
    list_filter  = ["type", "date"]

@admin.register(RavitaillementEngin)
class RavEnginAdmin(admin.ModelAdmin):
    list_display = ["date", "engin", "qte_donnee", "statut", "operateur"]
    list_filter  = ["statut", "engin"]

@admin.register(ConsommationDiverse)
class ConsDiverseAdmin(admin.ModelAdmin):
    list_display = ["date", "categorie", "quantite", "operateur"]
    list_filter  = ["categorie"]

@admin.register(Parametre)
class ParametreAdmin(admin.ModelAdmin):
    list_display = ["cle", "valeur"]
