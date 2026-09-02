# -*- coding: utf-8 -*-
"""Où l'on arrive en se connectant, et comment on revient à l'accueil.

CE QUI ÉTAIT EN CAUSE. Après connexion, on atterrissait sur `/demo` — une page
qui s'intitule « Démonstration temps réel », affiche un bandeau « Données
SIMULÉES à des fins d'illustration » et tire ses chiffres de `Math.random()`.
Son mode « Temps réel » existe, mais n'est pas celui par défaut. Un acheteur qui
venait de régler arrivait donc sur des données fausses, sous un avertissement.

PERSONNE NE L'AVAIT DÉCIDÉ. `/demo` était le `next` par défaut écrit un jour
dans DEUX fichiers — `auth.py` et `connexion.html` —, et les courriels avaient
suivi la page d'atterrissage au lieu de suivre ce qui est vendu. Deux
exemplaires d'une même destination se séparent au premier changement : l'un des
deux continue d'envoyer ailleurs, et rien ne le signale.

ET LE BANDEAU N'AVAIT PAS DE RETOUR. La marque est cliquable — un usage, pas une
affordance ; l'accueil n'existait que dans le tiroir, au bas de la dernière
rubrique. Le premier lien du bandeau est désormais « Accueil », sur toutes les
pages qui le portent, et la règle les lit TOUTES : une liste figée cesse de
décrire le site dès qu'on y ajoute une page.
"""
import glob
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import auth                                                        # noqa: E402

BANDEAU = '<nav class="links" aria-label="Navigation principale">'


def _pages_du_bandeau():
    """Les pages qui portent la navigation principale, reconnues à son rôle.

    RECONNUES PAR L'ÉTIQUETTE D'ACCESSIBILITÉ, ET NON PAR UNE LISTE DE NOMS :
    c'est elle qui dit « ceci est LA navigation du site », et les pages
    d'administration, qui portent un autre bandeau, s'en excluent d'elles-mêmes.
    """
    trouvees = {}
    for chemin in sorted(glob.glob(os.path.join(ICI, "*.html"))):
        source = io.open(chemin, encoding="utf-8").read()
        if BANDEAU in source:
            trouvees[os.path.basename(chemin)] = source
    return trouvees


def test_aucune_page_ne_peut_sortir_du_controle_en_se_renommant():
    """LA FAILLE QU'UN SEUIL NE FERMAIT PAS. La première version de ce
    garde-fou exigeait « au moins quarante pages ». Une page qui renommait son
    étiquette — « Navigation du site » au lieu de « Navigation principale » —
    quittait alors silencieusement l'ensemble contrôlé : quarante-huit pages au
    lieu de quarante-neuf, seuil tenu, règle verte, et cette page-là ne ramenait
    plus à l'accueil sans que rien ne le dise. Une mutation l'a montré, et c'est
    la seule des cinq qui avait survécu.

    LA PROPRIÉTÉ, SANS LISTE FIGÉE : un `nav class="links"` porte l'étiquette de
    la navigation principale, OU n'en porte aucune. Les pages d'administration
    et d'authentification sont dans le second cas — elles ont un bandeau réduit,
    volontairement hors du site. Une troisième valeur d'étiquette n'existe pas,
    et c'est ce qu'on vérifie : ni seuil, ni énumération de fichiers.
    """
    import re as _re
    intruses = {}
    for chemin in sorted(glob.glob(os.path.join(ICI, "*.html"))):
        source = io.open(chemin, encoding="utf-8").read()
        if '<nav class="links"' not in source:
            continue
        i = source.index('<nav class="links"')
        ouverture = source[i:source.index(">", i) + 1]
        etiquette = _re.search(r'aria-label="([^"]*)"', ouverture)
        if etiquette and etiquette.group(1) != "Navigation principale":
            intruses[os.path.basename(chemin)] = etiquette.group(1)
    assert not intruses, (
        "des bandeaux portent une étiquette qui les soustrait au contrôle : %s"
        % intruses)


def test_toutes_les_pages_ramenent_a_l_accueil_en_premier():
    """Le premier lien du bandeau est l'accueil, partout où le bandeau existe.

    La règle porte sur le CHEMIN, pas sur le libellé : renommer « Accueil » en
    « Sommaire » reste permis, l'envoyer ailleurs non.
    """
    fautives = {}
    for nom, source in _pages_du_bandeau().items():
        i = source.index(BANDEAU) + len(BANDEAU)
        premier = re.search(r'<a\s+href="([^"]*)"', source[i:i + 400])
        if not premier or premier.group(1) != "/":
            fautives[nom] = premier.group(1) if premier else "aucun lien"
    assert not fautives, ("des pages ne ramènent pas à l'accueil en premier : %s"
                          % fautives)


def test_l_accueil_ne_figure_qu_une_fois_dans_le_bandeau():
    """Deux « Accueil » dans le même bandeau signeraient une insertion faite
    deux fois — le genre de doublon qu'une reprise mécanique produit et qu'une
    relecture ne voit pas sur quarante-neuf fichiers."""
    fautives = {}
    for nom, source in _pages_du_bandeau().items():
        i = source.index(BANDEAU)
        bloc = source[i:source.index("</nav>", i)]
        n = len(re.findall(r'<a\s+href="/"', bloc))
        if n != 1:
            fautives[nom] = n
    assert not fautives, "l'accueil figure plusieurs fois : %s" % fautives


def test_les_deux_atterrissages_ne_peuvent_pas_se_separer():
    """LE SERVEUR ET LA PAGE DOIVENT VISER LE MÊME ENDROIT.

    `auth.page_login` redirige un client déjà connecté ; `connexion.html`
    redirige après une connexion réussie. Deux exemplaires, deux fichiers, et
    aucun moyen pour la page — statique — de lire la constante du serveur. La
    règle les compare donc terme à terme : c'est elle, et rien d'autre, qui
    empêche que l'un des deux continue d'envoyer sur l'ancienne page.
    """
    page = io.open(os.path.join(ICI, "connexion.html"), encoding="utf-8").read()
    # Les commentaires sont ôtés : celui qui explique ce choix CITE l'ancienne
    # destination pour dire pourquoi elle a changé.
    js = re.sub(r"/\*.*?\*/", "", page, flags=re.S)
    defaut = re.search(r"\?\s*nextRaw\s*:\s*'([^']*)'", js)
    assert defaut, "la destination par défaut n'est plus lisible dans la page"
    assert defaut.group(1) == auth.ACCUEIL, (
        "la page vise %r et le serveur %r" % (defaut.group(1), auth.ACCUEIL))


def test_on_n_atterrit_plus_sur_une_page_de_donnees_simulees():
    """LA RÈGLE NE NOMME PAS `/demo`, ELLE LIT LA PAGE VISÉE. Interdire une
    URL par son nom laisserait passer la même faute sous une autre adresse ;
    et la faute n'était pas « c'est /demo », mais « c'est une page qui prévient
    elle-même qu'elle montre des données inventées »."""
    import app
    cible = app.PAGES.get(auth.ACCUEIL)
    assert cible, "la destination d'atterrissage ne correspond à aucune page"
    source = io.open(os.path.join(ICI, cible), encoding="utf-8").read()
    for aveu in ("Données <strong>simulées</strong>", "aucune donnée réelle",
                 "⚠ Démonstration"):
        assert aveu not in source, (
            "on atterrit sur une page qui s'annonce elle-même comme une "
            "démonstration (%s)" % aveu)
