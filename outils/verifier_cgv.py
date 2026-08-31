#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confronte les clauses porteuses des CGV au corpus de jurisprudence.

POURQUOI CE SCRIPT EXISTE. Les conditions de vente publiées en projet reposent
sur des articles de loi, et plusieurs de leurs clauses ne valent QUE ce que la
jurisprudence leur laisse valoir : une clause limitative peut être réputée non
écrite, une renonciation peut être privée d'effet, une clause de suspension peut
être jugée disproportionnée. Aucun de ces points ne se tranche en lisant le code
seul, et aucun ne doit être tranché de mémoire — un texte inventé est
parfaitement crédible, et c'est exactement le risque que `librejustice.py` a été
écrit pour supprimer.

CE QU'IL NE FAIT PAS. Il ne rend AUCUN verdict. Il rapporte ce que le corpus
répond, décision par décision, avec sa référence et son adresse, pour que la
relecture parte de sources et non d'impressions. Les aperçus rendus par la
recherche ne sont pas la position de la cour — ils sont marqués comme tels par
le module — et il faut ouvrir la décision pour savoir ce qu'elle juge.

CE QU'IL FAIT QUAND LE CORPUS NE RÉPOND PAS. Il le DIT, et il sort en erreur.
Un contrôle silencieux sur un sujet de validité serait pire que pas de contrôle,
parce qu'il rassurerait : « aucune décision trouvée » et « je n'ai pas pu
chercher » sont deux phrases opposées, et les confondre est la faute que ce
dépôt refuse partout ailleurs.

Usage :  python3 outils/verifier_cgv.py            (tous les points)
         python3 outils/verifier_cgv.py retractation plafond
         LIBREJUSTICE_TOKEN=… python3 outils/verifier_cgv.py

À lancer d'un réseau qui joint librejustice.fr. Le mandataire sortant de
certains environnements d'assistance refuse cet hôte (403 sur CONNECT) : le
script le nomme alors au lieu de rendre une liste vide.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import librejustice  # noqa: E402


# ── LA GRILLE ─────────────────────────────────────────────────────────────
# Une entrée par clause dont la validité, et non la rédaction, est en jeu.
# `article` situe la clause dans le projet ; `ancrage` dit sur quel texte elle
# s'appuie ; `question` est ce qu'on demande au corpus, en français, tel qu'un
# juriste le demanderait.
POINTS = [
    {
        "cle": "retractation",
        "article": "Article 5 — renonciation au droit de rétractation",
        "ancrage": "code de la consommation, art. L221-3, L221-25 et L221-28, 13°",
        "enjeu": "LE POINT LE PLUS EXPOSÉ, ET IL N'A PLUS DE FILET. Le 13° "
                 "vise un CONTENU numérique, le 1° un service PLEINEMENT "
                 "EXÉCUTÉ ; un accès à durée indéterminée fourni de manière "
                 "continue n'entre parfaitement dans ni l'un ni l'autre. Le "
                 "remboursement commercial de quatorze jours ayant été "
                 "expressément écarté, aucune autre clause n'absorbe le coup "
                 "si la qualification tombe. À traiter en premier.",
        "question": "renonciation au droit de rétractation contenu numérique "
                    "service fourni en ligne exécution immédiate consentement "
                    "préalable exprès article L221-28",
    },
    {
        "cle": "plafond",
        "article": "Article 10 — plafond de responsabilité entre professionnels",
        "ancrage": "code civil, art. 1170 ; code de commerce, art. L442-1",
        "enjeu": "Une clause limitative qui contredit la portée de "
                 "l'obligation essentielle est réputée non écrite. Le plafond "
                 "retenu doit rester au-dessus de cette limite.",
        "question": "clause limitative de responsabilité réputée non écrite "
                    "obligation essentielle du débiteur prestataire informatique",
    },
    {
        "cle": "adhesion",
        "article": "Articles 8 à 11 — contrat d'adhésion",
        "ancrage": "code civil, art. 1110, 1171 et 1190",
        "enjeu": "Des conditions non négociables sont un contrat d'adhésion : "
                 "une clause créant un déséquilibre significatif y est réputée "
                 "non écrite, y compris entre professionnels.",
        "question": "contrat d'adhésion clause créant un déséquilibre "
                    "significatif réputée non écrite article 1171 code civil",
    },
    {
        "cle": "abusives",
        "article": "Articles 7, 9 et 14 — suspension, non-remboursement, modification",
        "ancrage": "code civil, art. 1171 ; code de commerce, art. L442-1",
        "enjeu": "La vente étant réservée aux professionnels, ces clauses ne "
                 "s'apprécient plus sous R212-1 mais sous le déséquilibre "
                 "significatif. LE PLUS EXPOSÉ DES TROIS : encaisser pour une "
                 "durée indéterminée puis fermer avec trois mois de préavis et "
                 "sans contrepartie.",
        "question": "clause abusive contrat de service en ligne suspension du "
                    "compte modification unilatérale des conditions absence de "
                    "remboursement consommateur",
    },
    {
        "cle": "competence",
        "article": "Article 15 — juridiction",
        "ancrage": "code de la consommation, art. R212-2 ; code de procédure civile",
        "enjeu": "L'attribution aux tribunaux de Paris est désormais stipulée, "
                 "la vente étant réservée aux professionnels. Tient-elle face à "
                 "un acheteur relevant de l'art. L221-3 ?",
        "question": "clause attributive de compétence inopposable au "
                    "consommateur contrat conclu en ligne",
    },
    {
        "cle": "disponibilite",
        "article": "Article 7 — obligation de moyens sur la disponibilité",
        "ancrage": "code civil, art. 1197 et 1231-1",
        "enjeu": "Qualifier l'obligation de moyens ne s'impose pas au juge : "
                 "la qualification retenue dépend de ce que le prestataire "
                 "promet par ailleurs.",
        "question": "obligation de moyens ou de résultat disponibilité d'un "
                    "service en ligne hébergement prestataire informatique",
    },
    {
        "cle": "extraction",
        "article": "Article 8 — interdiction d'extraction systématique",
        "ancrage": "code de la propriété intellectuelle, art. L342-1",
        "enjeu": "L'interdiction ne vaut que si le producteur justifie d'un "
                 "investissement substantiel dans la base.",
        "question": "droit du producteur de base de données extraction "
                    "réutilisation substantielle investissement article L342-1",
    },
    {
        "cle": "garantie",
        "article": "Article 6 — garantie légale de conformité du numérique",
        "ancrage": "code de la consommation, art. L224-25-12 et suivants",
        "enjeu": "Ne joue plus que pour l'acheteur relevant de l'art. L221-3 "
                 "— cinq salariés ou moins, objet hors activité principale. "
                 "Régime récent (2021) : la jurisprudence est encore rare, et "
                 "une liste vide ici est une RÉPONSE, pas un échec.",
        "question": "garantie légale de conformité contenu numérique service "
                    "numérique mise en conformité réduction du prix résolution",
    },
]


def _ligne(c=" "):
    return c * 78


def _rendre(point, res):
    print()
    print(_ligne("─"))
    print("  %s" % point["article"])
    print("  Ancrage : %s" % point["ancrage"])
    print("  Enjeu   : %s" % point["enjeu"])
    print("  Requête : %s" % res["requete"])
    print(_ligne("─"))
    if not res["ok"]:
        print("  ⛔ CORPUS INJOIGNABLE — %s" % res["motif"])
        print("     Ce point n'a PAS été vérifié. Ne pas le lire comme un feu vert.")
        return False
    if not res["decisions"]:
        print("  ○ Aucune décision dans le corpus pour cette question.")
        print("     C'est une réponse : le corpus a répondu et n'a rien. Sur un")
        print("     texte récent, c'est attendu ; cela ne valide pas la clause.")
        return True
    for d in res["decisions"]:
        print()
        print("  • %s" % (d.get("titre") or "(sans intitulé)"))
        situe = " · ".join(x for x in (d.get("juridiction"), d.get("chambre"),
                                       d.get("date"), d.get("numero")) if x)
        if situe:
            print("    %s" % situe)
        etat = " · ".join(x for x in (d.get("publication"), d.get("sort")) if x)
        if etat:
            print("    portée : %s" % etat)
        if d.get("url"):
            print("    %s" % d["url"])
        apercu = (d.get("apercu") or "").strip().replace("\n", " ")
        if apercu:
            print("    aperçu (NON CITABLE, ouvrir la décision) : %s"
                  % (apercu[:220] + ("…" if len(apercu) > 220 else "")))
    return True


def main(argv):
    demandes = [a.strip().lower() for a in argv[1:] if a.strip()]
    points = [p for p in POINTS if not demandes or p["cle"] in demandes]
    if not points:
        print("Aucun point ne correspond à %s." % ", ".join(demandes))
        print("Points connus : %s" % ", ".join(p["cle"] for p in POINTS))
        return 2

    print(_ligne("═"))
    print("  CONDITIONS DE VENTE — confrontation au corpus de jurisprudence")
    print("  %s" % librejustice.ENDPOINT)
    print(_ligne("═"))

    # LE CORPUS D'ABORD. Interroger huit fois un serveur absent produirait huit
    # messages identiques et laisserait croire à huit contrôles.
    dispo = librejustice.disponible()
    if not dispo.get("ok"):
        print()
        print("  ⛔ Corpus injoignable : %s" % dispo.get("motif") or "?")
        print()
        print("  AUCUN POINT N'A ÉTÉ VÉRIFIÉ. Ce n'est pas un résultat : c'est")
        print("  l'absence de résultat, et il ne faut pas la lire autrement.")
        print("  · si le refus vient d'un mandataire sortant (403 sur CONNECT),")
        print("    relancez depuis un réseau qui joint %s ;" % librejustice.ENDPOINT)
        print("  · si le serveur exige un jeton, posez LIBREJUSTICE_TOKEN.")
        return 1

    manques = 0
    for p in points:
        res = librejustice.rechercher(p["question"], limite=5)
        if not _rendre(p, res):
            manques += 1

    print()
    print(_ligne("═"))
    print("  %d point(s) confrontés, %d non vérifiés." % (len(points), manques))
    print("  RIEN ICI N'EST UN VERDICT. Une décision ne vaut que par sa portée :")
    print("  vérifiez la formation, la publication et le sort en appel ou en")
    print("  cassation avant de vous en prévaloir.")
    print("  %s" % librejustice.MENTION)
    print(_ligne("═"))
    return 1 if manques else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
