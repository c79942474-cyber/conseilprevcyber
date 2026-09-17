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

══════════════════════════════════════════════════════════════════════════
LES DIX PAGES DU MENU « CONSEIL & TRANSFORMATION »
══════════════════════════════════════════════════════════════════════════

Le même relevé, étendu aux dix pages de la rubrique, a donné : 100 blocs
encadrés, 3 qui étaient eux-mêmes des liens, 39 qui portaient un lien
enfermé dedans, 57 muets. Les 39 se partageaient en deux espèces qu'il
fallait séparer AVANT de convertir quoi que ce soit :

  · L'APPEL — « Générer dans l'espace administrateur → », « Voir la feuille
    de route → ». Il TERMINE le bloc : rien ne le suit. Le bloc entier peut
    devenir ce lien sans rien perdre. 37 blocs.
  · LA CITATION — « sauvegarde préalable de la configuration (voir
    continuité OT), plan de retour arrière écrit AVANT d'agir ». Le lien est
    AU MILIEU d'une phrase qui continue. Convertir le bloc avalerait la
    phrase entière dans un seul lien, et le numéro de l'étape avec. 2 blocs,
    laissés intacts.

LE CRITÈRE EST MESURÉ, PAS DEVINÉ : ce qui suit la fermeture du lien, une
fois les balises retirées, est-il vide ? Une règle plus bas refuse qu'un
bloc-ancre dise quoi que ce soit APRÈS son appel — c'est ce qui empêchera
un futur passage mécanique d'avaler les deux citations.

LES 57 BLOCS MUETS NE SONT PAS BRANCHÉS, sauf quatre. Un relevé a cherché,
dans le texte visible de chacun, le nom de menu d'une autre page du site :
aucun ne le porte. Leur inventer une destination serait deviner. Les quatre
exceptions sont les streams de `/feuille-de-route`, où la page avait déjà
relié le premier des six à son module : les quatre suivants partagent avec
leur cible des mots que les deux côtés écrivent noir sur blanc. Compléter
une série commencée n'est pas la même chose que l'inventer.
"""
import io
import os
import re

import acces
import ao_dc
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
#  LIRE UNE TUILE, ET LA DISTINGUER D'UN BOUTON
# ═══════════════════════════════════════════════════════════════════════════
# QU'EST-CE QU'UN « BLOC » ? Pas une classe : le site en emploie une dizaine
# — `card`, `liv-i`, `mod`, `step`, `lvl`, `bl`, `ph`, `q`… Énumérer les noms
# ferait une liste que le prochain gabarit oublierait d'allonger. On lit donc
# la FEUILLE : est bloc ce qui reçoit une bordure ET un rayon, c'est-à-dire ce
# que l'œil lit comme une tuile.
#
# ET COMMENT ÉVITER LES BOUTONS. `.btn`, `.eyebrow`, `.pagenav-btn` reçoivent
# aussi bordure et rayon, et sont déjà des liens : les compter parmi les blocs
# ferait dire aux règles des choses qui n'ont pas de sens pour eux. Le
# départage est structurel — une tuile a au moins DEUX éléments à l'intérieur
# (un titre et un texte, au minimum), un bouton n'en a aucun ou un seul. Le
# relevé donne 16 boutons écartés, aucune tuile perdue.
ENFANTS_MINIMUM = 2

# La classe marqueur que porte toute ancre-tuile. Voir `a.bloc` dans la
# feuille partagée, et la règle qui refuse une tuile-lien sans elle.
MARQUEUR = "bloc"

# Ce qu'un bloc doit DIRE quand il mène derrière une porte plus fermée que
# celle d'où l'on vient. Le régime ne se subit pas : il s'annonce.
ANNONCE = {"admin": "administrateur", "client": "compte"}


def _sans_commentaires(css):
    """Les commentaires CSS, retirés AVANT de découper en règles.

    Sans cela, `/* … */\n.liv-i{…}` donne un sélecteur qui commence par le
    commentaire, et `.liv-i` disparaît du relevé — le premier brouillon de ces
    règles perdait ainsi 34 tuiles sur 46 sans rien signaler."""
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def _classes_encadrees(css):
    """Les classes qui reçoivent bordure ET rayon — ce que l'œil lit comme
    une tuile, quelle que soit la classe que le gabarit lui a donnée."""
    out = set()
    for sel, corps in re.findall(r"([^{}]+)\{([^}]*)\}", _sans_commentaires(css)):
        if "border:" not in corps or "border-radius" not in corps:
            continue
        for un in sel.split(","):
            m = re.fullmatch(r"(?:a)?\.([a-zA-Z][\w-]*)", un.strip())
            if m:
                out.add(m.group(1))
    return out


def _styles_de(nom, feuille):
    """Ce qui habille cette page : la feuille partagée si elle la charge, plus
    son propre <style>."""
    src = io.open(os.path.join(ICI, nom), encoding="utf-8").read()
    partagee = feuille if 'href="/styles.css"' in src else ""
    return partagee + "\n" + "\n".join(
        re.findall(r"<style[^>]*>(.*?)</style>", src, re.S))


def _tuiles(html, classes):
    """Toute tuile du document : sa balise, ses classes, son lien s'il en a
    un, et si ce lien est un APPEL (rien ne le suit) ou une CITATION."""
    out = []
    for m in re.finditer(r"<(div|a|li|article)\b([^>]*)>", html):
        cl = re.search(r'class="([^"]*)"', m.group(2))
        if not cl:
            continue
        portees = set(cl.group(1).split())
        if not (portees & classes):
            continue
        corps = _corps(html, m.start(), m.group(1))
        if len(re.findall(r"<(?!/)[a-zA-Z]", corps)) < ENFANTS_MINIMUM:
            continue
        liens = list(re.finditer(r"<a\b[^>]*>.*?</a>", corps, re.S))
        suite = ""
        if len(liens) == 1:
            suite = re.sub(r"[\s\u00a0.,;:)]+", "",
                           re.sub(r"<[^>]+>", "", corps[liens[0].end():]))
        href = re.search(r'href="([^"]*)"', m.group(2))
        titre = re.search(r"<h[234][^>]*>(.*?)</h[234]>|"
                          r'<div class="[^"]*-t">(.*?)</div>', corps, re.S)
        brut = (titre.group(1) or titre.group(2)) if titre else corps[:60]
        out.append({
            "balise": m.group(1),
            "classes": portees,
            "href": href.group(1) if href else None,
            "titre": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", brut)).strip(),
            "corps": corps,
            "liens": [l.group(0) for l in liens],
            "appel": len(liens) == 1 and not suite,
            "citation": len(liens) == 1 and bool(suite),
        })
    return out


def _pages_du_menu_conseil():
    """Les pages de la rubrique « Conseil & transformation », LUES DANS LE
    MENU et non recopiées ici.

    C'est le menu qui définit la rubrique : une page qu'on y ajoute entre
    d'elle-même dans le périmètre de ces règles, et une page qu'on en retire
    en sort. Une liste recopiée ici resterait verte en mesurant l'ancienne
    rubrique."""
    nav = io.open(os.path.join(ICI, "nav.js"), encoding="utf-8").read()
    m = re.search(r'\{\s*t:\s*"Conseil & transformation",\s*l:\s*\[(.*?)\]\s*\}',
                  nav, re.S)
    assert m, "la rubrique « Conseil & transformation » a disparu de nav.js"
    return [u for u, _t in re.findall(r'\["(/[^"]+)",\s*"([^"]*)"\]', m.group(1))]


def _servir_chemin(chemin, anonyme, admin):
    c = admin if acces.statut(chemin) == "admin" else anonyme
    r = c.get(chemin)
    assert r.status_code == 200, (chemin, r.status_code)
    return r.data.decode("utf-8")


def _conseil_servi(anonyme, admin):
    """(chemin, html, tuiles) pour chacune des dix pages de la rubrique."""
    feuille = io.open(os.path.join(ICI, "styles.css"), encoding="utf-8").read()
    out = []
    for chemin in _pages_du_menu_conseil():
        nom = appli.PAGES.get(chemin)
        assert nom, "page du menu Conseil sans gabarit : %s" % chemin
        html = _servir_chemin(chemin, anonyme, admin)
        classes = _classes_encadrees(_styles_de(nom, feuille))
        coeur = re.search(r"<main\b[^>]*>(.*)</main>", html, re.S)
        out.append((chemin, html, _tuiles(coeur.group(1) if coeur else html, classes)))
    return out


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
    """`a.bloc` répare deux choses, et les deux comptent.

    `color:inherit` — sans elle le <h3> hérite du cyan de `a{}` au lieu de
    l'encre, et le texte change de couleur du seul fait de devenir cliquable ;
    `text-decoration:none` — même motif pour le soulignement.

    LE `display` N'EST PAS DANS `a.bloc`, ET C'EST VOULU : la tuile de
    `/formation` est une grille à deux colonnes, qu'un `display:block` venu
    d'ici — plus spécifique que son `.mod` — aurait mise à plat. Chaque classe
    de bloc le déclare donc pour elle-même, et la règle suivante le vérifie.

    La déclaration doit atteindre CHAQUE page qui pose des tuiles-liens,
    qu'elle vienne de la feuille partagée ou du <style> de la page."""
    partagee = _declaration(_feuille_servie(anonyme), "a.bloc") or ""
    manques = []
    for nom in _fichiers_a_cartes_cliquables():
        src = io.open(os.path.join(ICI, nom), encoding="utf-8").read()
        regle = partagee if 'href="/styles.css"' in src else ""
        regle += _declaration(_styles_locaux(nom), "a.bloc") or ""
        for propriete in ("color:inherit", "text-decoration:none"):
            if propriete not in regle.replace(" ", ""):
                manques.append("%s : %s" % (nom, propriete))
    assert not manques, manques


def test_chaque_classe_de_tuile_lien_declare_son_propre_display(anonyme, admin):
    """UN <a> EST EN LIGNE PAR DÉFAUT : sans `display`, la boîte ne va pas
    jusqu'aux bords et le clic rate les marges de la tuile. Comme `a.bloc` se
    garde de le fixer — pour ne pas aplatir la grille à deux colonnes de
    `/formation` —, c'est à chaque classe de tuile de le porter. Mesuré sur
    les classes RÉELLEMENT employées par les ancres servies, pas sur une liste
    écrite ici."""
    feuille = io.open(os.path.join(ICI, "styles.css"), encoding="utf-8").read()
    sans, examinees = [], 0
    for chemin, _html, tuiles in _conseil_servi(anonyme, admin):
        css = _sans_commentaires(_styles_de(appli.PAGES[chemin], feuille))
        regles = re.findall(r"([^{}]+)\{([^}]*)\}", css)
        for t in tuiles:
            if t["balise"] != "a":
                continue
            examinees += 1
            porte = False
            for classe in t["classes"] - {MARQUEUR}:
                vise = re.compile(r"a?\.%s" % re.escape(classe))
                for sel, corps in regles:
                    if any(vise.fullmatch(u.strip()) for u in sel.split(",")) \
                            and "display:" in corps.replace(" ", ""):
                        porte = True
                        break
                if porte:
                    break
            if not porte:
                sans.append("%s · %s (classes : %s) : aucune ne déclare de display"
                            % (chemin, t["titre"][:40], sorted(t["classes"])))
    assert not sans, sans
    assert examinees >= 40, "%d tuiles-liens examinées seulement" % examinees


def test_la_regle_du_bloc_cliquable_n_est_ecrite_qu_a_un_seul_endroit(anonyme):
    """Deux définitions de la même intention dérivent : on corrige l'une, on
    oublie l'autre, et deux pages cessent de se ressembler. La règle a vécu
    dans le <style> de `admin.html`, sous le nom `a.card`, jusqu'à ce qu'une
    deuxième page en ait besoin ; elle est montée dans la feuille partagée,
    et l'exemplaire local a été retiré. Cette règle refuse qu'il revienne."""
    endroits = []
    feuille = io.open(os.path.join(ICI, "styles.css"), encoding="utf-8").read()
    if _declaration(feuille, "a.bloc") is not None:
        endroits.append("styles.css")
    for nom in sorted(os.listdir(ICI)):
        if nom.endswith(".html") and _declaration(_styles_locaux(nom), "a.bloc") is not None:
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


# ═══════════════════════════════════════════════════════════════════════════
#  LES DIX PAGES DE LA RUBRIQUE « CONSEIL & TRANSFORMATION »
# ═══════════════════════════════════════════════════════════════════════════

def test_la_rubrique_conseil_tient_toujours_ses_dix_pages(anonyme, admin):
    """LE GARDE-FOU DE TOUT CE QUI SUIT. Les règles de cette section balayent
    une population lue dans le menu ; si ce balayage se vidait — rubrique
    renommée, format de `nav.js` changé —, elles resteraient vertes en ne
    mesurant plus rien. On compte donc ce qu'on regarde, et on l'affiche."""
    pages = _pages_du_menu_conseil()
    assert len(pages) >= 10, pages
    assert "/maturite-ot" in pages and "/gouvernance-ia" in pages

    releve = _conseil_servi(anonyme, admin)
    tuiles = sum(len(t) for _c, _h, t in releve)
    ancres = sum(1 for _c, _h, t in releve for x in t if x["balise"] == "a")
    assert tuiles >= 100, "%d tuiles seulement — le relevé s'est vidé" % tuiles
    assert ancres >= 40, "%d tuiles-liens seulement" % ancres


def test_aucune_tuile_ne_garde_un_appel_enferme(anonyme, admin):
    """UNE TUILE QUI PORTE SON APPEL EN BAS EST LE DÉFAUT D'ORIGINE.

    La cible du clic vaut alors une vingtaine de caractères au bas d'un bloc
    de deux cents pixels, dont le survol éclaire pourtant la tuile entière.
    Un appel — un lien que rien ne suit — doit être la tuile elle-même."""
    enfermes = []
    for chemin, _html, tuiles in _conseil_servi(anonyme, admin):
        for t in tuiles:
            if t["balise"] != "a" and t["appel"]:
                enfermes.append("%s · %s → %s" % (chemin, t["titre"][:44], t["liens"][0][:70]))
    assert not enfermes, enfermes


def test_une_citation_au_milieu_d_une_phrase_reste_une_citation(anonyme, admin):
    """L'AUTRE MOITIÉ DE LA MÊME DÉCISION. Deux blocs de
    `/gestion-des-changements` citent une page AU MILIEU d'une phrase qui
    continue — « sauvegarde préalable de la configuration (voir continuité
    OT), plan de retour arrière écrit AVANT d'agir ». Les convertir avalerait
    la phrase, et le numéro de l'étape avec.

    CE QUE LA PREMIÈRE VERSION NE MESURAIT PAS. Elle balayait les blocs
    porteurs d'une citation et vérifiait qu'aucun n'était devenu une ancre.
    Une mutation l'a traversée sans tomber : convertir le bloc SUPPRIME sa
    citation, le bloc sort du balayage, et la règle ne voyait plus rien à
    reprocher. Elle nomme donc les deux citations qu'elle protège — c'est une
    décision écrite, et une décision se relit."""
    CITATIONS = {("/gestion-des-changements", "/gestion-correctifs"),
                 ("/gestion-des-changements", "/continuite-ot")}
    routes = _routes_connues()
    trouvees, fautes = set(), []
    for chemin, _html, tuiles in _conseil_servi(anonyme, admin):
        for t in tuiles:
            if not t["citation"]:
                continue
            cible = re.search(r'href="([^"]*)"', t["liens"][0]).group(1)
            trouvees.add((chemin, cible))
            if t["balise"] == "a":
                fautes.append("%s · %s : la phrase a été avalée par le lien"
                              % (chemin, t["titre"][:44]))
            elif cible.startswith("/") and cible.split("?")[0] not in routes:
                fautes.append("%s · %s → %s : aucune route"
                              % (chemin, t["titre"][:44], cible))
    assert not fautes, fautes
    perdues = sorted(CITATIONS - trouvees)
    assert not perdues, (
        "ces liens cités au milieu d'une phrase ne sont plus des citations — "
        "le bloc les a-t-il avalés ? %s" % perdues)


def test_toute_tuile_qui_est_un_lien_porte_la_classe_marqueur(anonyme, admin):
    """`a.bloc` porte `color:inherit` et `text-decoration:none`. Une
    tuile-lien qui oublie le marqueur voit son titre passer au cyan de `a{}`
    et se souligner — sans que rien d'autre ne le signale. La classe dit
    aussi, dans le balisage, ce que le bloc est devenu."""
    nues = []
    for chemin, _html, tuiles in _conseil_servi(anonyme, admin):
        for t in tuiles:
            if t["balise"] == "a" and MARQUEUR not in t["classes"]:
                nues.append("%s · %s (classes : %s)"
                            % (chemin, t["titre"][:40], sorted(t["classes"])))
    assert not nues, nues


def test_l_appel_est_la_derniere_chose_que_dit_une_tuile_lien(anonyme, admin):
    """CE QUI EMPÊCHERA D'AVALER UNE CITATION. Une tuile-lien doit montrer où
    elle mène, et le montrer EN DERNIER : l'appel clôt le bloc. Convertir un
    bloc dont le lien est au milieu d'une phrase laisserait du texte après la
    flèche — c'est exactement ce que cette règle refuse."""
    fautes = []
    for chemin, _html, tuiles in _conseil_servi(anonyme, admin):
        for t in tuiles:
            if t["balise"] != "a":
                continue
            visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t["corps"])).strip()
            if "→" not in visible:
                fautes.append("%s · %s : aucun appel visible" % (chemin, t["titre"][:40]))
                continue
            apres = visible[visible.rindex("→") + 1:]
            if re.sub(r"[\s .]+", "", apres):
                fautes.append("%s · %s : « %s » suit encore l'appel"
                              % (chemin, t["titre"][:40], apres[:40]))
    assert not fautes, fautes


def test_une_tuile_lien_ne_mene_derriere_une_porte_plus_fermee_qu_en_le_disant(anonyme, admin):
    """LA PORTE PLUS FERMÉE S'ANNONCE, ELLE NE SE SUBIT PAS.

    Trente-quatre tuiles de livrables sont posées sur des pages OUVERTES et
    mènent à `/admin/livrables`. Un visiteur qui clique tombe sur la
    connexion — et c'est acceptable à une condition : que la tuile l'ait dit.
    Elles portent « Générer dans l'espace administrateur ». La règle exige ce
    mot ; une tuile qui mènerait à l'espace admin sans le nommer tombe."""
    murs, annonces = [], 0
    for chemin, _html, tuiles in _conseil_servi(anonyme, admin):
        depart = FERMETURE[acces.statut(chemin)]
        for t in tuiles:
            cible = t["href"]
            if t["balise"] != "a" or not cible or not cible.startswith("/"):
                continue
            regime = acces.statut(cible.split("?")[0])
            if FERMETURE[regime] <= depart:
                continue
            annonces += 1
            dit = ao_dc._sans_accent(re.sub(r"<[^>]+>", " ", t["corps"]).lower())
            if ANNONCE[regime] not in dit:
                murs.append("%s (%s) · %s → %s (%s) sans dire « %s »"
                            % (chemin, acces.statut(chemin), t["titre"][:36],
                               cible, regime, ANNONCE[regime]))
    assert not murs, murs
    assert annonces, "aucune tuile ne franchit de porte — la règle est muette"


def test_les_blocs_de_livrables_sont_CEUX_du_catalogue():
    """LE CONTRÔLE QUE LE GÉNÉRATEUR PROMETTAIT, ET QUI N'EXISTAIT PAS.

    `outils/generer_blocs_livrables.py` annonce dans son en-tête que
    « `tests/test_blocs_livrables.py` échoue si une page s'en écarte ». Ce
    fichier n'a jamais existé. Rien ne vérifiait donc les trente-quatre tuiles
    qu'il écrit, et le relevé du jour où cette règle a été écrite l'a montré :
    le générateur refusait de tourner depuis qu'un livrable avait été rangé
    dans un groupe sans page, sept pages étaient restées non régénérées, et
    deux livrables catalogués — `atelier-direction` et
    `sr-interface-surete-securite` — n'étaient atteignables depuis aucune
    page du site.

    On le lance donc en mode vérification, exactement comme à la main."""
    import importlib.util
    chemin = os.path.join(ICI, "outils", "generer_blocs_livrables.py")
    spec = importlib.util.spec_from_file_location("gen_blocs_livrables", chemin)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)

    sante = gen.livrables.sante_pages()
    assert sante["ok"], sante["problemes"]

    ecarts = []
    for page in gen.livrables.PAGES_CONSEIL:
        etat, _chemin = gen.traiter(page, verifier=True)
        if etat not in ("À JOUR", "À LA MAIN"):
            ecarts.append("%s : %s" % (page["url"], etat))
    assert not ecarts, ecarts
    assert sante["livrables_conseil"] >= 41, sante
