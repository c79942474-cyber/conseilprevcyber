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
