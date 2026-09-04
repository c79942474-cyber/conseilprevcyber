# -*- coding: utf-8 -*-
"""Tout formulaire public qui collecte des données porte sa mention d'information.

POURQUOI CETTE RÈGLE ÉNUMÈRE AU LIEU DE NOMMER. Une règle qui nommerait les
formulaires d'aujourd'hui laisserait passer celui qui sera écrit dans six mois.
Celle-ci RELÈVE tous les `<form>` du dépôt, écarte ceux qui n'appellent pas de
mention selon des critères énoncés ici, et exige de chaque autre les cinq
composantes de l'article 13 : finalité, base légale, durée, droits, lien.

LE TEXTE VIT DANS `rgpd.py`, LES PAGES LE RECOPIENT. La règle vérifie que la
copie est fidèle — des pages statiques qui portent chacune sa version divergent
à la première retouche, et c'est celle qu'on oublie qui reste fausse.

CE QUE LE CONSENTEMENT N'EST PAS. Une case « j'accepte que mes données soient
traitées », obligatoire pour envoyer, cumule deux défauts : elle invoque le
consentement (art. 6.1.a) là où traiter une demande ou tenir un compte relève
des mesures précontractuelles et du contrat (art. 6.1.b) ; et un consentement
exigé pour envoyer n'est pas libre (art. 7.4), donc invalide. Le Conseil d'État
l'a jugé sur cette forme (11 mars 2015, n° 368624).

MAIS TOUTE CASE OBLIGATOIRE N'EST PAS UN CONSENTEMENT RGPD, et la règle le
distingue explicitement. Trois cases conditionnent le paiement sur ce site :
la qualité professionnelle de l'acheteur, l'acceptation des conditions de vente,
et la renonciation au droit de rétractation (art. L221-25 du code de la
consommation). Ce sont des DÉCLARATIONS et des ACTES JURIDIQUES, exigés par le
droit de la consommation, pas des consentements au sens de l'article 4.11 du
RGPD : l'article 7.4 ne les concerne pas. Une règle qui les interdirait
supprimerait des cases que la loi impose — le défaut inverse, et tout aussi
grave.
"""
import io
import os
import re

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pages_html():
    """Toutes les pages du dépôt — pas une liste, le disque.

    Le relevé ne part d'AUCUNE liste écrite à la main : une page servie par une
    route à elle y tomberait autrement dans l'angle mort, et c'est précisément
    ce qui est arrivé sur le dépôt jumeau, où les trois pages qui ouvrent un
    compte échappaient au filet.
    """
    return sorted(n for n in os.listdir(RACINE) if n.endswith(".html"))


def _pages_atteignables():
    """Les pages qu'un VISITEUR peut ouvrir, selon la politique d'accès du site.

    POURQUOI CE TRI EXISTE, ET POURQUOI IL NE NOMME PERSONNE. La mention
    d'information est due à qui rencontre le formulaire. Une page d'admin,
    fermée par construction, n'est vue que par CONSEILPREV : lui réclamer une
    mention destinée au visiteur serait exiger une information que personne ne
    lira. Le tri ne nomme aucun fichier : il interroge `acces.py`, la politique
    qui décide déjà de ce qui est ouvert et dont l'application est vérifiée au
    démarrage. Une page qui deviendrait publique demain entrerait dans le filet
    le jour même, sans qu'on y touche.
    """
    import acces
    import app

    # PREMIÈRE SOURCE : le tableau des pages du menu.
    routes = {f: [r] for r, f in app.PAGES.items()}

    # DEUXIÈME SOURCE, ET C'EST ELLE QUI MANQUAIT. Connexion, inscription,
    # mot de passe oublié et réinitialisation ne figurent PAS dans ce tableau :
    # elles sont servies par des routes à elles, déclarées dans un blueprint.
    # S'arrêter au tableau les aurait laissées hors du filet — la faute exacte
    # commise sur le dépôt jumeau. La carte réelle des URL de Flask, elle, les
    # connaît toutes ; on l'interroge, et on rapproche chaque route de son
    # fichier par sa forme : « /admin/base-connaissance » et
    # « admin-base-connaissance.html » se rejoignent segment pour segment.
    for regle in app.app.url_map.iter_rules():
        segments = [s for s in str(regle.rule).strip("/").split("/")
                    if s and not s.startswith("<")]
        if not segments:
            continue
        routes.setdefault("-".join(segments) + ".html", []).append(str(regle.rule))

    ouvertes = set()
    for fichier in _pages_html():
        connues = routes.get(fichier)
        if not connues:
            # AUCUNE ROUTE CONNUE : on tranche du côté strict. Une page dont on
            # ignore comment elle est servie est présumée atteignable — mieux
            # vaut réclamer une mention de trop qu'en oublier une.
            ouvertes.add(fichier)
            continue
        if any(acces.ouvert(r) for r in connues):
            ouvertes.add(fichier)
    return ouvertes


CHAMPS_COLLECTE = ("email", "prenom", "prénom", "nom", "telephone", "téléphone",
                   "entreprise", "societe", "société", "organisation", "message",
                   "cv", "org")


def _formulaires():
    releve = []
    for nom in _pages_html():
        html = io.open(os.path.join(RACINE, nom), encoding="utf-8").read()
        for m in re.finditer(r"<form\b[^>]*>", html):
            ouverture = m.group(0)
            fermeture = html.find("</form>", m.end())
            corps = html[m.end():fermeture if fermeture != -1 else len(html)]
            ident = re.search(r'id="([^"]+)"', ouverture)
            releve.append((nom, ident.group(1) if ident else ouverture[:40], corps))
    return releve


def _champs(corps):
    """Les jetons qui NOMMENT les champs — id, name, placeholder, libellés.

    Chercher « nom » dans du HTML brut le trouve toujours : dans
    `autocomplete`, dans `nombre`, partout. On ne lit donc que ce qui nomme.
    """
    jetons = []
    for attribut in ("id", "name", "placeholder", "autocomplete"):
        jetons += re.findall(r'%s="([^"]*)"' % attribut, corps)
    jetons += re.findall(r"<label[^>]*>(.*?)</label>", corps, re.S)
    return " ".join(jetons).lower()


def _editable(balise):
    return not re.search(r"\b(disabled|readonly)\b", balise)


def _collecte(corps):
    """Ce formulaire collecte-t-il des données personnelles ?

      · il demande une identité ou des coordonnées MODIFIABLES — il collecte ;
      · il n'échange qu'un mot de passe sur un compte existant — il
        authentifie, l'information a été délivrée à l'ouverture ;
      · il n'offre que des cases à cocher ou des boutons — il ne collecte rien
        d'identifiant.
    """
    entrees = re.findall(r"<(?:input|textarea|select)\b[^>]*>", corps)
    modifiables = " ".join(
        b for b in entrees if _editable(b)
        and not re.search(r'type="(?:hidden|submit|button|checkbox|radio)"', b))
    noms = _champs(modifiables)
    demande_identite = any(re.search(r"\b%s\b" % re.escape(c), noms)
                           for c in CHAMPS_COLLECTE)
    if re.search(r'type="password"', corps) and not re.search(
            r'autocomplete="new-password"', modifiables):
        return False        # connexion pure
    return demande_identite


TOUS = _formulaires()
_ATTEIGNABLES = _pages_atteignables()
COLLECTEURS = [(f, i, c) for (f, i, c) in TOUS
               if _collecte(c) and f in _ATTEIGNABLES]


def test_le_tri_par_atteignabilite_ne_vide_pas_le_relevé():
    """Garde-fou : si `acces.ouvert` ou `app.PAGES` changeaient de forme, le
    tri renverrait un ensemble vide et TOUTES les règles ci-dessous
    deviendraient vertes sans rien mesurer."""
    assert len(_ATTEIGNABLES) >= 10, (
        "la politique d'accès ne déclare que %d page(s) ouverte(s) : le tri "
        "s'est probablement cassé." % len(_ATTEIGNABLES))

# Relevé du 4 septembre 2026 : 10 formulaires, dont 4 atteignables collectent
# — contact, vos projets, inscription et mot de passe oublié. Les deux
# formulaires d'admin et la réinitialisation sont fermés ; connexion,
# diagnostic et relecture ne collectent rien d'identifiant.
#
# LE POINT AVEUGLE DE TOUTE RÈGLE QUI ÉNUMÈRE CE QUI EXISTE : supprimer un
# formulaire supprime aussi l'essai qui le surveillait, et la suite reste verte.
# Le remède n'est pas de nommer les formulaires — ce serait renoncer à attraper
# les prochains — mais un PLANCHER : le faire baisser reste possible, et devient
# un geste délibéré, daté et motivé ici même.
PLANCHER_FORMULAIRES = 10
PLANCHER_COLLECTEURS = 4


def test_le_releve_trouve_bien_des_formulaires():
    assert len(TOUS) >= PLANCHER_FORMULAIRES, (
        "le relevé est tombé à %d formulaire(s), pour un plancher de %d : soit "
        "un formulaire a disparu — abaisser le plancher ici, en disant lequel "
        "et pourquoi —, soit le relevé s'est cassé et ne mesure plus rien."
        % (len(TOUS), PLANCHER_FORMULAIRES))
    assert len(COLLECTEURS) >= PLANCHER_COLLECTEURS, (
        "le nombre de formulaires vus comme collecteurs est tombé à %d, pour un "
        "plancher de %d." % (len(COLLECTEURS), PLANCHER_COLLECTEURS))


# ══════════════════════════════════════════════════════════════════════════
# Les cinq composantes de l'article 13
# ══════════════════════════════════════════════════════════════════════════
# « Base légale » exige la base de la COLLECTE (6.1.a ou 6.1.b), pas n'importe
# quel article 6.1 : une mention qui n'annoncerait plus que l'intérêt légitime
# de la prospection aurait perdu le fondement de sa finalité principale.
DUREE = (r"\d+\s*mois|trois ans|le temps du compte|"
         r"jusqu'à (?:votre|la) désinscription")
COMPOSANTES = {
    "finalité": (r"\bser(?:t|vent|vir)\b|traiter votre|instruire votre|"
                 r"créer et à tenir|tenir votre accès"),
    "base légale de la collecte": r"art\.\s*6\.1\.[ab]",
    "durée": DUREE,
    "droits": r"droits d'accès|rectification|effacement|opposition",
    "lien vers la politique": r'href="/politique-confidentialite"',
}


def _mention(corps):
    blocs = re.findall(r'<(p|div|span)[^>]*class="[^"]*rgpd-mention[^"]*"[^>]*>'
                       r'(.*?)</\1>', corps, re.S)
    return "\n".join(b for _, b in blocs)


@pytest.mark.parametrize("fichier,ident,corps", COLLECTEURS,
                         ids=["%s#%s" % (f, i) for f, i, _ in COLLECTEURS])
def test_un_formulaire_qui_collecte_porte_sa_mention(fichier, ident, corps):
    assert _mention(corps).strip(), (
        "%s#%s collecte des données personnelles et ne porte aucune mention "
        "d'information (art. 13). Ajouter un bloc de classe « rgpd-mention »."
        % (fichier, ident))


@pytest.mark.parametrize("fichier,ident,corps", COLLECTEURS,
                         ids=["%s#%s" % (f, i) for f, i, _ in COLLECTEURS])
def test_la_mention_porte_les_cinq_composantes(fichier, ident, corps):
    texte = _mention(corps)
    if not texte.strip():
        pytest.skip("mention absente : la règle précédente le dit déjà")
    manquantes = [nom for nom, motif in COMPOSANTES.items()
                  if not re.search(motif, texte, re.I)]
    assert not manquantes, (
        "%s#%s : la mention ne dit pas %s" % (fichier, ident, ", ".join(manquantes)))


@pytest.mark.parametrize("fichier,ident,corps", COLLECTEURS,
                         ids=["%s#%s" % (f, i) for f, i, _ in COLLECTEURS])
def test_chaque_finalite_annoncee_porte_sa_duree(fichier, ident, corps):
    """L'article 13.2.a exige la durée POUR CHAQUE finalité.

    Se contenter d'UNE durée quelque part laisserait passer une mention qui
    annonce deux finalités — la demande, puis la prospection — et n'en date
    qu'une. La mention est coupée là où la prospection commence (art. 6.1.f) :
    chaque moitié doit porter sa durée.
    """
    texte = _mention(corps)
    if not texte.strip():
        pytest.skip("mention absente : une autre règle le dit")
    coupe = re.search(r"art\.\s*6\.1\.f", texte, re.I)
    if not coupe:
        return
    for part, quoi in ((texte[:coupe.start()], "la demande elle-même"),
                       (texte[coupe.start():], "la prospection annoncée")):
        assert re.search(DUREE, part, re.I), (
            "%s#%s : aucune durée n'est annoncée pour %s (art. 13.2.a)"
            % (fichier, ident, quoi))


# ══════════════════════════════════════════════════════════════════════════
# La page recopie le texte canonique, à l'identique
# ══════════════════════════════════════════════════════════════════════════
def _sans_balises(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


@pytest.mark.parametrize("fichier,ident,corps", COLLECTEURS,
                         ids=["%s#%s" % (f, i) for f, i, _ in COLLECTEURS])
def test_la_mention_est_une_copie_fidele_du_texte_canonique(fichier, ident, corps):
    """Le texte affiché doit être MOT POUR MOT l'un de ceux de rgpd.py.

    Sans cette règle, une page pourrait porter les cinq composantes et dire
    autre chose que le registre — informer juste sur la forme, faux sur le
    fond.
    """
    import rgpd
    texte = _sans_balises(_mention(corps))
    if not texte:
        pytest.skip("mention absente : une autre règle le dit")
    canoniques = {cle: _sans_balises(v["texte"])
                  for cle, v in rgpd.MENTIONS_FORMULAIRES.items()}
    assert texte in canoniques.values(), (
        "%s#%s porte une mention qui ne correspond à aucun texte de "
        "rgpd.MENTIONS_FORMULAIRES. Soit la page a dérivé, soit le texte "
        "canonique doit être ajouté au module.\n  page : %s"
        % (fichier, ident, texte[:160]))


# ══════════════════════════════════════════════════════════════════════════
# Aucune case cochée ne conditionne un envoi — sauf celles que la loi impose
# ══════════════════════════════════════════════════════════════════════════
# Ce qui distingue une case interdite d'une case due, c'est CE QU'ELLE
# DÉCLARE : un consentement au traitement de données (interdit comme condition
# d'envoi, art. 7.4) ou un acte juridique exigé par le droit de la consommation
# (acceptation des conditions de vente, renonciation au droit de rétractation,
# déclaration de qualité professionnelle).
ACTES_DUS = ("conditions générales", "conditions de vente", "cgv",
             "rétractation", "retractation", "l221-25", "professionnel",
             "pour les besoins de mon activité")
CONSENTEMENT_RGPD = ("mes données", "mes donnees", "données personnelles",
                     "rgpd", "traitement de mes")


def _libelle_de_la_case(corps, position):
    """Le texte associé à une case : son <label> englobant ou suivant."""
    debut = max(0, position - 400)
    return corps[debut:position + 600].lower()


@pytest.mark.parametrize("fichier,ident,corps", TOUS,
                         ids=["%s#%s" % (f, i) for f, i, _ in TOUS])
def test_aucune_case_de_consentement_rgpd_ne_conditionne_l_envoi(fichier, ident,
                                                                 corps):
    for m in re.finditer(r"<input\b[^>]*type=\"checkbox\"[^>]*>", corps):
        balise = m.group(0)
        if "required" not in balise:
            continue
        libelle = _libelle_de_la_case(corps, m.start())
        if any(a in libelle for a in ACTES_DUS):
            continue        # acte juridique exigé par la loi, pas un consentement
        assert not any(c in libelle for c in CONSENTEMENT_RGPD), (
            "%s#%s : une case de consentement au traitement des données est "
            "obligatoire pour envoyer (%s). Un consentement exigé pour envoyer "
            "n'est pas libre (art. 7.4) ; le remplacer par une mention "
            "d'information." % (fichier, ident, balise.strip()))


@pytest.mark.parametrize("fichier,ident,corps", TOUS,
                         ids=["%s#%s" % (f, i) for f, i, _ in TOUS])
def test_aucune_case_n_est_precochee(fichier, ident, corps):
    """Une case cochée d'avance ne recueille aucun consentement : il faut un
    acte positif de la personne (CJUE, Planet49, C-673/17, 1er oct. 2019)."""
    for m in re.finditer(r"<input\b[^>]*type=\"checkbox\"[^>]*>", corps):
        balise = m.group(0)
        assert not re.search(r"\bchecked\b", balise), (
            "%s#%s : une case est cochée d'avance (%s) — aucun consentement "
            "n'est recueilli ainsi (CJUE, Planet49, C-673/17)."
            % (fichier, ident, balise.strip()))


# ══════════════════════════════════════════════════════════════════════════
# Ce que la mention annonce est ce que la politique publie
# ══════════════════════════════════════════════════════════════════════════
# LE DÉFAUT QUI A MOTIVÉ CETTE RÈGLE, sur le dépôt jumeau : une page annonçait
# sous son formulaire une conservation de « 13 mois » — la durée des COOKIES,
# reprise par inadvertance. Deux durées différentes pour la même donnée, sur le
# même site : l'information est fausse quelle que soit celle qui a raison.
#
# La comparaison porte sur la VALEUR, pas sur l'orthographe : « trois ans » et
# « 3 ans » disent la même chose, « 12 mois » et « 13 mois » non.
_NOMBRES = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
            "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11,
            "douze": 12, "treize": 13, "vingt-quatre": 24, "trente-six": 36}
_DUREE_VALEUR = re.compile(
    r"(\d+|%s)\s*(mois|ans?)" % "|".join(sorted(_NOMBRES, key=len, reverse=True)),
    re.I)


def _en_mois(texte):
    trouvees = set()
    for valeur, unite in _DUREE_VALEUR.findall(texte):
        v = int(valeur) if valeur.isdigit() else _NOMBRES.get(valeur.lower())
        if v is None:
            continue
        trouvees.add(v * 12 if unite.lower().startswith("an") else v)
    return trouvees


def _durees_publiees():
    chemin = os.path.join(RACINE, "politique-confidentialite.html")
    assert os.path.exists(chemin), "la politique publiée est introuvable"
    return _en_mois(io.open(chemin, encoding="utf-8").read())


def test_la_politique_publie_bien_des_durees():
    """Garde-fou : si l'extraction se cassait, la règle suivante deviendrait
    verte en comparant à un ensemble vide."""
    assert len(_durees_publiees()) >= 2, (
        "durées relevées dans la politique : %s — relevé suspect"
        % sorted(_durees_publiees()))


@pytest.mark.parametrize("fichier,ident,corps", COLLECTEURS,
                         ids=["%s#%s" % (f, i) for f, i, _ in COLLECTEURS])
def test_les_durees_annoncees_figurent_dans_la_politique(fichier, ident, corps):
    texte = _mention(corps)
    if not texte.strip():
        pytest.skip("mention absente : une autre règle le dit")
    orphelines = sorted(_en_mois(texte) - _durees_publiees())
    assert not orphelines, (
        "%s#%s annonce %s mois alors que la politique publiée ne fixe pas cette "
        "durée : soit la mention se trompe, soit la politique est à compléter."
        % (fichier, ident, orphelines))


def test_les_durees_canoniques_figurent_aussi_dans_la_politique():
    """Les textes de rgpd.py sont mesurés eux aussi, et pas seulement dans leur
    version affichée : un texte canonique faux resterait faux dans toutes les
    pages qui le recopieraient demain."""
    import rgpd
    publiees = _durees_publiees()
    fautes = []
    for cle, entree in rgpd.MENTIONS_FORMULAIRES.items():
        orphelines = sorted(_en_mois(entree["texte"]) - publiees)
        if orphelines:
            fautes.append("%s → %s mois" % (cle, orphelines))
    assert not fautes, (
        "rgpd.MENTIONS_FORMULAIRES annonce des durées absentes de la politique "
        "publiée : %s" % " | ".join(fautes))
