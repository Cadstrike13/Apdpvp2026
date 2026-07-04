# -*- coding: utf-8 -*-
"""
generate_pv.py

Génère le "PROCES-VERBAL DE VERIFICATIONS ET VISITES" de l'APDPVP
(document Word .docx + export .pdf) à partir de données fournies par
l'appelant (aucune valeur n'est codée en dur : tout ce qui est vide dans
le modèle papier est un paramètre de la fonction generate_pv()).

Le .docx est produit avec python-docx. Le .pdf est produit indépendamment
avec WeasyPrint (HTML/CSS -> PDF) : pas de LibreOffice, pas de conversion
docx->pdf, ce qui est nettement plus simple et fiable à faire tourner dans
un conteneur Alpine.

Dépendances :
    pip install python-docx weasyprint

    Sur Alpine, WeasyPrint a besoin de quelques libs système (Pango/Cairo),
    bien plus légères qu'une installation LibreOffice complète :
        apk add --no-cache py3-pip pango cairo gdk-pixbuf ttf-freefont \
                            fontconfig font-noto

Usage minimal :

    from generate_pv import generate_pv, TRAITEMENTS_PAR_DEFAUT

    generate_pv(
        output_path="pv_controle.docx",
        mode_pv="in situ",
        entite_controlee="Société ABC",
        nom_representant="M. Jean DUPONT",
        controleurs=[
            {"nom": "Mme X", "role": "Chef de Mission"},
            {"nom": "M. Y"},
        ],
        agents_interroges=[
            {"nom": "M. Z", "fonction": "DRH"},
        ],
        date_controle="14/03/2024",
        heure_controle="09h30",
        deliberation_numero="003/2024",
        deliberation_organe="Conseil de l'APDPVP",
        traitements=TRAITEMENTS_PAR_DEFAUT,
        lieu_signature="Libreville",
        date_signature="14/03/2024",
        heure_signature="12h15",
        generate_pdf=True,
    )
"""

import os
import html as html_lib
from copy import deepcopy

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL, WD_ROW_HEIGHT_RULE
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# WeasyPrint a besoin de libs système (Pango/Cairo/GObject, cf. docstring du
# module) absentes sur beaucoup de machines de dev (Windows notamment).
# L'import est donc différé jusqu'au premier besoin réel de générer un PDF,
# pour que la génération du .docx (et l'import de ce module) reste possible
# même sans ces libs installées.


# ---------------------------------------------------------------------------
# Données par défaut (reprises telles quelles du modèle papier fourni)
# ---------------------------------------------------------------------------

TRAITEMENTS_PAR_DEFAUT = [
    {"libelle": "a) Gestion du personnel"},
    {"libelle": "b) Gestions des clients"},
    {"libelle": "c) Communication par transmission"},
    {"libelle": "d) Contrôle d'accès sans usage biométrique"},
    {"libelle": "e) contrôle d'accès avec usage biométrique"},
    {"libelle": "f) Vidéosurveillance"},
    {"libelle": "g) Télé vidéosurveillance"},
    {"libelle": "h) Transfert des Données"},
    {"libelle": "i) Interconnexion"},
    {"libelle": "j) Géolocalisation"},
    {"libelle": "k) Autres Préciser"},
]

# Chaque traitement peut recevoir, en plus de "libelle" :
#   "cto", "cpa", "nc", "cpr"  -> booléens (case cochée oui/non)
#   "obs_controleur"           -> texte
#   "obs_entite"                -> texte


# ---------------------------------------------------------------------------
# Utilitaires bas niveau (mise en forme Word)
# ---------------------------------------------------------------------------

def _set_cell_shading(cell, hex_color):
    """Applique une couleur de fond à une cellule (ShadingType CLEAR)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def _set_cell_text(cell, text, bold=False, italic=False, size=10, align=None,
                    color=None, font_name="Calibri"):
    cell.text = ""
    para = cell.paragraphs[0]
    if align is not None:
        para.alignment = align
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = font_name
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    return run


def _set_col_widths(table, widths_cm):
    table.autofit = False
    for row in table.rows:
        for idx, width in enumerate(widths_cm):
            row.cells[idx].width = Cm(width)
    for idx, width in enumerate(widths_cm):
        table.columns[idx].width = Cm(width)


def _add_paragraph(doc, text="", size=11, bold=False, italic=False,
                    align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6,
                    font_name="Calibri"):
    para = doc.add_paragraph()
    para.alignment = align
    para.paragraph_format.space_after = Pt(space_after)
    if text:
        run = para.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.size = Pt(size)
        run.font.name = font_name
    return para


def _fill_line(length=25):
    """Ligne de pointillés utilisée pour les champs à remplir à la main."""
    return "." * length


def _set_landscape(section, margin_cm=1.5):
    """Bascule une section en A4 paysage."""
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(29.7)
    section.page_height = Cm(21)
    section.left_margin = Cm(margin_cm)
    section.right_margin = Cm(margin_cm)
    section.top_margin = Cm(margin_cm)
    section.bottom_margin = Cm(margin_cm)


def _set_portrait(section, margin_cm=2):
    """Bascule une section en A4 portrait."""
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(margin_cm)
    section.right_margin = Cm(margin_cm)
    section.top_margin = Cm(margin_cm)
    section.bottom_margin = Cm(margin_cm)


# ---------------------------------------------------------------------------
# Construction du document
# ---------------------------------------------------------------------------

def _build_header(doc, logo_path=None):
    """Bloc d'en-tête : logo/APDPVP à gauche, République gabonaise à droite."""
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    _set_col_widths(table, [9, 9])

    left, right = table.rows[0].cells

    # Colonne gauche : logo + APDPVP + services
    left.text = ""
    p = left.paragraphs[0]
    if logo_path and os.path.isfile(logo_path):
        run = p.add_run()
        run.add_picture(logo_path, width=Cm(1.6))
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

    for text, bold, size in [
        ("Autorité pour la Protection des Données\nPersonnelles et de la Vie Privée", False, 7),
        ("A P D P V P", True, 11),
    ]:
        pp = left.add_paragraph()
        pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for line in text.split("\n"):
            r = pp.add_run(line)
            r.bold = bold
            r.font.size = Pt(size)
            r.add_break() if line != text.split("\n")[-1] else None

    for text in ["SECRETARIAT GENERAL",
                 "DIRECTION DE L'EXPERTISE\nINFORMATIQUE ET DES CONTROLES",
                 "SERVICE CONTROLE ET CONTENTIEUX"]:
        pp = left.add_paragraph()
        pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        lines = text.split("\n")
        for i, line in enumerate(lines):
            r = pp.add_run(line)
            r.bold = True
            r.font.size = Pt(9)
            if i < len(lines) - 1:
                r.add_break()

    # Colonne droite : République gabonaise
    right.text = ""
    p = right.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("REPUBLIQUE GABONAISE")
    r.bold = True
    r.font.size = Pt(11)
    p2 = right.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("Union - Travail – Justice")
    r2.italic = True
    r2.font.size = Pt(10)

    # Supprime les bordures de ce tableau de mise en page
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tbl_pr.append(borders)

    doc.add_paragraph()


def _build_intro_table(doc, controleurs, entite_nom_representant, agents_interroges):
    """Tableau 'Contrôleurs APDPVP' / 'Entité contrôlée'."""
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    _set_col_widths(table, [9, 9])

    left, right = table.rows[0].cells

    # ---- Colonne gauche : contrôleurs ----
    left.text = ""
    p = left.paragraphs[0]
    r = p.add_run("Contrôleurs APDPVP :")
    r.bold = True
    r.font.size = Pt(10)

    controleurs = controleurs or []
    for i in range(4):
        entry = controleurs[i] if i < len(controleurs) else {}
        nom = entry.get("nom", "")
        role = entry.get("role", "")
        label = f"{nom}, {role}" if nom and role else (nom or _fill_line(20))
        pp = left.add_paragraph()
        pp.add_run(f"{i + 1}. ").font.size = Pt(10)
        pp.add_run(label if nom else _fill_line(20)).font.size = Pt(10)

    # ---- Colonne droite : entité contrôlée ----
    right.text = ""
    p = right.paragraphs[0]
    r = p.add_run("Entité contrôlée :")
    r.bold = True
    r.font.size = Pt(10)

    pp = right.add_paragraph()
    pp.add_run("Nom du représentant de l'entité : ").font.size = Pt(10)
    pp.add_run(entite_nom_representant or _fill_line(15)).font.size = Pt(10)

    pp = right.add_paragraph()
    pp.add_run("Agents interrogés :").font.size = Pt(10)

    agents_interroges = agents_interroges or []
    for i in range(5):
        entry = agents_interroges[i] if i < len(agents_interroges) else {}
        nom = entry.get("nom", "")
        fonction = entry.get("fonction", "")
        pp = right.add_paragraph()
        pp.add_run(f"{i + 1}. ").font.size = Pt(10)
        pp.add_run(nom or _fill_line(18)).font.size = Pt(10)
        pp.add_run(", ").font.size = Pt(10)
        pp.add_run(fonction or _fill_line(12)).font.size = Pt(10)

    doc.add_paragraph()


def _build_traitements_table(doc, traitements):
    """Tableau 3 : Examen des traitements des données personnelles."""
    _add_paragraph(doc, "3.  Tableau : Examen des traitements des données personnelles :",
                   bold=True, size=11, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)

    headers = ["", "CTO", "CPA", "NC", "CPR",
               "Observations du contrôleur", "Observations de l'entité contrôlée"]
    col_widths = [5.0, 1.8, 1.8, 1.8, 1.8, 7.15, 7.15]

    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    _set_col_widths(table, col_widths)

    for idx, h in enumerate(headers):
        _set_cell_text(table.rows[0].cells[idx], h, bold=True, size=9,
                        align=WD_ALIGN_PARAGRAPH.CENTER)
        if h in ("CTO", "CPA", "NCO", "CPR"):
            _set_cell_shading(table.rows[0].cells[idx], "D9D9D9")

    for item in traitements:
        row = table.add_row()
        cells = row.cells
        _set_cell_text(cells[0], item.get("libelle", ""), size=9)

        for col_idx, key in zip((1, 2, 3, 4), ("cto", "cpa", "nc", "cpr")):
            mark = "X" if item.get(key) else ""
            _set_cell_text(cells[col_idx], mark, size=10, bold=True,
                            align=WD_ALIGN_PARAGRAPH.CENTER)
            if key == "cpr":
                _set_cell_shading(cells[col_idx], "BFBFBF")

        _set_cell_text(cells[5], item.get("obs_controleur", ""), size=9)
        _set_cell_text(cells[6], item.get("obs_entite", ""), size=9)

    # ---- Hauteur des lignes : on force un minimum pour occuper au maximum
    # la hauteur disponible sur la page paysage, quel que soit le nombre de
    # lignes de traitements passées en paramètre. ----
    n_data_rows = len(traitements)
    usable_height_cm = 15.5  # hauteur restante estimée sous le titre "3. Tableau..."
                              # et au-dessus de la légende, sur une page A4 paysage
                              # avec marges de 1.5 cm.
    header_height_cm = 1.0
    remaining_cm = max(usable_height_cm - header_height_cm, n_data_rows * 0.9)
    data_row_height_cm = remaining_cm / n_data_rows if n_data_rows else 0

    header_row = table.rows[0]
    header_row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    header_row.height = Cm(header_height_cm)

    for row in table.rows[1:]:
        row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        row.height = Cm(data_row_height_cm)

    doc.add_paragraph()
    legend = _add_paragraph(
        doc,
        "Conformité Total (CTO) ; Conformité Partielle (CPA) ; Non Conforme (NC) ; "
        "Constations Préoccupantes (CPR)",
        size=9, italic=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6,
    )
    return legend


def _build_observations_generales(doc, obs_controleur_general, obs_entite_general):
    """Tableau d'observations générales (vu en page 3 du modèle)."""
    _add_paragraph(doc, "4.  Observations générales :", bold=True, size=11,
                   align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)

    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    _set_col_widths(table, [9, 9])

    _set_cell_text(table.rows[0].cells[0], "Observations du contrôleur",
                   bold=True, italic=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
    _set_cell_text(table.rows[0].cells[1], "Observations de l'entité contrôlée",
                   bold=True, italic=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)

    row = table.add_row()
    row.cells[0].width = Cm(9)
    row.cells[1].width = Cm(9)
    _set_cell_text(row.cells[0], obs_controleur_general or "", size=10)
    _set_cell_text(row.cells[1], obs_entite_general or "", size=10)
    # Donne un peu de hauteur à la ligne pour laisser de la place à l'écriture
    row.height = Cm(3)

    doc.add_paragraph()


def _build_closing(doc, lieu_signature, date_signature, heure_signature,
                    nom_controleur_signature, nom_representant_signature):
    _add_paragraph(
        doc,
        "Le présent procès-verbal de vérifications et visites In situ/ en ligne a été établi "
        "en présence des deux parties, permettant ainsi à l'entité contrôlée de reconnaître "
        "les constatations et de formuler ses observations le cas échéant.",
        size=11,
    )

    p = _add_paragraph(doc, size=11, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=18)
    p.add_run("Fait en double exemplaire, à ")
    p.add_run(lieu_signature or _fill_line(15))
    p.add_run(", le ")
    p.add_run(date_signature or _fill_line(10))
    p.add_run(", à ")
    p.add_run(heure_signature or _fill_line(8))

    table = doc.add_table(rows=2, cols=2)
    _set_col_widths(table, [9, 9])
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tbl_pr.append(borders)

    _set_cell_text(table.rows[0].cells[0], "Le contrôleur, chef de Mission :", bold=True, size=11)
    _set_cell_text(table.rows[0].cells[1], "Le représentant de l'entité contrôlée :", bold=True, size=11)
    _set_cell_text(table.rows[1].cells[0], nom_controleur_signature or "", size=11)
    _set_cell_text(table.rows[1].cells[1], nom_representant_signature or "", size=11)
    # espace laissé pour la signature manuscrite
    for cell in (table.rows[1].cells[0], table.rows[1].cells[1]):
        cell.paragraphs[0].paragraph_format.space_before = Pt(36)


# ---------------------------------------------------------------------------
# Fonction principale
# ---------------------------------------------------------------------------

def generate_pv(
    output_path,
    mode_pv="",
    entite_controlee="",
    nom_representant="",
    controleurs=None,
    agents_interroges=None,
    date_controle="",
    heure_controle="",
    deliberation_numero="",
    deliberation_organe="",
    traitements=None,
    obs_controleur_general="",
    obs_entite_general="",
    lieu_signature="",
    date_signature="",
    heure_signature="",
    nom_controleur_signature="",
    nom_representant_signature="",
    logo_path=None,
    generate_pdf=True,
):
    """
    Génère le procès-verbal de vérifications et visites de l'APDPVP.

    Paramètres
    ----------
    output_path : str
        Chemin du fichier .docx à produire (ex. "pv_controle.docx").
    mode_pv : str
        "in situ" ou "en ligne" (ou toute autre précision) -> remplit
        "Ce procès-verbal In situ/ en ligne ..., constate...".
    entite_controlee : str
        Nom de l'entité contrôlée (utilisé dans "mis en œuvre par ...").
    nom_representant : str
        Nom du représentant de l'entité contrôlée.
    controleurs : list[dict]
        Jusqu'à 4 entrées {"nom": str, "role": str}. Le rôle du premier est
        généralement "Chef de Mission".
    agents_interroges : list[dict]
        Jusqu'à 5 entrées {"nom": str, "fonction": str}.
    date_controle : str
        Date du contrôle, ex. "14/03/2024".
    heure_controle : str
        Heure du contrôle, ex. "09h30".
    deliberation_numero : str
        Numéro de la délibération portant adoption de la procédure des
        missions de contrôle (remplace "XX/2024").
    deliberation_organe : str
        Organe ayant adopté la délibération (remplace "XXX").
    traitements : list[dict]
        Lignes du tableau 3. Voir TRAITEMENTS_PAR_DEFAUT pour le format
        et les libellés standard (a à k). Chaque dict peut contenir :
        "libelle", "cto", "cpa", "nc", "cpr" (booléens),
        "obs_controleur", "obs_entite" (texte).
    obs_controleur_general / obs_entite_general : str
        Contenu du tableau "Observations générales" (page de clôture).
    lieu_signature, date_signature, heure_signature : str
        Renseignent "Fait en double exemplaire, à ..., le ..., à ...".
    nom_controleur_signature, nom_representant_signature : str
        Noms imprimés sous les blocs de signature (la signature
        manuscrite/scan est ajoutée après impression).
    logo_path : str, optionnel
        Chemin vers une image de logo APDPVP à insérer dans l'en-tête.
    generate_pdf : bool
        Si True (par défaut), génère également un .pdf (même nom de
        fichier, extension .pdf), rendu directement par WeasyPrint à
        partir d'un document HTML équivalent (pas de conversion du .docx).

    Retour
    ------
    dict avec les clés "docx" et "pdf" (chemins absolus des fichiers
    produits ; "pdf" vaut None si generate_pdf=False ou si LibreOffice
    n'est pas disponible).
    """
    traitements = deepcopy(traitements) if traitements is not None else deepcopy(TRAITEMENTS_PAR_DEFAUT)

    doc = Document()

    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # ---- En-tête ----
    _build_header(doc, logo_path=logo_path)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("PROCES-VERBAL DE VERIFICATIONS ET VISITES")
    r.bold = True
    r.font.size = Pt(13)
    doc.add_paragraph()

    # ---- Tableau contrôleurs / entité ----
    _build_intro_table(doc, controleurs, nom_representant, agents_interroges)

    # ---- Paragraphe d'introduction ----
    p = _add_paragraph(doc, size=11)
    p.add_run("Ce procès-verbal ")
    p.add_run(mode_pv or "In situ/ en ligne")
    p.add_run(
        ", constate les manquements ou non observés lors du contrôle de conformité "
        "des traitements mis en œuvre par "
    )
    p.add_run(entite_controlee or _fill_line(30)).bold = bool(entite_controlee)
    p.add_run(
        ", conformément aux dispositions des articles 201 et 202 de la loi n°025/2023 du "
        "12 juillet 2023 portant modification de la loi n°001/2011 du 25 septembre 2011 "
        "relative à la protection des données à caractère personnel."
    )

    # ---- Déroulement du contrôle ----
    _add_paragraph(doc, "Déroulement du Contrôle :", bold=True, size=11,
                   align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)

    p = _add_paragraph(doc, size=11)
    p.add_run("Le contrôle s'est déroulé le ")
    p.add_run(date_controle or _fill_line(10))
    p.add_run(" à ")
    p.add_run(heure_controle or _fill_line(8))
    p.add_run(", conformément à la délibération n° ")
    p.add_run(deliberation_numero or "XX/2024")
    p.add_run(" du ")
    p.add_run(deliberation_organe or "XXX")
    p.add_run(" portant adoption de la procédure des missions de contrôle de l'APDPVP.")

    _add_paragraph(doc, "Les différentes étapes du contrôle ont été les suivantes :",
                   size=11, align=WD_ALIGN_PARAGRAPH.LEFT)

    _add_paragraph(doc, "1.  Introduction :", bold=True, size=11,
                   align=WD_ALIGN_PARAGRAPH.LEFT, space_after=2)
    _add_paragraph(doc, "•  Le contrôleur, chef de mission a expliqué les motifs et le "
                        "cadre juridique du contrôle.", size=11, space_after=6)

    _add_paragraph(doc, "2.  Présentation des Documents :", bold=True, size=11,
                   align=WD_ALIGN_PARAGRAPH.LEFT, space_after=2)
    _add_paragraph(doc, "•  L'entité contrôlée a présenté les documents nécessaires pour "
                        "évaluer sa conformité à la loi n°025/2023 du 12 juillet 2023 "
                        "suscitée.", size=11, space_after=2)
    _add_paragraph(doc, "•  Les documents présentés sont annexés au procès-verbal.",
                   size=11, space_after=6)

    # ---- Tableau des traitements : page dédiée en orientation paysage ----
    landscape_section = doc.add_section(WD_SECTION.NEW_PAGE)
    _set_landscape(landscape_section)

    _build_traitements_table(doc, traitements)

    # ---- Retour au format portrait pour la suite du document ----
    portrait_section = doc.add_section(WD_SECTION.NEW_PAGE)
    _set_portrait(portrait_section)

    # ---- Observations générales + clôture ----
    _build_observations_generales(doc, obs_controleur_general, obs_entite_general)
    _build_closing(doc, lieu_signature, date_signature, heure_signature,
                   nom_controleur_signature, nom_representant_signature)

    # ---- Numérotation de page (pied de page simple) ----
    _add_page_numbers(doc)

    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.save(output_path)

    pdf_path = None
    if generate_pdf:
        html_string = _build_html_document(
            mode_pv=mode_pv,
            entite_controlee=entite_controlee,
            nom_representant=nom_representant,
            controleurs=controleurs,
            agents_interroges=agents_interroges,
            date_controle=date_controle,
            heure_controle=heure_controle,
            deliberation_numero=deliberation_numero,
            deliberation_organe=deliberation_organe,
            traitements=traitements,
            obs_controleur_general=obs_controleur_general,
            obs_entite_general=obs_entite_general,
            lieu_signature=lieu_signature,
            date_signature=date_signature,
            heure_signature=heure_signature,
            nom_controleur_signature=nom_controleur_signature,
            nom_representant_signature=nom_representant_signature,
        )
        pdf_output_path = os.path.splitext(output_path)[0] + ".pdf"
        pdf_path = _generate_pdf_weasyprint(html_string, pdf_output_path)

    return {"docx": output_path, "pdf": pdf_path}


def _add_page_numbers(doc):
    section = doc.sections[0]
    footer = section.footer
    para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run()

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")

    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(fld_end)


def _e(text):
    """Échappe le texte pour une insertion sûre dans le HTML."""
    return html_lib.escape(text or "", quote=True)


def _nl2br(text):
    return _e(text).replace("\n", "<br>")


def _build_html_document(
    mode_pv, entite_controlee, nom_representant, controleurs, agents_interroges,
    date_controle, heure_controle, deliberation_numero, deliberation_organe,
    traitements, obs_controleur_general, obs_entite_general,
    lieu_signature, date_signature, heure_signature,
    nom_controleur_signature, nom_representant_signature,
):
    """Construit le document HTML (mise en page équivalente au .docx) qui
    sera transformé en PDF par WeasyPrint. La page du tableau des
    traitements est basculée en paysage via le mécanisme CSS @page nommé
    (`page: landscape`), WeasyPrint insère alors automatiquement un saut de
    page à l'entrée et à la sortie de ce bloc."""

    controleurs = controleurs or []
    agents_interroges = agents_interroges or []
    traitements = traitements or []

    # ---- Bloc "Contrôleurs APDPVP" ----
    controleurs_html = ""
    for i in range(4):
        entry = controleurs[i] if i < len(controleurs) else {}
        nom = entry.get("nom", "")
        role = entry.get("role", "")
        label = f"{_e(nom)}, {_e(role)}" if nom and role else (_e(nom) or _fill_line(20))
        controleurs_html += f"<div>{i + 1}. {label}</div>"

    # ---- Bloc "Agents interrogés" ----
    agents_html = ""
    for i in range(5):
        entry = agents_interroges[i] if i < len(agents_interroges) else {}
        nom = entry.get("nom", "")
        fonction = entry.get("fonction", "")
        agents_html += (
            f"<div>{i + 1}. {_e(nom) or _fill_line(18)}, "
            f"{_e(fonction) or _fill_line(12)}</div>"
        )

    # ---- Tableau des traitements ----
    n_rows = max(len(traitements), 1)
    # Hauteur de ligne calculée pour occuper au maximum la page paysage
    # disponible (même logique que dans la version .docx).
    header_height_cm = 1.0
    usable_height_cm = 15.5
    row_height_cm = max((usable_height_cm - header_height_cm) / n_rows, 0.9)

    rows_html = ""
    for item in traitements:
        marks = {
            key: ("X" if item.get(key) else "")
            for key in ("cto", "cpa", "nc", "cpr")
        }
        cpr_class = ' class="cpr"' if True else ""  # la colonne CPR est toujours grisée
        rows_html += f"""
        <tr style="height:{row_height_cm}cm;">
            <td class="libelle">{_e(item.get('libelle', ''))}</td>
            <td class="mark">{marks['cto']}</td>
            <td class="mark">{marks['cpa']}</td>
            <td class="mark">{marks['nc']}</td>
            <td class="mark cpr">{marks['cpr']}</td>
            <td class="obs">{_nl2br(item.get('obs_controleur', ''))}</td>
            <td class="obs">{_nl2br(item.get('obs_entite', ''))}</td>
        </tr>"""

    intro_text = (
        f"Ce procès-verbal {_e(mode_pv) or 'In situ/ en ligne'}, constate les manquements "
        f"ou non observés lors du contrôle de conformité des traitements mis en œuvre par "
        f"<strong>{_e(entite_controlee) or _fill_line(30)}</strong>, conformément aux "
        f"dispositions des articles 201 et 202 de la loi n°025/2023 du 12 juillet 2023 "
        f"portant modification de la loi n°001/2011 du 25 septembre 2011 relative à la "
        f"protection des données à caractère personnel."
    )

    deroulement_text = (
        f"Le contrôle s'est déroulé le {_e(date_controle) or _fill_line(10)} à "
        f"{_e(heure_controle) or _fill_line(8)}, conformément à la délibération n° "
        f"{_e(deliberation_numero) or 'XX/2024'} du {_e(deliberation_organe) or 'XXX'} "
        f"portant adoption de la procédure des missions de contrôle de l'APDPVP."
    )

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>
    @page {{
        size: A4 portrait;
        margin: 1.5cm 2cm;
        @bottom-center {{ content: counter(page); font-size: 9pt; }}
    }}
    @page landscape {{
        size: A4 landscape;
        margin: 1.5cm;
        @bottom-center {{ content: counter(page); font-size: 9pt; }}
    }}
    body {{
        font-family: "Carlito", "Calibri", "DejaVu Sans", sans-serif;
        font-size: 11pt;
        color: #000;
    }}
    .header {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 12pt;
    }}
    .header .left, .header .right {{ width: 48%; text-align: center; }}
    .header .apdpvp {{ font-weight: bold; font-size: 13pt; margin-top: 4pt; }}
    .header .services {{ font-weight: bold; font-size: 9pt; margin-top: 6pt; }}
    .header .republique {{ font-weight: bold; font-size: 13pt; margin-top: 10pt; }}
    .header .devise {{ font-style: italic; font-size: 10pt; }}
    h1.title {{
        text-align: center;
        font-size: 15pt;
        margin: 18pt 0 18pt 0;
    }}
    table.intro {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 12pt;
        font-size: 10pt;
    }}
    table.intro td {{
        border: 1px solid #000;
        vertical-align: top;
        padding: 6pt;
        width: 50%;
    }}
    table.intro .label {{ font-weight: bold; margin-bottom: 4pt; }}
    p {{ text-align: justify; margin: 0 0 8pt 0; }}
    h2.section {{ font-size: 12pt; margin: 12pt 0 6pt 0; }}
    ul.etapes {{ margin: 0 0 8pt 0; padding-left: 16pt; }}
    ul.etapes li {{ margin-bottom: 2pt; }}

    .landscape-section {{ page: landscape; }}

    table.traitements {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 9pt;
    }}
    table.traitements th, table.traitements td {{
        border: 1px solid #000;
        padding: 4pt 6pt;
        vertical-align: middle;
    }}
    table.traitements th {{
        background: #d9d9d9;
        font-size: 9pt;
        text-align: center;
    }}
    table.traitements td.libelle {{ width: 18%; }}
    table.traitements td.mark, table.traitements th.mark {{
        width: 6%;
        text-align: center;
        font-weight: bold;
    }}
    table.traitements td.cpr, table.traitements th.cpr {{ background: #bfbfbf; }}
    table.traitements td.obs {{ width: 25%; }}
    p.legende {{ font-size: 9pt; font-style: italic; margin-top: 8pt; }}

    table.observations {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 14pt;
        font-size: 10pt;
    }}
    table.observations th {{
        border: 1px solid #000;
        font-style: italic;
        padding: 4pt;
        width: 50%;
    }}
    table.observations td {{
        border: 1px solid #000;
        vertical-align: top;
        padding: 6pt;
        height: 3cm;
    }}

    table.signatures {{ width: 100%; margin-top: 24pt; }}
    table.signatures td {{ width: 50%; vertical-align: top; font-weight: bold; }}
    table.signatures .nom {{ font-weight: normal; margin-top: 36pt; }}
</style>
</head>
<body>

<div class="header">
    <div class="left">
        <div style="font-size:7pt;">Autorité pour la Protection des Données<br>
            Personnelles et de la Vie Privée</div>
        <div class="apdpvp">A P D P V P</div>
        <div class="services">SECRETARIAT GENERAL</div>
        <div class="services">DIRECTION DE L'EXPERTISE<br>INFORMATIQUE ET DES CONTROLES</div>
        <div class="services">SERVICE CONTROLE ET CONTENTIEUX</div>
    </div>
    <div class="right">
        <div class="republique">REPUBLIQUE GABONAISE</div>
        <div class="devise">Union - Travail – Justice</div>
    </div>
</div>

<h1 class="title">PROCES-VERBAL DE VERIFICATIONS ET VISITES</h1>

<table class="intro">
    <tr>
        <td>
            <div class="label">Contrôleurs APDPVP :</div>
            {controleurs_html}
        </td>
        <td>
            <div class="label">Entité contrôlée :</div>
            <div>Nom du représentant de l'entité : {_e(nom_representant) or _fill_line(15)}</div>
            <div style="margin-top:4pt;">Agents interrogés :</div>
            {agents_html}
        </td>
    </tr>
</table>

<p>{intro_text}</p>

<h2 class="section">Déroulement du Contrôle :</h2>
<p>{deroulement_text}</p>
<p>Les différentes étapes du contrôle ont été les suivantes :</p>

<h2 class="section" style="font-size:11pt;">1. Introduction :</h2>
<ul class="etapes">
    <li>Le contrôleur, chef de mission a expliqué les motifs et le cadre juridique du contrôle.</li>
</ul>

<h2 class="section" style="font-size:11pt;">2. Présentation des Documents :</h2>
<ul class="etapes">
    <li>L'entité contrôlée a présenté les documents nécessaires pour évaluer sa conformité
        à la loi n°025/2023 du 12 juillet 2023 suscitée.</li>
    <li>Les documents présentés sont annexés au procès-verbal.</li>
</ul>

<div class="landscape-section">
    <h2 class="section">3. Tableau : Examen des traitements des données personnelles :</h2>
    <table class="traitements">
        <thead>
            <tr>
                <th class="libelle"></th>
                <th class="mark">CTO</th>
                <th class="mark">CPA</th>
                <th class="mark">NC</th>
                <th class="mark cpr">CPR</th>
                <th>Observations du contrôleur</th>
                <th>Observations de l'entité contrôlée</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    <p class="legende">Conformité Total (CTO) ; Conformité Partielle (CPA) ; Non Conforme (NC) ;
        Constations Préoccupantes (CPR)</p>
</div>

<h2 class="section">4. Observations générales :</h2>
<table class="observations">
    <tr>
        <th>Observations du contrôleur</th>
        <th>Observations de l'entité contrôlée</th>
    </tr>
    <tr>
        <td>{_nl2br(obs_controleur_general)}</td>
        <td>{_nl2br(obs_entite_general)}</td>
    </tr>
</table>

<p>Le présent procès-verbal de vérifications et visites In situ/ en ligne a été établi en
présence des deux parties, permettant ainsi à l'entité contrôlée de reconnaître les
constatations et de formuler ses observations le cas échéant.</p>

<p>Fait en double exemplaire, à {_e(lieu_signature) or _fill_line(15)}, le
{_e(date_signature) or _fill_line(10)}, à {_e(heure_signature) or _fill_line(8)}</p>

<table class="signatures">
    <tr>
        <td>
            Le contrôleur, chef de Mission :
            <div class="nom">{_e(nom_controleur_signature)}</div>
        </td>
        <td>
            Le représentant de l'entité contrôlée :
            <div class="nom">{_e(nom_representant_signature)}</div>
        </td>
    </tr>
</table>

</body>
</html>"""
    return html


def _generate_pdf_weasyprint(html_string, pdf_path, base_url=None):
    """Rend le HTML en PDF avec WeasyPrint. Retourne None (au lieu de lever)
    si WeasyPrint ou ses libs système (Pango/Cairo/GObject) sont absents —
    le .docx reste utilisable même sans génération du PDF."""
    try:
        from weasyprint import HTML as WeasyHTML
    except (ImportError, OSError) as exc:
        print(f"[generate_pv] PDF non généré (WeasyPrint indisponible) : {exc}")
        return None
    WeasyHTML(string=html_string, base_url=base_url).write_pdf(pdf_path)
    return pdf_path if os.path.isfile(pdf_path) else None


# ---------------------------------------------------------------------------
# Exemple d'exécution directe
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Jeu de données d'exemple complet, avec des cases cochées et des
    # observations remplies pour bien visualiser le rendu final du tableau.
    traitements_test = [
        {"libelle": "a) Gestion du personnel", "cto": True,
         "obs_controleur": "Registre des traitements à jour, mentions d'information conformes.",
         "obs_entite": "RAS."},
        {"libelle": "b) Gestions des clients", "cpa": True,
         "obs_controleur": "Durée de conservation des données clients non formalisée.",
         "obs_entite": "Une procédure sera rédigée sous 30 jours."},
        {"libelle": "c) Communication par transmission", "cto": True,
         "obs_controleur": "Flux chiffrés, destinataires identifiés.",
         "obs_entite": ""},
        {"libelle": "d) Contrôle d'accès sans usage biométrique", "cto": True,
         "obs_controleur": "Badges nominatifs, journalisation des accès en place.",
         "obs_entite": ""},
        {"libelle": "e) contrôle d'accès avec usage biométrique", "nc": True,
         "obs_controleur": "Absence d'autorisation préalable de l'APDPVP pour le dispositif biométrique.",
         "obs_entite": "L'entité indique avoir engagé la démarche d'autorisation."},
        {"libelle": "f) Vidéosurveillance", "cpa": True,
         "obs_controleur": "Caméras couvrant partiellement la voie publique, signalétique absente.",
         "obs_entite": "La signalétique sera installée sous 15 jours."},
        {"libelle": "g) Télé vidéosurveillance", "cto": True,
         "obs_controleur": "Accès distant restreint aux personnes habilitées.",
         "obs_entite": ""},
        {"libelle": "h) Transfert des Données", "cpr": True,
         "obs_controleur": "Transferts hors du territoire national sans garanties documentées.",
         "obs_entite": "L'entité conteste et transmettra le contrat de sous-traitance."},
        {"libelle": "i) Interconnexion", "cto": True,
         "obs_controleur": "Aucune interconnexion constatée à ce jour.",
         "obs_entite": ""},
        {"libelle": "j) Géolocalisation", "cto": True,
         "obs_controleur": "Géolocalisation des véhicules de service, finalité et durée conformes.",
         "obs_entite": ""},
        {"libelle": "k) Autres Préciser", "obs_controleur": "", "obs_entite": ""},
    ]

    result = generate_pv(
        output_path="/mnt/user-data/outputs/pv_controle_test.docx",
        mode_pv="in situ",
        entite_controlee="Société Exemple SA",
        nom_representant="M. Jean OBAME, Directeur Général",
        controleurs=[
            {"nom": "Mme Alice NZUE", "role": "Chef de Mission"},
            {"nom": "M. Paul MBADINGA", "role": "Contrôleur"},
            {"nom": "Mme Christelle ONDO", "role": "Contrôleur"},
        ],
        agents_interroges=[
            {"nom": "Mme Sarah IVALA", "fonction": "Responsable RH"},
            {"nom": "M. David KOMBILA", "fonction": "DSI"},
            {"nom": "M. Franck NGUEMA", "fonction": "Responsable Sécurité"},
        ],
        date_controle="14/03/2024",
        heure_controle="09h30",
        deliberation_numero="003/2024",
        deliberation_organe="Conseil de l'APDPVP",
        traitements=traitements_test,
        obs_controleur_general=(
            "Contrôle réalisé dans de bonnes conditions de coopération. Deux points de "
            "non-conformité relevés (biométrie, transfert de données) nécessitent une mise "
            "en conformité sous 30 jours, avec transmission des justificatifs à l'APDPVP."
        ),
        obs_entite_general=(
            "L'entité prend acte des constatations et s'engage à régulariser les points "
            "identifiés dans les délais impartis."
        ),
        lieu_signature="Libreville",
        date_signature="14/03/2024",
        heure_signature="12h15",
        nom_controleur_signature="Mme Alice NZUE",
        nom_representant_signature="M. Jean OBAME",
        generate_pdf=True,
    )
    print(result)