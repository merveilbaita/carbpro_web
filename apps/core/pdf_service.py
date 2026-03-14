"""
pdf_service.py — Génération PDF pour CarbPro Web
3 rapports disponibles :
  1. Rapport des entrées de carburant (mensuel)
  2. Attestation d'harmonisation mensuelle
  3. Rapport mensuel complet (engins + stock)
"""
import io
import base64
from datetime import datetime
from django.utils import timezone

MOIS_NOMS = [
    "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]


def _get_params():
    """Récupère les paramètres entreprise."""
    from .models import Parametre
    return {
        "nom":    Parametre.get("nom_entreprise", "Mont Gabaon Construction SARLU"),
        "unite":  Parametre.get("unite", "L"),
        "seuil":  float(Parametre.get("seuil_alerte_stock", "500")),
        "logo":   Parametre.get("logo_base64", ""),
    }


def _add_logo(story, logo_b64, max_width_cm=8):
    """Ajoute le logo centré si disponible."""
    from reportlab.platypus import Image, Spacer
    from reportlab.lib.units import cm

    if not logo_b64:
        return

    try:
        # Extraire les données base64
        if "," in logo_b64:
            header, data = logo_b64.split(",", 1)
        else:
            data = logo_b64

        img_bytes = base64.b64decode(data)
        buf = io.BytesIO(img_bytes)

        logo = Image(buf)
        ratio = logo.imageWidth / logo.imageHeight
        w = max_width_cm * cm
        h = w / ratio
        logo.drawWidth  = w
        logo.drawHeight = h
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 0.2 * cm))
    except Exception:
        pass  # Si logo corrompu, on continue sans


def _red_lines(story, color_rouge):
    """Lignes rouges séparatrices."""
    from reportlab.platypus import HRFlowable
    story.append(HRFlowable(width="100%", thickness=2.5, color=color_rouge, spaceAfter=4))


# ── 1. Rapport Entrées Mensuel ────────────────────────────────

def generer_rapport_entrees(mois, annee):
    """
    Génère le rapport des entrées de carburant du mois.
    Retourne un objet BytesIO contenant le PDF.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable
    )
    from reportlab.lib.units import cm
    from .models import OperationStock

    params    = _get_params()
    nom_mois  = MOIS_NOMS[int(mois)]
    BLEU      = colors.HexColor("#1A3A6B")
    BLEU_C    = colors.HexColor("#BDD7EE")
    ROUGE     = colors.HexColor("#8B0000")
    JAUNE     = colors.HexColor("#FFC000")
    BLANC     = colors.white

    # Récupérer les entrées
    entrees = list(OperationStock.objects.filter(
        type="entree", date__month=int(mois), date__year=int(annee)
    ).order_by("date"))

    total = sum(e.quantite for e in entrees)

    # Dates période
    if entrees:
        def fmt(d):
            mois_str = MOIS_NOMS[d.month]
            return f"{d.day:02d} {mois_str} {d.year}"
        date_debut = fmt(entrees[0].date)
        date_fin   = fmt(entrees[-1].date)
    else:
        date_debut = date_fin = f"01 {nom_mois} {annee}"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2.5*cm, leftMargin=2.5*cm,
                             topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    bold14 = ParagraphStyle("b14", fontName="Helvetica-Bold", fontSize=14,
                             leading=18, alignment=1, spaceAfter=2)
    bold11 = ParagraphStyle("b11", fontName="Helvetica-Bold", fontSize=11,
                             leading=14, alignment=1, spaceAfter=2)
    norm10 = ParagraphStyle("n10", fontName="Helvetica", fontSize=10,
                             leading=13, spaceAfter=0)

    story = []

    # Logo
    _add_logo(story, params["logo"])

    # Titre encadré de lignes rouges
    _red_lines(story, ROUGE)
    story.append(Paragraph("RAPPORT DES ENTREES DE CARBURANT", bold14))
    story.append(Paragraph(f"PERIODE : Du {date_debut} au {date_fin}", bold11))
    _red_lines(story, ROUGE)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Durant ce mois de {nom_mois} {annee}, les approvisionnements en carburant "
        f"enregistrés sont les suivants :", norm10))
    story.append(Spacer(1, 0.4*cm))

    # Tableau
    data = [["DATE", f"ENTRÉE ({params['unite']})"]]
    for e in entrees:
        qte = f"{e.quantite:,.2f}".replace(",", " ").replace(".", ",")
        data.append([e.date.strftime("%d/%m/%Y"), qte])
    total_str = f"{total:,.2f}".replace(",", " ").replace(".", ",")
    data.append(["TOTAL GENERAL", total_str])

    col_w = 7.5 * cm
    table = Table(data, colWidths=[col_w, col_w])
    n = len(data)
    style = TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),    BLEU),
        ("TEXTCOLOR",     (0, 0), (-1, 0),    BLANC),
        ("FONTNAME",      (0, 0), (-1, 0),    "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),    11),
        ("ALIGN",         (0, 0), (-1, -1),   "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1),   8),
        ("BOTTOMPADDING", (0, 0), (-1, -1),   8),
        ("FONTNAME",      (0, 1), (-1, n-2),  "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, n-2),  10),
        ("BACKGROUND",    (0, -1), (-1, -1),  JAUNE),
        ("FONTNAME",      (0, -1), (-1, -1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, -1), (-1, -1),  11),
        ("GRID",          (0, 0), (-1, -1),   0.5, colors.HexColor("#aabbcc")),
        ("BOX",           (0, 0), (-1, -1),   1.5, BLEU),
    ])
    # Lignes alternées
    for i in range(1, n - 1):
        if i % 2 == 0:
            style.add("BACKGROUND", (0, i), (-1, i), BLEU_C)
    table.setStyle(style)
    story.append(table)

    # Pied de page
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Paragraph(
        f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} "
        f"par CarbPro Web — {params['nom']}",
        ParagraphStyle("footer", fontName="Helvetica", fontSize=8,
                       textColor=colors.grey, alignment=1)
    ))

    doc.build(story)
    buf.seek(0)
    return buf


# ── 2. Attestation d'harmonisation ────────────────────────────

def generer_attestation(mois, annee, responsable=""):
    """
    Génère l'attestation d'harmonisation mensuelle avec 3 blocs signature.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable
    )
    from reportlab.lib.units import cm
    from .models import OperationStock, RavitaillementEngin, ConsommationDiverse

    params   = _get_params()
    nom_mois = MOIS_NOMS[int(mois)]
    BLEU     = colors.HexColor("#1A3A5C")
    BLEU_C   = colors.HexColor("#E8F1FB")
    ROUGE    = colors.HexColor("#8B0000")
    BLANC    = colors.white

    # Calculs
    from django.db.models import Sum
    entrees = OperationStock.objects.filter(
        type="entree", date__month=int(mois), date__year=int(annee)
    ).aggregate(t=Sum("quantite"))["t"] or 0

    sorties_stock = OperationStock.objects.filter(
        type="sortie", date__month=int(mois), date__year=int(annee)
    ).aggregate(t=Sum("quantite"))["t"] or 0

    sorties_engins = RavitaillementEngin.objects.filter(
        date__month=int(mois), date__year=int(annee)
    ).aggregate(t=Sum("qte_donnee"))["t"] or 0

    sorties_div = ConsommationDiverse.objects.filter(
        date__month=int(mois), date__year=int(annee)
    ).aggregate(t=Sum("quantite"))["t"] or 0

    sorties = sorties_stock + sorties_engins + sorties_div
    nb_ops  = (
        OperationStock.objects.filter(date__month=int(mois), date__year=int(annee)).count() +
        RavitaillementEngin.objects.filter(date__month=int(mois), date__year=int(annee)).count() +
        ConsommationDiverse.objects.filter(date__month=int(mois), date__year=int(annee)).count()
    )

    # Stock fin : dernière opération stock du mois
    last_op = OperationStock.objects.filter(
        date__month=int(mois), date__year=int(annee)
    ).order_by("-date", "-cree_le").first()
    stock_fin = last_op.stock_apres if last_op else 0

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2.5*cm, leftMargin=2.5*cm,
                             topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    center = ParagraphStyle("ct", parent=styles["Normal"], alignment=1, spaceAfter=4)
    bold_t = ParagraphStyle("bt", parent=center, fontName="Helvetica-Bold",
                             fontSize=15, textColor=BLEU, spaceAfter=4)
    bold_s = ParagraphStyle("bs", parent=center, fontName="Helvetica-Bold",
                             fontSize=12, textColor=BLEU, spaceAfter=4)
    norm_j = ParagraphStyle("nj", parent=styles["Normal"], fontSize=10,
                             leading=14, alignment=4)

    story = []

    # Logo
    _add_logo(story, params["logo"])

    # Titre
    _red_lines(story, ROUGE)
    story.append(Paragraph("ATTESTATION D'HARMONISATION DU STOCK DE CARBURANT", bold_t))
    story.append(Paragraph(f"Période : {nom_mois} {annee}", bold_s))
    _red_lines(story, ROUGE)
    story.append(Spacer(1, 0.7*cm))

    story.append(Paragraph(
        f"Le responsable soussigné atteste que le stock de carburant pour la "
        f"période du mois de <b>{nom_mois} {annee}</b> a été correctement géré "
        f"et que les données ci-dessous reflètent fidèlement les opérations "
        f"effectuées au cours de cette période.",
        norm_j
    ))
    story.append(Spacer(1, 0.7*cm))

    # Tableau données
    def fmt(v): return f"{v:.2f} {params['unite']}"
    data_t = [
        ["DÉSIGNATION", "VALEUR"],
        ["Période", f"{nom_mois} {annee}"],
        ["Total Entrées", fmt(entrees)],
        ["Total Sorties", fmt(sorties)],
        ["Bilan Net (Entrées − Sorties)", fmt(entrees - sorties)],
        ["Stock en fin de période", fmt(stock_fin)],
        ["Nombre d'opérations", str(nb_ops)],
        ["Date de génération", datetime.now().strftime("%d/%m/%Y")],
    ]
    dt = Table(data_t, colWidths=[10*cm, 6*cm])
    dt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BLEU),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  BLANC),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  11),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("FONTNAME",      (0, 1), (0, -1),  "Helvetica-Bold"),
        ("BACKGROUND",    (0, 1), (0, -1),  BLEU_C),
        ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 10),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#aabbcc")),
        ("BOX",           (0, 0), (-1, -1), 1,   BLEU),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(dt)
    story.append(Spacer(1, 0.6*cm))

    story.append(Paragraph(
        "Je certifie l'exactitude des informations contenues dans ce document.",
        ParagraphStyle("certif", parent=center, fontSize=10,
                       fontName="Helvetica-Oblique",
                       textColor=colors.HexColor("#444444"))
    ))
    story.append(Spacer(1, 1*cm))

    # 3 blocs signature
    col_w = (A4[0] - 5*cm) / 3
    sig_d = [
        ["POUR L'ENTREPRISE", "POUR LE FOURNISSEUR", "VISA DU DIRECTEUR"],
        ["", "", ""],
        ["Nom & Signature :", "Nom & Signature :", "Nom & Signature :"],
        [datetime.now().strftime("%d / %m / %Y"),
         datetime.now().strftime("%d / %m / %Y"),
         datetime.now().strftime("%d / %m / %Y")],
    ]
    sig_t = Table(sig_d, colWidths=[col_w, col_w, col_w],
                  rowHeights=[0.7*cm, 2.5*cm, 0.6*cm, 0.6*cm])
    sig_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BLEU),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  BLANC),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  10),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, 0),  "MIDDLE"),
        ("FONTNAME",      (0, 2), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 2), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 2), (-1, -1), colors.HexColor("#333333")),
        ("BOX",           (0, 0), (-1, -1), 1,   BLEU),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.HexColor("#aabbcc")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, 0),  2,   ROUGE),
    ]))
    story.append(sig_t)

    # Pied de page
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Paragraph(
        f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} "
        f"par CarbPro Web — {params['nom']}",
        ParagraphStyle("footer", fontName="Helvetica", fontSize=8,
                       textColor=colors.grey, alignment=1)
    ))

    doc.build(story)
    buf.seek(0)
    return buf


# ── 3. Rapport mensuel complet ────────────────────────────────

def generer_rapport_mensuel(mois, annee):
    """
    Rapport complet : résumé stock + détail engins + consommations diverses.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable, PageBreak
    )
    from reportlab.lib.units import cm
    from .models import OperationStock, RavitaillementEngin, ConsommationDiverse
    from django.db.models import Sum

    params   = _get_params()
    nom_mois = MOIS_NOMS[int(mois)]
    BLEU     = colors.HexColor("#1A3A6B")
    BLEU_C   = colors.HexColor("#EEF3FB")
    ROUGE    = colors.HexColor("#8B0000")
    JAUNE    = colors.HexColor("#FFC000")
    VERT     = colors.HexColor("#1a7a3c")
    BLANC    = colors.white

    # Données
    entrees_qs = OperationStock.objects.filter(
        type="entree", date__month=int(mois), date__year=int(annee)
    ).order_by("date")
    ravs_qs = RavitaillementEngin.objects.filter(
        date__month=int(mois), date__year=int(annee)
    ).select_related("engin").order_by("date")
    divs_qs = ConsommationDiverse.objects.filter(
        date__month=int(mois), date__year=int(annee)
    ).order_by("date")

    total_entrees = entrees_qs.aggregate(t=Sum("quantite"))["t"] or 0
    total_ravs    = ravs_qs.aggregate(t=Sum("qte_donnee"))["t"] or 0
    total_divs    = divs_qs.aggregate(t=Sum("quantite"))["t"] or 0
    total_sorties = total_ravs + total_divs

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    def style(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    bold16  = style("B16", fontName="Helvetica-Bold", fontSize=16, alignment=1, spaceAfter=2)
    bold12  = style("B12", fontName="Helvetica-Bold", fontSize=12, textColor=BLEU, spaceAfter=6)
    bold10  = style("B10", fontName="Helvetica-Bold", fontSize=10, spaceAfter=2)
    norm9   = style("N9",  fontName="Helvetica",      fontSize=9,  spaceAfter=0)
    center8 = style("C8",  fontName="Helvetica",      fontSize=8,  alignment=1, textColor=colors.grey)

    story = []

    # ── Page 1 : En-tête + résumé ──────────────────────────────
    _add_logo(story, params["logo"], max_width_cm=7)
    story.append(HRFlowable(width="100%", thickness=2.5, color=ROUGE, spaceAfter=4))
    story.append(Paragraph(f"RAPPORT MENSUEL DE CARBURANT — {nom_mois.upper()} {annee}", bold16))
    story.append(Paragraph(params["nom"], style("en", fontName="Helvetica", fontSize=11, alignment=1, textColor=colors.grey)))
    story.append(HRFlowable(width="100%", thickness=2.5, color=ROUGE, spaceBefore=4))
    story.append(Spacer(1, 0.6*cm))

    # Résumé KPI
    kpi_data = [
        ["ENTRÉES", "SORTIES ENGINS", "CONSOMM. DIVERSES", "BILAN NET"],
        [
            f"{total_entrees:.0f} {params['unite']}",
            f"{total_ravs:.0f} {params['unite']}",
            f"{total_divs:.0f} {params['unite']}",
            f"{total_entrees - total_sorties:.0f} {params['unite']}",
        ]
    ]
    kpi_t = Table(kpi_data, colWidths=[3.9*cm]*4)
    kpi_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BLEU),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  BLANC),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  9),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME",      (0, 1), (-1, 1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 1), (-1, 1),  14),
        ("TEXTCOLOR",     (0, 1), (0, 1),   VERT),
        ("TEXTCOLOR",     (1, 1), (2, 1),   ROUGE),
        ("TEXTCOLOR",     (3, 1), (3, 1),
         VERT if total_entrees >= total_sorties else ROUGE),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("BOX",           (0, 0), (-1, -1), 1, BLEU),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.HexColor("#aabbcc")),
    ]))
    story.append(kpi_t)
    story.append(Spacer(1, 0.8*cm))

    # ── Section Entrées ───────────────────────────────────────
    story.append(Paragraph("1. ENTRÉES DE CARBURANT", bold12))
    if entrees_qs:
        e_data = [["Date", f"Quantité ({params['unite']})", "Description", "Opérateur"]]
        for e in entrees_qs:
            e_data.append([
                e.date.strftime("%d/%m/%Y"),
                f"{e.quantite:.1f}",
                e.description or "—",
                e.operateur.username if e.operateur else "—",
            ])
        e_data.append(["TOTAL", f"{total_entrees:.1f}", "", ""])
        et = Table(e_data, colWidths=[2.5*cm, 3*cm, 7*cm, 3*cm])
        _style_tableau(et, BLEU, BLANC, BLEU_C, JAUNE)
        story.append(et)
    else:
        story.append(Paragraph("Aucune entrée ce mois.", norm9))
    story.append(Spacer(1, 0.6*cm))

    # ── Section Ravitaillements engins ────────────────────────
    story.append(Paragraph("2. RAVITAILLEMENTS ENGINS", bold12))
    if ravs_qs:
        r_data = [["Date", "Engin", "Idx Préc.", "Idx Act.", f"Qté ({params['unite']})", "Statut"]]
        for r in ravs_qs:
            statut_map = {"normal":"Normal","anomalie":"Anomalie",
                          "panne_index":"Panne idx","non_verifie":"Non vér."}
            r_data.append([
                r.date.strftime("%d/%m/%Y"),
                r.engin.id_engin,
                f"{r.index_precedent:.0f}" if r.engin.mode_appro == "avec_index" else "—",
                f"{r.index_actuel:.0f}" if r.engin.mode_appro == "avec_index" else "—",
                f"{r.qte_donnee:.1f}",
                statut_map.get(r.statut, r.statut),
            ])
        r_data.append(["TOTAL", "", "", "", f"{total_ravs:.1f}", ""])
        rt = Table(r_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm, 2.5*cm])
        _style_tableau(rt, BLEU, BLANC, BLEU_C, JAUNE)
        story.append(rt)
    else:
        story.append(Paragraph("Aucun ravitaillement ce mois.", norm9))
    story.append(Spacer(1, 0.6*cm))

    # ── Section Consommations diverses ────────────────────────
    story.append(Paragraph("3. CONSOMMATIONS DIVERSES", bold12))
    if divs_qs:
        d_data = [["Date", "Catégorie", f"Qté ({params['unite']})", "Motif"]]
        for d in divs_qs:
            d_data.append([
                d.date.strftime("%d/%m/%Y"),
                d.categorie,
                f"{d.quantite:.1f}",
                d.motif or "—",
            ])
        d_data.append(["TOTAL", "", f"{total_divs:.1f}", ""])
        dv = Table(d_data, colWidths=[2.5*cm, 5*cm, 3*cm, 5*cm])
        _style_tableau(dv, BLEU, BLANC, BLEU_C, JAUNE)
        story.append(dv)
    else:
        story.append(Paragraph("Aucune consommation diverse ce mois.", norm9))

    # Pied de page
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Paragraph(
        f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} "
        f"par CarbPro Web — {params['nom']}",
        center8
    ))

    doc.build(story)
    buf.seek(0)
    return buf


def _style_tableau(table, bleu, blanc, bleu_c, jaune):
    """Style standard pour les tableaux de rapport."""
    table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  bleu),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  blanc),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  9),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME",      (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -2), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -2), [blanc, bleu_c]),
        ("BACKGROUND",    (0, -1), (-1, -1), jaune),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, -1), (-1, -1), 9),
        ("GRID",          (0, 0), (-1, -1), 0.5, bleu),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
