# -*- coding: utf-8 -*-
"""La substance du site est ATTEINTE par au moins un parcours.

CE QUE LES RÈGLES EXISTANTES MESURAIENT, ET CE QU'ELLES NE VOYAIENT PAS. Cinq
fichiers d'essais gardent déjà les parcours : que chaque étape mène à une page
qui existe, qu'aucune ne soit visée deux fois, que chacune dise quoi faire, ce
qu'on gagne et le piège, que la liste des pages réservées ne mente pas. Toutes
mesurent la VALIDITÉ de ce qui est écrit. Aucune ne mesurait la COUVERTURE de
ce qui ne l'est pas.

LE RELEVÉ DU 4 SEPTEMBRE 2026 : dix-neuf parcours, quatre-vingt-dix-huit
étapes, aucune cassée — et QUINZE pages ouvertes qu'aucun parcours ne visitait.
Parmi elles, l'assistant (la voie la plus courte pour qui ne sait pas quoi
chercher), la checklist des vingt-sept points, le guide d'intégration, les
tendances de supervision, les services, les ressources. Rien ne plantait ; la
substance était simplement inatteignable autrement qu'en la cherchant.

ET UN PARCOURS SUR DIX-NEUF SE TERMINAIT PAR UN GESTE. Les dix-huit autres
s'arrêtaient sur une page de contenu — sept étapes, puis le bandeau s'éteint et
rien n'est proposé. Un chemin de lecture qui ne mène nulle part n'est pas un
parcours, c'est un sommaire dans l'ordre.

LA RÈGLE ÉNUMÈRE, ELLE NE NOMME PAS ce qu'il faut couvrir : elle part des pages
du site, en retire celles qui sont explicitement déclarées HORS PARCOURS avec
leur raison, et exige que tout le reste soit atteint. Une page ajoutée demain
tombe dans le filet le jour même — c'est la seule façon que le même écart ne se
reforme pas.
"""
import json
import os
import subprocess
import sys

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)


# ══════════════════════════════════════════════════════════════════════════
# Ce qui n'a pas à être dans un parcours — et pourquoi, page par page
# ══════════════════════════════════════════════════════════════════════════
# Ce ne sont pas des exemptions de confort : chacune porte sa raison, et la
# raison est lisible. Une page qu'on voudrait exempter sans savoir dire
# pourquoi est une page qui devrait être dans un parcours.
HORS_PARCOURS = {
    "/": "L'accueil est le point de DÉPART de tout parcours — l'y faire "
         "figurer comme étape reviendrait à demander au lecteur de revenir "
         "d'où il vient.",
    "/about": "Qui est CONSEILPREV ne fait avancer aucun travail : c'est une "
              "page de confiance, lue avant ou après, jamais pendant.",
    "/acces": "Ce qu'ouvre un compte et à quel prix — une page de décision "
              "commerciale, pas une étape de méthode.",
    "/cgv": "Conditions générales de vente : obligation d'affichage avant "
            "l'achat, et pièce contractuelle — ni méthode ni contenu qu'un "
            "chemin de lecture aurait à traverser.",
    "/mentions-legales": "Identité de l'éditeur et de l'hébergeur : obligation "
                         "d'affichage, lue quand on la cherche et jamais dans "
                         "un ordre imposé.",
    "/politique-confidentialite": "Obligation d'affichage. L'enfermer dans un "
                                  "parcours reviendrait à demander un chemin "
                                  "pour lire ses propres droits.",
    "/connecter": "Écran d'authentification : il ouvre l'accès, il ne le "
                  "documente pas — un parcours qui y ferait étape confondrait "
                  "la porte et ce qu'elle dessert.",
    "/faq": "Consultée par question, jamais dans l'ordre : un parcours "
            "imposerait une séquence à ce qui se lit par entrée.",
}


def _catalogue():
    """Les parcours, lus dans le VRAI module — jamais recopiés ici."""
    programme = (
        "var m = require('%s/parcours.js');"
        "process.stdout.write(JSON.stringify({p: m.PARCOURS, s: m.SECTEURS}));"
        % RACINE)
    out = subprocess.run(["node", "-e", programme],
                         capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        pytest.skip("node absent ou module illisible : %s" % out.stderr[:200])
    d = json.loads(out.stdout)
    return d["p"] + d["s"]


CATALOGUE = _catalogue()
VISITEES = set(e["url"] for p in CATALOGUE for e in p["etapes"])


def _pages():
    import app
    return dict(app.PAGES)


def test_le_releve_lit_bien_le_catalogue():
    """Garde-fou : une lecture cassée rendrait toutes les règles suivantes
    vertes en ne mesurant rien — le défaut que ce dépôt a déjà commis."""
    assert len(CATALOGUE) >= 19, "catalogue suspect : %d parcours" % len(CATALOGUE)
    assert len(VISITEES) >= 40, "relevé suspect : %d pages visitées" % len(VISITEES)


def test_toute_page_de_fond_est_atteinte_par_au_moins_un_parcours():
    """Le cœur de cette règle. Une page qui n'est dans aucun parcours n'est
    atteignable qu'en la cherchant — et on ne cherche que ce dont on sait
    déjà l'existence."""
    pages = _pages()
    orphelines = sorted(p for p in pages
                        if p not in VISITEES and p not in HORS_PARCOURS)
    assert not orphelines, (
        "ces pages ne sont visitées par AUCUN parcours : %s. Soit elles ont "
        "leur place dans un parcours — c'est le cas le plus fréquent —, soit "
        "elles rejoignent HORS_PARCOURS avec la raison qui les en dispense."
        % ", ".join(orphelines))


def test_les_exemptions_designent_des_pages_qui_existent():
    """Une exemption qui ne désigne plus rien est une exemption qui a survécu
    à sa page : elle ne protège plus rien et cache le compte réel."""
    pages = _pages()
    fantomes = sorted(p for p in HORS_PARCOURS if p not in pages)
    assert not fantomes, (
        "HORS_PARCOURS dispense des pages qui n'existent plus : %s"
        % ", ".join(fantomes))


def test_aucune_exemption_ne_dispense_une_page_deja_couverte():
    """Une page à la fois exemptée ET visitée signale une décision qui a
    changé sans que l'exemption suive. La laisser masque le vrai périmètre de
    ce qu'on s'autorise à ne pas couvrir."""
    doublons = sorted(p for p in HORS_PARCOURS if p in VISITEES)
    assert not doublons, (
        "ces pages sont dispensées de parcours et pourtant visitées : %s — "
        "retirer l'exemption devenue fausse." % ", ".join(doublons))


def test_chaque_exemption_porte_une_raison_lisible():
    """Une exemption sans motif est une exemption qu'on ne pourra pas
    contester dans six mois : elle deviendra un fait acquis."""
    courtes = sorted(p for p, r in HORS_PARCOURS.items() if len(r) < 40)
    assert not courtes, (
        "ces exemptions n'expliquent pas ce qu'elles dispensent : %s"
        % ", ".join(courtes))


# ══════════════════════════════════════════════════════════════════════════
# Tout parcours se termine par un geste
# ══════════════════════════════════════════════════════════════════════════
CONCLUSIONS = {"/vos-projets", "/contact"}


@pytest.mark.parametrize("pid", [p["id"] for p in CATALOGUE])
def test_chaque_parcours_se_termine_par_un_geste(pid):
    """LE DÉFAUT QUE CETTE RÈGLE FIXE. Dix-huit parcours sur dix-neuf
    s'arrêtaient sur une page de contenu. Le lecteur suivait la séquence
    jusqu'au bout et rien ne lui était proposé — ni écrire, ni demander, ni
    revenir. La conclusion est désormais ajoutée par énumération dans le
    module ; cette règle vérifie que l'énumération n'a oublié personne."""
    p = [x for x in CATALOGUE if x["id"] == pid][0]
    derniere = p["etapes"][-1]["url"]
    assert derniere in CONCLUSIONS, (
        "le parcours %s se termine sur %s, qui n'est pas un geste. Un chemin "
        "de lecture qui ne mène nulle part est un sommaire dans l'ordre."
        % (pid, derniere))


@pytest.mark.parametrize("pid", [p["id"] for p in CATALOGUE])
def test_la_conclusion_n_apparait_qu_une_fois(pid):
    """Deux conclusions dans un même parcours feraient deux fois le même
    geste, et la seconde serait de trop. Le module s'en garde en ne
    concluant pas ce qui conclut déjà — la règle le mesure."""
    p = [x for x in CATALOGUE if x["id"] == pid][0]
    urls = [e["url"] for e in p["etapes"]]
    combien = sum(1 for u in urls if u in CONCLUSIONS)
    assert combien == 1, (
        "le parcours %s porte %d conclusions : %s" % (pid, combien, urls))


@pytest.mark.parametrize("pid", [p["id"] for p in CATALOGUE])
def test_un_parcours_compte_au_moins_quatre_etapes(pid):
    """Trois étapes dont une conclusion, ce sont deux pages et un bouton :
    l'ordre de lecture n'a alors rien à apprendre à personne. Le relevé du
    4 septembre 2026 en trouvait un à DEUX étapes."""
    p = [x for x in CATALOGUE if x["id"] == pid][0]
    assert len(p["etapes"]) >= 4, (
        "le parcours %s ne compte que %d étape(s) : ce n'est pas un chemin de "
        "lecture, c'est un lien." % (pid, len(p["etapes"])))
