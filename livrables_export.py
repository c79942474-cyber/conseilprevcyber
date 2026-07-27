"""Export des livrables — Markdown → Word (.docx) et PDF mis en page CONSEILPREV.

Le générateur (livrables.py + assistant.generate) produit du Markdown ; ce module
le transforme en document professionnel. Les deux formats partagent délibérément
la MÊME charte — mêmes couleurs, même bloc de garde, mêmes tableaux, même pied de
page — pour qu'un livrable soit reconnaissable quel que soit le format choisi :
un client qui reçoit le PDF et le Word ne doit pas croire à deux documents.

python-docx et fpdf2 sont déjà des dépendances ; aucun moteur externe requis.
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EMBLEM = os.path.join(HERE, "emblem.png")

# --- Charte commune aux deux formats ------------------------------------------
# Une seule définition, déclinée en RGBColor (Word) ou en tuple (PDF) au moment
# de l'usage : la couleur d'un titre ne peut pas diverger d'un format à l'autre.
C_NAVY = (0x0A, 0x22, 0x30)      # titres, texte fort
C_TEAL = (0x0E, 0x6D, 0x7C)      # accent de marque
C_GREY = (0x55, 0x66, 0x66)      # mentions secondaires
C_LINE = (0xCB, 0xD5, 0xDB)      # filets et bordures
C_BAND = (0xEC, 0xF3, 0xF5)      # fond des en-têtes de tableau et du bloc de garde
C_ZEBRA = (0xF7, 0xFA, 0xFB)     # fond des lignes paires

CONTACT = ("CONSEILPREV · christophe.cerf@outlook.com · +33 6 60 69 21 45 · "
           "conseilprevcyber.onrender.com")
MENTION = ("Brouillon généré avec l'aide de l'IA à partir de la base de connaissance "
           "CONSEILPREV — à relire, compléter et valider par un consultant.")


def _hex(rgb):
    return "%02X%02X%02X" % rgb


# --- Analyse Markdown en blocs -----------------------------------------------
_INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*)")


def _blocks(md):
    lines = (md or "").replace("\r", "").split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        h = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if h:
            out.append(("h" + str(min(len(h.group(1)), 3)), h.group(2).strip()))
            i += 1
            continue
        if re.match(r"^\s*([-*_])\1{2,}\s*$", ln):
            out.append(("hr", None))
            i += 1
            continue
        # tableau : ligne d'en-tête + ligne de séparation
        if (re.match(r"^\s*\|.*\|\s*$", ln) and i + 1 < n
                and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]):
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append(("table", (head, rows)))
            continue
        if re.match(r"^\s*[-*]\s+", ln):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]))
                i += 1
            out.append(("ul", items))
            continue
        if re.match(r"^\s*\d+[.)]\s+", ln):
            items = []
            while i < n and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[i]))
                i += 1
            out.append(("ol", items))
            continue
        para = [ln]
        i += 1
        while (i < n and lines[i].strip()
               and not re.match(r"^(#{1,6}\s|\s*[-*]\s|\s*\d+[.)]\s|\s*\|)", lines[i])):
            para.append(lines[i])
            i += 1
        out.append(("p", " ".join(para)))
    return out


def _fiche(meta):
    """Lignes du bloc de garde (« document control »), champs vides écartés.

    Ces informations existaient déjà côté application mais n'atteignaient aucun
    des deux formats : `meta` était accepté puis ignoré. Le lecteur n'avait donc
    ni destinataire, ni périmètre, ni date sous les yeux."""
    meta = meta or {}
    champs = [("Client / organisation", meta.get("client")),
              ("Secteur d'activité", meta.get("secteur")),
              ("Périmètre", meta.get("perimetre")),
              ("Type de livrable", meta.get("label")),
              ("Date", meta.get("date")),
              ("Modèle utilisé", meta.get("model")),
              ("Statut", "Brouillon — à relire et valider")]
    return [(k, str(v).strip()) for k, v in champs if v and str(v).strip()]


def _sources(meta):
    """Documents de la base effectivement mobilisés, dédoublonnés."""
    out, vus = [], set()
    for s in ((meta or {}).get("sources") or []):
        titre = (s.get("title") or "").strip()
        if not titre or titre in vus:
            continue
        vus.add(titre)
        out.append((titre, (s.get("theme") or "").strip(),
                    "interne" if s.get("visibility") == "internal" else "public"))
    return out


# =============================================================================
#  Word (.docx)
# =============================================================================

def _add_runs(paragraph, text, color=None):
    """Ajoute le texte au paragraphe en interprétant **gras**, *italique*, `code`."""
    from docx.shared import Pt
    for part in _INLINE.split(text or ""):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(part)
        if color is not None:
            run.font.color.rgb = color


def _el(tag, **attrs):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn("w:" + k), v)
    return e


def _rule(doc):
    """Filet horizontal (bordure basse d'un paragraphe vide)."""
    p = doc.add_paragraph()
    pbdr = _el("w:pBdr")
    pbdr.append(_el("w:bottom", val="single", sz="6", space="1", color=_hex(C_LINE)))
    p._p.get_or_add_pPr().append(pbdr)
    return p


def _shade(cell, rgb):
    """Fond de cellule — indispensable pour distinguer l'en-tête d'un tableau."""
    cell._tc.get_or_add_tcPr().append(
        _el("w:shd", val="clear", color="auto", fill=_hex(rgb)))


def _champ(paragraph, instr):
    """Insère un champ Word (PAGE, NUMPAGES…) : une numérotation écrite en dur
    serait fausse dès la première modification du document par le consultant."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    run = paragraph.add_run()
    deb = OxmlElement("w:fldChar")
    deb.set(qn("w:fldCharType"), "begin")
    txt = OxmlElement("w:instrText")
    txt.set(qn("xml:space"), "preserve")
    txt.text = " %s " % instr
    fin = OxmlElement("w:fldChar")
    fin.set(qn("w:fldCharType"), "end")
    for e in (deb, txt, fin):
        run._r.append(e)
    return run


def _page_field(paragraph):
    """« page X / Y » via des champs Word."""
    _champ(paragraph, "PAGE")
    paragraph.add_run(" / ")
    _champ(paragraph, "NUMPAGES")


def build_docx(md, meta=None):
    """Construit le document Word (bytes) à partir du Markdown du livrable."""
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor

    meta = meta or {}
    NAVY, TEAL, GREY = RGBColor(*C_NAVY), RGBColor(*C_TEAL), RGBColor(*C_GREY)

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    # --- En-tête (lettre à en-tête) ---
    if os.path.exists(EMBLEM):
        try:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            p.add_run().add_picture(EMBLEM, width=Inches(0.55))
        except Exception:
            pass
    brand = doc.add_paragraph()
    brand.paragraph_format.space_after = Pt(0)
    r = brand.add_run("CONSEILPREV ")
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = NAVY
    r2 = brand.add_run("Cyber")
    r2.bold = True
    r2.font.size = Pt(11)
    r2.font.color.rgb = TEAL
    sp = doc.add_paragraph()
    sub = sp.add_run("Cybersécurité industrielle IT / OT / IIoT")
    sub.italic = True
    sub.font.size = Pt(8.5)
    sub.font.color.rgb = GREY
    _rule(doc)

    # --- Bloc de garde ---
    fiche = _fiche(meta)
    if fiche:
        t = doc.add_table(rows=0, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.LEFT
        for k, v in fiche:
            cells = t.add_row().cells
            cells[0].width = Inches(1.7)
            cells[1].width = Inches(4.6)
            rk = cells[0].paragraphs[0].add_run(k)
            rk.bold = True
            rk.font.size = Pt(9)
            rk.font.color.rgb = NAVY
            rv = cells[1].paragraphs[0].add_run(v)
            rv.font.size = Pt(9)
            for c in cells:
                c.paragraphs[0].paragraph_format.space_after = Pt(2)
            _shade(cells[0], C_BAND)
        doc.add_paragraph().paragraph_format.space_after = Pt(0)

    # --- Corps ---
    for kind, payload in _blocks(md):
        if kind in ("h1", "h2", "h3"):
            level = {"h1": 0, "h2": 1, "h3": 2}[kind]
            heading = doc.add_heading(level=level)
            heading.paragraph_format.space_before = Pt(14 if level else 6)
            heading.paragraph_format.space_after = Pt(4)
            _add_runs(heading, payload, color=NAVY)
            if level == 1:                       # filet sous les titres de section
                pbdr = _el("w:pBdr")
                pbdr.append(_el("w:bottom", val="single", sz="6", space="4",
                                color=_hex(C_LINE)))
                heading._p.get_or_add_pPr().append(pbdr)
        elif kind == "p":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY   # bloc justifié : rendu de rapport
            _add_runs(p, payload)
        elif kind == "ul":
            for it in payload:
                _add_runs(doc.add_paragraph(style="List Bullet"), it)
        elif kind == "ol":
            for it in payload:
                _add_runs(doc.add_paragraph(style="List Number"), it)
        elif kind == "table":
            head, rows = payload
            cols = max(1, len(head))
            table = doc.add_table(rows=1, cols=cols)
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            for j in range(cols):
                cell = table.rows[0].cells[j]
                run = cell.paragraphs[0].add_run(head[j] if j < len(head) else "")
                run.bold = True
                run.font.size = Pt(9.5)
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                _shade(cell, C_NAVY)
            for k, row in enumerate(rows):
                cells = table.add_row().cells
                for j in range(cols):
                    _add_runs(cells[j].paragraphs[0], row[j] if j < len(row) else "")
                    for r_ in cells[j].paragraphs[0].runs:
                        r_.font.size = Pt(9.5)
                    if k % 2:                     # zébrure : lecture des lignes longues
                        _shade(cells[j], C_ZEBRA)
            doc.add_paragraph().paragraph_format.space_after = Pt(0)
        elif kind == "hr":
            _rule(doc)

    # --- Annexe : sources mobilisées ---
    srcs = _sources(meta)
    if srcs:
        h = doc.add_heading(level=1)
        h.paragraph_format.space_before = Pt(16)
        _add_runs(h, "Sources mobilisées", color=NAVY)
        intro = doc.add_paragraph()
        ri = intro.add_run("Extraits de la base de connaissance CONSEILPREV ayant "
                           "servi à la rédaction de ce brouillon.")
        ri.italic = True
        ri.font.size = Pt(9)
        ri.font.color.rgb = GREY
        for titre, theme, vis in srcs:
            p = doc.add_paragraph(style="List Bullet")
            rt = p.add_run(titre)
            rt.bold = True
            rt.font.size = Pt(9.5)
            reste = " — %s · %s" % (theme or "sans thème", vis)
            rr = p.add_run(reste)
            rr.font.size = Pt(9)
            rr.font.color.rgb = GREY

    # --- Pied de page (toutes les pages) ---
    footer = doc.sections[0].footer
    fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    fp.text = ""
    fr = fp.add_run("CONSEILPREV Cyber · Brouillon à valider · page ")
    fr.font.size = Pt(8)
    fr.font.color.rgb = GREY
    _page_field(fp)
    for run in fp.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = GREY

    _rule(doc)
    note = doc.add_paragraph().add_run(MENTION)
    note.italic = True
    note.font.size = Pt(8.5)
    note.font.color.rgb = GREY
    contact = doc.add_paragraph().add_run(CONTACT)
    contact.font.size = Pt(8.5)
    contact.font.color.rgb = GREY

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# =============================================================================
#  PDF (fpdf2, sans dépendance système)
# =============================================================================
# Les polices de base sont encodées en Latin-1 : on translittère les quelques
# caractères hors jeu (tirets longs, flèches, guillemets courbes, emoji…) pour un
# rendu fiable, tout en conservant les accents français.
_PDF_MAP = {
    "—": " - ", "–": "-", "−": "-", "→": "->", "←": "<-",
    "⇒": "=>", "≤": "<=", "≥": ">=", "…": "...", "•": "·",
    "▪": "·", "‘": "'", "’": "'", "“": '"', "”": '"',
    " ": " ", " ": " ", "‹": "<", "›": ">", "✓": "v",
    "œ": "oe", "Œ": "OE", "€": "EUR",
}
_INLINE_STRIP = re.compile(r"\*\*([^*]+)\*\*|`([^`]+)`|\*([^*\n]+)\*")


def _pdf_txt(s):
    """Retire les marqueurs Markdown en ligne et translittère en Latin-1 sûr."""
    s = _INLINE_STRIP.sub(lambda m: m.group(1) or m.group(2) or m.group(3) or "", s or "")
    for k, v in _PDF_MAP.items():
        s = s.replace(k, v)
    # Les substitutions encadrées d'espaces (« — » -> « - ») en produisent en
    # double ; visibles à l'impression, ils font négligé.
    s = re.sub(r" {2,}", " ", s)
    return s.encode("latin-1", "ignore").decode("latin-1")


def _pdf_class():
    """Classe PDF avec en-tête courant et pied de page numéroté.

    Définie dans une fonction : fpdf n'est importé qu'au moment de l'export,
    l'application démarre donc même si la bibliothèque manque."""
    from fpdf import FPDF

    class _Livrable(FPDF):
        titre_courant = ""

        def header(self):
            # Page 1 : c'est la lettre à en-tête qui tient ce rôle.
            if self.page_no() == 1:
                return
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*C_GREY)
            self.cell(0, 5, _pdf_txt(self.titre_courant)[:110],
                      new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(*C_LINE)
            y = self.get_y()
            self.line(self.l_margin, y, self.w - self.r_margin, y)
            self.ln(3)
            self.set_text_color(0, 0, 0)

        def footer(self):
            self.set_y(-13)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*C_GREY)
            self.cell(self.epw / 2, 5, _pdf_txt("CONSEILPREV Cyber · Brouillon à valider"),
                      align="L")
            self.cell(self.epw / 2, 5, "page %d / {nb}" % self.page_no(), align="R")

    return _Livrable


def build_pdf(md, meta=None):
    """Construit le document PDF (bytes) à partir du Markdown du livrable."""
    meta = meta or {}
    pdf = _pdf_class()(format="A4", unit="mm")
    pdf.titre_courant = (meta.get("label") or "Livrable") + (
        " — " + meta["client"] if meta.get("client") else "")
    pdf.set_auto_page_break(True, margin=20)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()

    # --- En-tête (lettre à en-tête) ---
    if os.path.exists(EMBLEM):
        try:
            pdf.image(EMBLEM, x=16, y=12, w=9)
            pdf.set_x(28)
        except Exception:
            pass
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(pdf.get_string_width("CONSEILPREV "), 8, "CONSEILPREV ",
             new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*C_TEAL)
    pdf.cell(0, 8, "Cyber", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*C_GREY)
    pdf.cell(0, 5, _pdf_txt("Cybersécurité industrielle IT / OT / IIoT"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_draw_color(*C_LINE)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(3)

    def rule():
        pdf.ln(1)
        pdf.set_draw_color(*C_LINE)
        yy = pdf.get_y()
        pdf.line(pdf.l_margin, yy, pdf.w - pdf.r_margin, yy)
        pdf.ln(2)

    def _cell(text, h, width_off=0.0, align="L"):
        """multi_cell robuste : x réinitialisé, largeur explicite (jamais nulle)."""
        pdf.set_x(pdf.l_margin + width_off)
        pdf.multi_cell(pdf.epw - width_off, h, text, align=align)

    # --- Bloc de garde ---
    fiche = _fiche(meta)
    if fiche:
        lab_w, val_w = 42.0, pdf.epw - 42.0
        for k, v in fiche:
            y0 = pdf.get_y()
            pdf.set_fill_color(*C_BAND)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*C_NAVY)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(lab_w, 5.5, _pdf_txt(k), fill=True, border=0,
                           new_x="RIGHT", new_y="TOP", max_line_height=5.5)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(0, 0, 0)
            pdf.set_xy(pdf.l_margin + lab_w + 2, y0)
            pdf.multi_cell(val_w - 2, 5.5, _pdf_txt(v), border=0)
            pdf.set_y(max(pdf.get_y(), y0 + 5.5))
        pdf.ln(2)

    # --- Corps ---
    for kind, payload in _blocks(md):
        if kind in ("h1", "h2", "h3"):
            size, lh = {"h1": (16, 8), "h2": (13, 7), "h3": (11, 6)}[kind]
            pdf.ln(2 if kind == "h1" else 1)
            pdf.set_font("Helvetica", "B", size)
            pdf.set_text_color(*C_NAVY)
            _cell(_pdf_txt(payload), lh)
            if kind == "h2":                      # filet sous les titres de section
                pdf.set_draw_color(*C_LINE)
                yy = pdf.get_y()
                pdf.line(pdf.l_margin, yy, pdf.w - pdf.r_margin, yy)
                pdf.ln(2)
            pdf.set_text_color(0, 0, 0)
        elif kind == "p":
            pdf.set_font("Helvetica", "", 10.5)
            _cell(_pdf_txt(payload), 5, align="J")   # justifié, comme en Word
            pdf.ln(1)
        elif kind in ("ul", "ol"):
            pdf.set_font("Helvetica", "", 10.5)
            for idx, it in enumerate(payload, 1):
                marker = "  ·  " if kind == "ul" else "  %d.  " % idx
                _cell(_pdf_txt(marker + it), 5, width_off=3)
            pdf.ln(1)
        elif kind == "table":
            head, rows = payload
            cols = max(1, len(head))
            pdf.set_font("Helvetica", "", 9)
            try:
                from fpdf.fonts import FontFace
                entete = FontFace(emphasis="BOLD", color=(255, 255, 255),
                                  fill_color=C_NAVY)
                with pdf.table(first_row_as_headings=True, line_height=5,
                               headings_style=entete, cell_fill_color=C_ZEBRA,
                               cell_fill_mode="ROWS", borders_layout="ALL",
                               text_align="LEFT", padding=1.4) as table:
                    hr = table.row()
                    for j in range(cols):
                        hr.cell(_pdf_txt(head[j]) if j < len(head) else "")
                    for row in rows:
                        tr = table.row()
                        for j in range(cols):
                            tr.cell(_pdf_txt(row[j]) if j < len(row) else "")
            except Exception:
                # Repli : jamais d'export perdu pour un tableau récalcitrant.
                for row in [head] + rows:
                    pdf.multi_cell(0, 5, _pdf_txt(" | ".join(row)))
            pdf.ln(2)
        elif kind == "hr":
            rule()

    # --- Annexe : sources mobilisées ---
    srcs = _sources(meta)
    if srcs:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*C_NAVY)
        _cell(_pdf_txt("Sources mobilisées"), 7)
        pdf.set_draw_color(*C_LINE)
        yy = pdf.get_y()
        pdf.line(pdf.l_margin, yy, pdf.w - pdf.r_margin, yy)
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*C_GREY)
        _cell(_pdf_txt("Extraits de la base de connaissance CONSEILPREV ayant servi "
                       "à la rédaction de ce brouillon."), 4.5)
        pdf.ln(1)
        pdf.set_text_color(0, 0, 0)
        for titre, theme, vis in srcs:
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_x(pdf.l_margin + 3)
            pdf.multi_cell(pdf.epw - 3, 5, _pdf_txt("  ·  " + titre))
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*C_GREY)
            pdf.set_x(pdf.l_margin + 9)
            pdf.multi_cell(pdf.epw - 9, 4.5,
                           _pdf_txt("%s · %s" % (theme or "sans thème", vis)))
            pdf.set_text_color(0, 0, 0)

    rule()
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*C_GREY)
    _cell(_pdf_txt(MENTION), 4.5)
    pdf.set_font("Helvetica", "", 8.5)
    _cell(_pdf_txt(CONTACT.replace("·", "-")), 4.5)

    out = pdf.output()
    return bytes(out)
