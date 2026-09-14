# -*- coding: utf-8 -*-
"""Le pont pièce → livrable couvre les ONZE pièces, et la DPGF ne se chiffre pas.

DEUX DÉFAUTS, ET LE SECOND EST LE GRAVE.

LE PREMIER : LE PONT ÉTAIT INCOMPLET, ET RIEN NE LE MESURAIT. `_AO_REDACTION`
comptait sept entrées quand onze pièces ont la voie « rédiger » ou
« compléter ». Les quatre orphelines — mémoire technique, DPGF, autonomie
commerciale, convention de groupement — se rédigeaient quand même, puisque
l'atelier lit `ao_dc.voie()` et non cette table, mais le plan n'offrait aucun
document où déposer le brouillon. L'écart avait tenu des mois parce qu'aucune
règle ne comparait les deux ensembles ; la première règle de ce fichier le
fait, dans les deux sens.

LE SECOND : LE CONTEXTE CONTREDISAIT LA CONSIGNE, ET L'ARBITRAGE ÉTAIT LAISSÉ
AU MODÈLE. Le brief interdit d'écrire un prix qui ne figure pas au contexte.
Or, pour la DPGF, ce même contexte porte — mot pour mot, depuis le référentiel
— « Un prix pour chaque ligne du modèle fourni par l'acheteur, sans ligne
laissée à zéro ou vide ». C'est l'ordre d'inventer des montants, servi juste
après l'interdiction de le faire. Un modèle tranche ; nous ne saurions pas
comment, parce qu'un tableau de prix vraisemblable ne se distingue pas d'un
tableau juste à la relecture. La consigne « imprimé à chiffrer » tranche à sa
place, et les règles ci-dessous vérifient qu'elle part pour la DPGF, qu'elle
ne part QUE pour elle, et que la contradiction qu'elle lève existe encore —
faute de quoi la règle deviendrait vraie sans rien protéger.

CE QUE CES RÈGLES NE PEUVENT PAS FAIRE. Elles mesurent ce qui PART chez le
fournisseur, jamais ce qui en revient : `tests/` n'ouvre aucune socket. La
réponse, elle, se mesure dans `outils/recette_redaction_dpgf.py`, qui fait un
vrai appel et relève tout ce qui ressemble à un montant. La dernière règle de
ce fichier éprouve ce détecteur-là — un chercheur de prix qui ne trouve rien
rendrait la recette verte et inutile.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import ao_dc as A                                               # noqa: E402
import ao_redaction as R                                        # noqa: E402
import app as APP                                               # noqa: E402
import livrables                                                # noqa: E402

sys.path.insert(0, os.path.join(ICI, "outils"))
import recette_redaction_dpgf as RECETTE                         # noqa: E402

from conftest import ORIGINE                                     # noqa: E402


def _remplissage():
    return A.remplir(None)


def _redigeables():
    return {p["cle"]: p for p in R.pieces_redigeables(_remplissage())}


def _brief(cle):
    p = _redigeables()[cle]
    return R.brief(R.contexte(_remplissage(), None, p, socle=None,
                              dossier=None))


# --------------------------------------------------------------------------
# 1. LE PONT EST COMPLET, DANS LES DEUX SENS.
# --------------------------------------------------------------------------
def test_le_pont_couvre_exactement_les_pieces_que_l_atelier_accepte():
    """L'ensemble des clés du pont EST celui que `pieces_redigeables` retient.

    LES DEUX SENS COMPTENT, ET POUR DES RAISONS OPPOSÉES. Une pièce rédigeable
    sans pont : l'atelier produit un brouillon que le plan n'offre nulle part
    où déposer — c'est le défaut corrigé. Un pont sans pièce rédigeable : la
    page affiche un bouton sous une pièce que l'atelier refusera, et le refus
    n'arrive qu'après le clic.
    """
    atelier = set(_redigeables())
    pont = set(APP._AO_REDACTION)
    assert atelier == pont, (
        "sans pont : %r — pont orphelin : %r"
        % (sorted(atelier - pont), sorted(pont - atelier)))
    # LE TÉMOIN. Une barrière qui n'accepterait plus rien rendrait l'égalité
    # ci-dessus vraie et vide.
    assert len(atelier) == 11, len(atelier)


def test_chaque_pont_mene_a_un_livrable_qui_existe_et_lui_est_propre():
    """Un identifiant mort ouvrirait une page vide ; un identifiant partagé
    ferait ouvrir la note d'équipe en cliquant sur le mémoire technique."""
    vus = {}
    for cle, tid in APP._AO_REDACTION.items():
        assert livrables.get_type(tid), (
            "%s pointe vers le livrable %r, qui n'existe pas" % (cle, tid))
        assert tid not in vus, (
            "%s et %s ouvrent le même livrable %r" % (vus[tid], cle, tid))
        vus[tid] = cle


def _mots(txt):
    return {w for w in re.findall(r"[a-zàâçéèêëîïôûùüÿœ]{5,}",
                                  (txt or "").lower())}


def test_chaque_livrable_parle_de_SA_piece_et_pas_d_une_autre():
    """Le livrable porte le vocabulaire PROPRE à sa pièce.

    LA MESURE, ET POURQUOI ELLE N'EST PAS UNE PRÉSENCE DE MOT. On calcule le
    vocabulaire que chaque pièce ne partage avec AUCUNE autre — « métrologie »
    pour les moyens, « acomptes » pour la DPGF, « concertation » pour
    l'autonomie commerciale — et l'on exige que le livrable en reprenne au
    moins un. Un jeu de sections recopié d'une pièce voisine, ou rédigé en
    généralités qui conviendraient à n'importe quelle note, ne porte aucun de
    ces mots et tombe. Chercher un mot choisi d'avance, au contraire, serait
    vert le jour où l'on collerait ce mot dans une section creuse.
    """
    pieces = _redigeables()
    voc = {c: _mots(pieces[c]["nom"] + " "
                    + " ".join(pieces[c].get("contient") or []))
           for c in APP._AO_REDACTION}
    partage = set()
    for c, v in voc.items():
        for d, w in voc.items():
            if c != d:
                partage |= (v & w)
    for cle, tid in sorted(APP._AO_REDACTION.items()):
        t = livrables.get_type(tid)
        propres = voc[cle] - partage
        assert propres, (
            "%s n'a aucun vocabulaire propre : la règle ne mesure rien pour "
            "elle" % cle)
        # LES SECTIONS SONT MESURÉES À PART DU LIBELLÉ, et c'est une mutation
        # qui l'a imposé : remplacées par « Contexte de la mission /
        # Organisation proposée / Moyens mis en œuvre », les sections du cadre
        # de DPGF ont survécu — le libellé et le résumé, intacts, portaient
        # encore le vocabulaire propre et suffisaient à la règle. Or ce sont
        # les SECTIONS que la rédaction suit : un livrable au bon nom et au
        # plan générique produit un document générique.
        sections = _mots(" ".join(t["sections"]))
        assert propres & sections, (
            "les sections du livrable %r ne reprennent aucun des termes "
            "propres à %s (%r) : ce plan conviendrait à n'importe quelle "
            "pièce" % (tid, cle, sorted(propres)[:8]))
        assert propres & _mots(t["label"] + " " + t["desc"]), (
            "le libellé et le résumé de %r ne disent pas de quelle pièce il "
            "s'agit" % tid)


# --------------------------------------------------------------------------
# 2. CHAQUE DOSSIER PORTE SES PROPRES PONTS.
# --------------------------------------------------------------------------
def test_le_plan_de_candidature_ne_porte_que_les_ponts_de_candidature(marche):
    """Un mémoire technique affiché sous le dossier de candidature se
    préparerait pour la mauvaise remise : les deux dossiers ne partent ni au
    même moment ni, souvent, sur la même plateforme."""
    j = marche.post("/api/datacenter/marche/candidature", json={},
                    headers=ORIGINE).get_json()
    cand = {p["cle"] for p in A.DOSSIER_CANDIDATURE}
    ponts = j["plan"]["redaction"]
    assert ponts
    for r in ponts:
        assert r["piece"] in cand, r["piece"]
    assert {r["piece"] for r in ponts} == {
        c for c in APP._AO_REDACTION if c in cand}


def test_le_dossier_d_offre_porte_les_siens(marche):
    """Sans eux, les deux pièces rédigeables de l'offre n'ont aucun document
    où le brouillon se dépose — c'est exactement l'état d'avant."""
    j = marche.post("/api/datacenter/marche/candidature", json={},
                    headers=ORIGINE).get_json()
    offre = {p["cle"] for p in A.DOSSIER_OFFRE}
    ponts = j["dossier_offre"]["redaction"]
    assert {r["piece"] for r in ponts} == {
        c for c in APP._AO_REDACTION if c in offre}
    assert {r["piece"] for r in ponts} == {"memoire_technique", "dpgf"}
    for r in ponts:
        assert r["type"] and r["label"], r
    # ET LES DEUX LISTES NE SE RECOUVRENT PAS : une pièce affichée sous les
    # deux dossiers se préparerait deux fois, ou pas du tout.
    assert not ({r["piece"] for r in ponts}
                & {r["piece"] for r in j["plan"]["redaction"]})


# --------------------------------------------------------------------------
# 3. LA CONSIGNE ENVOYÉE AU MODÈLE.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("cle,attendu", [
    ("moyens", "du dossier de candidature"),
    ("memoire_technique", "du dossier d'offre"),
    ("dpgf", "du dossier d'offre"),
])
def test_le_brief_nomme_le_dossier_auquel_la_piece_appartient(cle, attendu):
    """« Pièce de candidature » servi pour un mémoire technique oriente le
    modèle vers ce qui prouve QUI NOUS SOMMES, quand l'offre démontre CE QUE
    NOUS PROPOSONS. Deux documents différents, et la note technique est celle
    sur laquelle se joue le marché."""
    tete = _brief(cle).splitlines()[0]
    assert attendu in tete, (cle, tete)


def test_la_consigne_de_ne_pas_chiffrer_part_pour_la_voie_completer_ET_ELLE_SEULE():
    """La correspondance est mesurée sur les ONZE pièces, pas affirmée sur
    une.

    LES DEUX ERREURS SE VALENT. Absente pour la DPGF, le modèle arbitre seul
    entre « n'inventez aucun prix » et « aucune ligne vide ». Présente pour une
    note de moyens, elle apprend au modèle à voir des montants là où il n'y en
    a pas, et à truffer une note de prose de crochets « à compléter ».
    """
    pieces = _redigeables()
    porte = {c for c in pieces if "IMPRIMÉ À CHIFFRER" in _brief(c)}
    completer = {c for c, p in pieces.items() if p["voie"] == "completer"}
    assert porte == completer, (
        "consigne servie à %r, voie « compléter » sur %r"
        % (sorted(porte), sorted(completer)))
    assert completer, "aucune pièce de voie « compléter » : la règle est vide"
    assert len(pieces) > len(completer), (
        "toutes les pièces sont de voie « compléter » : le témoin négatif "
        "n'existe plus")


def test_la_consigne_repond_a_la_contradiction_QUE_LE_CONTEXTE_PORTE_ENCORE():
    """LA RÈGLE QUI EMPÊCHE LES AUTRES DE DEVENIR CREUSES.

    La consigne « imprimé à chiffrer » n'a de raison d'être que parce que le
    contexte de la DPGF ordonne, lui, de ne laisser aucune ligne vide. Si
    quelqu'un retirait un jour cette exigence du référentiel, la consigne
    resterait verte partout en ne protégeant plus de rien — et personne ne le
    saurait. Cette règle mesure donc les DEUX moitiés : que la contradiction
    est toujours servie au modèle, et que la consigne la tranche en nommant ce
    qui reste à compléter.
    """
    dpgf = _redigeables()["dpgf"]
    exigences = " ".join(dpgf.get("contient") or []).lower()
    assert "vide" in exigences or "zéro" in exigences, (
        "le contexte de la DPGF n'ordonne plus de remplir chaque ligne : la "
        "consigne « imprimé à chiffrer » ne lève plus aucune contradiction, "
        "et sa présence n'est plus mesurable comme une protection\n%s"
        % exigences)
    b = _brief("dpgf")
    i = b.index("IMPRIMÉ À CHIFFRER")
    bloc = b[i:i + 900]
    assert "DÉPOSÉ" in bloc, (
        "la consigne ne distingue pas le document déposé du brouillon : elle "
        "contredit le contexte au lieu de le situer")
    assert R._A_COMPLETER in bloc, (
        "la consigne n'indique pas sous quelle forme laisser les montants")
    for mot in ("montant", "quantité", "taux"):
        assert mot in bloc.lower(), (
            "la consigne ne nomme pas « %s » : une seule des trois formes de "
            "chiffre serait couverte" % mot)


# --------------------------------------------------------------------------
# 4. LE DÉTECTEUR DE LA RECETTE.
# --------------------------------------------------------------------------
# UNE RECETTE QUI NE TROUVE JAMAIS RIEN EST PIRE QUE PAS DE RECETTE : elle
# rend un verdict vert sur un brouillon qu'elle n'a pas su lire. Le détecteur
# s'éprouve donc ici, sur des montants écrits comme ils le seraient vraiment.
MONTANTS_VRAIS = [
    "| Poste 1 | Étude d'avant-projet | 12 500 € |",
    "Total du lot : 1 250,00 EUR",
    "Le forfait s'élève à 3 200 euros pour cette phase.",
    "| 2.1 | Mission SSI | 980.50 TTC |",
    "Prix : 45 000",
    "Montant forfaitaire = 7 800,00 HT",
]
SANS_MONTANT = [
    "| Poste 1 | Étude d'avant-projet | [À COMPLÉTER : prix, depuis votre "
    "chiffrage] |",
    "## Postes attendus et mode de décomposition",
    "Correspondance ligne à ligne avec l'article 4.2 du CCTP.",
    "Unité imposée par le modèle : forfait.",
    "Les acomptes se règlent sur la base de cette répartition.",
]


@pytest.mark.parametrize("ligne", MONTANTS_VRAIS)
def test_le_detecteur_de_la_recette_voit_un_montant_ecrit_comme_on_les_ecrit(ligne):
    assert RECETTE._lignes_suspectes(ligne), ligne


@pytest.mark.parametrize("ligne", SANS_MONTANT)
def test_le_detecteur_ne_crie_pas_sur_un_cadre_sans_prix(ligne):
    """Un détecteur qui relève tout ferait échouer la recette sur un brouillon
    correct, et l'on prendrait l'habitude de passer outre — ce qui revient à
    ne plus la lire."""
    assert not RECETTE._lignes_suspectes(ligne), (
        ligne, RECETTE._lignes_suspectes(ligne))


def test_la_recette_refuse_de_rendre_un_verdict_sans_cle():
    """Sans clé, elle ne doit surtout pas rendre « passée » : un verdict vert
    obtenu sans appel est le pire des deux résultats possibles."""
    avant = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        assert RECETTE.main() == 2
    finally:
        if avant is not None:
            os.environ["ANTHROPIC_API_KEY"] = avant


# --------------------------------------------------------------------------
# 5. LA CARTE D'OFFRE, EXÉCUTÉE.
# --------------------------------------------------------------------------
# UN PONT QUE LA PAGE N'AFFICHE PAS NE SERT À RIEN, et c'est exactement l'état
# qu'on vient de quitter : l'atelier acceptait la DPGF et le mémoire technique,
# le serveur sait maintenant quel livrable les reçoit — mais `offreRendre` ne
# lisait pas `redaction`, et aucune carte d'offre ne portait de bouton. Ces
# règles exécutent le rendu ; lire `o.redaction` dans le fichier dirait qu'une
# ligne existe, pas qu'un bouton s'affiche sous la bonne pièce.
import html as _html                                             # noqa: E402
import json as _json                                             # noqa: E402
import subprocess as _sub                                        # noqa: E402

from test_ao_formulaires import _js_source                        # noqa: E402


def _offre_rendue(offre):
    prog = (_js_source("esc", "info", "aoExigence", "offreRendre")
            + "\nvar CADRE = { glossaire: {} };"
            + "\nvar zone = { innerHTML: '' };"
            + "\nfunction $(s){ return s === '#ig-ao-offre-out' "
              "? zone : null; }"
            + "\noffreRendre(JSON.parse(process.env.OFFRE));"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    out = _sub.run(["node"], input=prog, capture_output=True, text=True,
                   timeout=60,
                   env=dict(os.environ, OFFRE=_json.dumps(offre)))
    assert out.returncode == 0, out.stderr[-2000:]
    return _html.unescape(out.stdout)


def _offre_avec_ponts():
    o = A.offre()
    dossiers = APP._ao_dossiers_des_pieces()
    o["redaction"] = [
        {"piece": c, "type": t,
         "label": (livrables.get_type(t) or {}).get("label")}
        for c, t in APP._AO_REDACTION.items() if dossiers.get(c) == "offre"]
    return o


def test_les_pieces_d_offre_redigeables_portent_leur_bouton():
    """Et elles seules : l'acte d'engagement et le DC4 se remplissent sur leur
    cerfa ; un bouton « mettre en brouillon » sous eux proposerait de générer
    un formulaire officiel sur des faits que personne n'a vérifiés."""
    o = _offre_avec_ponts()
    h = _offre_rendue(o)
    boutons = set(re.findall(r'data-rediger="([^"]+)"', h))
    assert boutons == {"memoire_technique", "dpgf"}, boutons
    # ET CHAQUE BOUTON A SA ZONE DE SORTIE : sans elle le clic ne fait rien,
    # le gestionnaire s'arrête sur `if (!z) return`.
    assert set(re.findall(r'data-redout="([^"]+)"', h)) == boutons


def _phrases_par_piece(h):
    """La phrase et le bouton de CHAQUE bloc de rédaction, appariés dans leur
    propre bloc.

    LA PREMIÈRE VERSION DE CES RÈGLES CHERCHAIT « la phrase, puis plus loin le
    bouton » sur la page entière : avec `re.S`, elle appariait la phrase de la
    DPGF au bouton du mémoire technique — et la règle du mémoire lisait donc
    le texte de sa voisine. Une expression qui traverse les cartes ne mesure
    pas la carte qu'elle nomme.
    """
    out = {}
    for bloc in re.findall(r'<div class="ig-ao-red">(.*?)</div>\s*</div>',
                           h, re.S):
        m = re.search(r'data-rediger="([^"]+)"', bloc)
        t = re.search(r"<span>(.*?)</span>", bloc, re.S)
        if m and t:
            out[m.group(1)] = t.group(1)
    return out


def test_la_carte_de_la_DPGF_dit_que_les_prix_restent_a_porter():
    """LA PHRASE EST LE SEUL ENDROIT OÙ L'OPÉRATEUR L'APPREND AVANT DE
    CLIQUER. « Cette note se rédige », servi ici, ferait attendre une DPGF
    finie — et l'écart entre ce qui est promis et ce qui sort ne se
    découvrirait qu'après une minute d'attente, sur un document qu'on croit
    prêt à déposer."""
    phrases = _phrases_par_piece(_offre_rendue(_offre_avec_ponts()))
    assert "dpgf" in phrases, (
        "la carte de la DPGF ne porte aucune phrase avec son bouton", phrases)
    phrase = phrases["dpgf"]
    assert "prix restent à porter" in phrase, phrase
    assert "chiffrage" in phrase, phrase
    assert "note se rédige" not in phrase, (
        "la DPGF est annoncée comme une note à rédiger", phrase)


def test_la_carte_du_memoire_technique_reste_annoncee_comme_une_note():
    """Le témoin de la règle précédente : si la phrase « prix » s'affichait
    partout, elle ne dirait plus rien de la DPGF."""
    phrases = _phrases_par_piece(_offre_rendue(_offre_avec_ponts()))
    assert "memoire_technique" in phrases, phrases
    phrase = phrases["memoire_technique"]
    assert "note se rédige" in phrase, phrase
    assert "prix" not in phrase, phrase


def test_une_offre_sans_ponts_n_affiche_aucun_bouton():
    """Le serveur peut ne pas en envoyer — une version plus ancienne, une
    erreur de composition. La carte doit alors se dessiner entière, sans
    bouton mort ni trou."""
    o = A.offre()
    o.pop("redaction", None)
    h = _offre_rendue(o)
    assert "data-rediger=" not in h
    # `ig-ao-cp` EST UN PRÉFIXE DE `ig-ao-cph`, l'en-tête interne de chaque
    # carte : compter la chaîne nue rendait huit cartes pour quatre pièces.
    assert len(re.findall(r'class="ig-ao-cp[ "]', h)) == len(o["pieces"])
