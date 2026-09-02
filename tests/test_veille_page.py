"""La page de veille : ce qu'elle sert, et ce qu'elle ne détient pas.

LE DÉFAUT DE STRUCTURE QUE CES RÈGLES TIENNENT. La page portait sa propre table
de classement, écrite dans son script. Tant qu'il s'agissait de huit familles de
produits, cela pouvait passer ; avec six axes adossés au vocabulaire de la base
documentaire, une copie côté page serait un second vocabulaire — et un filtre
qui ne désigne plus rien ne lève aucune erreur, il rend simplement zéro
résultat. La page ne doit donc rien détenir : elle affiche ce que l'API classe.
"""
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import automation                                                   # noqa: E402
import veille_facettes as vf                                        # noqa: E402
import veille_sources                                               # noqa: E402

PAGE = open(os.path.join(ICI, "veille.html"), encoding="utf-8").read()


def _script_execute():
    """Le script de la page, COMMENTAIRES RETIRÉS.

    LA PREMIÈRE VERSION DE CES RÈGLES LISAIT LE FICHIER ENTIER, et elles ont
    échoué sur leur propre commentaire — celui qui explique quelle taxonomie a
    été retirée. Une règle qui compte les MOTS du fichier ne dit rien de ce que
    la page FAIT : elle serait restée verte devant une table de classement dont
    on aurait renommé les entrées, et elle tombe devant une phrase d'explication
    qui ne change rien. On ne regarde donc que ce qui s'exécute.

    Le pied de page et la navigation sont également hors champ : « NIS2 »,
    « DORA » ou « Veille » y sont de la prose et des liens, pas un vocabulaire
    de classement.
    """
    debut = PAGE.index("(function(){")
    fin = PAGE.index("})();", debut)
    code = PAGE[debut:fin]
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    return re.sub(r"^\s*//.*$", "", code, flags=re.M)


SCRIPT = _script_execute()


# ── 1. Le titre demandé ────────────────────────────────────────────────────

def test_le_titre_annonce_la_veille_reglementaire():
    attendu = "Veille : actualités réglementaires, nouveaux standards et normes"
    assert attendu in PAGE
    assert "réglementaires" in PAGE and "standards" in PAGE


def test_les_quatre_sujets_sont_annonces_au_lecteur():
    for mot in ("industrielle", "IA", "GRC", "centres de données"):
        assert mot in PAGE, mot


# ── 2. La page ne détient aucun vocabulaire ────────────────────────────────

def test_la_page_ne_recopie_pas_le_vocabulaire_de_la_maison():
    """LA RÈGLE DE STRUCTURE. Si un thème de la base documentaire apparaissait
    en dur dans la page, il y aurait deux exemplaires du vocabulaire — et c'est
    celui qu'on oublie de corriger qui reste, sans que rien ne le dise."""
    # LA BONNE LISTE EST CELLE QUE LE MODULE PEUT ÉMETTRE — pas tout
    # `rag_store.THEMES` : « Veille » y figure et est aussi le sujet de la page,
    # qui a le droit d'écrire son propre nom dans un message d'erreur. Ce qu'on
    # cherche, ce sont les valeurs qui divergeraient si la page tenait sa
    # propre table.
    emises = [n for n, _ in (vf.THEMES + vf.STANDARDS + vf.SECTEURS + vf.ENTREPRISES)]
    recopies = [t for t in emises if t in SCRIPT]
    assert not recopies, "vocabulaire recopié dans le script : %s" % recopies[:5]


def test_la_page_ne_contient_plus_la_taxonomie_des_vulnerabilites():
    """« Microsoft & Windows », « Linux & Unix », « Mobile » : les facettes d'un
    flux de vulnérabilités, sans objet devant un communiqué de la Commission."""
    for ancien in ("Linux & Unix", "Bases de donn\u00e9es", "Microsoft & Windows"):
        assert ancien not in SCRIPT, ancien
    # Et surtout : plus aucune expression régulière de classement. C'est la
    # forme qui compte, pas les noms — renommer les entrées aurait laissé la
    # règle précédente verte.
    assert "THEME_RULES" not in SCRIPT
    assert SCRIPT.count("/scada|") == 0


def test_les_six_axes_sont_proposes_au_lecteur():
    for identifiant in ("vdomaine", "vpays", "vtheme", "vstandard",
                        "vsecteur", "ventreprise", "vreg"):
        assert 'id="%s"' % identifiant in PAGE, identifiant


# ── 3. Ce que l'API sert ───────────────────────────────────────────────────

def test_la_veille_est_publique_et_rend_ses_facettes(anonyme):
    j = anonyme.get("/api/veille").get_json()
    assert j["ok"] is True
    assert "facettes" in j and "libelles_pays" in j["facettes"]
    assert set(j["facettes"]).issuperset(
        {"themes", "standards", "secteurs", "entreprises", "pays", "reglementaire"})


def test_les_elements_servis_sont_deja_classes(anonyme, monkeypatch):
    monkeypatch.setattr(automation, "veille_list", lambda limit=60: [
        {"guid": "g", "source": "cisa_ics", "title": "IEC 62443 advisory for SCADA",
         "link": "https://x", "published": 0, "resume": "Siemens SIMATIC."}])
    j = anonyme.get("/api/veille").get_json()
    it = j["items"][0]
    assert it["facettes"]["pays"] == "US"
    assert "IEC 62443" in it["facettes"]["standards"]
    assert "Siemens" in it["facettes"]["entreprises"]
    assert it["emetteur"] and it["lien_libelle"]


def test_la_mention_de_transparence_suit_la_realite(anonyme, monkeypatch):
    """UNE MENTION QUI DÉCRIT AUTRE CHOSE QUE LA RÉALITÉ VAUT MOINS QUE PAS DE
    MENTION. Par défaut on reprend le chapeau publié par la source : il n'y a
    aucune génération, et l'annoncer serait faux."""
    monkeypatch.setattr(automation, "VEILLE_RESUME", False)
    assert anonyme.get("/api/veille").get_json()["resume_ia"] is False
    monkeypatch.setattr(automation, "VEILLE_RESUME", True)
    assert anonyme.get("/api/veille").get_json()["resume_ia"] is True


def test_la_page_n_affiche_la_mention_que_si_l_api_le_dit():
    """Le pendant côté page : la mention est masquée, et n'apparaît que sur
    `resume_ia`. Une mention affichée en dur redeviendrait fausse."""
    assert 'id="vnote" style="display:none"' in PAGE
    assert "j.resume_ia" in PAGE


def test_le_filtre_par_pays_est_servi_par_l_api(anonyme, monkeypatch):
    monkeypatch.setattr(automation, "veille_list", lambda limit=60: [
        {"guid": "a", "source": "cisa_ics", "title": "US", "link": "", "published": 0, "resume": ""},
        {"guid": "b", "source": "certfr_avis", "title": "FR", "link": "", "published": 0, "resume": ""}])
    j = anonyme.get("/api/veille?pays=FR").get_json()
    assert [i["title"] for i in j["items"]] == ["FR"]


# ── 4. La table de santé ───────────────────────────────────────────────────

def test_la_sante_des_flux_est_reservee_a_l_administrateur(anonyme, connecte):
    assert anonyme.get("/api/admin/veille/sante").status_code in (401, 403, 302)
    assert connecte.get("/api/admin/veille/sante").status_code in (401, 403, 302)


def test_la_sante_nomme_chaque_flux_du_catalogue(admin):
    j = admin.get("/api/admin/veille/sante").get_json()
    assert j["total"] == len(veille_sources.SOURCES)
    cles = {l["cle"] for l in j["sources"]}
    assert cles == {s["cle"] for s in veille_sources.SOURCES}
    for ligne in j["sources"]:
        assert ligne["sante"] in ("ok", "muet", "jamais_joint", "pas_encore_essaye")


# ── 5. La mise en trois colonnes ───────────────────────────────────────────

def _regle_css(selecteur):
    """Le corps d'une règle CSS, COMMENTAIRES RETIRÉS.

    La première version de la règle suivante lisait le fichier entier — et
    elle est tombée sur MON PROPRE COMMENTAIRE, celui qui explique pourquoi il
    ne faut pas figer trois colonnes. Une règle qui compte les mots du fichier
    ne dit rien de ce que la page FAIT : elle serait restée verte devant une
    grille figée dont on aurait déplacé l'explication.
    """
    sans = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    m = re.search(re.escape(selecteur) + r"\s*\{([^}]*)\}", sans)
    return m.group(1) if m else ""


def test_la_liste_se_replie_au_lieu_de_figer_trois_colonnes():
    """TROIS COLONNES SUR UNE PAGE, PAS SUR UN TÉLÉPHONE.

    Figer trois colonnes donnerait des cartes de quatre-vingt-dix pixels sur un
    écran étroit. Le plancher de `minmax` fait le repli tout seul — trois
    colonnes sur la page, deux sur une tablette, une sur un téléphone — sans
    point de rupture à maintenir, donc sans point de rupture à oublier.
    """
    regle = _regle_css("#vlist")
    # `display` NOMMÉMENT : chercher « grid » tout court restait vrai grâce à
    # `grid-template-columns`, qui ne sert à rien sans la grille. Une mutation
    # passant en `display:block` survivait — la page serait revenue à une
    # colonne, avec la déclaration des trois toujours écrite au-dessus.
    assert "display:grid" in regle.replace(" ", "")
    assert "repeat(auto-fill,minmax(300px,1fr))" in regle
    assert "repeat(3," not in regle, "colonnes figées : illisible sur mobile"


def test_le_message_de_liste_vide_tient_toute_la_largeur():
    """Laissé dans une colonne, « aucun élément pour cette combinaison de
    filtres » se lirait comme un premier résultat vide plutôt que comme une
    réponse à la recherche."""
    assert "#vlist .vempty{grid-column:1/-1}" in PAGE


def test_la_section_n_est_plus_bridee_sous_la_largeur_de_page():
    """Neuf cents pixels convenaient à une colonne unique ; à trois, ils
    donneraient des cartes de deux cent quatre-vingt-quatre pixels."""
    assert 'class="section" style="padding-top:22px;max-width:900px"' not in PAGE


def test_le_chapeau_est_borne_sinon_les_colonnes_font_perdre_de_la_place():
    """CE QUI FAIT RÉELLEMENT GAGNER LA PLACE. Sans borne, un chapeau de
    régulateur de vingt lignes impose sa hauteur à toute la rangée : trois
    colonnes rendraient alors MOINS d'actualités par écran qu'une seule."""
    assert "-webkit-line-clamp:5" in PAGE


ORIGINE = {"Origin": "http://localhost"}


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


# ── LA PAGE VIDE DIT CE QUI S'EST PASSÉ, ET NE PROMET RIEN ───────────────
#
# CE QUI ÉTAIT ÉCRIT. « La collecte automatique démarre — les premières
# actualités apparaîtront ici sous quelques heures. » Et cela s'affichait
# indéfiniment : la page ne pouvait pas distinguer « le service vient de
# démarrer » de « les trente-six flux échouent depuis une semaine ». Une
# mention qui décrit autre chose que la réalité vaut moins que pas de mention ;
# celle-ci promettait en plus.

def test_l_etat_de_collecte_distingue_aucun_passage_d_un_passage_infructueux(anonyme):
    import automation
    automation._state.set("veille.last_pass", None)
    automation._state._mem.pop("veille.last_pass", None)
    j = anonyme.get("/api/veille").get_json()
    assert j["collecte"]["jamais"] is True and j["collecte"]["le"] is None

    automation._state.set("veille.last_pass", "1756600000000")
    j = anonyme.get("/api/veille").get_json()
    assert j["collecte"]["jamais"] is False
    assert j["collecte"]["le"] == 1756600000000


def test_un_passage_infructueux_laisse_quand_meme_sa_trace(monkeypatch):
    """Seul « last_new » existait : un passage qui ne rapporte rien ne laissait
    aucune trace, et c'est précisément le cas qu'il fallait pouvoir nommer."""
    import automation
    automation._state._mem.pop("veille.last_pass", None)
    monkeypatch.setattr(automation, "veille_sources_ordre", None, raising=False)
    monkeypatch.setattr(automation.veille_sources, "ordre_de_passage", lambda: [])
    assert automation.veille_refresh(fetcher=lambda url: []) == 0
    assert automation.veille_collecte()["jamais"] is False, (
        "un passage sans nouveauté n'a laissé aucune trace")


def test_la_page_porte_deux_messages_et_aucune_promesse_de_delai():
    src = _src("veille.html")
    corps = re.sub(r"/\*.*?\*/", "", re.sub(r"<!--.*?-->", "", src, flags=re.S), flags=re.S)
    assert "col.jamais" in corps, "la page ne distingue plus les deux états"
    assert "n’a pas encore eu lieu" in corps
    assert "n’ont rien rapporté au dernier passage" in corps
    # LA RÈGLE QUI EMPÊCHE LA PROMESSE DE REVENIR.
    for promesse in ("quelques heures", "bientôt", "prochainement", "sous peu",
                     "d’ici peu", "dans quelques"):
        assert promesse not in corps, "promesse de délai réintroduite : " + promesse


# ── DIAGNOSTIQUER NE DOIT PAS DEMANDER SIX HEURES ────────────────────────

def test_la_relance_rend_la_sante_du_passage_qu_elle_vient_de_faire(admin, monkeypatch):
    """L'état des flux vit en mémoire de PROCESSUS et le service tourne avec
    plusieurs ouvriers : un second appel pourrait tomber sur un ouvrier qui n'a
    rien collecté et rendre un tableau vide, qui se lirait « rien n'a tourné »."""
    import automation
    monkeypatch.setattr(automation, "veille_refresh", lambda: 0)
    j = admin.post("/api/admin/veille/refresh", headers=ORIGINE).get_json()
    assert j["ok"] is True
    assert "sources" in j and "total" in j and "a_regarder" in j
    assert len(j["sources"]) == j["total"] >= 30
    assert {"cle", "nom", "sante", "erreur"} <= set(j["sources"][0])


def test_la_relance_reste_reservee_a_l_administrateur(anonyme, connecte):
    for client in (anonyme, connecte):
        r = client.post("/api/admin/veille/refresh", headers=ORIGINE)
        assert r.status_code in (401, 403), r.status_code


def test_la_console_declenche_la_collecte_et_affiche_ce_retour():
    """La route existait et RIEN NE L'APPELAIT : le panneau ne lisait que la
    santé, et restait caché tant qu'aucun flux n'était signalé — donc tant que
    rien n'avait été essayé. Le bouton était inatteignable."""
    src = _src("admin.html")
    assert 'id="veilBtn"' in src
    assert "/api/admin/veille/refresh" in src
    # Le panneau n'est plus masqué par défaut, sinon le bouton reste hors
    # d'atteinte dans le cas même où il sert.
    bloc = src[src.index('id="veilPanel"'):src.index('id="veilPanel"') + 260]
    assert "display:none" not in bloc
    # Le retour de la relance est rendu directement, sans second appel.
    script = src[src.index("veilBtn.addEventListener"):]
    apres = script[:script.index("catch")]
    assert "veilRendre(j)" in apres
    assert "veille/sante" not in apres, "un second appel pourrait changer d'ouvrier"


# ═══════════════════════════════════════════════════════════════════════════
#  PARTAGER UN ÉLÉMENT DE VEILLE SUR LINKEDIN
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QUI EST PARTAGÉ N'EST PAS DE NOUS, ET C'EST LE POINT. L'adresse envoyée à
# LinkedIn est celle de l'ÉDITEUR — le bulletin du CERT-FR, l'avis de la CISA.
# Son robot ira lire cette page-là et y prendra ses balises OpenGraph : la carte
# publiée porte donc son titre, son image et son nom. Le classement que nous
# ajoutons (domaine, pays, standard) reste sur notre page. Nous ne signons pas
# le travail d'un autre, et c'est le comportement correct.
#
# LA CONTRAINTE QUI COMMANDE LE RESTE : `share-offsite` NE PREND QU'UNE URL.
# Depuis 2021 `title`, `summary` et `mini` sont ignorés en silence. Les
# transmettre donnerait l'illusion de maîtriser la carte publiée.

_GABARIT = PAGE[PAGE.index("function itemHTML"):PAGE.index("function render(")]


def test_la_page_ne_fabrique_aucune_adresse_de_partage():
    """LE MÊME PRINCIPE QUE POUR LE VOCABULAIRE, APPLIQUÉ AU PARTAGE. Une
    adresse recopiée dans le script en ferait un second exemplaire, et c'est
    celui qu'on oublie de corriger qui partirait sur LinkedIn — sans erreur,
    sans trace, sur le compte du lecteur.
    """
    assert "linkedin.com" not in PAGE.lower(), (
        "la page porte une adresse LinkedIn en dur ; elle doit la recevoir de "
        "l'API, qui en est le seul dépositaire")
    assert re.search(r"partage\s*&&\s*j\.partage\.linkedin", PAGE), (
        "la page doit lire le point d'entrée servi par /api/veille")


def test_l_api_sert_un_point_d_entree_de_partage_utilisable(anonyme):
    """UNE CLÉ QUI EXISTE NE SUFFIT PAS : elle doit mener quelque part. La
    règle vérifie la FORME — un point d'entrée de partage qui attend une URL —
    plutôt que la chaîne exacte, qui doit pouvoir changer le jour où LinkedIn
    change la sienne.
    """
    p = (anonyme.get("/api/veille").get_json() or {}).get("partage") or {}
    lien = p.get("linkedin") or ""
    assert lien.startswith("https://"), "le point d'entrée doit être en https : %r" % lien
    assert "linkedin.com" in lien, "le point d'entrée doit être chez LinkedIn : %r" % lien
    assert lien.rstrip().endswith("="), (
        "le point d'entrée doit se terminer par le paramètre à compléter, "
        "sinon la page devrait savoir comment l'assembler : %r" % lien)


def test_un_element_sans_adresse_ne_recoit_pas_de_bouton():
    """LA VEILLE PUBLIE UN ÉLÉMENT SANS LIEN PLUTÔT QUE DE L'OMETTRE — c'est
    une règle de ce dépôt, et elle a sa raison. Mais lui coller un bouton de
    partage produirait un partage VIDE : le lecteur publierait sur son compte
    un lien qui ne mène nulle part, et un partage erroné ne se reprend pas.

    La propriété : la construction du bouton dépend DES DEUX conditions — le
    point d'entrée reçu du serveur, et l'adresse de l'élément.
    """
    m = re.search(r"var part\s*=\s*\(([^)]*)\)", _GABARIT)
    assert m, "le bouton de partage n'est plus construit sous une garde"
    garde = m.group(1)
    assert "LINKEDIN" in garde, (
        "sans le point d'entrée, la page fabriquerait l'adresse elle-même : %r"
        % garde)
    assert "lien" in garde, (
        "un élément sans adresse recevrait un bouton de partage vide : %r"
        % garde)


def test_l_adresse_de_la_source_est_encodee_avant_d_etre_partagee():
    """UNE ADRESSE AVEC UN `&` CASSE LE PARTAGE SANS RIEN LEVER. Beaucoup de
    bulletins portent des paramètres de requête ; passée telle quelle, la
    partie située après le premier `&` serait lue par LinkedIn comme un de SES
    paramètres, et l'adresse partagée serait tronquée. Le lecteur publierait un
    lien mort en croyant partager l'article.
    """
    bloc = _GABARIT[_GABARIT.index("var part"):]
    bloc = bloc[:bloc.index("return")]
    assert "encodeURIComponent" in bloc, (
        "l'adresse de la source doit être encodée avant d'entrer dans "
        "l'adresse de partage")


def test_le_bouton_se_nomme_pour_qui_ne_voit_pas_l_icone():
    """UNE ICÔNE SEULE N'EST PAS UN LIBELLÉ. Un lecteur d'écran annoncerait un
    lien sans destination ni objet ; la règle exige que le bouton porte son
    intention ET de quoi distinguer un élément d'un autre — soixante boutons
    « Partager sur LinkedIn » identiques ne se distinguent pas à l'oreille.
    """
    bloc = _GABARIT[_GABARIT.index("var part"):]
    bloc = bloc[:bloc.index("return")]
    assert "aria-label" in bloc, "le bouton de partage n'a pas de libellé accessible"
    apres = bloc[bloc.index("aria-label"):]
    assert "it.title" in apres[:220], (
        "le libellé accessible doit nommer l'élément partagé, sinon tous les "
        "boutons de la grille s'annoncent de la même façon")
