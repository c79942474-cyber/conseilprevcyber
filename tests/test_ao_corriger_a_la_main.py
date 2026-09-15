# -*- coding: utf-8 -*-
"""« Analyser, vérifier, CORRIGER » — la troisième étape n'existait pas.

TROIS DÉFAUTS, ET LE TROISIÈME EXPLIQUE LES DEUX AUTRES.

1. LE MOTEUR IGNORAIT LES CORRECTIONS. `remplir()` ne lisait `saisies` que
   dans la branche des rubriques déclarées `source: "saisie"` — 27 sur 93.
   Une valeur tapée pour `dc1.candidat` (source « fiche ») ou `dc1.acheteur`
   (source « consultation ») était SILENCIEUSEMENT jetée. Un acheteur mal lu,
   un objet tronqué, un SIRET d'une autre filiale : le module affichait sa
   lecture, et rien ne permettait de la reprendre.

2. LA PAGE N'OFFRAIT DE CHAMP QUE SUR CES 27. Les 66 autres s'affichaient en
   texte mort — et 66 d'entre elles, sans valeur, n'affichaient RIEN : la
   ligne disait « à saisir » au-dessus du vide.

3. L'ATELIER TRAVAILLAIT SANS VOUS, ET SON TRAVAIL ÉTAIT JETÉ. `atelierLancer`
   envoyait `fiche`, `analyse` et `documents` — pas `saisies`. La route les
   lit pourtant, et recevait un dictionnaire vide : l'atelier repartait de
   zéro et déclarait incomplètes des pièces qu'on venait de compléter. Et au
   retour, `atelierBilan` écrivait un résumé dans un coin de page en JETANT le
   `remplissage` final et les onze `brouillons` que l'atelier avait produits.
   D'où « toutes les pièces ne sont pas produites automatiquement » : elles
   l'étaient, côté serveur, puis perdues au retour.

LA SEULE EXCEPTION EST LA DÉCLARATION, et c'est la doctrine du module : elle
affirme un fait dont la fausseté est sanctionnée pénalement, et se prend à la
main par une personne habilitée. Ni le moteur ni la page n'y écrivent.
"""
import io
import json
import os
import re
import subprocess

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import ao_dc as A                                                # noqa: E402

from test_ao_formulaires import _js_source                       # noqa: E402

FICHE = {"raison_sociale": "CONSEILPREV", "siret": "49453015700038"}


def _ligne(rap, piece, cle):
    p = next(x for x in rap["pieces"] if x["cle"] == piece)
    return next(x for x in p["rubriques"] if x["cle"] == cle)


def _toutes(rap):
    for p in rap["pieces"]:
        for l in p.get("rubriques") or []:
            yield p["cle"], l


# --------------------------------------------------------------------------
# 1. LE MOTEUR ACCEPTE LA CORRECTION, QUELLE QUE SOIT LA SOURCE.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("piece,cle,source", [
    ("dc1", "candidat", "fiche"),
    ("dc1", "acheteur", "consultation"),
])
def test_une_correction_l_emporte_sur_ce_que_le_moteur_avait_lu(piece, cle,
                                                                source):
    """C'est le cœur du correctif : jusqu'ici la valeur tapée disparaissait
    sans un mot."""
    ref = _ligne(A.remplir(fiche=FICHE), piece, cle)
    assert ref["source"] == source, (
        "la rubrique a changé de source : la règle ne mesure plus le cas "
        "qu'elle nomme")
    k = "%s.%s" % (piece, cle)
    l = _ligne(A.remplir(fiche=FICHE, saisies={k: "VALEUR CORRIGÉE"}),
               piece, cle)
    assert l["valeur"] == "VALEUR CORRIGÉE", l
    assert l["statut"] == "rempli", l
    assert l.get("corrige") is True, l
    # ET CE QUE LE MODULE AVAIT LU EST GARDÉ : sans lui, corriger efface la
    # lecture et l'on ne peut plus comparer ni revenir dessus.
    assert l.get("valeur_moteur") == (ref.get("valeur") or ""), l


def test_vider_le_champ_rend_la_lecture_du_moteur():
    """La correction se DÉFAIT. Une correction irréversible obligerait à
    retaper de mémoire ce que le module avait trouvé."""
    avant = _ligne(A.remplir(fiche=FICHE), "dc1", "candidat")
    apres = _ligne(A.remplir(fiche=FICHE, saisies={"dc1.candidat": "   "}),
                   "dc1", "candidat")
    assert apres["valeur"] == avant["valeur"]
    assert not apres.get("corrige")


def test_recopier_la_valeur_du_moteur_ne_compte_pas_pour_une_correction():
    """Sinon toute rubrique relue à l'identique se marquerait « corrigée », et
    la marque ne voudrait plus rien dire."""
    v = _ligne(A.remplir(fiche=FICHE), "dc1", "candidat")["valeur"]
    l = _ligne(A.remplir(fiche=FICHE, saisies={"dc1.candidat": v}),
               "dc1", "candidat")
    assert not l.get("corrige"), l


def _analyse_qui_diverge():
    """Deux pièces de la consultation qui ne disent PAS le même acheteur.

    LA PREMIÈRE VERSION DE CETTE RÈGLE ÉTAIT VIDE, et une mutation l'a montré :
    elle bouclait sur un remplissage construit SANS analyse, où aucune
    divergence n'existe. La boucle ne testait donc jamais rien, et supprimer
    le code qui tranche la divergence ne la faisait pas tomber. Il faut
    fabriquer le conflit pour pouvoir mesurer qu'il est tranché.
    """
    return A.analyser([
        {"nom": "01_RC.pdf", "extension": "pdf", "cote": "consultation",
         "texte": "Le pouvoir adjudicateur est la Commune de Sainte-Anne. "
                  "Le candidat produit le DC1 et le DC2."},
        {"nom": "02_CCAP.pdf", "extension": "pdf", "cote": "consultation",
         "texte": "Le pouvoir adjudicateur est la Communauté d'agglomération "
                  "du Levant. Les prestations sont réglées par le présent "
                  "cahier des clauses administratives particulières."},
    ])


def test_le_temoin_une_divergence_existe_bien_avant_correction():
    """Le témoin de la règle suivante. Sans conflit fabriqué, la règle qui
    vérifie qu'il est tranché est verte et vide — c'est ce qu'une mutation a
    prouvé sur sa première rédaction."""
    rap = A.remplir(fiche=FICHE, analyse=_analyse_qui_diverge())
    diverge = [(p, l["cle"]) for p, l in _toutes(rap)
               if l.get("divergences") or l.get("a_confirmer")]
    assert diverge, (
        "aucune divergence n'est produite par ce dossier : la règle suivante "
        "ne mesurerait rien")


def test_une_correction_tranche_la_divergence_qu_elle_remplace():
    """Une divergence ou un « à confirmer » porte sur la valeur qu'on vient de
    remplacer : la garder ferait signaler un conflit déjà tranché."""
    an = _analyse_qui_diverge()
    avant = A.remplir(fiche=FICHE, analyse=an)
    cibles = [(p, l["cle"]) for p, l in _toutes(avant)
              if l.get("divergences") or l.get("a_confirmer")]
    assert cibles, "le témoin a disparu"
    rap = A.remplir(fiche=FICHE, analyse=an,
                    saisies={"%s.%s" % (p, c): "TRANCHÉ" for p, c in cibles})
    for p, c in cibles:
        l = _ligne(rap, p, c)
        assert l.get("corrige"), (p, c, l)
        assert not l.get("divergences"), (p, c, l)
        assert not l.get("a_confirmer"), (p, c, l)


def test_AUCUNE_declaration_ne_se_remplit_par_une_saisie():
    """LA DOCTRINE, MESURÉE SUR TOUTES LES DÉCLARATIONS. Un programme qui
    écrirait dans une déclaration sur l'honneur produirait une affirmation que
    personne n'a faite, et dont la fausseté est sanctionnée pénalement."""
    saisies = {"%s.%s" % (p, l["cle"]): "OUI JE DÉCLARE"
               for p, l in _toutes(A.remplir(fiche=FICHE))
               if l["source"] == "declaration"}
    assert saisies, "aucune déclaration au catalogue : la règle est vide"
    rap = A.remplir(fiche=FICHE, saisies=saisies)
    for _p, l in _toutes(rap):
        if l["source"] == "declaration":
            assert l["statut"] == "a_declarer", l
            assert "OUI JE DÉCLARE" not in str(l.get("valeur") or ""), l
            assert not l.get("corrige"), l


def test_toutes_les_rubriques_NON_declaratives_sont_corrigeables():
    """La couverture, mesurée sur les quatre-vingt-treize : c'est le compte
    qui distingue « on peut corriger » de « on peut corriger un quart »."""
    base = list(_toutes(A.remplir(fiche=FICHE)))
    ouvertes = [(p, l["cle"]) for p, l in base if l["source"] != "declaration"]
    assert len(ouvertes) > 60, len(ouvertes)
    saisies = {"%s.%s" % (p, c): "Z-%s" % c for p, c in ouvertes}
    rap = A.remplir(fiche=FICHE, saisies=saisies)
    refus = [(p, l["cle"]) for p, l in _toutes(rap)
             if l["source"] != "declaration"
             and l["valeur"] != "Z-%s" % l["cle"]]
    assert not refus, ("rubriques qui refusent encore la correction : %r"
                       % refus[:10])


# --------------------------------------------------------------------------
# 2. LA PAGE OFFRE UN CHAMP PARTOUT OÙ LE MOTEUR EN ACCEPTE UN.
# --------------------------------------------------------------------------
def _carte(remplissage, ouverte=None):
    # LES DEUX GARDES DU FOCUS ENTRENT AU BANC, ET C'EST LE BANC QUI L'A
    # DEMANDÉ : `aoRempliRendre` les appelle, et sans elles il tombe sur
    # « aoFocusRetenir is not defined ». Il exécute, il ne relit pas.
    prog = (_js_source("esc", "info", "aoMenuDocs", "aoFormulairesBoutons",
                       "aoProduira", "aoLotBarre", "aoLotEtatCarte",
                       "aoFocusRetenir", "aoFocusRendre",
                       "aoRempliRendre")
            + "\nvar AO_FORMULAIRES = null;\nvar AO_DOC = '';"
            + "\nvar AO_SAISIES = {};\nvar AO_CHOISIES = {};"
            + "\nvar AO_PRODUIT = {};\nvar AO_LOT_FMT = 'docx';"
            # L'APERÇU ET L'OUVERTURE EN GRAND sont un ÉTAT de la zone : la
            # carte le lit pour savoir si elle déroule quatre rubriques ou
            # toutes. Sans ces deux-là, le banc tombe — et c'est son office.
            + "\nvar AO_OUVERTE = process.env.OUVERTE || null;"
            + "\nvar AO_APERCU = 4;"
            + "\nvar AO_REMPLI = null;"
            + "\nfunction aoOuvrir() {}\nfunction aoPieceEmporter() {}"
            + "\nvar AO_DERNIER = null;"
            + "\nvar AO_ETAT_CLASSE = { rempli: 'ok', a_saisir: 'att',"
              " a_declarer: 'dec', non_trouve: 'att', invalide: 'mal' };"
            + "\nvar CADRE = { glossaire: {} };"
            + "\nfunction fr(n){ return String(Math.round(Number(n)||0)); }"
            + "\nfunction aoOctets(n){ return n + ' o'; }"
            + "\nfunction aoBrancherMenu(){}\nfunction aoBrancherLot(){}"
            + "\nfunction aoExporter(){}\nfunction aoDossierComplet(){}"
            + "\nfunction aoFormulaireRemplir(){}\nfunction aoRemplir(){}"
            + "\nfunction aoFicheEnregistrer(){}"
            + "\nvar zone = { innerHTML: '',"
              " querySelectorAll: function(){ return []; },"
              " querySelector: function(){ return null; } };"
            + "\nfunction $(s){ return s === '#ig-ao-rempli' ? zone : null; }"
            + "\nglobal.document = { querySelectorAll: function(){ return []; },"
              " querySelector: function(){ return null; } };"
            + "\naoRempliRendre(JSON.parse(process.env.R));"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60,
                         env=dict(os.environ, R=json.dumps(remplissage),
                                  OUVERTE=ouverte or ""))
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


def test_la_page_offre_un_champ_sur_CHAQUE_rubrique_non_declarative():
    """LA RÈGLE EXÉCUTE LE RENDU. Chercher « data-saisie » dans le fichier
    dirait qu'une balise existe quelque part ; on compte ici les champs
    RÉELLEMENT produits, et on les compare une à une aux rubriques que le
    moteur accepte de corriger."""
    rap = A.remplir(fiche=FICHE)
    # CHAQUE PIÈCE EST MESURÉE OUVERTE, ET LA RÈGLE LE DIT. Depuis que la
    # carte repliée montre un APERÇU — ce qui demande attention, puis le
    # reste, quatre lignes — « toutes les rubriques » n'est vrai que de la
    # pièce ouverte. Mesurer sur l'aperçu ferait dire à cette règle « 4 champs
    # sur 93 » et la ferait tomber pour une raison SANS RAPPORT avec ce
    # qu'elle prétend : elle éprouve le droit de corriger, pas le repli.
    h = "".join(_carte(rap, ouverte=x["cle"]) for x in rap["pieces"])
    champs = set(re.findall(r'data-saisie="([^"]+)"', h))
    attendus = {"%s.%s" % (p, l["cle"]) for p, l in _toutes(rap)
                if l["source"] != "declaration"}
    interdits = {"%s.%s" % (p, l["cle"]) for p, l in _toutes(rap)
                 if l["source"] == "declaration"}
    assert champs == attendus, (
        "manquent : %r — en trop : %r"
        % (sorted(attendus - champs)[:8], sorted(champs - attendus)[:8]))
    assert not (champs & interdits), sorted(champs & interdits)
    # LE TÉMOIN : il y avait 27 champs avant ce correctif.
    assert len(champs) > 60, len(champs)


def test_une_rubrique_corrigee_se_voit_et_dit_ce_que_le_module_avait_lu():
    """Sans marque, une correction se perd parmi quatre-vingt-treize lignes —
    et l'on croit lu ce qu'on a écrit soi-même."""
    h = _carte(A.remplir(fiche=FICHE,
                         saisies={"dc1.candidat": "AUTRE RAISON"}),
                ouverte="dc1")
    # LA BALISE ENTIÈRE, PAS SA FIN. La classe précède `data-saisie` dans le
    # balisage : partir de l'attribut cherché la laisse hors de portée, et la
    # règle tombe sur une marque pourtant présente.
    m = re.search(r'<input[^>]*data-saisie="dc1\.candidat"[^>]*>', h)
    assert m, "aucun champ pour dc1.candidat"
    assert "ig-ao-si-cor" in m.group(0), (
        "le champ corrigé ne porte aucune marque : %s" % m.group(0))
    # LA LECTURE EST CHERCHÉE DANS SA PROPRE MARQUE, pas n'importe où dans la
    # carte : « CONSEILPREV » figure aussi sur les autres rubriques tirées de
    # la fiche, et une mutation qui supprimait tout le bloc de rappel a donc
    # survécu à la première rédaction de cette règle.
    rappel = re.search(r'<span class="ig-ao-cor">(.*?)</span>', h, re.S)
    assert rappel, "aucun rappel de ce que le module avait lu"
    assert "CONSEILPREV" in rappel.group(1), (
        "le rappel ne dit pas la valeur remplacée : %s" % rappel.group(1))
    assert "Corrigé à la main" in rappel.group(1)


# --------------------------------------------------------------------------
# 3. L'ATELIER REÇOIT LE TRAVAIL, ET LE REND.
# --------------------------------------------------------------------------
def test_l_atelier_recoit_ce_que_vous_avez_tape():
    """Il partait sans `saisies` et recevait donc un dictionnaire vide : le
    geste le plus coûteux du module défaisait le travail de l'opérateur."""
    src = _js_source("atelierLancer")
    corps = src[src.index("JSON.stringify"):src.index("600000")]
    for champ in ("saisies", "fournies", "perimetre", "documents", "fiche",
                  "analyse"):
        assert champ in corps, (
            "l'atelier part sans « %s » : il travaille sur autre chose que "
            "l'écran" % champ)
    assert "AO_SAISIES" in corps, (
        "le champ « saisies » part vide : il ne lit pas la table des saisies")


def test_l_atelier_rend_son_remplissage_dans_les_cartes():
    """LE DÉFAUT QUI EXPLIQUE TOUT LE RESTE. L'atelier rend le remplissage
    final et les onze brouillons ; `atelierBilan` écrivait un résumé et jetait
    les deux. Les cartes restaient dans l'état d'avant, et l'on concluait que
    les pièces n'étaient pas produites."""
    # LA RÈGLE EXÉCUTE `atelierBilan`. Sa première rédaction cherchait
    # « j.remplissage » dans le source : une mutation qui remplaçait la
    # condition par `if (false)` laissait le nom en place, dans un bloc mort,
    # et la règle restait verte pendant que le remplissage était de nouveau
    # jeté. On compte ici les APPELS réellement faits.
    prog = (_js_source("esc", "atelierBilan")
            + "\nvar appels = [];"
            + "\nvar AO_REMPLI = null, AO_ANALYSE = {x:1}, AO_CHOIX_FAIT = true;"
            + "\nfunction aoRempliRendre(r){ appels.push(['cartes',"
              " (r && r.pieces || []).length]); }"
            + "\nfunction aoRedigerRendre(z, b){ appels.push(['brouillon',"
              " b.cle]); }"
            + "\nfunction aoToutChoisir(){}"
            + "\nvar zone = { innerHTML: '', hidden: true };"
            + "\nfunction $(s){ return { tag: s }; }"
            + "\nglobal.document = { getElementById: function(){"
              " return zone; } };"
            + "\natelierBilan(JSON.parse(process.env.J));"
            + "\nprocess.stdout.write(JSON.stringify(appels));\n")
    charge = {"remplies": 40, "rubriques": 93, "tours": 2,
              "remplissage": {"pieces": [{"cle": "dc1"}, {"cle": "dc2"}]},
              "brouillons": [{"cle": "moyens", "markdown": "## Moyens"},
                             {"cle": "qse", "markdown": "## QSE"}]}
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60,
                         env=dict(os.environ, J=json.dumps(charge)))
    assert out.returncode == 0, out.stderr[-2000:]
    appels = json.loads(out.stdout)
    assert ["cartes", 2] in appels, (
        "le remplissage rendu par l'atelier n'est pas redessiné : %r" % appels)
    montres = {a[1] for a in appels if a[0] == "brouillon"}
    assert montres == {"moyens", "qse"}, (
        "les brouillons sont comptés mais jamais montrés : %r" % appels)


def test_le_remplissage_de_l_atelier_porte_deja_vos_corrections():
    """La garantie qui rend le retour sûr : ce qui revient a été calculé AVEC
    les saisies, donc l'atelier comble les trous sans reprendre la main sur ce
    que vous avez tranché. Mesuré sur le moteur, qui est ce que la route
    appelle."""
    saisies = {"dc1.candidat": "TRANCHÉ PAR MOI"}
    rap = A.remplir(fiche=FICHE, saisies=saisies,
                    extraits={"dc1.candidat": {"valeur": "LU PAR LE MODÈLE",
                                               "citation": "x",
                                               "fichier": "y", "part": 0.1}})
    l = _ligne(rap, "dc1", "candidat")
    assert l["valeur"] == "TRANCHÉ PAR MOI", (
        "un extrait du modèle écrase la correction de l'opérateur : relancer "
        "l'atelier défait le travail fait à la main — %r" % l)
