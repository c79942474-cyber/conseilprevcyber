# -*- coding: utf-8 -*-
"""Chaque article de loi cité par les conditions a été OUVERT, pas supposé.

POURQUOI CE FICHIER EXISTE. Le document annonçait « treize articles cités » ;
il en citait quinze. Personne ne l'avait vu, parce qu'aucune règle ne comptait :
la phrase « treize articles » était une affirmation, comme les phrases de droit
qu'elle chapeautait. Deux de ces phrases étaient fausses, et les deux au même
endroit — le renvoi de l'article L221-3.

CE QUE CES RÈGLES MESURENT, ET CE QU'ELLES REFUSENT DE FAIRE. Elles ne jugent
aucune clause : la validité se juge, et `outils/verifier_cgv.py` s'en occupe en
interrogeant le corpus. Elles vérifient trois choses, toutes vérifiables :

  · que ce que la page CITE et ce que la table VÉRIFIE soient le même ensemble,
    dans les deux sens — une citation ajoutée sans vérification tombe, une
    fiche dont la citation a disparu tombe aussi ;
  · que la page et la table ne puissent pas dériver l'une de l'autre sur le
    point qui a déjà fauté : la portée du renvoi de L221-3 est CALCULÉE depuis
    la table, et c'est cette valeur calculée qu'on cherche dans la page ;
  · que ce qui a été établi par une décision de justice, et non par la lettre
    d'un texte, porte le lien vers cette décision.

CE QU'UNE RÈGLE NE DOIT PAS FAIRE ICI : chercher « hors établissement » quelque
part dans la page. Le document fait trois cents lignes ; le mot s'y trouverait
pour dix raisons sans rapport, et la règle serait verte sans rien mesurer. Les
règles ci-dessous découpent la page en PARAGRAPHES — l'unité par laquelle un
contrat accorde quelque chose — et n'interrogent que ceux qui accordent au
titre de L221-3.
"""
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import cgv_articles                                                # noqa: E402
import paiement                                                    # noqa: E402


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _paragraphes(source):
    """La page en paragraphes, balises retirées et espaces normalisés.

    LE PARAGRAPHE ET NON LA PHRASE. « Le cas de l'article L221-3. » et « Qui les
    réunit toutes bénéficie du délai de quatorze jours » sont deux phrases et un
    seul octroi ; découper en phrases faisait perdre la seconde, et la règle
    croyait n'avoir trouvé qu'un octroi là où il y en a deux.
    """
    sortie = []
    for balise, dedans in re.findall(r"<(p|li)\b[^>]*>(.*?)</\1>",
                                     source, re.S | re.I):
        txt = re.sub(r"<[^>]+>", " ", dedans)
        txt = txt.replace("&nbsp;", " ").replace("&#160;", " ")
        txt = txt.replace("\u00a0", " ").replace("&amp;", "&")
        txt = re.sub(r"\s+", " ", txt).strip()
        if txt:
            sortie.append(txt)
    return sortie


# ── 1. LES DEUX SENS DE L'ACCORD ENTRE LA PAGE ET LA TABLE ────────────────

def test_chaque_article_cite_par_la_page_a_ete_ouvert():
    """Une citation qui n'est pas dans la table est une affirmation juridique
    que personne n'a vérifiée. C'est cette règle qui a attrapé L221-1 le jour
    où la correction l'a introduit dans le chapeau."""
    e = cgv_articles.etat()
    assert not e["non_verifies"], (
        "la page cite %s sans qu'aucune fiche ne dise sa version en vigueur ni "
        "ce qu'il dit" % ", ".join(e["non_verifies"]))


def test_aucune_fiche_ne_survit_a_la_disparition_de_sa_citation():
    """L'écart inverse, et il est plus sournois : la table décrit un document
    qui a changé. Une fiche orpheline donne l'impression d'un contrôle qui ne
    porte plus sur rien."""
    e = cgv_articles.etat()
    assert not e["orphelins"], (
        "la table vérifie %s, que la page ne cite plus"
        % ", ".join(e["orphelins"]))


def test_les_exceptions_sont_nommees_une_par_une_et_toutes_utiles():
    """Un nombre de quatre chiffres n'est pas toujours un article : le
    millésime d'une loi en a la forme. On les NOMME au lieu de les filtrer —
    et on exige que chaque nom serve encore, sinon la liste devient un fourre-
    tout où une vraie citation passerait inaperçue."""
    citees = set(cgv_articles.etat()["citees"])
    for jeton, motif in cgv_articles.NON_CITATIONS.items():
        assert jeton in citees, (
            "« %s » est écarté des citations alors que la page ne le contient "
            "plus : l'exception ne sert plus qu'à masquer" % jeton)
        assert len(motif) > 20, "l'exception « %s » n'est pas motivée" % jeton
        assert jeton not in cgv_articles.ARTICLES, (
            "« %s » est à la fois écarté et vérifié" % jeton)


def test_chaque_fiche_porte_sa_version_en_vigueur_et_son_adresse():
    """Une vérification sans date de version ne vaut rien : un code change, et
    « vérifié » sans « quelle version » ne dit pas si l'on parle du texte
    d'aujourd'hui."""
    for cle, f in cgv_articles.ARTICLES.items():
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", f.get("depuis") or ""), (
            "%s : pas de date de version en vigueur" % cle)
        assert (f.get("url") or "").startswith(cgv_articles.CORPUS + "/texte/"), (
            "%s : pas d'adresse où relire le texte" % cle)
        assert len(f.get("dit") or "") > 40, (
            "%s : la fiche ne dit pas ce que le texte dit" % cle)
        assert len(f.get("porte") or "") > 10, (
            "%s : la fiche ne dit pas ce que la page en tire" % cle)
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", cgv_articles.VERIFIE_LE)


def test_la_table_declare_la_version_du_contrat_qu_elle_a_verifiee():
    """Une table vérifiée sur la version « a » et publiée avec la version « b »
    dirait d'un texte ce qui a été lu dans un autre."""
    assert cgv_articles.VERSION == paiement.VERSION_CGV, (
        "la table dit avoir vérifié la version %s, le serveur en conserve %s"
        % (cgv_articles.VERSION, paiement.VERSION_CGV))
    assert cgv_articles.VERSION in _src("cgv.html")


# ── 2. LE CONSTAT A — LA CONDITION QUI MANQUAIT ───────────────────────────

def _octrois_au_titre_de_L221_3(source):
    """Les paragraphes où la page ÉTEND ou fait BÉNÉFICIER au titre de L221-3.
    Ce sont les seuls qui doivent nommer la condition — l'exiger partout ferait
    passer la règle sur des paragraphes sans rapport."""
    return [p for p in _paragraphes(source)
            if "L221-3" in p and re.search(r"étend|bénéfici", p)]


def test_tout_octroi_au_titre_de_L221_3_nomme_les_trois_conditions():
    """Le chapeau et l'article 5 énonçaient DEUX conditions sur trois. La
    troisième — le contrat conclu hors établissement — est celle qui décide, et
    c'est la seule que la vente en ligne ne remplit pas d'elle-même."""
    src = _src("cgv.html")
    octrois = _octrois_au_titre_de_L221_3(src)
    assert len(octrois) >= 2, (
        "la page n'accorde plus rien au titre de L221-3 : la règle ne mesure "
        "plus rien (trouvé %d paragraphe(s))" % len(octrois))
    for p in octrois:
        assert "hors établissement" in p, (
            "ce paragraphe accorde au titre de L221-3 sans dire que le contrat "
            "doit avoir été conclu hors établissement : « %s »" % p[:180])


def test_la_page_dit_que_la_vente_en_ligne_ne_suffit_pas():
    """Nommer la condition ne suffisait pas : un lecteur qui souscrit en ligne
    conclurait qu'il l'a remplie. La page doit dire le contraire, et le dire
    là où elle pose la réserve."""
    chapeau = next(p for p in _paragraphes(_src("cgv.html"))
                   if "L221-3" in p and "étend" in p)
    assert "L221-1" in chapeau, (
        "la réserve ne renvoie pas à la définition qui la commande")
    assert "présence physique simultanée" in chapeau, (
        "la réserve ne dit pas ce que « hors établissement » exige")
    assert re.search(r"en ligne ne suffit pas|ne suffit pas à remplir", chapeau), (
        "la réserve laisse croire qu'une souscription en ligne remplit la "
        "condition")


def test_l_arret_qui_tranche_est_cite_dans_la_page_et_a_ete_ouvert():
    """Un aperçu de recherche peut citer l'argument d'une partie et non ce que
    la cour juge. Les deux décisions du constat A ont été ouvertes ; celle qui
    tranche est nommée dans le contrat lui-même."""
    src = _src("cgv.html")
    for cle, d in cgv_articles.DECISIONS.items():
        assert "/decision/" in d["url"], "%s : pas une adresse de décision" % cle
        assert len(d["tient"]) > 60, (
            "%s : on ne sait pas ce que la décision juge" % cle)
    cass = cgv_articles.DECISIONS["cass-com-23-16.886"]
    assert "23-16.886" in src, (
        "l'arrêt qui refuse aux professionnels le régime des contrats à "
        "distance n'est pas cité dans les conditions")
    assert "4 septembre 2024" in src, (
        "l'arrêt est cité sans sa date : invérifiable pour le lecteur")
    assert cass["url"] in _src("docs/cgv-points-ouverts.md")


# ── 3. LE CONSTAT B — LA PORTÉE DU RENVOI, CALCULÉE ───────────────────────

def _sections_etendues():
    return sorted(n for n, s in cgv_articles.EXTENSION_L221_3.items()
                  if s["etendue"])


def test_la_portee_du_renvoi_est_celle_qui_a_ete_mesuree():
    """Les sections 2, 3 et 6 — et non la 4. C'est ce qui rend les deux
    constats cohérents : le législateur a étendu au petit professionnel
    l'appareil « hors établissement », et rien de l'appareil « à distance »."""
    assert _sections_etendues() == ["2", "3", "6"]
    assert cgv_articles.EXTENSION_L221_3["4"]["etendue"] is False
    for n, s in cgv_articles.EXTENSION_L221_3.items():
        assert re.match(r"^L221-\d+$", s["temoin"]), (
            "section %s : pas d'article témoin qui prouve où elle se trouve" % n)


def test_la_page_annonce_exactement_les_sections_que_la_table_a_mesurees():
    """LA RÈGLE QUI EMPÊCHE LA DÉRIVE. La liste cherchée dans la page n'est pas
    écrite ici : elle est CALCULÉE depuis la table. Changer la table sans
    changer la page, ou l'inverse, fait tomber cette règle — c'est exactement
    l'écart qui avait laissé passer la garantie du numérique."""
    sec = _sections_etendues()
    attendu = "sections %s et %s" % (", ".join(sec[:-1]), sec[-1])
    assert attendu in re.sub(r"\s+", " ", _src("cgv.html")), (
        "la page n'annonce pas « %s » : la portée du renvoi qu'elle affiche ne "
        "correspond plus à celle qui a été mesurée" % attendu)


def test_aucun_article_hors_portee_n_est_presente_comme_un_du_legal():
    """L'article 6 annonçait la garantie du numérique comme un effet du renvoi.
    Elle est au chapitre IV ; le renvoi ne l'atteint pas. On mesure la propriété
    et non la formule : toute phrase qui invoque L221-3 à côté d'un article que
    la table dit NON ÉTENDU doit dire d'où vient l'obligation."""
    src = _src("cgv.html")
    hors = {a for a, f in cgv_articles.ARTICLES.items() if f["etendu"] is False}
    assert hors, "plus aucun article hors portée : la règle ne mesure plus rien"
    vus = 0
    for p in _paragraphes(src):
        joints = [a for a in hors if a in p]
        if not ("L221-3" in p and joints):
            continue
        vus += 1
        assert "présent contrat" in p and "ne l'atteint pas" in p, (
            "ce paragraphe rattache %s au renvoi de L221-3 sans dire que le "
            "renvoi ne l'atteint pas, ni d'où vient alors l'obligation : "
            "« %s »" % (", ".join(joints), p[:180]))
    assert vus, (
        "aucun paragraphe ne rapproche L221-3 d'un article hors portée : soit "
        "la page a changé, soit le découpage ne la lit plus")


def test_la_garantie_maintenue_est_donnee_par_le_contrat_et_sa_duree_suit_le_texte():
    """Elle est maintenue — le document l'avait promise publiquement — mais sur
    le bon fondement, et avec la portée que L224-25-12 lui donne réellement :
    la période de fourniture, et non deux ans."""
    src = re.sub(r"\s+", " ", _src("cgv.html"))
    assert "par le présent contrat" in src
    assert "au cours de la période durant laquelle l'accès est fourni" in src
    assert "et non pendant deux ans" in src, (
        "la durée réelle de la garantie n'est pas dite ; « deux ans » est "
        "l'erreur que tout le monde fait ici")


# ── 4. CE QUI EST JUGÉ ET CE QUI EST ÉCRIT NE SE VÉRIFIENT PAS PAREIL ─────

def test_la_conformite_de_la_delivrance_porte_le_lien_vers_l_arret_qui_la_fonde():
    """L'article 1604 définit la délivrance comme « le transport de la chose
    vendue en la puissance et possession de l'acheteur ». La CONFORMITÉ n'y est
    pas écrite : elle est jugée. La page a raison, mais pas pour la raison
    qu'on croit en lisant le texte — et la fiche doit le dire."""
    f = cgv_articles.ARTICLES["1604"]
    assert "/decision/" in (f.get("juge") or ""), (
        "1604 : la proposition est jurisprudentielle et la fiche ne renvoie à "
        "aucune décision")
    assert "17-12.580" in f["dit"], (
        "1604 : la fiche affirme la conformité sans dire quel arrêt la pose")
    assert f["juge"] in _src("docs/cgv-points-ouverts.md")


def test_le_document_rend_la_table_sans_en_perdre_une_ligne():
    """Le document et le module diraient deux choses différentes si l'un
    changeait seul. On énumère : chaque article, avec SA date de version."""
    doc = _src("docs/cgv-points-ouverts.md")
    for cle, f in cgv_articles.ARTICLES.items():
        assert f["url"] in doc, "%s : absent du document" % cle
        ligne = next((l for l in doc.splitlines()
                      if l.startswith("| [%s](" % cle)), None)
        assert ligne, "%s : pas de ligne dans le tableau du document" % cle
        assert f["depuis"] in ligne, (
            "%s : le document ne porte pas la version en vigueur %s"
            % (cle, f["depuis"]))
    lignes = [l for l in doc.splitlines() if re.match(r"^\| \[[0-9L]", l)]
    assert len(lignes) == len(cgv_articles.ARTICLES), (
        "le tableau du document compte %d lignes pour %d articles vérifiés"
        % (len(lignes), len(cgv_articles.ARTICLES)))
