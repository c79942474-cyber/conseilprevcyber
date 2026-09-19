# -*- coding: utf-8 -*-
"""Le conseiller de parcours, et la conclusion qui cesse d'être une copie.

DEUX DÉFAUTS MESURÉS, ET CE QUI LES RELIE.

  1. LA CONCLUSION ÉTAIT LA MÊME VINGT-DEUX FOIS. `conclure` ajoute une
     dernière étape « Soumettre votre projet » à tout itinéraire qui n'écrit
     pas la sienne. Elle disait à tout le monde exactement la même chose. C'est
     la seule étape où le site DEMANDE quelque chose au lecteur, et c'était la
     seule qui ne savait pas ce qu'il venait de faire.

  2. LA MODALE OUVRAIT SUR TREIZE RÔLES. Choisir supposait de connaître notre
     découpage — ce qu'un premier visiteur ignore par définition. Cinq entrées
     « centre de données » visitent des pages qui se recouvrent à 80 % et plus,
     et rien à l'écran ne disait laquelle était la sienne avant de l'ouvrir.

CE QUI LES RELIE, ET QUI EST LE CŒUR DE CE FICHIER. On a d'abord cru que le
second défaut était un problème de DOUBLONS : `dc-couts` et `dc-charge-ia`
visitent EXACTEMENT les mêmes quatre pages. La mesure a dit autre chose — sur
trois de ces quatre pages, les deux itinéraires posent une question
différente, et l'ordre lui-même est inverse (l'un part des quantités et
descend vers les honoraires, l'autre part de la charge et descend vers le
bâtiment). Supprimer l'un aurait supprimé une lecture, pas une redite.

D'où la définition qu'on retient ici, et qui commande la règle du §2 :

    UN DOUBLON N'EST PAS DEUX ITINÉRAIRES QUI VISITENT LES MÊMES PAGES.
    C'EST DEUX ITINÉRAIRES QU'AUCUNE RÉPONSE DU VISITEUR NE SÉPARE.

Elle est vérifiable, elle porte sur ce que le visiteur vit, et elle tombe au
bon endroit : si deux profils deviennent identiques, le conseiller ne peut
plus les distinguer, et c'est à ce moment-là qu'il faut fusionner.
"""
import itertools
import json
import os
import re
import subprocess
import sys
import unicodedata

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

_CACHE = {}


def _lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


def _noeud(expr):
    """Évalue une expression contre le VRAI module, jamais contre une copie."""
    if expr in _CACHE:
        return _CACHE[expr]
    script = os.path.join(ICI, "tests", "_pc_conseil_%d.js" % (abs(hash(expr)) % 10 ** 8))
    with open(script, "w", encoding="utf-8") as f:
        f.write("const m=require('%s/parcours.js');"
                "process.stdout.write(JSON.stringify(%s));" % (ICI, expr))
    try:
        out = subprocess.run(["node", script], capture_output=True, text=True, timeout=120)
        assert out.returncode == 0, out.stderr
        v = json.loads(out.stdout)
        _CACHE[expr] = v
        return v
    finally:
        os.remove(script)


def _donnees():
    return _noeud("{p:m.PARCOURS,s:m.SECTEURS,e:m.EMPORTER,q:m.QUESTIONS,"
                  "poids:m.POIDS_Q,marge:m.MARGE_MINIMALE}")


def _conseils(combinaisons):
    """Un seul aller-retour vers node pour N combinaisons — sinon la suite rampe."""
    arg = json.dumps(combinaisons)
    return _noeud("(%s).map(function(r){return m.conseiller(r);})" % arg)


def _toutes_combinaisons():
    d = _donnees()
    axes = []
    for q in d["q"]:
        axes.append([c["v"] for c in q["choix"] if c["v"]])
    cles = [q["cle"] for q in d["q"]]
    out = []
    for combo in itertools.product(*axes):
        out.append(dict(zip(cles, combo)))
    return out


def _sansaccents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


_VIDES = set("votre vos chaque leur les des une aux dans avec pour que qui est sont".split())


def _mots(s):
    s = _sansaccents(s or "").lower().replace("’", " ").replace("'", " ")
    return [w for w in re.split(r"[^a-z0-9]+", s) if len(w) >= 5 and w not in _VIDES]


def _bigrammes(s):
    w = _mots(s)
    return {w[i] + " " + w[i + 1] for i in range(len(w) - 1)}


def _vocabulaire_des_pages():
    """Ce que CHAQUE page promet, tiré de tous les libellés qui la désignent."""
    d = _donnees()
    voc = {}
    for p in d["p"] + d["s"]:
        for e in p["etapes"]:
            v = voc.setdefault(e["url"], set())
            v |= _bigrammes(e["label"])
            v |= set(_mots(e["label"]))
    par_terme = {}
    for url, termes in voc.items():
        for t in termes:
            par_terme.setdefault(t, set()).add(url)
    return par_terme


# ══════════════════════════════════════════════════════════════════════════
#  1. LA CONCLUSION SAIT CE QUE LE LECTEUR VIENT DE FAIRE
# ══════════════════════════════════════════════════════════════════════════

def _conclusions_ajoutees():
    """Les itinéraires dont la dernière étape a été AJOUTÉE par `conclure`."""
    d = _donnees()
    out = []
    for p in d["p"] + d["s"]:
        if p["etapes"][-1]["url"] == "/vos-projets":
            out.append((p["id"], p, p["etapes"][-1]))
    return out


def test_chaque_itineraire_declare_ce_qu_on_emporte_de_lui():
    """UN ITINÉRAIRE DONT ON NE SAIT PAS DIRE CE QU'IL PRODUIT n'a pas de
    conclusion à offrir. `conclure` sait dégrader — il retombe sur la phrase
    commune plutôt que d'afficher un trou, parce qu'une exception levée dans le
    navigateur tuerait le bandeau sur TOUTES les pages pour une faute
    d'inventaire. C'est donc ici, et nulle part ailleurs, que l'absence se
    refuse.
    """
    d = _donnees()
    for pid, p, fin in _conclusions_ajoutees():
        assert pid in d["e"], (
            "%s reçoit la conclusion commune sans déclarer ce qu'on emporte de lui"
            % pid)
        assert fin["gain"].startswith("Vous arrivez avec "), (
            "%s n'annonce pas ce que le lecteur emporte" % pid)


def test_aucun_itineraire_ne_conclut_par_la_phrase_d_un_autre():
    """VINGT-DEUX FOIS LA MÊME PHRASE, C'ÉTAIT L'ÉTAT DE DÉPART.

    Cette règle seule serait faible : réécrire une phrase suffirait à la faire
    passer sans rien rendre de plus vrai. Elle ne vaut que tenue avec les deux
    suivantes, qui exigent que la phrase PORTE sur l'itinéraire.
    """
    vus = {}
    for pid, p, fin in _conclusions_ajoutees():
        vus.setdefault(fin["gain"], []).append(pid)
    doublons = {g: ids for g, ids in vus.items() if len(ids) > 1}
    assert not doublons, "conclusions identiques : %s" % (
        [ids for ids in doublons.values()],)


def test_chaque_conclusion_cite_une_etape_de_SON_itineraire():
    """LA MOITIÉ POSITIVE. Ce qu'on emporte doit être nommé par au moins une
    des pages qu'on a traversées — sinon c'est une promesse qui ne s'appuie sur
    rien de ce qui précède.

    On compare des BIGRAMMES, pas des mots. Un mot isolé collisionne : « ordre »
    figure dans « L'ordre d'une mission » et dans « donneurs d'ordre », ce qui
    faisait tomber la règle pour une raison sans rapport avec ce qu'elle
    prétend mesurer. Deux mots consécutifs désignent une chose.
    """
    par_terme = _vocabulaire_des_pages()
    d = _donnees()
    for pid, p, fin in _conclusions_ajoutees():
        siennes = {e["url"] for e in p["etapes"]}
        cite = [b for b in _bigrammes(d["e"][pid])
                if b in par_terme and par_terme[b] & siennes]
        assert cite, (
            "ce qu'on emporte de « %s » ne nomme aucune de ses étapes : %r"
            % (pid, d["e"][pid]))


def _mots_qui_nomment_une_page():
    """Les mots qui figurent dans un LIBELLÉ d'étape : ceux-là désignent une
    page, et les employer promet d'y être passé."""
    d = _donnees()
    nomme = {}
    for p in d["p"] + d["s"]:
        for e in p["etapes"]:
            for w in set(_mots(e["label"])):
                nomme.setdefault(w, set()).add(e["url"])
    return nomme


def _vocabulaire_de(p, sauf_la_conclusion=True):
    """Tout ce qu'UN itinéraire dit, sur ses propres pages — pas seulement ses
    libellés. C'est la seule exonération admise par la règle ci-dessous.

    LA CONCLUSION EN EST EXCLUE, ET C'EST TOUT LE POINT. La première version
    l'incluait : le texte jugé entrait dans le vocabulaire qui servait à le
    juger, donc s'exonérait lui-même. La règle passait toujours — non pas
    parce que les conclusions étaient justes, mais parce qu'une promesse
    quelconque y devenait sa propre preuve. Mesurée par une mutation qui
    faisait promettre à « énergie » les clauses d'un fournisseur de modèle,
    elle n'a rien vu.
    """
    voc = set()
    etapes = p["etapes"][:-1] if sauf_la_conclusion else p["etapes"]
    for e in etapes:
        voc |= set(_mots(" ".join([e["label"], e.get("action") or "",
                                   e.get("gain") or "", e.get("tip") or ""])))
    return voc


def test_aucune_conclusion_ne_promet_une_page_que_l_itineraire_ne_montre_pas():
    """LA MOITIÉ QUI MORD : celle qui attrape le copier-coller.

    La règle précédente se contente d'UN terme commun ; recopier la conclusion
    d'un itinéraire sur un autre la passerait souvent. Celle-ci prend le
    problème par l'autre bout : un mot qui figure dans le LIBELLÉ d'une page
    DÉSIGNE cette page, et l'employer promet au lecteur d'y être passé.

    ELLE EXONÈRE, ET C'EST CE QUI LA REND UTILISABLE. Une première version ne
    regardait que les libellés et tombait sur « registre » — parce que
    « Registre des missions » est un libellé — alors que l'itinéraire concerné
    dit lui-même, sur SA page, « repérez le registre des pièces à remettre ».
    Le mot n'y usurpait rien. On confronte donc le terme à TOUT ce que
    l'itinéraire dit sur ses propres pages : s'il s'y trouve, le lecteur l'aura
    rencontré, et la promesse est tenue.
    """
    nomme = _mots_qui_nomment_une_page()
    d = _donnees()
    for pid, p, fin in _conclusions_ajoutees():
        siennes = {e["url"] for e in p["etapes"]}
        voc = _vocabulaire_de(p)
        usurpe = sorted(w for w in set(_mots(d["e"][pid]))
                        if w in nomme and not (nomme[w] & siennes) and w not in voc)
        assert not usurpe, (
            "« %s » promet ce que ses pages ne disent nulle part : %s"
            % (pid, usurpe))


def test_l_itineraire_qui_ecrit_sa_propre_conclusion_n_en_recoit_pas_une_seconde():
    """`achats` FINIT SUR /contact, ET C'EST ÉCRIT À LA MAIN : « faites relire
    votre dossier de consultation avant publication ». Lui coller en plus la
    conclusion commune lui donnerait deux fins, dont une hors sujet.
    """
    d = _donnees()
    achats = [p for p in d["p"] if p["id"] == "achats"][0]
    urls = [e["url"] for e in achats["etapes"]]
    assert urls[-1] == "/contact", urls[-1]
    assert "/vos-projets" not in urls, "achats reçoit DEUX conclusions"
    assert "achats" not in d["e"], (
        "achats déclare ce qu'on emporte alors qu'il écrit sa propre conclusion")


def test_le_geste_commun_reste_commun():
    """LA RÈGLE QUI EMPÊCHE DE SUR-CORRIGER, et elle compte autant que les
    autres. Remplir le formulaire de contact EST le même acte pour les
    vingt-deux itinéraires. Réécrire vingt-deux fois « décrivez votre
    périmètre » n'aurait rien rendu de plus vrai — c'est exactement la
    reformulation qui fait passer un contrôle sans rien corriger.

    Ce qui devait changer, c'est ce qu'on EMPORTE. Le geste, lui, reste écrit
    une seule fois, et cette règle le vérifie.
    """
    actions = {fin["action"] for _, _, fin in _conclusions_ajoutees()}
    tips = {fin["tip"] for _, _, fin in _conclusions_ajoutees()}
    assert len(actions) == 1, "le geste final a été dupliqué en %d versions" % len(actions)
    assert len(tips) == 1, "le conseil final a été dupliqué en %d versions" % len(tips)


# ══════════════════════════════════════════════════════════════════════════
#  2. LE DOUBLON, DÉFINI PAR CE QUE LE VISITEUR PEUT RÉPONDRE
# ══════════════════════════════════════════════════════════════════════════

def test_deux_itineraires_qu_aucune_reponse_ne_separe_sont_un_doublon():
    """LA RÈGLE QUI PORTE LA DÉFINITION DU FICHIER.

    `dc-couts` et `dc-charge-ia` visitent EXACTEMENT les mêmes quatre pages :
    par les URL, ils sont identiques à 100 %. Par ce qu'ils demandent au
    visiteur, ils ne le sont pas — l'un vise l'argent et les délais, l'autre la
    technique, et l'un traite l'IA quand l'autre non. C'est cette séparation-là
    qui compte : c'est la seule que le visiteur peut exprimer.

    Deux profils identiques signifieraient qu'aucune réponse ne les départage.
    Le conseiller ne pourrait alors que tirer au sort — et ce serait le moment
    de fusionner les deux itinéraires, pas de truquer le classement.
    """
    d = _donnees()
    vus = {}
    for p in d["p"]:
        prof = p.get("profil") or {}
        if not prof.get("objet"):
            continue
        cle = (tuple(sorted(prof.get("objet", []))),
               tuple(sorted(prof.get("declencheur", []))),
               tuple(sorted(prof.get("levier", []))))
        vus.setdefault(cle, []).append(p["id"])
    jumeaux = [ids for ids in vus.values() if len(ids) > 1]
    assert not jumeaux, (
        "aucune réponse du visiteur ne sépare ces itinéraires : %s" % jumeaux)


def test_deux_itineraires_aux_memes_pages_donnent_des_lectures_differentes():
    """L'AUTRE MOITIÉ DE LA DÉFINITION. Si deux itinéraires visitent le même
    jeu de pages, ce qu'ils y font doit différer — sinon ce ne sont pas deux
    lectures, c'est deux fois la même, et la règle d'au-dessus ne suffirait pas
    à le voir.

    La conclusion commune est exclue du décompte : elle est ajoutée par
    `conclure`, et son geste est volontairement le même partout.
    """
    d = _donnees()
    roles = [p for p in d["p"]]
    for a, b in itertools.combinations(roles, 2):
        ua = {e["url"] for e in a["etapes"]}
        ub = {e["url"] for e in b["etapes"]}
        if ua != ub:
            continue
        partagees = [u for u in ua if u != "/vos-projets"]
        pa = {e["url"]: e for e in a["etapes"]}
        pb = {e["url"]: e for e in b["etapes"]}
        differentes = [u for u in partagees if pa[u]["action"] != pb[u]["action"]]
        assert len(differentes) * 2 >= len(partagees), (
            "%s et %s visitent les mêmes pages et y font la même chose sur "
            "%d des %d pages partagées"
            % (a["id"], b["id"], len(partagees) - len(differentes), len(partagees)))


# ══════════════════════════════════════════════════════════════════════════
#  3. LE CONSEILLER SE REJOUE, SE CONTESTE, ET S'ABSTIENT QUAND IL FAUT
# ══════════════════════════════════════════════════════════════════════════

def test_les_memes_reponses_donnent_toujours_le_meme_classement():
    """C'EST LA RAISON D'ÊTRE DU MOTEUR, et pas un détail d'implémentation.

    On aurait pu appeler un modèle de langage pour choisir l'itinéraire. Une
    recommandation qu'on ne peut pas rejouer ne se défend pas en réunion :
    « pourquoi ce parcours ? — le modèle l'a dit » n'est pas une réponse. Ici
    deux appels identiques rendent le même classement, au mot près.
    """
    rep = {"objet": "datacenter", "declencheur": "projet", "levier": "budget"}
    deux = _conseils([rep, rep])
    assert json.dumps(deux[0], sort_keys=True) == json.dumps(deux[1], sort_keys=True)


def test_il_n_existe_qu_UN_recours():
    """DEUX ITINÉRAIRES SANS PROFIL, ET L'UN DISPARAÎT SANS BRUIT. Le moteur
    reconnaît le recours à l'absence d'objet, et n'en garde qu'un. Un second
    — par exemple un itinéraire ajouté dont on a oublié le profil — ne serait
    ni candidat ni recours : il n'existerait plus, et rien ne le dirait.
    """
    d = _donnees()
    sans = [p["id"] for p in d["p"] if not (p.get("profil") or {}).get("objet")]
    assert sans == ["decouverte"], (
        "le conseiller compte %d itinéraires sans profil : %s" % (len(sans), sans))


def test_TOUS_les_itineraires_sont_atteignables_sauf_le_recours():
    """UN ITINÉRAIRE QUE LE CONSEILLER NE PROPOSE JAMAIS est un itinéraire que
    ce chemin-là n'ouvre à personne.

    CE QUI EST ATTENDU SE DÉRIVE DE LA LISTE DES PARCOURS, PAS DES PROFILS.
    Une première version lisait « tous ceux qui ont un objet » : effacer le
    profil d'un itinéraire le retirait alors des DEUX côtés de la comparaison,
    et la règle passait en ayant perdu de vue un parcours entier. On part donc
    des treize itinéraires, on en retranche le seul recours, et on exige que
    les douze restants sortent au moins une fois des soixante-quatre
    combinaisons complètes. Un profil trop étroit, dominé sur chacun de ses
    axes, ou tout bonnement absent, se voit ici.
    """
    combos = _toutes_combinaisons()
    atteints = set()
    for r in _conseils(combos):
        # « TROP LARGE » N'EST PAS UNE RECOMMANDATION. Le conseiller y dit
        # explicitement qu'il n'a pas assez demandé, et il aligne les premiers
        # ex æquo par ordre alphabétique. Compter ces trois-là comme
        # « atteints » laissait passer un itinéraire dominé sur tous ses axes :
        # il ne sortait plus jamais que par ce classement de secours, où être
        # cité tient à la première lettre de son identifiant.
        if r["verdict"] in ("retenu", "partage"):
            for x in r["retenus"]:
                atteints.add(x["id"])
        if r.get("second"):
            atteints.add(r["second"]["id"])
    d = _donnees()
    attendus = {p["id"] for p in d["p"]} - {"decouverte"}
    manquants = sorted(attendus - atteints)
    assert not manquants, (
        "aucune combinaison de réponses ne mène à : %s" % manquants)


def test_le_conseiller_ne_tranche_jamais_sur_une_egalite_stricte():
    """UN GAGNANT DÉSIGNÉ À ÉGALITÉ EST UN TIRAGE AU SORT DÉGUISÉ.

    On recalcule l'écart à la main depuis le classement rendu, au lieu de faire
    confiance au verdict : c'est précisément la valeur que le verdict prétend
    respecter, et une règle qui la lirait dans le même champ ne vérifierait
    rien.
    """
    for r in _conseils(_toutes_combinaisons()):
        cl = r["classement"]
        if len(cl) < 2:
            continue
        ecart = cl[0]["score"] - cl[1]["score"]
        if ecart <= 0:
            assert r["verdict"] != "retenu", (
                "verdict « retenu » alors que deux itinéraires sont à égalité : %s"
                % [c["id"] for c in cl[:3]])


def test_l_ecart_annonce_est_l_ecart_reel():
    """LE MOTIF PORTE UN NOMBRE, et un nombre écrit à la main dans une phrase
    est un nombre qui se désynchronise. On vérifie qu'il vaut l'écart réel.
    """
    for r in _conseils(_toutes_combinaisons()):
        if r["verdict"] != "retenu":
            continue
        cl = r["classement"]
        ecart = cl[0]["score"] - cl[1]["score"] if len(cl) > 1 else cl[0]["score"]
        chiffres = re.findall(r"\b(\d+)\b", r["motif"])
        assert chiffres and int(chiffres[0]) == ecart, (
            "le motif annonce %r pour un écart réel de %d" % (r["motif"], ecart))


def test_tout_ecarte_porte_un_motif_qui_nomme_LA_REPONSE_DU_VISITEUR():
    """UN CONSEIL QU'ON NE PEUT PAS CONTREDIRE NE VAUT RIEN EN RÉUNION.

    « score inférieur » n'explique rien. Le motif doit citer ce que le visiteur
    a répondu, en clair — c'est le seul endroit où il peut se dire « non, ce
    n'est pas ma situation » et reprendre la main.
    """
    d = _donnees()
    clair = _noeud("m.EN_CLAIR")
    combos = _toutes_combinaisons()
    for rep, r in zip(combos, _conseils(combos)):
        attendus = {clair[c][v] for c, v in rep.items() if v in clair.get(c, {})}
        for e in r["ecartes"]:
            assert e["motif"], "%s écarté sans motif" % e["id"]
            assert any(a in e["motif"] for a in attendus), (
                "le motif d'écart de %s ne cite aucune réponse du visiteur : %r"
                % (e["id"], e["motif"]))


def test_le_second_n_est_jamais_aussi_presente_comme_ecarte():
    """IL L'ÉTAIT. Le deuxième du classement apparaissait en « voyez celui-ci
    plutôt », puis trois lignes plus bas dans les écartés avec son motif de
    rejet. Le lecteur y lisait deux avis contraires sur le même itinéraire.
    """
    for r in _conseils(_toutes_combinaisons()):
        if not r.get("second"):
            continue
        ids = {e["id"] for e in r["ecartes"]}
        assert r["second"]["id"] not in ids, (
            "%s est à la fois proposé en second et écarté" % r["second"]["id"])


def test_le_second_dit_ce_qu_il_apporte_MEME_quand_il_n_ajoute_aucune_page():
    """LE CAS QUI RÉVÈLE TOUT LE RESTE. Plusieurs itinéraires de ce site
    visitent exactement les mêmes pages. Le second peut donc n'ajouter AUCUNE
    adresse — et changer entièrement la lecture. Afficher « rien » laisserait
    croire qu'il n'apporte rien : c'est faux, et c'est la chose qu'il faut dire
    à l'endroit exact où le lecteur hésite entre les deux.
    """
    vus_sans_ajout = 0
    for r in _conseils(_toutes_combinaisons()):
        s = r.get("second")
        if not s:
            continue
        assert s.get("apport"), "%s proposé en second sans dire ce qu'il apporte" % s["id"]
        if not s["urls_en_plus"]:
            vus_sans_ajout += 1
            assert "aucune page de plus" in s["apport"], s["apport"]
            assert "mêmes pages" in s["apport"], s["apport"]
    assert vus_sans_ajout, (
        "aucune combinaison ne met deux itinéraires aux mêmes pages en "
        "concurrence : cette règle ne mesure plus rien")


def test_le_recours_ne_concourt_jamais_contre_les_autres():
    """LE FILET DOIT ÊTRE FRANC. `decouverte` n'a pas d'objet dans son profil,
    et c'est ce qui le définit. Lui en donner un le ferait gagner au mauvais
    moment — ou, pire, perdre de justesse au moment où on en aurait eu besoin.
    """
    for rep, r in zip(_toutes_combinaisons(), _conseils(_toutes_combinaisons())):
        ids = {x["id"] for x in r["retenus"]}
        assert "decouverte" not in ids, (
            "le recours a été retenu alors que %s désignait quelque chose" % rep)
    vide = _conseils([{}])[0]
    assert vide["verdict"] == "recours"
    assert [x["id"] for x in vide["retenus"]] == ["decouverte"]
    assert vide["retenus"][0]["entree"], (
        "le recours est proposé sans dire ce qu'il est : un lot de consolation")


def test_le_conseiller_dit_quand_il_n_a_pas_ASSEZ_DEMANDE():
    """CINQ ITINÉRAIRES À ÉGALITÉ N'EST PAS UNE ÉGALITÉ, c'est une question
    sans réponse. Les afficher tous les cinq ressemble à un choix et n'en est
    pas un. Le conseiller nomme alors la question restée vide — c'est elle qui
    trancherait.
    """
    r = _conseils([{"objet": "industriel"}])[0]
    assert r["verdict"] == "trop_large", r["verdict"]
    assert set(r["manquantes"]) == {"declencheur", "levier"}, r["manquantes"]
    d = _donnees()
    titres = {q["cle"]: q["titre"].lower() for q in d["q"]}
    for cle in r["manquantes"]:
        assert titres[cle] in r["motif"], (
            "le motif ne nomme pas la question manquante « %s » : %r"
            % (cle, r["motif"]))


# ══════════════════════════════════════════════════════════════════════════
#  4. LES QUESTIONS PARLENT LA LANGUE DU VISITEUR
# ══════════════════════════════════════════════════════════════════════════

def test_aucune_question_n_emploie_NOTRE_vocabulaire():
    """LA PORTE EXISTE POUR CEUX QUI NE CONNAISSENT PAS NOTRE DÉCOUPAGE.

    Une question qui demanderait « êtes-vous exploitant, intégrateur ou
    fournisseur au sens de la 62443 ? » ne servirait qu'à ceux qui n'en ont pas
    besoin. On mesure donc que ni les questions ni leurs réponses n'emploient
    les termes du site.
    """
    d = _donnees()
    interdits = ["62443", "nis 2", "nis2", "dora", "ebios", "parcours",
                 "itinéraire", "sl-t", "csms", "iec", "pue", "ia act"]
    for q in d["q"]:
        textes = [q["titre"]] + [c["l"] for c in q["choix"]]
        for t in textes:
            bas = t.lower()
            for mot in interdits:
                assert mot not in bas, (
                    "la question « %s » emploie notre vocabulaire : %r dans %r"
                    % (q["cle"], mot, t))


def test_chaque_question_offre_UNE_sortie_neutre():
    """« JE NE SAIS PAS ENCORE » DOIT ÊTRE UNE RÉPONSE POSSIBLE, et c'est elle
    qui est cochée au départ : obliger à trancher trois fois pour voir un
    résultat transforme une aide en formulaire. Une réponse neutre ne pèse
    rien, et le conseiller le dit au lieu d'inventer un gagnant.
    """
    d = _donnees()
    for q in d["q"]:
        neutres = [c for c in q["choix"] if c.get("neutre")]
        assert len(neutres) == 1, "%s : %d réponses neutres" % (q["cle"], len(neutres))
        assert neutres[0]["v"] == "", q["cle"]
        assert len([c for c in q["choix"] if c["v"]]) >= 3, (
            "%s n'offre pas assez de vraies réponses pour départager" % q["cle"])


def test_les_poids_classent_les_questions_par_ce_qu_elles_CONTRAIGNENT():
    """L'OBJET EST LA CONTRAINTE DURE : envoyer un exploitant de centre de
    données sur l'analyse de risque d'un réseau OT est FAUX, pas seulement mal
    réglé. Le déclencheur décide de l'ordre de lecture. Le levier n'est qu'un
    départage. Si cet ordre s'inversait, le conseiller recommanderait le bon
    métier sur le mauvais objet.
    """
    d = _donnees()
    poids = d["poids"]
    assert poids["objet"] > poids["declencheur"] > poids["levier"] >= 1, poids
    assert poids["levier"] >= d["marge"], (
        "le levier pèse moins que la marge d'abstention : il ne pourrait "
        "jamais départager deux itinéraires, et la troisième question ne "
        "servirait à rien")


def test_le_score_maximum_AFFICHE_est_le_score_maximum_ATTEIGNABLE():
    """« 6 / 6 » EST ÉCRIT DANS LE RENDU, et un total figé dans une chaîne est
    un total qui se désynchronise dès qu'un poids bouge. On le recalcule.
    """
    d = _donnees()
    total = sum(d["poids"].values())
    src = _lire("parcours.js")
    i = src.index("function carteVerdict(")
    bloc = src[i:src.index("\n  }", i)]
    affiches = re.findall(r'"\s*/\s*(\d+)\s*(?:<|")', bloc) or re.findall(r"/\s*(\d+)", bloc)
    assert affiches, "le rendu n'affiche aucun total"
    assert int(affiches[0]) == total, (
        "le rendu annonce un maximum de %s alors que les poids totalisent %d"
        % (affiches[0], total))
    obtenus = max(x["score"] for r in _conseils(_toutes_combinaisons())
                  for x in r["classement"])
    assert obtenus == total, (
        "aucune combinaison n'atteint le maximum annoncé (%d atteint, %d annoncé)"
        % (obtenus, total))


# ══════════════════════════════════════════════════════════════════════════
#  5. LA PORTE, ET LA FICHE QUI S'AGRANDIT
# ══════════════════════════════════════════════════════════════════════════

def _sans_commentaires(src):
    """Les commentaires de ce dépôt EXPLIQUENT les règles ; ils citent donc les
    sélecteurs qu'elles cherchent. Une règle qui les lirait se satisferait de
    sa propre explication."""
    return re.sub(r"/\*.*?\*/", " ", src, flags=re.S)


def test_la_porte_est_repliee_au_depart():
    """CELUI QUI SAIT QU'IL EST RSSI NE DOIT PAS LA TRAVERSER. Ouverte par
    défaut, elle pousserait les deux listes déroulantes — la voie rapide — hors
    de l'écran pour tout le monde.
    """
    src = _sans_commentaires(_lire("parcours.js"))
    m = re.search(r'<details class=\\?"pc-conseil\\?"([^>]*)>', src)
    assert m, "la porte du conseiller n'est pas une liste dépliable"
    assert "open" not in m.group(1), "la porte s'ouvre toute seule"


def test_le_verdict_REMPLIT_le_menu_au_lieu_de_le_remplacer():
    """LE VISITEUR GARDE LA MAIN. Un conseil qui déciderait à sa place serait
    plus court à écrire et beaucoup plus difficile à démentir : il verrait un
    itinéraire s'ouvrir sans savoir lequel a été choisi, ni pouvoir en changer.
    """
    src = _sans_commentaires(_lire("parcours.js"))
    i = src.index("function brancherConseil(")
    bloc = src[i:src.index("\n  }\n", i)]
    assert 'sel.value = b.getAttribute("data-pc-aller")' in bloc, (
        "le verdict n'écrit pas dans la liste déroulante")
    assert "maj()" in bloc, "le verdict ne déclenche pas l'affichage de la fiche"
    assert 'id="pc-select"' in src, "la liste déroulante des rôles a disparu"


def test_le_verdict_se_recalcule_a_CHAQUE_reponse():
    """LE CLASSEMENT BOUGE PENDANT QU'ON RÉPOND, et c'est ce qui apprend au
    visiteur quelle question compte. Le moteur étant pur, cela ne coûte rien —
    attendre un bouton « calculer » n'aurait coûté que de l'attention.
    """
    src = _sans_commentaires(_lire("parcours.js"))
    i = src.index("function brancherConseil(")
    bloc = src[i:src.index("\n  }\n", i)]
    assert 'd.addEventListener("change", calculer)' in bloc, (
        "le verdict ne suit pas les réponses")


def test_la_fiche_s_agrandit_QUAND_IL_Y_A_QUELQUE_CHOSE_A_LIRE():
    """LA MODALE FAIT DEUX MÉTIERS. Tant qu'on CHOISIT, elle porte deux menus
    et doit rester compacte. Dès qu'un itinéraire est affiché, elle porte
    jusqu'à onze étapes avec leur action, leur gain et leur piège — et 780 px
    les empilaient en colonnes étroites.

    La classe doit donc suivre la PRÉSENCE D'UNE FICHE, pas le clic sur un
    menu : piloter depuis les deux écouteurs aurait donné deux endroits à tenir
    d'accord, et c'est dans `fiche()` qu'on sait s'il y a quelque chose à lire.
    """
    src = _sans_commentaires(_lire("parcours.js"))
    i = src.index("function fiche(id, idSec) {")
    bloc = src[i:i + 1400]
    assert 'classList.toggle("pc-lecture"' in bloc, (
        "l'agrandissement n'est pas décidé dans fiche()")
    assert "!!(p || sec)" in bloc, (
        "l'agrandissement ne suit pas la présence d'une fiche")


def test_la_carte_de_lecture_est_plus_large_que_la_carte_de_choix():
    """SI LES DEUX LARGEURS SE REJOIGNAIENT, tout le reste — la transition, la
    bascule, les tailles de texte — continuerait de fonctionner sans rien
    agrandir du tout.
    """
    src = _lire("parcours.js")
    choix = re.search(r"\.pc-card\{[^\"]*max-width:(\d+)px", src)
    lecture = re.search(r"\.pc-card\.pc-lecture\{max-width:(\d+)px", src)
    assert choix and lecture, "l'une des deux largeurs n'est plus déclarée"
    assert int(lecture.group(1)) > int(choix.group(1)) + 100, (
        "la lecture n'est pas plus large que le choix : %s vs %s"
        % (lecture.group(1), choix.group(1)))


def test_le_mouvement_se_coupe_pour_qui_le_demande():
    """UNE MODALE QUI CHANGE DE LARGEUR SOUS LES YEUX est exactement ce que
    `prefers-reduced-motion` désigne.
    """
    src = _lire("parcours.js").replace(" ", "")
    blocs = re.findall(r"prefers-reduced-motion:reduce\)\{(.*?)\}\}", src, flags=re.S)
    assert blocs, "aucune déclaration `prefers-reduced-motion`"
    # LA PREMIÈRE N'EST PAS LA BONNE. Le fichier en portait déjà une, pour
    # l'animation du bouton d'ouverture ; une règle qui lirait « la première »
    # passerait sans que la modale cesse de bouger. On cherche celle qui parle
    # de la carte.
    vise = [b for b in blocs if ".pc-card" in b]
    assert vise, ("la préférence existe pour d'autres éléments, mais rien "
                  "n'arrête l'agrandissement de la modale")
    assert any("transition:none" in b for b in vise), vise
