#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifie que la promesse imprimée sur les pages conseil est tenue.

Les pages « Conseil & transformation » affirment, pour chaque livrable, qu'il
est rédigeable par l'IA à partir de la base de connaissance et exportable en
Word ou PDF. Ce script le vérifie livrable par livrable, au lieu de le croire :

  1. le catalogue est cohérent (aucune page sans livrable, aucun groupe conseil
     sans page pour l'exposer) ;
  2. chaque livrable produit un prompt qui le cite vraiment, et une requête
     d'ancrage sur la base de connaissance ;
  3. chaque livrable s'exporte réellement en .docx ET en .pdf, signatures de
     fichier vérifiées ;
  4. chaque page rend atteignable CHACUN de ses livrables, par son propre lien,
     et n'annonce aucun livrable qui n'existe pas ;
  5. tout lien /admin/livrables?type=... du site pointe sur un type réel.

Usage :  python3 outils/verifier_livrables.py
         Code de sortie non nul si quoi que ce soit cloche.
"""
import io
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import livrables                                    # noqa: E402
from livrables_export import build_docx, build_pdf  # noqa: E402

MD = ("# Titre\n\nUn paragraphe de test.\n\n## Section\n\n- point un\n- point deux\n\n"
      "| Colonne | Valeur |\n|---|---|\n| a | b |\n")

pb = []


def verifier(condition, message):
    if not condition:
        pb.append(message)


def main():
    # ── 1. Cohérence du catalogue ────────────────────────────────────────
    sante = livrables.sante_pages()
    for p in sante["problemes"]:
        pb.append("catalogue : " + p)

    # ── 2 et 3. Chaque livrable est rédigeable, ancré et exportable ──────
    for t in livrables.TYPES:
        tid, lab = t["id"], t.get("label", "")
        verifier(t.get("groupe"), "%s : groupe manquant" % tid)
        verifier(t.get("desc"), "%s : description manquante" % tid)
        verifier(t.get("sections"), "%s : aucune section" % tid)
        try:
            _sys, usr = livrables.build_prompts(tid, {"client": "ACME", "perimetre": "site de Rouen"})
            verifier(usr and len(usr) > 80, "%s : prompt trop court" % tid)
            # Le prompt doit parler DU livrable demandé, pas d'un gabarit vague.
            tete = lab.split("—")[0].strip().lower()[:12]
            verifier(tete and tete in (usr or "").lower(),
                     "%s : le prompt ne cite pas le livrable" % tid)
        except Exception as e:                                  # noqa: BLE001
            pb.append("%s : build_prompts lève %s" % (tid, e))
        try:
            q = livrables.retrieval_query(tid, {"client": "ACME", "perimetre": "site de Rouen"})
            verifier(q and len(q) > 15, "%s : requête d'ancrage vide" % tid)
        except Exception as e:                                  # noqa: BLE001
            pb.append("%s : retrieval_query lève %s" % (tid, e))
        meta = {"titre": lab, "client": "ACME", "type": tid}
        try:
            d = build_docx(MD, meta)
            verifier(d and d[:2] == b"PK" and len(d) > 4000,
                     "%s : export Word douteux (%d o)" % (tid, len(d or b"")))
        except Exception as e:                                  # noqa: BLE001
            pb.append("%s : build_docx lève %s" % (tid, e))
        try:
            f = build_pdf(MD, meta)
            verifier(f and f[:4] == b"%PDF" and len(f) > 800,
                     "%s : export PDF douteux (%d o)" % (tid, len(f or b"")))
        except Exception as e:                                  # noqa: BLE001
            pb.append("%s : build_pdf lève %s" % (tid, e))

    # ── 4. Chaque page rend atteignable chacun de ses livrables ─────────
    for page in livrables.PAGES_CONSEIL:
        chemin = os.path.join(RACINE, page["url"].lstrip("/") + ".html")
        if not os.path.isfile(chemin):
            pb.append("page %s : fichier absent" % page["url"])
            continue
        html = io.open(chemin, encoding="utf-8").read()
        attendus = [t["id"] for t in livrables.livrables_de_page(page["url"])]
        presents = re.findall(r'/admin/livrables\?type=([a-z0-9-]+)', html)
        for tid in attendus:
            verifier(tid in presents,
                     "page %s : le livrable %s n'a aucun lien de génération" % (page["url"], tid))
        for tid in presents:
            verifier(tid in attendus,
                     "page %s : lien vers %s, qui n'est pas un livrable de cette page"
                     % (page["url"], tid))
        # La promesse doit être présente, et dire les trois choses.
        for mot, quoi in (("rédigeable par l'IA", "rédaction IA"),
                          ("base de connaissance", "ancrage"),
                          ("Word ou PDF", "export")):
            verifier(mot in html, "page %s : la promesse ne mentionne pas %s" % (page["url"], quoi))

    # ── 5. Aucun lien mort vers un type inexistant, partout sur le site ─
    connus = {t["id"] for t in livrables.TYPES}
    for nom in sorted(os.listdir(RACINE)):
        if not nom.endswith(".html"):
            continue
        html = io.open(os.path.join(RACINE, nom), encoding="utf-8").read()
        for tid in set(re.findall(r'/admin/livrables\?type=([a-z0-9-]+)', html)):
            verifier(tid in connus, "%s : lien vers le type inconnu « %s »" % (nom, tid))

    # ── Verdict ─────────────────────────────────────────────────────────
    print("catalogue : %d livrables · %d pages conseil · %d livrables rattachés"
          % (sante["livrables"], sante["pages"], sante["livrables_conseil"]))
    if pb:
        print("\n%d PROBLÈME(S) :" % len(pb))
        for x in pb:
            print("   ", x)
        return 1
    print("\nAucun problème : chaque livrable de chaque page est rédigeable par l'IA, "
          "ancré sur la base de connaissance, exportable en Word et en PDF, et atteignable "
          "par son propre lien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
