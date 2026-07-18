"""Source CSV : lit un fichier CSV et produit des événements normalisables.

Colonnes reconnues (insensible à la casse, toutes optionnelles) :
    asset, zone, type, event (ou message/description), severity, ts
Les colonnes inconnues sont ignorées ; les alias sont gérés par core.normalize_event.
"""
import csv


def read_csv(path, delimiter=","):
    """Génère un dict par ligne de CSV (clés en minuscules)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            if not row:
                continue
            clean = {(k or "").strip().lower(): (v.strip() if isinstance(v, str) else v)
                     for k, v in row.items()}
            # Ligne entièrement vide -> on saute.
            if not any(clean.values()):
                continue
            yield clean
