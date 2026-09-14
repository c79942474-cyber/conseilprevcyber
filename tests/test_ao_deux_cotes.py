# -*- coding: utf-8 -*-
"""Le dépôt a deux côtés, et nos documents cessent d'être lus comme le règlement.

LE DÉFAUT, MESURÉ AVANT CORRECTION. §1 ne connaissait qu'un côté : celui de
l'acheteur. Un mémoire technique CONSEILPREV déposé là n'était pas seulement
ignoré — il était IDENTIFIÉ « règlement de consultation ». La raison est
mécanique et elle est inévitable : un mémoire technique reprend, par
construction, les critères de jugement pondérés de la consultation à laquelle
il répond, et cette seule phrase suffit à le faire reconnaître comme le
règlement. Son texte entrait alors dans la détection des exigences, et le
module annonçait « l'acheteur demande un mémoire technique » en citant NOTRE
fichier. Le compte « N documents retenus sur 23 » était gonflé par notre
paperasse, et le motif affiché était faux.

AUCUNE HEURISTIQUE NE POUVAIT TRANCHER. Un document qui EXIGE et un document
qui RÉPOND parlent des mêmes pièces, dans les mêmes termes — c'est même la
condition pour que la réponse soit bonne. Le côté est donc DÉCLARÉ par
l'opérateur, et le module ne le discute pas.

CE QUE CES RÈGLES MESURENT :
  1. qu'un document du cabinet ne produit AUCUNE exigence, quel que soit son
     texte — la règle exécute le cas exact qui s'était trompé ;
  2. qu'il est pour autant rattaché à la pièce qu'il fournit, et que ce qui
     n'est rattaché à rien le DIT plutôt que de disparaître ;
  3. que ce rattachement ne change pas ce qui est retenu — retenir est
     l'affaire de l'acheteur, et confondre les deux est le défaut d'origine ;
  4. que la page offre bien deux zones et que le côté part avec le document ;
  5. que le brouillon s'emporte, puisqu'il n'est conservé nulle part.
"""
import html
import io
import json
import os
import re
import subprocess

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import ao_dc as A                                                # noqa: E402
import livrables_export                                          # noqa: E402

from conftest import ORIGINE                                     # noqa: E402
from test_ao_formulaires import _js_source                       # noqa: E402


# LE CAS EXACT QUI S'ÉTAIT TROMPÉ. La phrase sur les critères pondérés est ce
# qui faisait basculer l'identification vers « rc » : la retirer rendrait la
# règle verte sans rien prouver.
MEMOIRE = ("Mémoire technique. Notre méthodologie d'audit de centre de "
           "données. Les critères de jugement pondérés sont traités un à un.")
RC = ("Le candidat produit le DC1 et le DC2.")


def _docs(cote_memoire):
    return [
        {"nom": "01_RC.pdf", "extension": "pdf", "texte": RC,
         "cote": "consultation"},
        {"nom": "memoire-technique-CONSEILPREV-2025.docx", "extension": "docx",
         "texte": MEMOIRE, "cote": cote_memoire},
    ]


# --------------------------------------------------------------------------
# 1. NOS DOCUMENTS NE PARLENT PLUS À LA PLACE DE L'ACHETEUR.
# --------------------------------------------------------------------------
def test_le_temoin_le_meme_memoire_du_cote_consultation_est_bien_pris_pour_le_RC():
    """LA RÈGLE QUI EMPÊCHE LA SUIVANTE D'ÊTRE CREUSE.

    Si l'identification cessait un jour de confondre un mémoire avec un
    règlement — pour une raison sans rapport avec cette séparation — la règle
    suivante resterait verte en ne protégeant plus de rien. On mesure donc
    d'abord que le piège EXISTE TOUJOURS : déposé du côté consultation, ce
    mémoire est bel et bien lu comme le règlement.
    """
    a = A.analyser(_docs("consultation"))
    lus = {p["fichier"] for p in a["pieces"]}
    assert "memoire-technique-CONSEILPREV-2025.docx" in lus, (
        "le mémoire n'est plus confondu avec une pièce de consultation : le "
        "piège que la séparation neutralise a disparu, et la règle suivante "
        "ne mesure plus rien")
    assert a["exigences"]["memoire_technique"]["repere"], (
        "le mémoire ne produit plus d'exigence même du côté consultation")


def test_un_document_du_cabinet_ne_produit_aucune_exigence():
    """Le même fichier, le même texte, déclaré nôtre : il ne dit plus rien de
    ce que l'acheteur exige."""
    a = A.analyser(_docs("cabinet"))
    assert [p["fichier"] for p in a["pieces"]] == ["01_RC.pdf"], (
        "un document du cabinet est encore compté parmi les pièces de "
        "consultation : %r" % [p["fichier"] for p in a["pieces"]])
    assert not a["exigences"]["memoire_technique"]["repere"], (
        "notre propre mémoire fait encore croire que l'acheteur en demande un")
    # ET AUCUNE exigence ne peut citer un fichier du cabinet.
    noms = {c["fichier"] for c in a["pieces_cabinet"]}
    for cle, e in a["exigences"].items():
        f = (e.get("citation") or {}).get("fichier")
        assert f not in noms, (
            "l'exigence %s est citée depuis notre propre document %r" % (cle, f))


def test_le_cote_inconnu_retombe_du_cote_qui_est_LU():
    """Le repli prudent : une valeur inattendue ne doit pas soustraire un
    document à la lecture. Un côté inconnu traité comme « cabinet » ferait
    disparaître une pièce de consultation en silence — l'inverse ne fait que
    remettre le document sous les yeux du module."""
    docs = _docs("consultation")
    docs[1]["cote"] = "n'importe quoi"
    a = A.analyser(docs)
    assert len(a["pieces"]) == 2, [p["fichier"] for p in a["pieces"]]
    assert not a["pieces_cabinet"]


def test_sans_cote_declaree_le_comportement_est_celui_d_avant():
    """La compatibilité, mesurée : tout appelant écrit avant cette séparation
    continue de fonctionner comme avant."""
    docs = [{k: v for k, v in d.items() if k != "cote"}
            for d in _docs("consultation")]
    assert len(A.analyser(docs)["pieces"]) == 2


# --------------------------------------------------------------------------
# 2. CE QUE NOUS DÉPOSONS EST RATTACHÉ, OU DIT NE PAS L'ÊTRE.
# --------------------------------------------------------------------------
CABINET = [
    ("attestation-assurance-rc-pro-2026.pdf", "attestations_assurances"),
    ("attestation-urssaf-vigilance.pdf", "regularite_fiscale_sociale"),
    ("bilan-2024.pdf", "bilans"),
    ("CV-chef-de-projet.pdf", "cv"),
    ("organigramme-mission.docx", "organigramme"),
    ("memoire-technique-2025.docx", "memoire_technique"),
    ("convention-collective-syntec.pdf", "conventions"),
]


@pytest.mark.parametrize("fichier,attendue", CABINET)
def test_chaque_document_du_cabinet_rejoint_SA_piece(fichier, attendue):
    """Le rattachement est éprouvé pièce par pièce, sur des noms tels qu'on
    les écrit vraiment — pas sur un nom construit pour passer."""
    assert A.piece_du_cabinet(fichier) == attendue, A.piece_du_cabinet(fichier)


def test_les_cles_rattachables_existent_toutes_au_catalogue():
    """Une clé mal orthographiée dans la table rattacherait un document à une
    pièce qui n'existe pas : la ligne dirait « fournie » sous aucune carte."""
    connues = {p["cle"] for p, _d in A._catalogue()}
    inconnues = sorted(set(A.CABINET_MOTIFS) - connues)
    assert not inconnues, inconnues


def test_un_document_que_rien_ne_rattache_LE_DIT():
    """Le taire ferait croire le document pris en compte. C'est le pire des
    deux échecs possibles : on a déposé, on n'a rien, et rien ne le dit."""
    a = A.analyser([{"nom": "plaquette-commerciale.pdf", "extension": "pdf",
                     "texte": "CONSEILPREV.", "cote": "cabinet"}])
    ligne = a["pieces_cabinet"][0]
    assert ligne["cle"] is None
    quoi = (ligne.get("pourquoi") or "").strip()
    assert quoi, "un document non rattaché sort sans un mot"
    # ET LE MESSAGE DIT QUOI FAIRE. Constater « non rattaché » laisse
    # l'opérateur devant un fichier déposé qui ne sert à rien, sans geste à
    # tenter : c'est le cas où il redépose trois fois le même document.
    assert any(v in quoi.lower() for v in ("renommez", "rattachez")), (
        "le message constate l'échec sans nommer le geste qui le répare : %r"
        % quoi)


def test_tenir_une_piece_NE_LA_FAIT_PAS_RETENIR():
    """LE DÉFAUT D'ORIGINE, PRIS PAR L'AUTRE BOUT. Ce qui est retenu est ce
    que l'ACHETEUR demande ; tenir une attestation qu'il ne réclame pas n'en
    fait pas une pièce du dossier. Les confondre, c'est reconstruire le compte
    gonflé qu'on vient de défaire — par une autre porte."""
    a = A.analyser([
        {"nom": "01_RC.pdf", "extension": "pdf", "cote": "consultation",
         "texte": RC},
        {"nom": "bilan-2024.pdf", "extension": "pdf", "cote": "cabinet",
         "texte": "Bilan."},
    ])
    sel = A.selection(a)
    assert "bilans" not in {x["cle"] for x in sel["lignes"] if x["retenue"]}, (
        "un bilan que personne ne demande entre dans les pièces retenues")
    assert "bilans" in sel["tenues_hors_selection"], (
        "le bilan déposé disparaît : on le chercherait sans le trouver")
    assert sel["retenues"] == A.selection(A.analyser(
        [{"nom": "01_RC.pdf", "extension": "pdf", "texte": RC}]))["retenues"], (
        "déposer un document du cabinet change le nombre de pièces retenues")


def test_une_piece_demandee_ET_tenue_est_dite_tenue():
    """C'est le compte qui manquait : sur N documents demandés, lesquels sont
    déjà dans nos dossiers."""
    a = A.analyser([
        {"nom": "01_RC.pdf", "extension": "pdf", "cote": "consultation",
         "texte": "Le candidat produit une attestation d'assurance "
                  "responsabilité civile professionnelle."},
        {"nom": "attestation-rc-pro-2026.pdf", "extension": "pdf",
         "cote": "cabinet", "texte": "AXA atteste."},
    ])
    sel = A.selection(a)
    ligne = next(x for x in sel["lignes"] if x["cle"] == "attestations_assurances")
    assert ligne["retenue"] and ligne["pourquoi"] == "citee"
    assert ligne["fichier_cabinet"] == "attestation-rc-pro-2026.pdf"
    assert "attestations_assurances" in sel["deja_tenues"]
    # ET ELLE N'EST PAS CONFONDUE AVEC LE CERFA VIERGE JOINT PAR L'ACHETEUR.
    assert ligne["fichier_fourni"] is None, (
        "« nous l'avons » et « il l'attend rempli » sont devenus le même champ")


# --------------------------------------------------------------------------
# 3. LA ROUTE LAISSE PASSER LE CÔTÉ, ET LE BORNE.
# --------------------------------------------------------------------------
def test_la_route_transmet_le_cote_et_refuse_d_en_inventer_un_troisieme(marche):
    j = marche.post("/api/datacenter/marche/analyser", json={"documents": [
        {"nom": "01_RC.pdf", "extension": ".pdf", "texte": RC,
         "cote": "consultation"},
        {"nom": "memoire-technique-2025.docx", "extension": ".docx",
         "texte": MEMOIRE, "cote": "cabinet"},
        {"nom": "note-libre.txt", "extension": ".txt", "texte": "Rien.",
         "cote": "CABINET-BIDON"},
    ]}, headers=ORIGINE).get_json()
    assert j["ok"], j
    a = j["analyse"]
    assert {c["fichier"] for c in a["pieces_cabinet"]} == {
        "memoire-technique-2025.docx"}
    assert not a["exigences"]["memoire_technique"]["repere"], (
        "la route perd le côté en chemin : notre mémoire redevient une "
        "exigence de l'acheteur")


# --------------------------------------------------------------------------
# 4. LA PAGE, EXÉCUTÉE.
# --------------------------------------------------------------------------
def _depot_rendu():
    prog = (_js_source("esc", "aoOctets", "aoDocuments", "aoBrancherDepot",
                       "aoEnAttenteRendre")
            + "\nfunction fr(n){ return String(Math.round(Number(n)||0)); }"
            + "\nvar AO_EN_ATTENTE = [];"
            + "\nvar AO_TRANSPORT_MAX = 4000000;"
            + "\nfunction accepteDepot(){ return '.pdf,.docx'; }"
            + "\nvar zones = {};"
            + "\nfunction elem(){ return { innerHTML: '', value: '',"
              " files: [], setAttribute: function(){},"
              " addEventListener: function(){} }; }"
            + "\nvar depot = elem();"
            + "\nfunction $(s){ if (s === '#ig-ao-depot') return depot;"
              " if (!zones[s]) zones[s] = elem(); return zones[s]; }"
            + "\naoDocuments();"
            + "\nprocess.stdout.write(depot.innerHTML);\n")
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    return html.unescape(out.stdout)


def test_la_page_offre_DEUX_zones_de_depot_et_les_nomme():
    """Une seule zone ramènerait le module à deviner — c'est-à-dire au
    défaut."""
    h = _depot_rendu()
    champs = re.findall(r'<input id="([^"]+)" type="file"', h)
    assert len(champs) == 2, champs
    libelles = re.findall(r'<span class="dc-lab">(.*?)</span>', h, re.S)
    assert any("consultation" in l for l in libelles), libelles
    assert any("cabinet" in l.lower() for l in libelles), libelles
    # ET CHAQUE ZONE DIT CE QU'ELLE FAIT DU FICHIER, parce que c'est là que se
    # joue la différence : un côté sert à repérer ce qui est exigé, l'autre
    # non.
    aides = " ".join(re.findall(r'<span class="dc-aide">(.*?)</span>', h, re.S))
    assert "EXIGÉ" in aides or "exigé" in aides.lower(), aides[:400]


def test_le_cote_part_avec_chaque_document():
    """LE POINT LE PLUS FRAGILE DE LA CHAÎNE. `aoLire` lit un fichier, il ne
    connaît pas la file : si le côté n'était pas recollé par l'index après
    `Promise.all`, tout repartirait « consultation » et la séparation ne
    servirait à rien — sans que rien ne le montre à l'écran."""
    src = _js_source("aoAnalyser")
    # LA PREMIÈRE VERSION DE CETTE RÈGLE ÉTAIT VERTE POUR RIEN. Elle cherchait
    # « AO_EN_ATTENTE[i] » et « .cote » quelque part dans la fonction — or
    # `AO_EN_ATTENTE[i]` y figure DÉJÀ, sans rapport, dans la boucle de
    # lecture (`aoLire(AO_EN_ATTENTE[i].file)`). Une mutation qui écrivait
    # `x.cote = "consultation"` en dur — c'est-à-dire qui supprimait toute la
    # séparation — a donc survécu. On mesure maintenant L'AFFECTATION
    # elle-même : ce qui est écrit dans `cote` doit venir de la file.
    ligne = next((l for l in src.splitlines() if ".cote =" in l), None)
    assert ligne, "aucune affectation de côté sur les documents lus"
    droite = ligne.split(".cote =", 1)[1]
    assert "AO_EN_ATTENTE" in droite, (
        "le côté affecté ne vient pas de la file : il est écrit en dur, et "
        "tous les documents repartent du même côté — %s" % ligne.strip())
    bloc = src[src.index("Promise.all"):]
    assert bloc.index(".cote =") < bloc.index("documents: docs"), (
        "le côté est posé après l'envoi : il ne part pas")


def test_la_file_porte_le_cote_de_chaque_fichier():
    src = _js_source("aoBrancherDepot")
    assert src.count("cote: cote") == 2, (
        "l'ajout et le remplacement ne portent pas tous deux le côté : "
        "redéposer un fichier lui ferait perdre son camp")


# --------------------------------------------------------------------------
# 5. LE BROUILLON S'EMPORTE, PUISQU'IL N'EST CONSERVÉ NULLE PART.
# --------------------------------------------------------------------------
def test_les_trois_formats_sont_offerts_sous_le_brouillon():
    src = _js_source("aoRedigerRendre")
    # LES TROIS FORMATS SONT CEUX QUE LE COMPOSEUR SERT, LUS CHEZ LUI. Les
    # écrire ici ferait passer la règle le jour où la page en offrirait un
    # quatrième que le serveur refuse — bouton mort, et personne pour le dire.
    for f in sorted(livrables_export.FORMATS):
        assert '"%s"' % f in src, (
            "le format %s est servi par /brouillon et la page ne l'offre pas"
            % f)
    assert "data-brouillon" in src, "aucun bouton d'emport"
    # L'APOSTROPHE EST ÉCHAPPÉE DANS LA SOURCE (« n\\'est ») : la chercher
    # telle qu'on la lit à l'écran ne trouve rien. On mesure donc le fragment
    # qui porte le sens et qu'aucun échappement ne traverse.
    assert "pas conservé" in src, (
        "la page ne dit pas que le brouillon sera perdu : on ne l'emporterait "
        "qu'après l'avoir perdu une fois")


@pytest.mark.parametrize("fmt", ["docx", "pdf", "xlsx"])
def test_la_route_rend_un_vrai_fichier_dans_chaque_format(marche, fmt):
    r = marche.post("/api/datacenter/marche/brouillon", json={
        "markdown": "## Moyens\n\nUn paragraphe.\n\n- un point\n- un autre\n",
        "format": fmt, "piece": "moyens", "nom": "Note sur les moyens"},
        headers=ORIGINE)
    assert r.status_code == 200, r.get_json()
    assert r.headers["Content-Type"].startswith(livrables_export.MIME[fmt])
    assert ("brouillon-moyens.%s" % fmt) in r.headers["Content-Disposition"]
    assert len(r.data) > 400, len(r.data)


def test_le_document_emporte_DIT_qu_il_est_un_brouillon():
    """Sorti en Word, il ressemble à une pièce finie. C'est la version qu'on
    retrouve trois semaines plus tard, et rien sur la page ne rappelle alors
    qu'elle n'a été ni relue ni signée."""
    import app as APP
    src = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    i = src.index("def api_datacenter_marche_brouillon")
    bloc = src[i:src.index("\n@app.route", i)]
    code = "\n".join(l for l in bloc.splitlines()
                     if not l.lstrip().startswith("#"))
    assert "BROUILLON" in code and "chapeau" in code, (
        "le cartouche ne dit pas que le document est un brouillon")
    assert '"ia"' in code, (
        "le document ne déclare pas avoir été écrit par un modèle")


def test_la_route_refuse_un_corps_vide_et_un_texte_demesure(marche):
    """Un document vide se lit comme un document raté plutôt que comme une
    demande mal formée ; et la borne haute empêche ce point d'export de
    devenir un convertisseur de documents quelconques."""
    r = marche.post("/api/datacenter/marche/brouillon",
                    json={"markdown": "   "}, headers=ORIGINE)
    assert r.status_code == 400 and r.get_json()["error"] == "vide"
    r = marche.post("/api/datacenter/marche/brouillon",
                    json={"markdown": "a" * 130001}, headers=ORIGINE)
    assert r.status_code == 400 and r.get_json()["error"] == "trop_long"


def test_la_route_du_brouillon_est_fermee_a_l_administration(anonyme, connecte):
    """Le brouillon porte le nom de l'acheteur, l'objet du marché et les
    moyens du cabinet."""
    for client in (anonyme, connecte):
        r = client.post("/api/datacenter/marche/brouillon",
                        json={"markdown": "## x"}, headers=ORIGINE)
        assert r.status_code in (401, 403), r.status_code


def test_le_brouillon_n_est_conserve_nulle_part():
    """LA DÉCISION, MESURÉE PLUTÔT QU'AFFIRMÉE. « Téléchargeable seulement »
    veut dire qu'aucun magasin n'est écrit : la route compose et rend, elle ne
    range pas. Une ligne d'écriture ajoutée ici changerait la nature de ce
    point d'accès sans que son nom bouge."""
    src = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    i = src.index("def api_datacenter_marche_brouillon")
    bloc = src[i:src.index("\n@app.route", i)]
    code = "\n".join(l for l in bloc.splitlines()
                     if not l.lstrip().startswith("#"))
    for ecriture in ("ao_projet.", "rag.", "rag_store", "store()", "open(",
                     "commit(", "INSERT"):
        assert ecriture not in code, (
            "la route du brouillon écrit quelque part (%r) : elle ne devait "
            "que mettre en page" % ecriture)
