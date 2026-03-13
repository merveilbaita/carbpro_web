from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum
import json, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import date

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

    # ── Feuille Entrées ───────────────────────────────────────
    ws_e = wb.active
    ws_e.title = "Entrées Stock"
    en_tete = ["Date", "Quantité (L)", "Description", "Opérateur"]
    ws_e.append(en_tete)
    for cell in ws_e[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1A3A6B")
        cell.alignment = Alignment(horizontal="center")

    for op in OperationStock.objects.filter(
            type="entree", date__month=mois, date__year=annee
    ).order_by("date"):
        ws_e.append([
            op.date.strftime("%d/%m/%Y"),
            op.quantite,
            op.description,
            op.operateur.get_full_name() or op.operateur.username if op.operateur else "",
        ])

    # ── Feuille Ravitaillements Engins ────────────────────────
    ws_r = wb.create_sheet("Appro Engins")
    en_tete_r = ["Date","Engin","Index Préc.","Index Act.","Différence",
                  "Qté (L)","Taux Réel","Norme Réf","Statut","Commentaire","Opérateur"]
    ws_r.append(en_tete_r)
    for cell in ws_r[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1A3A6B")

    for rav in RavitaillementEngin.objects.filter(
            date__month=mois, date__year=annee
    ).select_related("engin","operateur").order_by("date"):
        ws_r.append([
            rav.date.strftime("%d/%m/%Y"),
            rav.engin.id_engin,
            rav.index_precedent,
            rav.index_actuel,
            rav.difference_index,
            rav.qte_donnee,
            rav.taux_reel,
            rav.norme_ref,
            rav.statut,
            rav.commentaire,
            rav.operateur.username if rav.operateur else "",
        ])

    # ── Feuille Consommations Diverses ────────────────────────
    ws_d = wb.create_sheet("Consommations Diverses")
    ws_d.append(["Date","Catégorie","Quantité (L)","Motif","Opérateur"])
    for cell in ws_d[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1A3A6B")

    for div in ConsommationDiverse.objects.filter(
            date__month=mois, date__year=annee
    ).select_related("operateur").order_by("date"):
        ws_d.append([
            div.date.strftime("%d/%m/%Y"),
            div.categorie,
            div.quantite,
            div.motif,
            div.operateur.username if div.operateur else "",
        ])

    # Ajuster largeurs colonnes
    for ws in [ws_e, ws_r, ws_d]:
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

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
