"""LES PARCOURS GUIDÉS DISENT-ILS ENCORE LA VÉRITÉ SUR LE SITE ?

CE QUI S'EST PASSÉ, ET QU'AUCUN CONTRÔLE N'A VU. Les parcours annoncent, avant
le clic, les étapes qui demandent un compte : « 🔒 Compte requis », et la modale
le promet en toutes lettres. Cette liste était écrite à la main dans
parcours.js. La politique d'accès du site a ensuite changé — elle vit désormais
dans acces.py, qui refuse de démarrer si une route ne l'applique pas — et la
liste des parcours, elle, n'a pas bougé. Neuf pages visitées par des étapes
étaient devenues réservées et continuaient de s'annoncer libres : le diagnostic,
NIS 2, le cockpit, la feuille de route, l'operating model, la maturité OT et les
trois pages de centres de données.

RIEN N'AVAIT PLANTÉ. C'est bien le problème. Un lien mort se voit ; une promesse
devenue fausse ne se voit pas — le visiteur clique, tombe sur un formulaire de
connexion, et c'est le guide qui l'y a envoyé en lui disant que c'était ouvert.
La même mécanique que les liens profonds dont l'ancre a été renommée : ça
continue de « fonctionner », et ça ne tient plus ce qui était annoncé.

CE QUE CE FICHIER ÉPROUVE, donc :
  1. toute étape vise une page qui EXISTE (une route, pas une intention) ;
  2. toute étape vers une page fermée est ANNONCÉE fermée, et aucune étape
     ouverte ne porte un cadenas qu'elle ne mérite pas — la comparaison se fait
     contre acces.py, jamais contre une seconde liste écrite ici ;
  3. toute étape est PONDÉRÉE (entrée dans AXES_URL), sans quoi le croisement
     rôle × secteur devient muet sur cette page sans le dire ;
  4. les pages construites pour le site sont ATTEIGNABLES par un parcours au
     moins — cinq d'entre elles ne l'étaient par aucun ;
  5. le premier visiteur, celui qui n'a pas de compte, voit quelque chose AVANT
     le mur ;
  6. le module qui affiche les cadenas peut réellement demander au serveur si
     la liste écrite est encore juste.

Les données sont lues DANS parcours.js par Node, jamais recopiées : un parcours
corrigé ici et pas là-bas éprouverait un site imaginaire.
"""
import json
import os
import re
import subprocess
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import acces  # noqa: E402


def _lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


def _module():
    """PARCOURS et SECTEURS, tels que le navigateur les verra."""
    out = subprocess.run(
        ["node", "-e",
         "const m=require('%s/parcours.js');"
         "process.stdout.write(JSON.stringify({p:m.PARCOURS,s:m.SECTEURS,"
         "a:m.AXES_URL}));" % ICI],
        capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


MOD = _module()


def _itineraires():
    """Tous les itinéraires, rôles et secteurs confondus : (nom, étapes)."""
    for p in MOD["p"]:
        yield p["id"], p["etapes"]
    for s in MOD["s"]:
        yield "sec:" + s["id"], s["etapes"]


def _urls():
    vues = {}
    for nom, etapes in _itineraires():
        for e in etapes:
            vues.setdefault(e["url"], []).append(nom)
    return vues


def _routes_du_site():
    """Les chemins que app.py sert réellement — pas ceux qu'on croit servir."""
    return set(re.findall(r'@app\.route\("(/[^"<]*)"', _lire("app.py")))


def _reserve_declaree():
    """La liste écrite dans parcours.js, celle qui s'affiche à l'ouverture."""
    js = _lire("parcours.js")
    m = re.search(r"var RESERVE = \{(.*?)\};", js, re.S)
    assert m, "la liste RESERVE est introuvable dans parcours.js"
    return set(re.findall(r'"(/[^"]*)"', m.group(1)))


# ── 1. Une étape vise une page qui existe ──────────────────────────────────

def test_toute_etape_vise_une_route_du_site():
    """Une étape vers une page supprimée n'échoue nulle part : elle rend un 404
    au visiteur qui suivait le guide."""
    routes = _routes_du_site()
    morts = {u: p for u, p in _urls().items() if u not in routes}
    assert not morts, morts


# ── 2. LE CONTRÔLE QUI COMPTE : le cadenas dit la vérité ───────────────────

def test_toute_etape_fermee_est_annoncee_fermee():
    """La promesse de la modale : « vous le savez avant de cliquer ».

    C'est ce contrôle-ci qui manquait. La politique est lue dans acces.py —
    la source qui fait autorité, celle qui empêche l'application de démarrer
    quand une route ne l'applique pas."""
    declaree = _reserve_declaree()
    muettes = sorted(u for u in _urls()
                     if acces.statut(u) == "client" and u not in declaree)
    assert not muettes, (
        "ces pages demandent un compte et le parcours ne le dit pas — le "
        "visiteur clique et tombe sur un formulaire de connexion : %s" % muettes)


def test_aucune_page_ouverte_ne_porte_un_cadenas():
    """Le défaut inverse, plus discret : un cadenas de trop décourage un clic
    qui aurait abouti, et il use le cadenas là où il est mérité."""
    declaree = _reserve_declaree()
    fausses = sorted(u for u in declaree if acces.statut(u) != "client")
    assert not fausses, fausses


def test_la_liste_ecrite_ne_contient_rien_qui_n_existe_pas():
    routes = _routes_du_site()
    assert not sorted(u for u in _reserve_declaree() if u not in routes)


# ── 3. Une étape non pondérée rend le croisement muet ──────────────────────

def test_toute_etape_est_ponderee():
    """Sans entrée dans AXES_URL, une étape pèse zéro : elle ne peut jamais
    devenir prioritaire ni détour, et rien ne le signale. Une entrée VIDE est
    un choix recevable — l'absence d'entrée, non."""
    manquantes = {u: p for u, p in _urls().items() if u not in MOD["a"]}
    assert not manquantes, manquantes


# ── 4. Les pages construites sont atteignables ─────────────────────────────

# Les pages d'offre et de méthode du site : celles pour lesquelles un guide a un
# sens. Écrites une par une, parce qu'une règle automatique ferait entrer ici la
# page de connexion et les mentions légales, qu'aucun parcours ne doit traverser.
PAGES_A_GUIDER = [
    "/architecture-cible", "/continuite-ot", "/formation",
    "/gestion-des-changements", "/gouvernance-ia", "/relecture-contrat",
]


def test_les_pages_construites_sont_atteignables_par_un_parcours():
    """Cinq pages ont été construites, mises au menu — et aucun parcours n'y
    menait. Elles portaient même leurs axes dans AXES_URL : quelqu'un les avait
    pensées dans le croisement, aucun itinéraire n'y passait. Une page qu'aucun
    guide ne traverse n'est atteinte que par ceux qui la cherchaient déjà."""
    vues = _urls()
    orphelines = [u for u in PAGES_A_GUIDER if u not in vues]
    assert not orphelines, orphelines


def test_chaque_page_ajoutee_est_placee_ou_elle_sert():
    """Une page casée dans un parcours au hasard pour satisfaire le contrôle
    ci-dessus serait pire que l'oubli. On fige donc l'itinéraire qui la porte."""
    attendu = {
        "/formation": "rssi",
        "/gestion-des-changements": "ot",
        "/continuite-ot": "ot",
        "/architecture-cible": "projet",
        "/relecture-contrat": "achats",
        "/gouvernance-ia": "conformite",
    }
    vues = _urls()
    for url, role in attendu.items():
        assert role in vues.get(url, []), (url, vues.get(url))


# ── 5. Le premier visiteur voit quelque chose avant le mur ─────────────────

def test_le_parcours_de_decouverte_commence_par_ce_qui_est_ouvert():
    """Le parcours écrit pour celui qui n'a RIEN — pas même un compte —
    ouvrait sur trois pages fermées d'affilée. Il était le seul à ne rien
    montrer au visiteur auquel il s'adresse."""
    dec = [p for p in MOD["p"] if p["id"] == "decouverte"][0]
    deux = [e["url"] for e in dec["etapes"][:2]]
    fermees = [u for u in deux if acces.statut(u) != "direct"]
    assert not fermees, (
        "les deux premières étapes de « Première visite » doivent être en accès "
        "direct : %s" % fermees)


def test_le_parcours_de_decouverte_previent_du_mur():
    """Montrer avant le mur ne dispense pas d'annoncer le mur."""
    js = _lire("parcours.js")
    i = js.index('id: "decouverte"')
    bloc = js[i:i + 1200]
    assert "accès libre" in bloc and "demandent un compte" in bloc


# ── 6. Le module peut vérifier sa liste auprès du serveur ──────────────────

def test_parcours_rafraichit_sa_liste_depuis_le_serveur():
    """La liste écrite dans parcours.js est la réponse immédiate, pas la
    vérité. Sans ce rafraîchissement, elle redeviendrait fausse au prochain
    changement de politique — entre le déploiement et le jour où quelqu'un
    relit ce fichier."""
    js = _lire("parcours.js")
    assert "window.navAcces" in js
    assert "synchroniserAcces" in js
    # Et il est réellement appelé à l'amorçage, pas seulement défini.
    i = js.index("function init()")
    assert "synchroniserAcces()" in js[i:i + 400]


def test_nav_offre_bien_cette_reponse():
    """L'autre moitié du contrat. Si nav.js cessait de l'offrir, parcours.js
    retomberait silencieusement sur sa liste écrite."""
    nav = _lire("nav.js")
    assert "window.navAcces = accesPromesse" in nav
    assert '"/api/acces"' in nav


def test_une_seule_question_de_session_par_page():
    """/api/auth/me est en no-store : chaque appel coûte une lecture de compte
    en base. parcours.js doit passer par la promesse partagée de nav.js, pas
    en lancer une seconde.

    On cherche l'APPEL, pas la mention. Écrit d'abord comme une simple absence
    de la chaîne, ce contrôle tombait sur le commentaire qui explique justement
    pourquoi on ne l'appelle pas — un contrôle qui interdit d'expliquer sa
    propre raison d'être finit par faire supprimer l'explication."""
    js = _lire("parcours.js")
    appels = re.findall(r'fetch\(\s*"(/api/[^"]*)"', js)
    assert "/api/auth/me" not in appels, appels


def test_toute_page_qui_porte_les_parcours_porte_nav():
    """parcours.js s'appuie sur nav.js pour connaître l'état d'accès. Une page
    qui porterait l'un sans l'autre afficherait des cadenas figés — y compris à
    un client connecté, à qui rien n'est fermé."""
    seules = []
    for nom in os.listdir(ICI):
        if not nom.endswith(".html"):
            continue
        h = _lire(nom)
        if "/parcours.js" in h and "/nav.js" not in h:
            seules.append(nom)
    assert not seules, seules


# ── 7. Ce qu'une étape doit porter pour être un guide ──────────────────────

def test_chaque_etape_dit_quoi_faire_ce_qu_on_gagne_et_le_piege():
    """Une étape sans les trois est un sommaire, pas un guide."""
    maigres = []
    for nom, etapes in _itineraires():
        for e in etapes:
            for champ in ("action", "gain", "tip"):
                if len(e.get(champ, "")) < 40:
                    maigres.append((nom, e["url"], champ))
    assert not maigres, maigres


def test_aucune_note_sectorielle_n_en_ecrase_une_autre():
    """Une clé écrite deux fois dans le même objet JavaScript ne lève rien :
    la seconde efface la première, et la moitié de ce qu'on avait à dire
    disparaît sans bruit. C'était le cas du secteur « eau » sur /nis2."""
    js = _lire("parcours.js")
    doublons = []
    for m in re.finditer(r"notes: \{(.*?)\n      \},", js, re.S):
        cles = re.findall(r'"(/[a-z0-9\-]+)":', m.group(1))
        doublons += [c for c in set(cles) if cles.count(c) > 1]
    assert not doublons, doublons


def test_une_note_sectorielle_vise_une_page_du_site():
    """Une note attachée à une URL qu'aucune étape ne visite ne s'affichera
    jamais : elle est écrite pour personne."""
    vues = set(_urls())
    perdues = []
    for s in MOD["s"]:
        for url in s.get("notes", {}):
            if url not in vues:
                perdues.append((s["id"], url))
    assert not perdues, perdues
