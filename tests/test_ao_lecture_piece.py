# -*- coding: utf-8 -*-
"""Voir les pièces du dossier marché déposées — le texte lu, ses relevés surlignés.

CE QUI A DÉCLENCHÉ CE FICHIER. On pouvait déposer un dossier de consultation,
le faire analyser, le conserver chiffré — et jamais le RELIRE. L'écran rendait
des citations de trois lignes et rien autour. Quand l'outil annonce « non
trouvé dans cette pièce », la question suivante est toujours la même : le
document ne le porte pas, ou l'extraction l'a perdu ? Un PDF scanné rend trois
lignes de bruit, un tableau à deux colonnes ressort entrelacé — aucune citation
ne le dit, et le texte lu, si.

CE QUE LE LECTEUR MONTRE, ET CE QU'IL NE MONTRE PAS. Le TEXTE EXTRAIT, pas le
fichier d'origine : le PDF n'est pas conservé — il est passé à l'antivirus,
ouvert par l'extracteur, puis abandonné. Laisser croire le contraire ferait
prendre une extraction incomplète pour le document lui-même. Une règle de ce
fichier exige que l'écran le dise en toutes lettres.

LE DÉFAUT QUE LA MESURE A TROUVÉ, ET QUE CES RÈGLES VERROUILLENT. Les citations
rendues par le relevé sont NORMALISÉES — le releveur fait l'équivalent de
`" ".join(split())`. Surligner de `position` à `position + len(citation)` était
donc FAUX dès qu'un passage contenait un saut de ligne : mesuré, un caractère
d'écart sur l'essai le plus simple, et davantage sur un texte de PDF où les
retours à la ligne sont partout. Un surlignage décalé de dix caractères désigne
la phrase d'à côté avec l'aplomb d'une preuve. Le lecteur rejoue donc la
normalisation à l'envers, et REFUSE de surligner ce qu'il ne peut pas
réaligner : ne rien surligner se voit, surligner à côté non.
"""
import base64
import html
import io
import json
import os
import re
import subprocess

import pytest

import ao_dc

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGINE = {"Origin": "http://localhost"}

from test_ao_formulaires import _js_source                      # noqa: E402


#: Un texte tel qu'un extracteur PDF le rend : les phrases coupées par des
#: sauts de ligne. C'est ce qui met le décalage en évidence — un texte d'une
#: seule ligne l'aurait masqué.
TEXTE_PDF = (
    "REGLEMENT DE LA CONSULTATION\n\n"
    "Maitre d'ouvrage :\nCommunaute d'agglomeration\nde Sophia Antipolis\n"
    "Objet :   construction d'un centre\nde donnees de 2 MW.\n"
    "Procedure adaptee ouverte.\n")


def _lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _node(prog, env=None):
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=dict(os.environ, **(env or {})))
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


def _marques_et_html(texte, analyse=None, nom="RC.pdf"):
    """Ce que le surligneur produit RÉELLEMENT, en l'exécutant.

    Chercher les noms des fonctions dans le fichier ne dirait rien de leur
    résultat — et une branche morte laisserait la règle verte pendant que
    l'écran ne surligne plus rien. Le piège est consigné deux fois ailleurs
    dans ce dépôt ; on l'évite d'emblée.
    """
    if analyse is None:
        analyse = ao_dc.analyser([{"nom": nom, "texte": texte,
                                   "extension": ".pdf"}])
    prog = (_js_source("esc", "aoTexteFin", "aoTexteMarques", "aoTexteHtml")
            + "\nvar AO_ANALYSE = JSON.parse(process.env.AN);"
            + "\nvar t = process.env.T;"
            + "\nvar m = aoTexteMarques(process.env.N, t);"
            + "\nprocess.stdout.write(JSON.stringify("
              "{marques: m, html: aoTexteHtml(t, m)}));")
    return json.loads(_node(prog, {"AN": json.dumps(analyse), "T": texte,
                                   "N": nom}))


def _sans_balises(h):
    return html.unescape(re.sub(r"<[^>]+>", "", h))


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE TEXTE ARRIVE JUSQU'À LA PAGE
# ═══════════════════════════════════════════════════════════════════════════

def test_l_analyse_renvoie_le_texte_qu_elle_a_lu(marche):
    """Sans cela, « voir » n'existerait qu'après avoir rattaché un projet.

    On mesure le CONTENU rendu, pas la présence d'une clé : un `textes` vide
    passerait une règle qui se contenterait de la chercher.
    """
    charge = [{"nom": "RC.txt", "contenu":
               base64.b64encode(TEXTE_PDF.encode("utf-8")).decode()}]
    j = marche.post("/api/datacenter/marche/analyser",
                    json={"documents": charge}, headers=ORIGINE).get_json()
    assert j and j.get("ok"), j
    assert "RC.txt" in (j.get("textes") or {}), sorted(j.get("textes") or {})
    assert "Sophia Antipolis" in j["textes"]["RC.txt"], j["textes"]["RC.txt"][:200]


def test_le_texte_rendu_est_celui_sur_lequel_les_releves_ont_tourne(marche):
    """LA RÈGLE QUI FAIT QUE LE LECTEUR SERT À QUELQUE CHOSE.

    Si la route rendait un autre texte — l'original avant extraction, une
    version tronquée — le surlignage par position désignerait des passages au
    hasard. On vérifie donc que CHAQUE citation de l'analyse se retrouve, une
    fois normalisée, à la position qu'elle annonce dans le texte rendu.
    """
    charge = [{"nom": "RC.txt", "contenu":
               base64.b64encode(TEXTE_PDF.encode("utf-8")).decode()}]
    j = marche.post("/api/datacenter/marche/analyser",
                    json={"documents": charge}, headers=ORIGINE).get_json()
    t = j["textes"]["RC.txt"]
    vues = 0
    for p in j["analyse"]["pieces"] + (j["analyse"].get("inconnues") or []):
        if p["fichier"] != "RC.txt":
            continue
        for r in p.get("releves") or []:
            for c in r.get("citations") or []:
                i = c["position"]
                fenetre = " ".join(t[i:i + len(c["texte"]) + 40].split())
                assert fenetre.startswith(c["texte"]), (
                    "la citation %r n'est pas à la position %d du texte rendu"
                    % (c["texte"][:50], i))
                vues += 1
    assert vues >= 2, "trop peu de citations pour que la règle prouve quoi que ce soit"


# ═══════════════════════════════════════════════════════════════════════════
#  2. LE SURLIGNAGE EST PROUVÉ, OU IL N'EST PAS
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_surlignage_redonne_exactement_la_citation_du_releve():
    """LA RÈGLE DÉCISIVE DE CE FICHIER.

    Le passage surligné, une fois normalisé comme le releveur normalise, doit
    redonner la citation MOT POUR MOT. C'est ce qui distingue un surlignage
    juste d'un surlignage décalé — et le décalage est précisément le défaut
    mesuré avant d'écrire ces lignes.
    """
    a = ao_dc.analyser([{"nom": "RC.pdf", "texte": TEXTE_PDF,
                         "extension": ".pdf"}])
    r = _marques_et_html(TEXTE_PDF, a)
    attendues = {}
    for p in a["pieces"] + (a.get("inconnues") or []):
        for rl in p.get("releves") or []:
            for c in rl.get("citations") or []:
                attendues.setdefault(rl["cle"], []).append(c["texte"])
    assert r["marques"], "aucun passage surligné sur un texte qui en porte"
    for m in r["marques"]:
        vu = " ".join(TEXTE_PDF[m["i"]:m["j"]].split())
        assert vu in attendues.get(m["cle"], []), (
            "le passage surligné pour « %s » est %r ; le relevé cite %r"
            % (m["cle"], vu, attendues.get(m["cle"])))


def test_un_passage_qu_on_ne_sait_pas_realigner_n_est_pas_surligne():
    """ON NE SURLIGNE QUE CE QU'ON PEUT PROUVER.

    Le témoin : une citation qui ne correspond à rien à sa position. Surligner
    « la longueur annoncée à partir de la position annoncée » marquerait une
    plage arbitraire — avec l'apparence d'une preuve. Ne rien marquer se voit.
    """
    faux = {"pieces": [{"fichier": "RC.pdf", "releves": [
        {"cle": "acheteur", "libelle": "Acheteur", "trouve": True,
         "citations": [{"texte": "CECI N'EST PAS DANS LE DOCUMENT",
                        "position": 30, "part": 10}]}]}]}
    r = _marques_et_html(TEXTE_PDF, faux)
    assert r["marques"] == [], r["marques"]
    assert "<mark" not in r["html"], r["html"][:300]


def test_le_texte_survit_intact_au_surlignage():
    """Ôter les balises doit redonner le document, caractère pour caractère.

    Un lecteur qui perd un mot en le surlignant fait lire autre chose que ce
    qui a été analysé — c'est-à-dire l'inverse de son office.
    """
    r = _marques_et_html(TEXTE_PDF)
    assert _sans_balises(r["html"]) == TEXTE_PDF


def test_le_surlignage_echappe_ce_qu_il_montre():
    """Un document de marché contient des chevrons et des esperluettes.

    Les écrire tels quels ferait rendre du balisage par le document lu — et,
    au-delà de l'affichage cassé, injecterait dans la page ce qu'un tiers a
    mis dans un fichier déposé.

    LES DEUX CHEMINS SONT ÉPROUVÉS, ET LE PREMIER ESSAI N'EN ÉPROUVAIT QU'UN.
    `aoTexteHtml` échappe à DEUX endroits : ce qui est HORS des marques, et ce
    qui est DEDANS. Le texte d'essai plaçait le balisage à l'intérieur d'une
    marque, si bien que retirer l'échappement du dehors ne faisait rien — la
    mutation survivait et la règle restait verte. On place donc du balisage
    des deux côtés, sur des marques CONNUES, et l'on vérifie les deux.
    """
    # TROIS ZONES, TROIS APPELS À `esc`, ET IL FAUT DU BALISAGE DANS CHACUNE.
    # `aoTexteHtml` échappe ce qui précède une marque, ce qu'elle contient, et
    # la queue qui la suit. Le premier essai plaçait la marque en position 0 :
    # la tranche « avant » était VIDE, et retirer son échappement ne changeait
    # rien. Les positions sont CALCULÉES, pas comptées à la main — la version
    # comptée était fausse d'un caractère, et la règle passait sans éprouver.
    AVANT = "<i>avant</i> & la marque : "
    DEDANS = "Objet : <b>gras</b> du document"
    APRES = " puis <script>alert(1)</script> & la queue.\n"
    t = AVANT + DEDANS + APRES
    faux = {"pieces": [{"fichier": "RC.pdf", "releves": [
        {"cle": "objet", "libelle": "Objet", "trouve": True,
         "citations": [{"texte": DEDANS, "position": t.index(DEDANS),
                        "part": 0}]}]}]}
    r = _marques_et_html(t, faux)
    assert len(r["marques"]) == 1, r["marques"]
    assert r["marques"][0]["i"] > 0, (
        "la marque est en tête : la zone « avant » reste vide et n'éprouve rien")
    for interdit in ("<i>avant</i>", "<b>gras</b>", "<script>"):
        assert interdit not in r["html"], (
            "%s n'est pas échappé — une des trois zones passe en clair"
            % interdit)
    for attendu in ("&lt;i&gt;", "&lt;b&gt;", "&lt;script&gt;"):
        assert attendu in r["html"], r["html"][:500]
    assert _sans_balises(r["html"]) == t


def test_deux_releves_qui_se_recouvrent_ne_produisent_pas_de_balises_imbriquees():
    """« Objet : … » est cité par plusieurs motifs ; deux marques imbriquées
    produiraient du HTML cassé.

    LE PREMIER ESSAI NE PROUVAIT RIEN, ET LA MUTATION L'A MONTRÉ. Il tournait
    sur TEXTE_PDF, dont les citations sont adjacentes mais ne se recouvrent
    pas : retirer l'écart anti-recouvrement ne changeait donc rien, et la
    règle passait sans avoir rien éprouvé. On construit ici un recouvrement
    VOLONTAIRE — deux citations qui partagent des caractères — parce qu'un
    garde-fou ne se mesure qu'en lui présentant ce qu'il est censé arrêter.
    """
    t = "Objet du marche : construction d'un centre de donnees de 2 MW.\n"

    def _cite(cle, libelle, frag):
        """La citation à sa position RÉELLE. Écrire « position: 19 » à la main
        décalait la seconde d'un caractère : le réalignement la refusait, il
        ne restait qu'une marque, et la règle passait sans qu'aucun
        recouvrement n'ait jamais eu lieu."""
        i = t.index(frag)
        return {"cle": cle, "libelle": libelle, "trouve": True,
                "citations": [{"texte": frag, "position": i,
                               "part": round(100 * i / len(t))}]}

    couvrantes = {"pieces": [{"fichier": "RC.pdf", "releves": [
        _cite("objet", "Objet", "Objet du marche : construction"),
        _cite("performances", "Puissance",
              "construction d'un centre de donnees")]}]}
    r = _marques_et_html(t, couvrantes)
    assert len(r["marques"]) == 1, (
        "les deux citations se recouvrent ; une seule doit être posée : %r"
        % r["marques"])
    fin = -1
    for m in r["marques"]:
        assert m["i"] >= fin, (m, fin)
        fin = m["j"]
    assert r["html"].count("<mark") == r["html"].count("</mark>") == 1
    assert _sans_balises(r["html"]) == t

    # ET LE TÉMOIN : deux citations DISJOINTES sont toutes deux posées. Sans
    # lui, un écart qui jetterait tout passerait aussi bien.
    disjointes = {"pieces": [{"fichier": "RC.pdf", "releves": [
        _cite("objet", "Objet", "Objet du marche"),
        _cite("performances", "Puissance", "de donnees de 2 MW")]}]}
    r2 = _marques_et_html(t, disjointes)
    assert len(r2["marques"]) == 2, r2["marques"]


# ═══════════════════════════════════════════════════════════════════════════
#  3. CE QUE L'ÉCRAN DIT
# ═══════════════════════════════════════════════════════════════════════════

def _lecteur_rendu(nom, textes, analyse):
    """Le HTML que `aoTexteOuvrir` écrit RÉELLEMENT dans la page."""
    prog = (_js_source("esc", "aoTextesPoser", "aoTexteFin", "aoTexteMarques",
                       "aoTexteHtml", "aoTexteFermer", "aoTexteBrancher",
                       "aoTexteOuvrir")
            + "\nvar AO_TEXTES = {}, AO_TEXTE_OUVERT = null;"
            + "\nvar AO_ANALYSE = JSON.parse(process.env.AN);"
            + "\naoTextesPoser(JSON.parse(process.env.TX), true);"
            + "\nvar zone = { innerHTML: '', querySelectorAll: function () "
              "{ return []; } };"
            + "\nfunction $(s) { return s === '#ig-ao-lect' ? zone : null; }"
            + "\nfunction fr(n) { return String(n); }"
            + "\naoTexteOuvrir(process.env.N);"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    return html.unescape(_node(prog, {"AN": json.dumps(analyse),
                                      "TX": json.dumps(textes), "N": nom}))


def test_le_lecteur_montre_le_texte_et_dit_que_ce_n_est_pas_le_fichier():
    """DEUX CHOSES À LA FOIS, ET LA SECONDE COMPTE AUTANT.

    Il montre le texte — sinon il ne sert à rien. Et il dit que c'est le texte
    EXTRAIT et non le fichier d'origine — sinon on prendrait une extraction
    incomplète pour le document, et on chercherait une mise en page que le
    site ne conserve pas.
    """
    a = ao_dc.analyser([{"nom": "RC.pdf", "texte": TEXTE_PDF,
                         "extension": ".pdf"}])
    h = _lecteur_rendu("RC.pdf", {"RC.pdf": TEXTE_PDF}, a)
    assert "Sophia Antipolis" in h, h[:400]
    assert "texte extrait, pas le fichier" in h, (
        "le lecteur laisse croire qu'il montre le fichier d'origine")
    assert "ne conserve pas le PDF" in h, h[:600]
    assert "<mark" in h, "le lecteur ne surligne rien"


def test_une_piece_sans_texte_le_dit_au_lieu_de_s_ouvrir_vide():
    """Un DWG, une archive, un PDF scanné franchissent l'analyse sans rendre
    une ligne. Un lecteur vide et muet se lirait comme un bogue, et on
    chercherait la panne au lieu de chercher le fichier."""
    h = _lecteur_rendu("plan.dwg", {}, {"pieces": []})
    assert "Aucun texte" in h, h[:400]
    assert "PDF scanné" in h, h[:400]
    assert "<mark" not in h


def test_le_bouton_lire_est_pose_sur_les_pieces_ET_sur_les_non_reconnues():
    """C'EST SUR UN FICHIER NON RECONNU QU'ON EN A LE PLUS BESOIN.

    « Non reconnu » laisse une question sans réponse : le fichier ne portait
    rien, ou l'identification n'a pas su le nommer ? Les deux se distinguent
    en lisant le texte, et d'aucune autre manière. Mesuré sur le HTML que
    `aoRendre` produit, pas cherché dans le fichier.
    """
    a = ao_dc.analyser([
        {"nom": "reglement-de-consultation.pdf", "texte":
         "REGLEMENT DE LA CONSULTATION\nLe present reglement de la "
         "consultation fixe les modalites de remise des offres.\n",
         "extension": ".pdf"},
        {"nom": "annexe-7.pdf", "texte":
         "ANNEXE 7\nMaitre d ouvrage : CASA\nObjet : un centre de donnees.\n",
         "extension": ".pdf"}])
    # LA PRÉMISSE SE VÉRIFIE, ELLE NE SE SUPPOSE PAS. Le premier essai
    # donnait à « annexe-7.pdf » un texte portant « REGLEMENT DE LA
    # CONSULTATION » : la pièce était RECONNUE, son bouton venait du chemin
    # des pièces identifiées, et la règle passait sans jamais éprouver le
    # chemin des non reconnues. La mutation qui retirait ce bouton survivait.
    assert [p["fichier"] for p in a["inconnues"]] == ["annexe-7.pdf"], (
        "la pièce d'essai n'est plus « non reconnue » : la règle n'éprouve "
        "plus ce qu'elle prétend — %r" % [p["fichier"] for p in a["pieces"]])
    assert [p["fichier"] for p in a["pieces"]] == [
        "reglement-de-consultation.pdf"], a["pieces"]
    prog = (_js_source("esc", "info", "aoTexteBouton", "aoTexteFermer",
                       "aoTexteBrancherListe", "aoIgnores", "aoRendre")
            + "\nvar AO_TEXTES = {}, AO_TEXTE_OUVERT = null;"
            + "\nvar zone = { innerHTML: '', querySelectorAll: function () "
              "{ return []; } };"
            + "\nvar ign = { innerHTML: '' }, lect = { innerHTML: '' };"
            + "\nfunction $(s) { return s === '#ig-ao-out' ? zone"
              " : (s === '#ig-ao-ign' ? ign"
              " : (s === '#ig-ao-lect' ? lect : null)); }"
            + "\nvar CADRE = { glossaire: {} };"
            + "\nglobal.document = { querySelectorAll: function () { return []; },"
              " querySelector: function () { return null; } };"
            + "\naoRendre(JSON.parse(process.env.AN));"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    h = html.unescape(_node(prog, {"AN": json.dumps(a)}))
    assert 'data-lire="reglement-de-consultation.pdf"' in h, (
        "aucun bouton de lecture sur une pièce identifiée")
    assert 'data-lire="annexe-7.pdf"' in h, (
        "aucun bouton de lecture sur un fichier non reconnu — c'est pourtant "
        "là qu'on en a le plus besoin")


def test_la_taille_affichee_dit_qu_elle_est_celle_du_texte():
    """« 85 o » à côté de « RC.pdf » se lit comme la taille du PDF.

    C'est celle du texte extrait. Le mot manquait, et il change ce que le
    chiffre veut dire.

    ANCRAGE. Cette règle s'ancrait sur la PREMIÈRE occurrence de
    `<li><span class="n">` dans le script — et une seconde liste, écrite plus
    haut pour la sélection du § 14, l'a fait lire un bloc qui n'est pas celui
    qu'elle garde. Elle couvre maintenant TOUS les endroits où le bloc du
    dossier conservé affiche une taille : la liste détaillée et la liste
    déroulante. Une règle qui n'en regarde qu'un reste verte pendant que
    l'autre ment.
    """
    js = _lire("ingenierie-dc.js")
    i = js.index("\n  function aoProjetRendre(")
    bloc = js[i:js.index("\n  function ", i + 10)]
    tailles = [m.end() for m in re.finditer(r"aoOctets\(", bloc)]
    assert tailles, "le dossier conservé n'affiche plus la taille de ses pièces"
    muettes = [bloc[k:k + 70].split("\n")[0] for k in tailles
               if "de texte" not in bloc[k:k + 70]]
    assert not muettes, (
        "%d endroit(s) affichent une taille sans dire qu'elle est celle du "
        "texte : %s" % (len(muettes), muettes))


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES DEUX SOURCES DE TEXTE, ET LEUR PRÉSÉANCE
# ═══════════════════════════════════════════════════════════════════════════

def _preseance(ordre):
    """La table de textes après avoir appliqué les deux sources dans `ordre`.

    `ordre` est une liste de [table, ecraser]. On EXÉCUTE `aoTextesPoser` :
    la règle de préséance est une règle de comportement, pas une ligne à
    reconnaître.
    """
    prog = (_js_source("aoTextesPoser")
            + "\nvar AO_TEXTES = {};"
            + "\nJSON.parse(process.env.O).forEach(function (x) {"
              " aoTextesPoser(x[0], x[1]); });"
            + "\nprocess.stdout.write(JSON.stringify(AO_TEXTES));")
    return json.loads(_node(prog, {"O": json.dumps(ordre)}))


def test_ce_qui_vient_d_etre_lu_l_emporte_sur_le_coffre_dans_les_deux_ordres():
    """LES DEUX RÉPONSES N'ARRIVENT PAS DANS UN ORDRE GARANTI.

    L'analyse d'abord puis l'état du projet — sauf quand l'état arrive au
    chargement, avant toute analyse. Une pièce redéposée sous le même nom
    remplace la sienne au dossier ; son texte doit suivre, sinon le lecteur
    montre l'ancienne version sous le relevé de la nouvelle.
    """
    frais, coffre = {"RC.pdf": "NEUF"}, {"RC.pdf": "VIEUX"}
    assert _preseance([[coffre, False], [frais, True]]) == {"RC.pdf": "NEUF"}
    assert _preseance([[frais, True], [coffre, False]]) == {"RC.pdf": "NEUF"}


def test_le_coffre_comble_ce_que_la_session_n_a_pas_lu():
    """LE TÉMOIN INVERSE. Si le coffre n'apportait rien, le lecteur serait
    muet sur un dossier conservé qu'on n'a pas redéposé — c'est-à-dire dans
    le cas pour lequel la conservation existe."""
    assert _preseance([[{"RC.pdf": "NEUF"}, True],
                       [{"CCAP.pdf": "DU COFFRE"}, False]]) == {
        "RC.pdf": "NEUF", "CCAP.pdf": "DU COFFRE"}


def test_le_texte_vide_n_ecrase_jamais_un_texte_lu():
    """Une pièce sans texte extrait ne doit pas effacer celui d'une autre
    source : on perdrait une lecture au profit d'un vide."""
    assert _preseance([[{"RC.pdf": "LU"}, True],
                       [{"RC.pdf": ""}, True]]) == {"RC.pdf": "LU"}


def test_le_coffre_rend_le_texte_de_ses_pieces_par_nom():
    """`aoTextesDuCoffre` lit le dossier conservé. Une pièce sans texte n'y
    entre pas : une entrée vide ferait afficher un lecteur vide plutôt que le
    message qui explique pourquoi."""
    prog = (_js_source("aoTextesDuCoffre")
            + "\nprocess.stdout.write(JSON.stringify("
              "aoTextesDuCoffre(JSON.parse(process.env.D))));")
    d = {"pieces": [{"nom": "RC.pdf", "texte": "ABC"},
                    {"nom": "plan.dwg", "texte": ""},
                    {"nom": "sans-nom", "texte": "X"}]}
    out = json.loads(_node(prog, {"D": json.dumps(d)}))
    assert out == {"RC.pdf": "ABC", "sans-nom": "X"}, out


# ═══════════════════════════════════════════════════════════════════════════
#  5. LA LISIBILITÉ DU SURLIGNAGE, MESURÉE
# ═══════════════════════════════════════════════════════════════════════════
# Un surlignage qui ne se distingue pas du fond ne surligne rien ; un
# surlignage sur lequel le texte devient illisible cache précisément ce qu'il
# désigne. Les deux se calculent.

def _lum(hexa):
    h = hexa.lstrip("#")
    def c(i):
        v = int(h[i:i + 2], 16) / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return .2126 * c(0) + .7152 * c(2) + .0722 * c(4)


def _contraste(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + .05) / (min(la, lb) + .05)


def _composer(rgba, alpha, fond):
    f = fond.lstrip("#")
    return "#%02X%02X%02X" % tuple(
        int(round(rgba[k] * alpha + int(f[k * 2:k * 2 + 2], 16) * (1 - alpha)))
        for k in (0, 1, 2))


def test_le_surlignage_se_voit_et_reste_lisible():
    """Les deux contraintes ensemble, calculées sur la composition réelle.

    Le halo doit se détacher du fond de lecture (≥ 3:1, seuil des éléments non
    textuels) ET le texte doit rester lisible dessus (≥ 4,5:1). C'est cette
    seconde contrainte qui impose d'inverser la couleur du texte : un texte
    clair sur l'ambre à .75 retombe à 2,54:1 — illisible exactement là où il
    faut lire.
    """
    page = _lire("ingenierie-datacenter.html")
    m = re.search(r"\.ig-ao-mk\{[^}]*background:\s*rgba\((\d+),\s*(\d+),\s*"
                  r"(\d+),\s*\.?(\d+)\)[^}]*color:\s*(#[0-9A-Fa-f]{6})", page)
    assert m, "la couleur du surlignage n'est plus lisible dans la feuille"
    rgba = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    alpha = float("0." + m.group(4))
    encre = m.group(5)

    # Le fond de lecture : un voile noir sur --panel, comme la feuille le pose.
    mf = re.search(r"\.ig-ao-lect-t\{[^}]*background:\s*rgba\(0,\s*0,\s*0,\s*"
                   r"\.?(\d+)\)", page)
    assert mf, "le fond de la surface de lecture n'est plus lisible"
    mp = re.search(r"--panel\s*:\s*(#[0-9A-Fa-f]{6})", _lire("styles.css"))
    assert mp, "--panel n'est plus déclarée"
    lec = _composer((0, 0, 0), float("0." + mf.group(1)), mp.group(1))
    lec = _composer((0, 0, 0), 0.30, lec)      # le panneau porte lui aussi un voile

    halo = _composer(rgba, alpha, lec)
    c_fond = _contraste(halo, lec)
    c_texte = _contraste(encre, halo)
    assert c_fond >= 3.0, (
        "le surlignage tient %.2f:1 sur la surface de lecture : il ne se voit "
        "pas comme un surlignage" % c_fond)
    assert c_texte >= 4.5, (
        "le texte tient %.2f:1 sur le surlignage : il cache ce qu'il désigne"
        % c_texte)


def test_la_surface_de_lecture_tient_un_long_texte():
    """On y lit parfois plusieurs centaines de lignes. Le contraste d'une
    étiquette ne suffit pas : on exige davantage que le plancher AA."""
    page, css = _lire("ingenierie-datacenter.html"), _lire("styles.css")
    mf = re.search(r"\.ig-ao-lect-t\{[^}]*background:\s*rgba\(0,\s*0,\s*0,\s*"
                   r"\.?(\d+)\)", page)
    mp = re.search(r"--panel\s*:\s*(#[0-9A-Fa-f]{6})", css)
    mi = re.search(r"--ink\s*:\s*(#[0-9A-Fa-f]{6})", css)
    assert mf and mp and mi
    lec = _composer((0, 0, 0), 0.30, mp.group(1))
    lec = _composer((0, 0, 0), float("0." + mf.group(1)), lec)
    c = _contraste(mi.group(1), lec)
    assert c >= 9.0, "la surface de lecture tient %.2f:1" % c
