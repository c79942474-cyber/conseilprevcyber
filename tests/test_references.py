# -*- coding: utf-8 -*-
"""LE REGISTRE DES MISSIONS — /references

CE QUE CETTE PAGE EST, ET CE QU'ELLE N'EST PAS. Elle donne, mission par
mission, le donneur d'ordre, l'objet, la période et l'interlocuteur — ce qu'un
acheteur demande pour VÉRIFIER. Elle ne raconte pas ce qui a été conduit :
c'est le rôle de /etudes-de-cas. Six missions figurent dans les deux, et
chaque page dit que l'autre existe, sans quoi le recouvrement passerait pour
une redite.

DEUX DÉCISIONS Y SONT PRISES, ET CES RÈGLES LES TIENNENT.

  — AUCUN NOM DE PERSONNE PHYSIQUE. Le document de références nomme cinq
    interlocuteurs : nom, employeur, poste. Dans un document privé, cela ne
    pose rien. Sur une page ouverte, c'est une DIFFUSION DE DONNÉES
    PERSONNELLES, qui demande l'accord des intéressés — accord qui n'a pas été
    sollicité pour cet usage. La page désigne donc chacun par sa fonction et sa
    direction, et renvoie les coordonnées à la demande. La règle nomme les cinq
    et exige leur absence : c'est une décision, elle doit être vérifiable.

  — AUCUNE CITATION DE CLIENT. Le document n'en contient pas. Une page de
    références qui en afficherait aurait donc des recommandations rédigées à la
    place de ceux à qui elles seraient attribuées.

ET UN DÉFAUT TROUVÉ EN NAVIGATEUR, qui ne se voyait pas à la lecture : le pied
de page a été repris de /etudes-de-cas et entraînait avec lui les balises
<script> qui le suivaient. etudes-cartes.js s'exécutait DEUX FOIS et clonait au
second passage les copies du premier — trente copies de dérive pour dix cartes.
Rien ne plantait ; le rail était trois fois trop long. La règle vaut désormais
pour les deux pages.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

PAGE = "references.html"
URL = "/references"
PAGES_A_CARTES = (PAGE, "etudes-de-cas.html")


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _texte(html_):
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", html_))).strip()


def _cartes(nom=PAGE):
    src = _src(nom)
    out = {}
    for m in re.finditer(r'<button type="button" class="case (e\d+)"', src):
        out[m.group(1)] = src[m.start():src.index("</button>", m.start())]
    return out


CARTES = _cartes()

# ═══════════════════════════════════════════════════════════════════════════
#  1. LES DIX MISSIONS, ET CE QUE CHACUNE DOIT DIRE
# ═══════════════════════════════════════════════════════════════════════════

# Le registre, tel que le document de références l'énonce : l'intitulé, la
# période, et deux termes qui ne peuvent pas s'être perdus en route.
REGISTRE = {
    "e4":  ("DT MASTER-CARBON", "2023 — 2026", ["Net Zéro", "cofondateur"]),
    "e1":  ("EDF / TALAN Consulting", "2022 — 2024", ["DSI EDF", "risques IA"]),
    "e2":  ("RENAULT GROUP", "2021 — 2022", ["WP.29", "CSMS"]),
    "e3":  ("ALSTOM / AIRBUS Cyberdéfense", "2021", ["SIEM", "Réseau express métropolitain"]),
    "e5":  ("ATOS / Société du Grand Paris", "2021", ["EBIOS RM", "EGIS"]),
    "e6":  ("GRDF / THALES Cyber", "2020", ["biométhane", "système d’information industriel"]),
    "e7":  ("Éditeur de solutions logicielles et IA", "En cours",
            ["règlement européen sur l’intelligence artificielle", "six mois"]),
    "e8":  ("Campus Numérique in the Alps", "En cours", ["alternance", "intelligence artificielle"]),
    "e9":  ("CONSEILPREV — plateformes numériques", "En cours", ["i-aes.com", "i-aes.eu"]),
    "e10": ("Projet confidentiel — infrastructure IA agentique", "En cours",
            ["agents métier", "Trois phases"]),
}


def test_les_DIX_missions_sont_la_et_pas_une_de_plus():
    assert len(CARTES) == 10, sorted(CARTES)
    assert set(CARTES) == set(REGISTRE), (sorted(CARTES), sorted(REGISTRE))


@pytest.mark.parametrize("cle", sorted(REGISTRE))
def test_chaque_mission_porte_son_intitule_sa_periode_et_sa_substance(cle):
    """LA PÉRIODE EST CHERCHÉE LÀ OÙ ELLE S'AFFICHE, ET NON DANS LA CARTE.
    Une mutation qui l'effaçait du bandeau du recto a survécu à la première
    version de cette règle : la période figure AUSSI sur l'en-tête du verso,
    et chercher dans la carte entière laissait l'une couvrir l'autre. Les deux
    endroits sont donc mesurés séparément — et ils doivent s'accorder."""
    nom, periode, termes = REGISTRE[cle]
    b = CARTES[cle]
    lu = _texte(b)
    assert nom in lu, "%s : intitulé absent" % cle
    bas = _texte(re.search(r'<span class="case-bas">(.*?)</span>\s*</span>', b, re.S).group(1))
    assert periode in bas, "%s : le recto n'affiche plus la période (%r)" % (cle, bas)
    etat = _texte(re.search(r'<span class="v-etat">(.*?)</span>', b, re.S).group(1))
    assert periode == etat, (
        "%s : le recto dit %r et le verso %r" % (cle, periode, etat))
    manquants = [t for t in termes if _texte(t) not in lu]
    assert not manquants, "%s a perdu : %s" % (cle, ", ".join(manquants))


@pytest.mark.parametrize("cle", sorted(REGISTRE))
def test_chaque_carte_a_ses_deux_faces_et_de_quoi_les_lire(cle):
    b = CARTES[cle]
    assert b.count('class="case-face case-recto"') == 1
    assert b.count('class="case-face case-verso"') == 1
    recto = b[b.index("case-recto"):b.index("case-verso")]
    verso = b[b.index("case-verso"):]
    assert len(_texte(recto)) >= 50, "%s : recto de %d caractères" % (cle, len(_texte(recto)))
    # LE PROPOS EST MESURÉ, PAS LE VERSO. Un verso porte aussi son en-tête, son
    # intitulé et son pied : vider le seul paragraphe qui raconte la mission le
    # laissait au-dessus du seuil, et la règle passait sur une carte devenue
    # muette. C'est le paragraphe qu'on mesure.
    #
    # ET LE PLANCHER VIENT DU DOCUMENT, PAS D'UN NOMBRE ROND. Posé d'abord à
    # 110, il faisait tomber TROIS fiches véridiques — GRDF (69 caractères),
    # ALSTOM (73), ATOS (107) : le document de références les énonce en une
    # phrase, et une règle qui exige plus force à broder. Le plancher est donc
    # calé sous la plus courte des dix, à 60, ce qui laisse quand même tomber
    # un propos remplacé par deux mots-clés.
    propos = _texte(re.search(r'<span class="para">(.*?)</span>', verso, re.S).group(1))
    assert len(propos) >= 60, (
        "%s : le propos ne fait que %d caractères — « %s »"
        % (cle, len(propos), propos))
    assert '<span class="tags">' in recto, "%s : pas de mots-clés sur la face visible" % cle
    assert "Interlocuteur" in verso, "%s : le verso ne dit pas auprès de qui vérifier" % cle


# ═══════════════════════════════════════════════════════════════════════════
#  2. LA DÉCISION QUI ENGAGE — aucune personne physique nommée
# ═══════════════════════════════════════════════════════════════════════════

# CES CINQ NOMS FIGURENT AU DOCUMENT DE RÉFÉRENCES, ET NE DOIVENT PAS FIGURER
# SUR LA PAGE OUVERTE. Les écrire ici n'est pas les publier : ce fichier n'est
# pas servi, et c'est le seul endroit où la décision devient vérifiable. Sans
# eux, la règle ne mesurerait rien — elle affirmerait.
NOMS_DU_DOCUMENT = ["Carlos Galan", "Romain Doaré", "Milette Sumawang",
                    "Laurent Moine", "Abel Bouchara"]


def test_AUCUN_NOM_DE_PERSONNE_PHYSIQUE_n_est_publie():
    """Publier le nom, l'employeur et le poste d'une personne sur une page
    ouverte est une diffusion de données personnelles : elle demande son
    accord, qui n'a pas été sollicité pour cet usage. La page désigne donc
    chacun par sa fonction, et renvoie les coordonnées à la demande."""
    lu = _texte(_src(PAGE))
    trouves = [n for n in NOMS_DU_DOCUMENT if n in lu]
    assert not trouves, (
        "des personnes physiques sont nommées sur une page ouverte : %s"
        % ", ".join(trouves))


def _interlocuteurs():
    for cle, bloc in CARTES.items():
        m = re.search(r"<strong>Interlocuteur&nbsp;:</strong>\s*(.*?)\.<br>", bloc, re.S)
        if not m:
            m = re.search(r"<strong>Interlocuteur&nbsp;:</strong>\s*(.*?)\.", bloc, re.S)
        assert m, "%s : pas d'interlocuteur déclaré" % cle
        yield cle, _texte(m.group(1))


# Un interlocuteur est désigné par CE QU'IL FAIT, jamais par qui il est. Le
# vocabulaire est déclaré ici pour que la règle mesure au lieu de supposer.
FONCTIONS = ("direction", "responsable", "expertise", "consultant", "contrat",
             "projet", "pôle")


def test_chaque_interlocuteur_est_designe_par_sa_FONCTION():
    """LE DÉFAUT QUE CETTE RÈGLE PREND, ET QUE LA PRÉCÉDENTE NE PRENDRAIT PAS :
    un nom qui ne figure pas dans la liste des cinq. Elle ne cherche donc pas
    l'absence d'un nom, elle exige la PRÉSENCE d'une fonction — « Direction de
    la sûreté du SI » passe, « Jean Dupont » non."""
    fautes = []
    for cle, qui in _interlocuteurs():
        if not any(f in qui.lower() for f in FONCTIONS):
            fautes.append("%s → « %s »" % (cle, qui))
    assert not fautes, (
        "des interlocuteurs ne sont pas désignés par une fonction :\n  %s\n"
        "vocabulaire attendu : %s" % ("\n  ".join(fautes), ", ".join(FONCTIONS)))


def test_la_page_DIT_pourquoi_elle_ne_nomme_personne():
    """Une page qui tait les noms sans dire pourquoi laisse croire qu'elle n'a
    rien à montrer. Elle dit la raison, et ce qui reste disponible."""
    lu = _texte(_src(PAGE))
    assert "Aucun nom de personne physique" in lu
    assert "données personnelles" in lu
    assert "sur demande" in lu, (
        "la page ne dit pas que les attestations et les coordonnées se "
        "fournissent : elle aurait l'air de n'avoir rien à produire")


def test_aucune_citation_de_client_n_est_ATTRIBUEE_a_quiconque():
    lu = _texte(_src(PAGE))
    assert "Aucune citation de client" in lu
    assert "«" not in lu.replace("« Postes", ""), (
        "des guillemets français apparaissent : une citation aurait été "
        "rédigée à la place de celui à qui elle serait attribuée")


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES ÉTATS — les deux faces disent la même chose
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_carte_declare_UN_etat_et_ses_deux_faces_s_accordent():
    scelles = internes = achevees = 0
    for cle, bloc in CARTES.items():
        lu = _texte(bloc)
        scelle = 'class="scelle"' in bloc
        interne = 'class="interne"' in bloc
        assert not (scelle and interne), "%s porte deux états" % cle
        if scelle:
            scelles += 1
            assert "engagement de confidentialité" in lu, cle
            assert "Mission en cours." in lu, cle
            assert "Attestation de bonne exécution" not in lu, (
                "%s est confidentielle et promet une attestation" % cle)
        elif interne:
            internes += 1
            assert "Projet interne, sans donneur d’ordre." in lu, cle
            assert "engagement de confidentialité" not in lu, cle
        else:
            achevees += 1
            assert "Mission achevée." in lu, cle
            assert "Attestation de bonne exécution" in lu, cle
    assert (achevees, scelles, internes) == (6, 3, 1), (achevees, scelles, internes)


def test_le_nom_accessible_porte_l_etat_et_AUCUN_balisage():
    """Le même défaut avait été pris sur /etudes-de-cas : le gabarit injectait
    la marque d'état dans aria-label telle qu'elle est écrite, c'est-à-dire du
    balisage — l'attribut se refermait au premier guillemet."""
    import html as _h
    for m in re.finditer(r'aria-label="([^"]*)"', _src(PAGE)):
        v = _h.unescape(m.group(1))
        assert "<" not in v and ">" not in v and v.strip(), v[:70]
    for cle, bloc in CARTES.items():
        lu = re.search(r'aria-label="([^"]*)"', bloc).group(1)
        attendu = ("mission en cours" if 'class="scelle"' in bloc
                   else "projet interne, sans donneur d’ordre"
                   if 'class="interne"' in bloc else "mission achevée")
        assert attendu in lu, "%s annonce « %s »" % (cle, lu)


# ═══════════════════════════════════════════════════════════════════════════
#  4. LA PAGE EST SERVIE, ATTEINTE, ET LISIBLE SANS SCRIPT
# ═══════════════════════════════════════════════════════════════════════════

def test_un_VISITEUR_ANONYME_recoit_le_registre_et_non_une_connexion(anonyme):
    """CE QUE LES GARDES NE COUVRENT PAS, ET QUE CETTE RÈGLE MESURE.

    Deux garde-fous refusent déjà le démarrage : celui d'acces.py, si la page
    se sert sans que l'ouverture soit décidée ; et celui d'app.py, si elle est
    au menu sans route. Aucun des deux ne regarde CE QUE REÇOIT le visiteur.
    Une page ouverte au menu, routée, déclarée — et posée derrière un
    formulaire de connexion — les passerait tous les deux.

    On demande donc la page sans compte, et on vérifie qu'elle rend le
    registre. C'est ce que voit l'acheteur qui reçoit le lien par courriel."""
    r = anonyme.get(URL)
    assert r.status_code == 200, r.status_code
    lu = _texte(r.get_data(as_text=True))
    assert "Registre des missions" in lu or "Dix missions" in lu, lu[:200]
    for cle in ("e1", "e9"):
        assert REGISTRE[cle][0] in lu, REGISTRE[cle][0]
    assert "Mot de passe" not in lu and "Connexion à votre espace" not in lu, (
        "le visiteur anonyme reçoit un formulaire de connexion")
    import acces
    assert URL in acces.DIRECT


def test_les_dix_missions_sont_LISIBLES_SANS_SCRIPT(anonyme):
    """Un registre que le script fabriquerait serait invisible à l'indexeur, au
    lecteur sans script et à l'aperçu partagé — c'est-à-dire à l'acheteur qui
    reçoit le lien dans un courriel."""
    lu = _texte(anonyme.get(URL).get_data(as_text=True))
    for cle, (nom, periode, termes) in REGISTRE.items():
        assert nom in lu, nom
        assert termes[0] in lu, (cle, termes[0])


@pytest.mark.parametrize("page,url", [(PAGE, URL),
                                      ("etudes-de-cas.html", "/etudes-de-cas")])
def test_chaque_script_est_servi_ET_CHARGE_UNE_SEULE_FOIS(anonyme, page, url):
    """LE DÉFAUT, MESURÉ EN NAVIGATEUR : le pied de page repris d'une autre
    page entraînait ses balises <script>. etudes-cartes.js s'exécutait deux
    fois et clonait au second passage les copies du premier — trente copies de
    dérive pour dix cartes. Rien ne plantait, le rail était trois fois trop
    long. Une page qui charge deux fois le même script n'est jamais correcte."""
    servi = anonyme.get(url).get_data(as_text=True)
    scripts = re.findall(r'<script src="(/[^"?]+\.js)', servi)
    assert scripts, "la page ne référence aucun script ?"
    doubles = sorted({s for s in scripts if scripts.count(s) > 1})
    assert not doubles, "%s charge deux fois : %s" % (url, ", ".join(doubles))
    fautes = []
    for s in scripts:
        r = anonyme.get(s)
        t = (r.headers.get("Content-Type") or "").lower()
        if r.status_code != 200 or "javascript" not in t:
            fautes.append("%s → %d, type %r" % (s, r.status_code, t))
    assert not fautes, "\n  ".join(fautes)


def test_le_parcours_qui_visite_la_page_la_PONDERE_aussi():
    """Une étape dont l'URL n'a pas d'axe ne pèse rien : le parcours la
    traverse, et le classement par rôle l'ignore. La couverture serait verte
    et la page resterait sans poids."""
    js = _src("parcours.js")
    axes = re.search(r'"%s":\s*\[([^\]]*)\]' % URL, js)
    assert axes, "/references n'a aucun axe : l'étape ne pèserait rien"
    assert len(re.findall(r'"[^"]+"', axes.group(1))) >= 1
    assert 'url: "%s"' % URL in js, "aucun parcours ne visite la page"


# ═══════════════════════════════════════════════════════════════════════════
#  5. LES DEUX PAGES — un mécanisme, deux propos
# ═══════════════════════════════════════════════════════════════════════════

def test_le_mecanisme_des_cartes_N_EST_DEFINI_QU_UNE_FOIS():
    """LE PIÈGE QUE CETTE RÈGLE FERME : recopier le bloc CSS dans la seconde
    page. Les deux définitions auraient divergé au premier correctif — celui
    qui neutralise la loupe, par exemple, se serait appliqué à une page et pas
    à l'autre, et le défaut serait revenu sur une seule des deux."""
    # UN REMPLACEMENT PORTÉ N'EST PAS UNE REDÉFINITION, et la règle doit
    # savoir les distinguer : « .fiche-calc .case-co{...} » ajuste la taille du
    # nom sur la seule fiche chiffrée — c'est légitime, et une recherche par
    # sous-chaîne l'aurait compté comme une seconde définition. On ne cherche
    # donc que le sélecteur NU, en début de règle.
    for classe in ("case-pivot", "case-face", "kal-rail", "case-co"):
        nue = re.compile(r"(?:^|[}\n])\s*\.%s\s*\{" % classe, re.M)
        endroits = [f for f in ("styles.css",) + PAGES_A_CARTES
                    if nue.search(_src(f))]
        assert endroits == ["styles.css"], (
            ".%s est défini nu dans %s : le mécanisme doit vivre dans la "
            "feuille partagée, et nulle part ailleurs" % (classe, endroits))


@pytest.mark.parametrize("page", PAGES_A_CARTES)
def test_chaque_page_a_cartes_DIT_QUE_L_AUTRE_EXISTE(page):
    """Six missions figurent dans les deux. Sans un renvoi explicite, le
    recouvrement se lit comme une redite — et le lecteur choisit au hasard
    celle qui ne répond pas à sa question."""
    src = _src(page)
    autre = "/etudes-de-cas" if page == PAGE else URL
    # LE RENVOI EST UN LIEN DANS LE CHAPEAU, PAS DES MOTS QUELQUE PART. Une
    # mutation qui retirait la balise <a> en gardant le texte a survécu à la
    # première version : le pied de page et le bouton d'appel portaient
    # l'adresse ailleurs, et le chapeau gardait les mots sans le lien. On
    # mesure donc le lien, à l'endroit où le lecteur choisit sa page.
    tete = src[src.index('<section class="page-head">'):src.index("</section>")]
    assert 'href="%s"' % autre in tete, (
        "%s ne renvoie pas vers %s DANS SON CHAPEAU : le lecteur choisira au "
        "hasard celle qui ne répond pas à sa question" % (page, autre))
    mots = _texte(tete).lower()
    attendu = "registre" if autre == URL else "études de cas"
    assert attendu in mots, (
        "%s renvoie vers %s sans dire ce qu'on y trouve" % (page, autre))
