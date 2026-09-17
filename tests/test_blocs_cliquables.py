"""EN CLIQUANT SUR LE BLOC, ET PAS SUR LES VINGT CARACTÈRES DU BAS.

CE QUI A AMENÉ CE FICHIER. La page `/maturite-ot` ouvre sur trois cartes —
« Diagnostic express », « Audit de conformité 62443 », « Assessment de
maturité ». Les deux premières portaient leur lien dans la dernière ligne :
la cible du clic mesurait une vingtaine de caractères au bas d'un bloc haut
de deux cents pixels, dont tout le reste — titre, description, étiquettes —
avait l'apparence d'une chose qu'on ouvre et ne répondait pas. La troisième
n'avait aucun lien.

CE QUE CES RÈGLES MESURENT, ET CE QU'ELLES REFUSENT DE MESURER. Elles ne
lisent pas le source des gabarits : elles DEMANDENT les pages à
l'application, comme le ferait un visiteur, et regardent ce qui redescend.
Un gabarit juste servi par une route absente ne passerait pas.

Quatre défauts sont visés, et chacun a déjà été rencontré ailleurs :

  1. LE BLOC N'EST PAS LE LIEN — le cas d'origine ci-dessus ;
  2. LE LIEN IMBRIQUÉ — un <a> dans un <a> est interdit par le HTML. Le
     navigateur referme SILENCIEUSEMENT l'extérieur : le bloc cesse d'être
     cliquable là où on croit venir de le rendre cliquable, et rien dans le
     source ne le dit ;
  3. LA DESTINATION QUI N'EXISTE PAS — une route retirée, une ancre
     renommée. Le clic répond, et n'amène nulle part ;
  4. LA PORTE PLUS FERMÉE QUE CELLE D'OÙ L'ON VIENT — un bloc posé sur une
     page ouverte qui mène derrière l'inscription. Le visiteur clique et
     tombe sur un mur. `acces.statut` sait répondre ; encore faut-il le lui
     demander.

POURQUOI LES RÈGLES SONT À L'ÉCHELLE DU SITE. Les cartes-liens existaient
déjà dans `/admin` avant `/maturite-ot`. Les mesurer sur la seule page qui
vient de changer laisserait la suivante se tromper en silence.
"""
import io
import os
import re

import acces
import app as appli

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── LE RATTACHEMENT D'UN GABARIT À SON CHEMIN ──────────────────────────────
# `app.PAGES` associe déjà un chemin à son fichier pour les 52 pages du site.
# `admin.html` n'y figure pas : le tableau de bord est servi par sa propre
# route, derrière `@admin_required`. On l'écrit donc à la main — et une règle
# plus bas REFUSE qu'un gabarit à cartes cliquables n'ait ni l'un ni l'autre,
# faute de quoi une page nouvelle échapperait sans bruit à tout ce fichier.
HORS_REGISTRE = {"admin.html": "/admin"}

# Rang des trois régimes d'accès, du plus ouvert au plus fermé.
FERMETURE = {"direct": 0, "client": 1, "admin": 2}


# ── LIRE UN DOCUMENT COMME LE FERAIT UN NAVIGATEUR ─────────────────────────
# UNE EXPRESSION NON GOURMANDE NE SAIT PAS LIRE UNE CARTE. `<div class="card">
# … <div class="ico">🩺</div> …</div>` : `</div>` non gourmand s'arrête sur la
# fermeture de l'icône, et le corps mesuré s'arrête avant le titre. Le premier
# brouillon de ces règles portait ce défaut, et il ne se voyait pas tant que
# les cartes étaient des <a> sans <a> dedans. On compte donc les imbrications.
_BALISE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>", re.S)
_OUVRANTE = re.compile(r"<(a|div)\b([^>]*)>", re.S)


def _corps(html, debut, nom):
    """Le corps de l'élément `nom` ouvert en `debut`, imbrications comptées."""
    depart = html.index(">", debut) + 1
    profondeur = 1
    for m in _BALISE.finditer(html, depart):
        if m.group(2).lower() != nom:
            continue
        if m.group(1):
            profondeur -= 1
            if profondeur == 0:
                return html[depart:m.start()]
        elif not m.group(3):
            profondeur += 1
    raise AssertionError("élément <%s> jamais refermé" % nom)


def _cartes(html):
    """Toute carte du document — celle qui est un lien comme celle qui ne
    l'est pas. Rend le nom de balise, le href, le titre et le corps."""
    trouvees = []
    for m in _OUVRANTE.finditer(html):
        classes = re.search(r'class="([^"]*)"', m.group(2))
        if not classes or "card" not in classes.group(1).split():
            continue
        corps = _corps(html, m.start(), m.group(1))
        href = re.search(r'href="([^"]*)"', m.group(2))
        titre = re.search(r"<h3[^>]*>(.*?)</h3>", corps, re.S)
        trouvees.append({
            "balise": m.group(1),
            "href": href.group(1) if href else None,
            "titre": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", titre.group(1))).strip()
                     if titre else "(sans titre)",
            "corps": corps,
        })
    return trouvees


def _fichiers_a_cartes_cliquables():
    """Les gabarits du site dont un bloc entier est un lien."""
    noms = []
    for nom in sorted(os.listdir(ICI)):
        if not nom.endswith(".html"):
            continue
        src = io.open(os.path.join(ICI, nom), encoding="utf-8").read()
        if [c for c in _cartes(src) if c["balise"] == "a"]:
            noms.append(nom)
    return noms


def _chemin_du_fichier(nom):
    for chemin, fichier in appli.PAGES.items():
        if fichier == nom:
            return chemin
    return HORS_REGISTRE.get(nom)


def _servir(nom, anonyme, admin):
    """La page telle qu'elle redescend à qui a le droit de la lire."""
    chemin = _chemin_du_fichier(nom)
    assert chemin, nom
    c = admin if acces.statut(chemin) == "admin" else anonyme
    r = c.get(chemin)
    assert r.status_code == 200, (chemin, r.status_code)
    return chemin, r.data.decode("utf-8")


def _pages_servies(anonyme, admin):
    return [(nom,) + _servir(nom, anonyme, admin)
            for nom in _fichiers_a_cartes_cliquables()]


# ═══════════════════════════════════════════════════════════════════════════
#  LE BLOC EST LE LIEN
# ═══════════════════════════════════════════════════════════════════════════

def test_les_trois_regards_sont_trois_blocs_cliquables(anonyme):
    """Les trois cartes de `/maturite-ot` sont des <a> qui portent un href.

    C'est la demande d'origine, mesurée sur la page servie : « en cliquant
    sur ces blocs ». Une carte redevenue <div> ne passe pas, même si elle
    garde un lien à l'intérieur."""
    html = anonyme.get("/maturite-ot").data.decode("utf-8")
    debut = html.index("Trois regards")
    section = html[debut:html.index("</section>", debut)]

    cartes = _cartes(section)
    assert len(cartes) == 3, [c["titre"] for c in cartes]

    inertes = [c["titre"] for c in cartes if c["balise"] != "a" or not c["href"]]
    assert not inertes, "blocs qui ne sont pas eux-mêmes le lien : %s" % inertes

    # Et les trois regards sont bien les trois attendus, chacun vers sa cible.
    assert {c["titre"]: c["href"] for c in cartes} == {
        "Diagnostic express": "/diagnostic",
        "Audit de conformité 62443": "/audit-conformite",
        "Assessment de maturité": "#auto-evaluation",
    }


def test_aucun_bloc_cliquable_ne_renferme_un_autre_lien(anonyme, admin):
    """Un <a> dans un <a> : le navigateur referme l'extérieur sans rien dire.

    Le bloc cesse alors d'être cliquable ailleurs que sur le lien intérieur
    — exactement le défaut qu'on venait de corriger."""
    fautes = []
    for nom, chemin, html in _pages_servies(anonyme, admin):
        for c in _cartes(html):
            if c["balise"] != "a":
                continue
            dedans = re.findall(r"<a\b[^>]*>", c["corps"])
            if dedans:
                fautes.append("%s · %s : %d lien(s) imbriqué(s) %s"
                              % (chemin, c["titre"], len(dedans), dedans))
    assert not fautes, fautes


def test_chaque_bloc_cliquable_montre_encore_ou_il_mene(anonyme, admin):
    """Rendre le bloc cliquable ne doit pas effacer l'appel qui l'annonce.

    La flèche « Ouvrir → », « Lancer le diagnostic → » : elle reste écrite,
    en <span>, sinon rien à l'écran ne dit que le bloc s'ouvre."""
    muets = []
    for nom, chemin, html in _pages_servies(anonyme, admin):
        for c in _cartes(html):
            if c["balise"] != "a":
                continue
            texte = re.sub(r"<[^>]+>", " ", c["corps"])
            if "→" not in texte:
                muets.append("%s · %s" % (chemin, c["titre"]))
    assert not muets, "blocs cliquables sans appel visible : %s" % muets


# ═══════════════════════════════════════════════════════════════════════════
#  LA DESTINATION
# ═══════════════════════════════════════════════════════════════════════════

def _routes_connues():
    return {r.rule for r in appli.app.url_map.iter_rules() if "GET" in (r.methods or ())}


def test_chaque_destination_de_bloc_existe_vraiment(anonyme, admin):
    """Une ancre visée est présente dans la page servie ; un chemin visé est
    une route que l'application sert. Pas de clic qui n'amène nulle part."""
    routes = _routes_connues()
    perdus = []
    for nom, chemin, html in _pages_servies(anonyme, admin):
        for c in _cartes(html):
            cible = c["href"]
            if not cible or c["balise"] != "a":
                continue
            if cible.startswith("#"):
                if ('id="%s"' % cible[1:]) not in html:
                    perdus.append("%s · %s → ancre %s absente de la page"
                                  % (chemin, c["titre"], cible))
            elif cible.startswith("/"):
                if cible.split("?")[0] not in routes:
                    perdus.append("%s · %s → %s : aucune route"
                                  % (chemin, c["titre"], cible))
    assert not perdus, perdus


def test_un_bloc_ne_renvoie_jamais_a_la_page_qui_le_porte(anonyme, admin):
    """Se renvoyer à soi-même est un clic qui ne bouge rien.

    C'est ce qui a décidé de la cible du troisième regard : il décrit
    `/maturite-ot`, il est POSÉ sur `/maturite-ot`, il vise donc l'endroit de
    la page qu'il annonce — `#auto-evaluation` — et non la page elle-même."""
    boucles = []
    for nom, chemin, html in _pages_servies(anonyme, admin):
        for c in _cartes(html):
            if c["balise"] != "a" or not c["href"]:
                continue
            if c["href"].split("?")[0].rstrip("/") == chemin.rstrip("/"):
                boucles.append("%s · %s → %s" % (chemin, c["titre"], c["href"]))
    assert not boucles, boucles


def test_un_bloc_ne_mene_pas_derriere_une_porte_plus_fermee_que_la_sienne(anonyme, admin):
    """Un bloc sur une page ouverte qui mène à une page fermée : le visiteur
    clique et tombe sur l'inscription. `acces.statut` tranche les trois
    régimes — direct, client, admin — et le clic ne doit pas les remonter."""
    murs = []
    for nom, chemin, html in _pages_servies(anonyme, admin):
        depart = FERMETURE[acces.statut(chemin)]
        for c in _cartes(html):
            cible = c["href"]
            if not cible or c["balise"] != "a" or not cible.startswith("/"):
                continue
            arrivee = FERMETURE[acces.statut(cible.split("?")[0])]
            if arrivee > depart:
                murs.append("%s (%s) · %s → %s (%s)"
                            % (chemin, acces.statut(chemin), c["titre"],
                               cible, acces.statut(cible.split("?")[0])))
    assert not murs, murs


# ═══════════════════════════════════════════════════════════════════════════
#  CE QUI REND LE BLOC CLIQUABLE À L'ÉCRAN
# ═══════════════════════════════════════════════════════════════════════════

def _feuille_servie(anonyme):
    return anonyme.get("/styles.css").data.decode("utf-8")


def _styles_locaux(nom):
    src = io.open(os.path.join(ICI, nom), encoding="utf-8").read()
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", src, re.S))


def _declaration(css, selecteur):
    """Le contenu de la règle `selecteur{…}`, ou None."""
    m = re.search(re.escape(selecteur) + r"\s*\{([^}]*)\}", css)
    return m.group(1) if m else None


def test_la_regle_du_bloc_cliquable_est_servie_a_qui_s_en_sert(anonyme, admin):
    """`a.card` répare trois choses, et les trois comptent.

    `display:block` — un <a> est en ligne, et la boîte ne va pas jusqu'aux
    bords ; `color:inherit` — sans elle le <h3> hérite du cyan de `a{}` au
    lieu de l'encre, et le texte change de couleur du seul fait de devenir
    cliquable ; `text-decoration:none` — même motif pour le soulignement.

    La déclaration doit atteindre CHAQUE page qui pose des cartes-liens,
    qu'elle vienne de la feuille partagée ou du <style> de la page."""
    partagee = _declaration(_feuille_servie(anonyme), "a.card") or ""
    manques = []
    for nom in _fichiers_a_cartes_cliquables():
        src = io.open(os.path.join(ICI, nom), encoding="utf-8").read()
        regle = partagee if 'href="/styles.css"' in src else ""
        regle += _declaration(_styles_locaux(nom), "a.card") or ""
        for propriete in ("display:block", "color:inherit", "text-decoration:none"):
            if propriete not in regle.replace(" ", ""):
                manques.append("%s : %s" % (nom, propriete))
    assert not manques, manques


def test_la_regle_du_bloc_cliquable_n_est_ecrite_qu_a_un_seul_endroit(anonyme):
    """Deux définitions de la même intention dérivent : on corrige l'une, on
    oublie l'autre, et deux pages cessent de se ressembler. `a.card` a vécu
    dans le <style> de `admin.html` jusqu'à ce qu'une deuxième page en ait
    besoin ; elle est montée dans la feuille partagée, et l'exemplaire local
    a été retiré. Cette règle refuse qu'il revienne."""
    endroits = []
    feuille = io.open(os.path.join(ICI, "styles.css"), encoding="utf-8").read()
    if _declaration(feuille, "a.card") is not None:
        endroits.append("styles.css")
    for nom in sorted(os.listdir(ICI)):
        if nom.endswith(".html") and _declaration(_styles_locaux(nom), "a.card") is not None:
            endroits.append(nom)
    assert endroits == ["styles.css"], endroits


def test_chaque_ancre_visee_par_un_bloc_passe_sous_l_en_tete_collant(anonyme, admin):
    """L'en-tête est `position:sticky;top:0`. Sans marge, viser une ancre
    amène le titre DERRIÈRE la barre, où il est illisible : le clic paraît
    avoir raté. La marge se mesure contre la hauteur RÉELLE de la barre, lue
    dans la même feuille — si l'en-tête grandit, la règle le dit."""
    css = _feuille_servie(anonyme)
    barre = re.search(r"\.nav\s*\{[^}]*height:\s*(\d+)px", css)
    assert barre, "hauteur de l'en-tête introuvable dans la feuille"
    hauteur = int(barre.group(1))

    trop_haut = []
    for nom, chemin, html in _pages_servies(anonyme, admin):
        src = io.open(os.path.join(ICI, nom), encoding="utf-8").read()
        feuilles = css + "\n" + _styles_locaux(nom) if 'href="/styles.css"' in src \
                   else _styles_locaux(nom)
        for c in _cartes(html):
            if c["balise"] != "a" or not c["href"] or not c["href"].startswith("#"):
                continue
            ancre = c["href"][1:]
            marges = [int(v) for sel, corps in re.findall(r"([^{}]+)\{([^}]*)\}", feuilles)
                      if ("#" + ancre) in re.split(r"[\s,>]+", sel.strip())
                      or ("#" + ancre) in [s.strip() for s in sel.split(",")]
                      for v in re.findall(r"scroll-margin-top:\s*(\d+)px", corps)]
            if not marges or max(marges) < hauteur:
                trop_haut.append("%s · %s → #%s : marge %s pour un en-tête de %dpx"
                                 % (chemin, c["titre"], ancre,
                                    max(marges) if marges else "absente", hauteur))
    assert not trop_haut, trop_haut


def test_toute_page_a_blocs_cliquables_est_rattachee_a_son_chemin():
    """Le garde-fou de tout ce fichier : un gabarit qui pose des cartes-liens
    sans qu'on sache à quelle adresse il est servi échapperait en silence aux
    huit règles ci-dessus. Elles ne diraient plus rien, et resteraient
    vertes."""
    orphelins = [nom for nom in _fichiers_a_cartes_cliquables()
                 if not _chemin_du_fichier(nom)]
    assert not orphelins, (
        "gabarits à blocs cliquables sans chemin connu — à inscrire dans "
        "`app.PAGES` ou dans HORS_REGISTRE : %s" % orphelins)
