from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
import json, openpyxl, os
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import date


# ── PWA : Service Worker servi depuis la racine ───────────────
@require_GET
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request):
    sw_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        '..', 'static', 'sw.js'
    )
    # Chercher dans staticfiles (production) ou static (dev)
    for candidate in [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), 'staticfiles', 'sw.js'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), 'static', 'sw.js'),
    ]:
        if os.path.exists(candidate):
            with open(candidate, 'r') as f:
                return HttpResponse(f.read(),
                    content_type='application/javascript')
    return HttpResponse('// SW not found', content_type='application/javascript')


# ── PWA : Page offline ────────────────────────────────────────
def offline(request):
    return render(request, 'core/offline.html')

from .models import (
    OperationStock, RavitaillementEngin,
    ConsommationDiverse, Engin, Parametre
)
from .forms import (
    RavitaillementStockForm, ApproEnginForm, ConsommationDiverseForm
)


# ── Helpers ───────────────────────────────────────────────────

def get_stock_actuel():
    """Calcule le stock actuel depuis toutes les opérations."""
    entrees = OperationStock.objects.filter(type="entree").aggregate(
        t=Sum("quantite"))["t"] or 0
    sorties_stock = OperationStock.objects.filter(type="sortie").aggregate(
        t=Sum("quantite"))["t"] or 0
    sorties_engin = RavitaillementEngin.objects.aggregate(
        t=Sum("qte_donnee"))["t"] or 0
    sorties_div = ConsommationDiverse.objects.aggregate(
        t=Sum("quantite"))["t"] or 0
    return entrees - sorties_stock - sorties_engin - sorties_div


def recalc_stock_apres(op_stock):
    """Recalcule stock_apres pour une OperationStock."""
    ops = OperationStock.objects.order_by("date", "cree_le")
    stock = 0
    for op in ops:
        if op.type == "entree":
            stock += op.quantite
        else:
            stock -= op.quantite
        op.stock_apres = stock
        op.save(update_fields=["stock_apres"])


# ── Dashboard ─────────────────────────────────────────────────

@login_required
def dashboard(request):
    stock   = get_stock_actuel()
    now     = timezone.localdate()
    mois    = now.month
    annee   = now.year

    entrees_mois = OperationStock.objects.filter(
        type="entree", date__month=mois, date__year=annee
    ).aggregate(t=Sum("quantite"))["t"] or 0

    sorties_engin_mois = RavitaillementEngin.objects.filter(
        date__month=mois, date__year=annee
    ).aggregate(t=Sum("qte_donnee"))["t"] or 0

    sorties_div_mois = ConsommationDiverse.objects.filter(
        date__month=mois, date__year=annee
    ).aggregate(t=Sum("quantite"))["t"] or 0

    sorties_mois = sorties_engin_mois + sorties_div_mois

    nb_engins    = Engin.objects.filter(actif=True).count()
    dernieres_ops = OperationStock.objects.select_related("operateur")[:5]
    derniers_ravs = RavitaillementEngin.objects.select_related(
        "engin", "operateur")[:5]

    ctx = {
        "stock":          stock,
        "stock_negatif":  stock < 0,
        "entrees_mois":   entrees_mois,
        "sorties_mois":   sorties_mois,
        "nb_engins":      nb_engins,
        "dernieres_ops":  dernieres_ops,
        "derniers_ravs":  derniers_ravs,
        "mois_label":     now.strftime("%B %Y"),
    }
    return render(request, "core/dashboard.html", ctx)


# ── Ravitaillement Stock ───────────────────────────────────────

@login_required
def ravitaillement_stock(request):
    if request.method == "POST":
        form = RavitaillementStockForm(request.POST)
        if form.is_valid():
            op = form.save(commit=False)
            op.type      = "entree"
            op.operateur = request.user
            # Calcul stock_apres
            stock_avant = get_stock_actuel()
            op.stock_apres = stock_avant + op.quantite
            op.save()
            messages.success(request,
                f"✅ Entrée de {op.quantite:,.0f} L enregistrée. "
                f"Stock actuel : {op.stock_apres:,.0f} L")
            return redirect("dashboard")
    else:
        form = RavitaillementStockForm()

    return render(request, "core/ravitaillement_stock.html", {
        "form":  form,
        "stock": get_stock_actuel(),
    })


# ── Approvisionnement Engin ────────────────────────────────────

@login_required
def appro_engin(request):
    if request.method == "POST":
        form = ApproEnginForm(request.POST)
        if form.is_valid():
            rav          = form.save(commit=False)
            rav.operateur = request.user
            engin         = rav.engin
            panne         = form.cleaned_data.get("panne_index")
            premier       = form.cleaned_data.get("premier_plein")

            # Statut
            if panne:
                rav.statut = "panne_index"
            elif engin.mode_appro == "sans_index" or premier:
                rav.statut = "non_verifie"
            else:
                diff = (rav.index_actuel or 0) - (rav.index_precedent or 0)
                rav.difference_index = diff
                # Calcul taux réel selon type
                NORMES = {
                    "camion_benne": ("km", 2.0, 1.9),
                    "excavatrice":  ("h",  25.0, None),
                    "chargeur":     ("h",  20.0, None),
                    "bulldozer":    ("h",  27.0, None),
                    "niveleuse":    ("h",  14.0, None),
                    "compacteur":   ("h",  12.0, None),
                }
                info = NORMES.get(engin.type_engin)
                if info and diff > 0:
                    unite, norme, seuil_min = info
                    if unite == "km":
                        taux = diff / rav.qte_donnee if rav.qte_donnee else 0
                        rav.taux_reel = round(taux, 3)
                        rav.norme_ref = norme
                        rav.statut    = "anomalie" if seuil_min and taux < seuil_min else "normal"
                    else:
                        taux = rav.qte_donnee / diff if diff else 0
                        rav.taux_reel = round(taux, 3)
                        rav.norme_ref = norme
                        rav.statut    = "anomalie" if taux > norme * 1.1 else "normal"
                else:
                    rav.statut = "non_verifie"

            # Sortie stock
            stock_avant = get_stock_actuel()
            stock_apres = stock_avant - rav.qte_donnee
            rav.save()

            # Enregistrer la sortie correspondante
            OperationStock.objects.create(
                date        = rav.date,
                type        = "sortie",
                quantite    = rav.qte_donnee,
                stock_apres = stock_apres,
                description = f"Appro {engin.id_engin}",
                operateur   = request.user,
            )

            tag_stock = f"⚠️ Stock négatif : {stock_apres:,.0f} L" if stock_apres < 0 \
                        else f"Stock restant : {stock_apres:,.0f} L"
            messages.success(request,
                f"✅ Ravitaillement {engin.id_engin} enregistré ({rav.qte_donnee:,.0f} L). "
                f"{tag_stock}")
            return redirect("dashboard")
    else:
        form = ApproEnginForm()

    # Données engins pour le JS (mode_appro + dernier index)
    engins_data = {}
    for e in Engin.objects.filter(actif=True):
        dernier = RavitaillementEngin.objects.filter(
            engin=e).order_by("-date", "-cree_le").first()
        engins_data[e.id_engin] = {
            "mode":          e.mode_appro,
            "type":          e.type_engin,
            "dernier_index": dernier.index_actuel if dernier else 0,
        }

    return render(request, "core/appro_engin.html", {
        "form":        form,
        "stock":       get_stock_actuel(),
        "engins_data": json.dumps(engins_data),
    })


# ── Consommation Diverse ──────────────────────────────────────

@login_required
def consommation_diverse(request):
    if request.method == "POST":
        form = ConsommationDiverseForm(request.POST)
        if form.is_valid():
            div           = form.save(commit=False)
            div.operateur = request.user
            stock_avant   = get_stock_actuel()
            div.stock_apres = stock_avant - div.quantite
            div.save()

            OperationStock.objects.create(
                date        = div.date,
                type        = "sortie",
                quantite    = div.quantite,
                stock_apres = div.stock_apres,
                description = f"Divers — {div.categorie}",
                operateur   = request.user,
            )

            messages.success(request,
                f"✅ Consommation {div.categorie} enregistrée ({div.quantite:,.0f} L).")
            return redirect("dashboard")
    else:
        form = ConsommationDiverseForm()

    return render(request, "core/consommation_diverse.html", {
        "form":  form,
        "stock": get_stock_actuel(),
    })


# ── Historique ────────────────────────────────────────────────

@login_required
def historique(request):
    mois  = request.GET.get("mois",  timezone.localdate().month)
    annee = request.GET.get("annee", timezone.localdate().year)

    ops   = OperationStock.objects.filter(
        date__month=mois, date__year=annee
    ).select_related("operateur").order_by("-date")

    ravs  = RavitaillementEngin.objects.filter(
        date__month=mois, date__year=annee
    ).select_related("engin", "operateur").order_by("-date")

    divs  = ConsommationDiverse.objects.filter(
        date__month=mois, date__year=annee
    ).select_related("operateur").order_by("-date")

    annees = range(2024, timezone.localdate().year + 2)

    ctx = {
        "ops": ops, "ravs": ravs, "divs": divs,
        "mois": int(mois), "annee": int(annee),
        "annees": annees,
        "mois_choices": [
            (1,"Janvier"),(2,"Février"),(3,"Mars"),(4,"Avril"),
            (5,"Mai"),(6,"Juin"),(7,"Juillet"),(8,"Août"),
            (9,"Septembre"),(10,"Octobre"),(11,"Novembre"),(12,"Décembre"),
        ],
    }
    return render(request, "core/historique.html", ctx)


# ── Export Excel (compatible import desktop) ──────────────────

@login_required
def export_excel(request):
    mois  = request.GET.get("mois",  timezone.localdate().month)
    annee = request.GET.get("annee", timezone.localdate().year)

    wb = openpyxl.Workbook()

    BLEU   = "1A3A6B"
    JAUNE  = "FFC000"

    # ── Feuille 1 : Synthèse entrées (lue par l'import desktop) ──
    # L'import desktop cherche les feuilles contenant "synth"
    # et lit : col 0=?, col 1=date, col 2=quantite
    ws_s = wb.active
    ws_s.title = "Synthèse"

    ws_s.append(["", "Date", "Quantité (L)", "Description", "Opérateur"])
    for cell in ws_s[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=BLEU)
        cell.alignment = Alignment(horizontal="center")

    for op in OperationStock.objects.filter(
        type="entree", date__month=mois, date__year=annee
    ).order_by("date"):
        ws_s.append([
            "",
            op.date,          # col index 1 — datetime lu par l'import
            op.quantite,      # col index 2 — quantite
            op.description,
            op.operateur.username if op.operateur else "",
        ])
        # Formater la cellule date comme datetime pour que openpyxl la reconnaisse
        ws_s.cell(row=ws_s.max_row, column=2).number_format = "DD/MM/YYYY"

    # ── Feuille 2 : Rapport journalier (lue par l'import desktop) ─
    # Structure attendue (min_row=12, index base 0) :
    # col 1 = date, col 4 = type_excel, col 5 = id_engin,
    # col 6 = index_prec, col 7 = index_act, col 8 = qte, col 9 = obs
    ws_r = wb.create_sheet("Rapport journalier")

    # Lignes 1-11 : en-tête (l'import commence à row 12)
    ws_r.append(["RAPPORT JOURNALIER — Export CarbPro Web"])
    for _ in range(10):
        ws_r.append([])  # lignes vides jusqu'à row 11

    # Ligne 12 : en-tête colonnes
    header = ["", "Date", "", "", "Type", "ID Engin",
              "Index Préc.", "Index Act.", "Quantité (L)", "Observations"]
    ws_r.append(header)
    for cell in ws_r[12]:
        if cell.value:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor=BLEU)
            cell.alignment = Alignment(horizontal="center")

    # Type mapping inverse : type_interne → type_excel pour l'import
    TYPE_EXCEL_MAP = {
        "camion_benne":    "CAMION BENNE",
        "excavatrice":     "EXCAVATRICE",
        "chargeur":        "CHARGEUR",
        "bulldozer":       "BULLDOZER",
        "niveleuse":       "NIVELEUSE",
        "compacteur":      "COMPACTEUR",
        "vehicule":        "LAND CR. DIR",
        "equipement_fixe": "WATER TANK",
        "autre":           "PORTE-CHAR",
    }

    # Ravitaillements engins
    for rav in RavitaillementEngin.objects.filter(
        date__month=mois, date__year=annee
    ).select_related("engin").order_by("date"):
        type_excel = TYPE_EXCEL_MAP.get(rav.engin.type_engin, rav.engin.type_engin.upper())
        idx_prec   = rav.index_precedent if rav.engin.mode_appro == "avec_index" else ""
        idx_act    = rav.index_actuel    if rav.engin.mode_appro == "avec_index" else ""
        if rav.statut == "panne_index":
            idx_prec = "Panne"
            idx_act  = "Panne"
        row = ["", rav.date, "", "", type_excel, rav.engin.id_engin,
               idx_prec, idx_act, rav.qte_donnee, rav.commentaire or ""]
        ws_r.append(row)
        ws_r.cell(row=ws_r.max_row, column=2).number_format = "DD/MM/YYYY"

    # Consommations diverses — mappées vers les types diverses attendus
    CAT_EXCEL_MAP = {
        "Garage":                 "GARAGE",
        "Groupe électrogène":     "GROUPE ELEC",
        "Bidon":                  "BIDON",
        "Fuel Tank":              "FUEL TANK",
        "Land Cruiser Direction": "LAND CR. DIR",
        "Autre":                  "AUTRES",
    }
    for div in ConsommationDiverse.objects.filter(
        date__month=mois, date__year=annee
    ).order_by("date"):
        type_excel = CAT_EXCEL_MAP.get(div.categorie, "AUTRES")
        row = ["", div.date, "", "", type_excel, "",
               "", "", div.quantite, div.motif or ""]
        ws_r.append(row)
        ws_r.cell(row=ws_r.max_row, column=2).number_format = "DD/MM/YYYY"

    # ── Feuille 3 : Résumé lisible (pour consultation) ───────────
    ws_info = wb.create_sheet("Résumé Web")
    ws_info.append(["Export CarbPro Web",
                    f"Période : {mois}/{annee}",
                    f"Généré le {date.today().strftime('%d/%m/%Y')}"])
    ws_info.append([])
    ws_info.append(["Ce fichier est compatible avec l'import de GestionCarburantPro Desktop"])

    # Ajuster largeurs
    for ws in [ws_s, ws_r]:
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 35)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="carbpro_export_{annee}_{int(mois):02d}.xlsx"'
    )
    wb.save(response)
    return response


# ── Engins (lecture seule pour les opérateurs terrain) ────────

@login_required
def liste_engins(request):
    engins = Engin.objects.filter(actif=True).order_by("id_engin")
    return render(request, "core/liste_engins.html", {"engins": engins})

@login_required
def import_excel(request):
    rapport = None

    if request.method == "POST" and request.FILES.get("fichier"):
        import tempfile, os
        fichier = request.FILES["fichier"]

        # Vérifier extension
        if not fichier.name.endswith((".xlsx", ".xls")):
            messages.error(request, "❌ Format invalide. Seuls les fichiers .xlsx sont acceptés.")
            return redirect("import_excel")

        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            for chunk in fichier.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            from .import_service import importer_depuis_excel
            rapport = importer_depuis_excel(tmp_path, operateur=request.user)

            total_ok = (rapport["entrees_stock_ok"] +
                        rapport["rav_ok"] +
                        rapport["diverses_ok"])

            if total_ok > 0:
                messages.success(request,
                    f"✅ Import terminé : {rapport['entrees_stock_ok']} entrées stock, "
                    f"{rapport['rav_ok']} ravitaillements engins, "
                    f"{rapport['diverses_ok']} consommations diverses."
                )
            else:
                messages.warning(request,
                    "⚠️ Aucune donnée importée. Vérifiez le format du fichier.")

        except Exception as ex:
            messages.error(request, f"❌ Erreur lors de l'import : {ex}")
        finally:
            os.unlink(tmp_path)

    return render(request, "core/import_excel.html", {"rapport": rapport})
# ── Import Excel ───────────────────────────────────────────────

@login_required
def import_excel(request):
    rapport = None

    if request.method == "POST" and request.FILES.get("fichier"):
        import tempfile, os
        fichier = request.FILES["fichier"]

        if not fichier.name.endswith((".xlsx", ".xls")):
            messages.error(request, "❌ Format invalide. Seuls les fichiers .xlsx sont acceptés.")
            return redirect("import_excel")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            for chunk in fichier.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            from .import_service import importer_depuis_excel
            rapport = importer_depuis_excel(tmp_path, operateur=request.user)

            total_ok = (rapport["entrees_stock_ok"] +
                        rapport["rav_ok"] +
                        rapport["diverses_ok"])

            if total_ok > 0:
                messages.success(request,
                    f"✅ Import terminé : {rapport['entrees_stock_ok']} entrées stock, "
                    f"{rapport['rav_ok']} ravitaillements engins, "
                    f"{rapport['diverses_ok']} consommations diverses."
                )
            else:
                messages.warning(request,
                    "⚠️ Aucune donnée importée. Vérifiez le format du fichier.")

        except Exception as ex:
            messages.error(request, f"❌ Erreur lors de l'import : {ex}")
        finally:
            os.unlink(tmp_path)

    return render(request, "core/import_excel.html", {"rapport": rapport})
