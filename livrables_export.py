"""Export des livrables — Markdown → document Word (.docx) mis en page CONSEILPREV.

Le générateur (livrables.py + assistant.generate) produit du Markdown ; ce module
le transforme en document Word professionnel et sourcé : en-tête avec emblème,
titres stylés, listes, tableaux, et pied de page (mention « brouillon » + contact).

python-docx est déjà une dépendance (extraction DOCX de la base de connaissance).
Aucun moteur externe requis — fonctionne sur l'hébergement Render.
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EMBLEM = os.path.join(HERE, "emblem.png")

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


def _add_runs(paragraph, text):
    """Ajoute le texte au paragraphe en interprétant **gras**, *italique*, `code`."""
    for part in _INLINE.split(text or ""):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            paragraph.add_run(part[1:-1]).italic = True
        else:
            paragraph.add_run(part)


def _rule(doc):
    """Filet horizontal (bordure basse d'un paragraphe vide)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "CBD5DB")):
        bottom.set(qn(k), v)
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def build_docx(md, meta=None):
    """Construit le document Word (bytes) à partir du Markdown du livrable."""
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    meta = meta or {}
    NAVY = RGBColor(0x0A, 0x22, 0x30)
    TEAL = RGBColor(0x0E, 0x6D, 0x7C)
    GREY = RGBColor(0x55, 0x66, 0x66)

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    # En-tête (lettre à en-tête) : emblème + nom + baseline.
    if os.path.exists(EMBLEM):
        try:
            doc.add_paragraph().add_run().add_picture(EMBLEM, width=Inches(0.55))
        except Exception:
            pass
    brand = doc.add_paragraph()
    r = brand.add_run("CONSEILPREV ")
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = NAVY
    r2 = brand.add_run("Cyber")
    r2.bold = True
    r2.font.size = Pt(11)
    r2.font.color.rgb = TEAL
    sub = doc.add_paragraph().add_run("Cybersécurité industrielle IT / OT / IIoT")
    sub.italic = True
    sub.font.size = Pt(8.5)
    sub.font.color.rgb = GREY
    _rule(doc)

    for kind, payload in _blocks(md):
        if kind in ("h1", "h2", "h3"):
            level = {"h1": 0, "h2": 1, "h3": 2}[kind]
            heading = doc.add_heading(level=level)
            _add_runs(heading, payload)
            for run in heading.runs:
                run.font.color.rgb = NAVY
        elif kind == "p":
            _add_runs(doc.add_paragraph(), payload)
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
            for j in range(cols):
                cell = table.rows[0].cells[j]
                run = cell.paragraphs[0].add_run(head[j] if j < len(head) else "")
                run.bold = True
            for row in rows:
                cells = table.add_row().cells
                for j in range(cols):
                    _add_runs(cells[j].paragraphs[0], row[j] if j < len(row) else "")
        elif kind == "hr":
            _rule(doc)

    _rule(doc)
    note = doc.add_paragraph().add_run(
        "Brouillon généré avec l'aide de l'IA à partir de la base de connaissance "
        "CONSEILPREV — à relire, compléter et valider par un consultant.")
    note.italic = True
    note.font.size = Pt(8.5)
    note.font.color.rgb = GREY
    contact = doc.add_paragraph().add_run(
        "CONSEILPREV · christophe.cerf@outlook.com · +33 6 60 69 21 45 · "
        "conseilprevcyber.onrender.com")
    contact.font.size = Pt(8.5)
    contact.font.color.rgb = GREY

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# --- Export PDF (fpdf2, sans dépendance système) -----------------------------
# fpdf2 est une bibliothèque Python pure (aucun moteur externe, compatible Render).
# Les polices de base sont encodées en Latin-1 : on translittère les quelques
# caractères hors jeu (tirets longs, flèches, guillemets courbes, emoji…) pour un
# rendu fiable, tout en conservant les accents français.
_PDF_MAP = {
    "—": " - ", "–": "-", "−": "-", "→": "->", "←": "<-",
    "⇒": "=>", "≤": "<=", "≥": ">=", "…": "...", "•": "·",
    "▪": "·", "‘": "'", "’": "'", "“": '"', "”": '"',
    " ": " ", " ": " ", "‹": "<", "›": ">", "✓": "v",
    "œ": "oe", "Œ": "OE", "€": "EUR",
}
_INLINE_STRIP = re.compile(r"\*\*([^*]+)\*\*|`([^`]+)`|\*([^*\n]+)\*")


def _pdf_txt(s):
    """Retire les marqueurs Markdown en ligne et translittère en Latin-1 sûr."""
    s = _INLINE_STRIP.sub(lambda m: m.group(1) or m.group(2) or m.group(3) or "", s or "")
    for k, v in _PDF_MAP.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "ignore").decode("latin-1")


def build_pdf(md, meta=None):
    """Construit le document PDF (bytes) à partir du Markdown du livrable."""
    from fpdf import FPDF
    meta = meta or {}
    NAVY, TEAL, GREY = (10, 34, 48), (14, 109, 124), (85, 102, 102)

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(True, margin=18)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()

    # En-tête (lettre à en-tête) : emblème + nom + baseline.
    if os.path.exists(EMBLEM):
        try:
            pdf.image(EMBLEM, x=16, y=12, w=9)
            pdf.set_x(28)
        except Exception:
            pass
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*NAVY)
    pdf.cell(pdf.get_string_width("CONSEILPREV "), 8, "CONSEILPREV ", new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 8, "Cyber", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 5, _pdf_txt("Cybersécurité industrielle IT / OT / IIoT"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_draw_color(203, 213, 219)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(3)

    def rule():
        pdf.ln(1)
        pdf.set_draw_color(203, 213, 219)
        yy = pdf.get_y()
        pdf.line(pdf.l_margin, yy, pdf.w - pdf.r_margin, yy)
        pdf.ln(2)

    def _cell(text, h, width_off=0.0):
        """multi_cell robuste : x réinitialisé, largeur explicite (jamais nulle)."""
        pdf.set_x(pdf.l_margin + width_off)
        pdf.multi_cell(pdf.epw - width_off, h, text)

    for kind, payload in _blocks(md):
        if kind in ("h1", "h2", "h3"):
            size, lh = {"h1": (16, 8), "h2": (13, 7), "h3": (11, 6)}[kind]
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", size)
            pdf.set_text_color(*NAVY)
            _cell(_pdf_txt(payload), lh)
            pdf.set_text_color(0, 0, 0)
        elif kind == "p":
            pdf.set_font("Helvetica", "", 10.5)
            _cell(_pdf_txt(payload), 5)
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
                with pdf.table(first_row_as_headings=True, line_height=5) as table:
                    hr = table.row()
                    for j in range(cols):
                        hr.cell(_pdf_txt(head[j]) if j < len(head) else "")
                    for row in rows:
                        tr = table.row()
                        for j in range(cols):
                            tr.cell(_pdf_txt(row[j]) if j < len(row) else "")
            except Exception:
                for row in [head] + rows:
                    pdf.multi_cell(0, 5, _pdf_txt(" | ".join(row)))
            pdf.ln(1)
        elif kind == "hr":
            rule()

    rule()
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*GREY)
    _cell(_pdf_txt(
        "Brouillon généré avec l'aide de l'IA à partir de la base de connaissance "
        "CONSEILPREV — à relire, compléter et valider par un consultant."), 4.5)
    pdf.set_font("Helvetica", "", 8.5)
    _cell(_pdf_txt(
        "CONSEILPREV - christophe.cerf@outlook.com - +33 6 60 69 21 45 - "
        "conseilprevcyber.onrender.com"), 4.5)

    out = pdf.output()
    return bytes(out)
