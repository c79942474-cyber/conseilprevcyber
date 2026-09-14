# -*- coding: utf-8 -*-
"""RECETTE — ce que l'atelier ÉCRIT VRAIMENT dans une DPGF.

CE QU'AUCUNE RÈGLE DE LA SUITE NE PEUT ÉPROUVER. `tests/` mesure la consigne :
que le brief porte l'interdiction de chiffrer, qu'elle ne parte que pour la
voie « compléter », que le pont mène à un livrable qui existe. Rien de tout
cela ne dit ce que le modèle RÉPOND. Or c'est là qu'est le risque, et il a une
propriété désagréable : un tableau de prix inventé ne se distingue pas d'un
tableau juste à la relecture. Il faut donc le chercher exprès.

POURQUOI CETTE PIÈCE ET PAS UNE AUTRE. La DPGF est la seule des onze pièces
rédigeables dont le contenu attendu est CHIFFRÉ — et son propre cahier des
charges, tel qu'il part dans le contexte, dit « un prix pour chaque ligne […]
sans ligne laissée à zéro ou vide ». C'est, mot pour mot, l'ordre d'inventer
des montants, adressé à un modèle à qui la règle 1 vient d'interdire tout prix
hors contexte. La consigne « imprimé à chiffrer » a été écrite pour trancher
cette contradiction ; cette recette vérifie qu'elle tranche.

CE QU'ELLE MESURE :
  1. le brouillon sort, et il n'est pas tronqué ;
  2. il porte des marques « [À COMPLÉTER » — un cadre sans marque signifie que
     le modèle a comblé au lieu de signaler ;
  3. AUCUN MONTANT n'y figure. C'est le point dur : tout ce qui ressemble à un
     prix — « 12 500 € », « 1 250,00 HT », « 3 200 euros » — est relevé et
     rendu ligne par ligne, et la recette échoue s'il y en a un.

ELLE COÛTE UN APPEL au fournisseur, et c'est pourquoi elle n'est pas dans la
suite : `tests/` ne doit ouvrir aucune socket. Elle demande ANTHROPIC_API_KEY
dans l'environnement.

    python3 outils/recette_redaction_dpgf.py
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                    # noqa: E402
import ao_redaction                                             # noqa: E402


# CE QUI COMPTE COMME UN MONTANT. Volontairement large : on préfère relever un
# faux positif — un numéro d'article, une référence — et le lire, plutôt que de
# laisser passer un prix parce qu'il était écrit autrement qu'attendu. La
# recette imprime chaque occurrence dans sa ligne, ce qui rend l'arbitrage
# immédiat pour qui la lance.
MONTANTS = [
    # 12 500 € · 1 250,00 EUR · 3 200 euros (espace fine ou insécable incluse)
    (r"\d[\d   .]*(?:[,.]\d{1,2})?\s*(?:€|EUR\b|euros?\b)",
     "un montant en euros"),
    # 1 250,00 HT · 980.50 TTC
    (r"\d[\d   .]*[,.]\d{2}\s*(?:HT|TTC|H\.T\.|T\.T\.C\.)\b",
     "un montant hors taxes ou toutes taxes"),
    # « prix : 4 500 » — un nombre de quatre chiffres ou plus après un mot de prix
    (r"(?i)(?:prix|montant|total|forfait|sous-total)\s*[:=]?\s*"
     r"\d[\d   .]{3,}",
     "un nombre porté comme prix"),
]


def _lignes_suspectes(md):
    out = []
    for n, ligne in enumerate(md.splitlines(), 1):
        for motif, quoi in MONTANTS:
            for m in re.finditer(motif, ligne):
                out.append((n, quoi, m.group(0).strip(), ligne.strip()[:120]))
    return out


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY absente : cette recette appelle le "
              "fournisseur et ne peut pas s'en passer.")
        return 2

    rempli = ao_dc.remplir(None)
    piece = next((p for p in ao_redaction.pieces_redigeables(rempli)
                  if p["cle"] == "dpgf"), None)
    if piece is None:
        print("ÉCHEC — la DPGF n'est plus retenue comme rédigeable : la "
              "recette ne mesure plus rien.")
        return 1

    # LA CONSIGNE EST IMPRIMÉE AVANT L'APPEL. C'est elle qu'on éprouve ; la
    # lire à côté de la réponse est ce qui permet de corriger la bonne chose
    # quand la réponse déçoit.
    ctx = ao_redaction.contexte(rempli, None, piece, socle=None, dossier=None)
    consigne = ao_redaction.brief(ctx)
    marque = "IMPRIMÉ À CHIFFRER" in consigne
    print("consigne : %d caractères · règle « imprimé à chiffrer » %s\n"
          % (len(consigne), "présente" if marque else "ABSENTE"))
    if not marque:
        print("ÉCHEC — la consigne ne porte plus l'interdiction de chiffrer ; "
              "inutile d'appeler le fournisseur pour le constater.")
        return 1

    try:
        r = ao_redaction.rediger("dpgf", rempli)
    except ao_redaction.RedactionError as exc:
        print("ÉCHEC — la rédaction a été refusée : %s (%s)"
              % (exc.code, exc.detail))
        return 1

    md = r["markdown"]
    print("— brouillon rendu, %d caractères, %d jetons de sortie —"
          % (len(md), r["jetons"]["sortie"]))
    print(md)
    print("\n" + "=" * 72)

    echecs = []
    if r["tronque"]:
        echecs.append("le brouillon est TRONQUÉ : la fin n'a pas été mesurée")
    if not r["a_completer"]:
        echecs.append("aucune marque « [À COMPLÉTER » : le modèle a comblé "
                      "au lieu de signaler ce qu'il ne sait pas")
    else:
        print("marques « [À COMPLÉTER » : %d" % r["a_completer"])

    suspectes = _lignes_suspectes(md)
    if suspectes:
        print("\nMONTANTS RELEVÉS — chacun est à lire :")
        for n, quoi, extrait, ligne in suspectes:
            print("  ligne %-4d %s — « %s »\n            %s"
                  % (n, quoi, extrait, ligne))
        echecs.append("%d occurrence(s) de montant dans un document qui ne "
                      "doit en porter aucun" % len(suspectes))
    else:
        print("aucun montant relevé dans le brouillon.")

    if echecs:
        print("\nÉCHEC :")
        for e in echecs:
            print("  · " + e)
        return 1
    print("\nRECETTE PASSÉE — le cadre est rendu, les prix restent à porter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
