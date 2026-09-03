# -*- coding: utf-8 -*-
"""Client Impact — une démonstration qui se vérifie, pas une affirmation.

CE QUE CES RÈGLES GARDENT, ET POURQUOI CE SONT DES PROPRIÉTÉS.

  — LE SERVICE RESTE IDENTIQUE. C'est toute la thèse : « à service égal ». Une
    configuration qui toucherait à la puissance, au taux de charge, aux heures
    ou au parc de serveurs comparerait deux services différents, et l'écart
    d'empreinte ne prouverait plus rien — un site deux fois plus petit émet
    deux fois moins, ce n'est pas une performance.
  — L'IDENTITÉ MULTIPLICATIVE EST RECALCULÉE ICI, pas lue. Se contenter de
    croire le drapeau `identite_verifiee` que rend le module serait vert parce
    que le module le dit — exactement le défaut que ce dépôt traque.
  — AUCUN CHIFFRE D'EMPREINTE N'EST ÉCRIT. Ni dans le module, ni dans la page.
    Un nombre figé dans une page de marketing ment au premier réglage du
    moteur, et personne ne le voit : la carte continue de l'afficher avec
    l'assurance d'un chiffre.
  — LA PAGE DIT D'OÙ VIENNENT LES NOMBRES. Un cas type sans résultat ne trompe
    personne ; un cas type AVEC des nombres se lit comme une mesure de terrain
    si rien ne dit qu'ils sortent d'un moteur de calcul.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter as D                                             # noqa: E402
import impact_client as I                                          # noqa: E402

PAGE = "etudes-de-cas.html"
SCRIPT = "impact-client.js"


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


ETUDE = I.comparer()


def _conf(cle):
    return [c for c in ETUDE["configurations"] if c["cle"] == cle][0]


# ═══════════════════════════════════════════════════════════════════════════
#  1. « LE MÊME SERVICE » EST UNE CONTRAINTE, PAS UNE FORMULE DE STYLE
# ═══════════════════════════════════════════════════════════════════════════

def test_aucune_configuration_ne_touche_a_ce_qui_definit_le_service():
    """SANS CETTE RÈGLE, LA DÉMONSTRATION S'EFFONDRE. Comparer deux sites de
    puissances différentes reviendrait à féliciter le plus petit."""
    invariants = {i["cle"] for i in I.INVARIANTS}
    assert len(invariants) >= 4, "trop peu d'invariants pour que la règle morde"
    for c in I.CONFIGURATIONS:
        touches = invariants & set(c["leviers"])
        assert not touches, (
            "la configuration « %s » modifie %s, qui définit le service"
            % (c["cle"], sorted(touches)))


def test_le_module_REFUSE_de_se_charger_si_le_service_bouge(monkeypatch):
    """LE TÉMOIN. La règle précédente lit la table ; celle-ci vérifie que le
    contrôle du module attrape réellement le cas, au lieu d'être un commentaire
    d'intention."""
    faux = [dict(I.CONFIGURATIONS[0]), dict(I.CONFIGURATIONS[1])]
    faux[0]["leviers"] = dict(faux[0]["leviers"], puissance_it_kw=600)
    monkeypatch.setattr(I, "CONFIGURATIONS", faux)
    fautes = I._verifier()
    assert any("SERVICE" in f for f in fautes), fautes


def test_chaque_invariant_dit_pourquoi_il_en_est_un():
    """Un invariant sans justification est une constante qu'on déplacera le
    jour où elle gêne."""
    for i in I.INVARIANTS:
        assert (i.get("pourquoi") or "").strip(), i["cle"]
        assert (i.get("nom") or "").strip() and i.get("unite"), i["cle"]


def test_les_deux_sites_recoivent_reellement_le_meme_service():
    """LA PREUVE PAR LE MOTEUR, ET NON PAR LA TABLE. Les deux profils passés au
    calcul doivent rendre la MÊME énergie informatique : c'est la définition
    opérationnelle de « le même service »."""
    e = {}
    for c in I.CONFIGURATIONS:
        profil = dict(I.SERVICE)
        profil.update(c["leviers"])
        e[c["cle"]] = D.etude(profil)["energie"]["energie_it_MWh"]["valeur"]
    valeurs = sorted(set(round(v, 6) for v in e.values()))
    assert len(valeurs) == 1, (
        "les configurations ne rendent pas le même service informatique : %s" % e)


# ═══════════════════════════════════════════════════════════════════════════
#  2. LA DÉCOMPOSITION SE VÉRIFIE — elle ne se croit pas
# ═══════════════════════════════════════════════════════════════════════════

def test_l_identite_multiplicative_est_RECALCULEE_et_tombe_juste():
    """CROIRE LE DRAPEAU DU MODULE SERAIT VERT PARCE QUE LE MODULE LE DIT. On
    refait le calcul depuis le moteur : le rapport des émissions d'exploitation
    DOIT être le produit du rapport des PUE par celui des intensités de réseau.
    Si l'identité cesse de tomber juste, la décomposition ne décompose plus
    rien et la carte doit se taire."""
    a, b = {}, {}
    for cle, dest in (("a", a), ("b", b)):
        c = [x for x in I.CONFIGURATIONS if x["cle"] == cle][0]
        profil = dict(I.SERVICE)
        profil.update(c["leviers"])
        r = D.etude(profil)
        dest["pue"] = r["energie"]["pue"]["valeur"]
        dest["co2"] = r["carbone"]["co2_exploitation_localise_t"]["valeur"]
        dest["pays"] = c["leviers"]["pays"]
    attendu = ((a["pue"] / b["pue"])
               * (D.INTENSITE_RESEAU[a["pays"]] / D.INTENSITE_RESEAU[b["pays"]]))
    constate = a["co2"] / b["co2"]
    assert abs(attendu - constate) <= 1e-6 * constate, (attendu, constate)
    d = ETUDE["decomposition"]
    assert d["identite_verifiee"] is True
    assert abs(d["produit"] - attendu) <= 1e-9, (d["produit"], attendu)


def test_la_decomposition_se_TAIT_si_l_identite_ne_tombe_plus(monkeypatch):
    """Afficher une décomposition qui ne décompose plus présenterait comme une
    explication ce qui n'en serait plus une.

    MA PREMIÈRE VERSION NE ROMPAIT RIEN. Elle changeait l'intensité d'un pays
    dans la table — or le moteur lit la MÊME table, donc les deux côtés
    bougeaient ensemble et l'identité continuait de tomber juste. Une règle qui
    croit éprouver un garde-fou sans jamais le solliciter. On casse donc la
    CHAÎNE elle-même : un calcul du carbone qui ne serait plus le produit de
    l'énergie par l'intensité."""
    vrai = D.etude

    def truque(profil):
        r = vrai(profil)
        if profil.get("pays") == "PL":
            r["carbone"]["co2_exploitation_localise_t"]["valeur"] *= 1.4
        return r

    monkeypatch.setattr(D, "etude", truque)
    e = I.comparer()
    assert e["decomposition"]["identite_verifiee"] is False, (
        "la chaîne de calcul est rompue et la décomposition s'affiche quand même")
    assert (e["decomposition"]["reserve_si_fausse"] or "").strip()


def test_le_facteur_reseau_vient_bien_DU_PAYS_et_le_dit(monkeypatch):
    """LE RÉCIT DE CETTE FICHE EST « C'EST LE CHOIX DU LIEU ». Le moteur accepte
    une intensité imposée en entrée qui court-circuite le pays : le chiffre
    resterait juste et le récit deviendrait faux. La démonstration le vérifie
    au lieu de le supposer."""
    assert I.comparer()["decomposition"]["intensite_du_pays"] is True
    faux = [dict(c) for c in I.CONFIGURATIONS]
    faux[0]["leviers"] = dict(faux[0]["leviers"], intensite_reseau_g=50)
    monkeypatch.setattr(I, "CONFIGURATIONS", faux)
    assert I.comparer()["decomposition"]["intensite_du_pays"] is False, (
        "une intensité imposée passe pour l'intensité du pays")


def test_la_decomposition_lit_l_intensite_EMPLOYEE_pas_une_seconde_table():
    """DEUX SOURCES DIVERGENT. Le facteur affiché doit être celui qui a servi au
    calcul, et le moteur le déclare dans les entrées de sa formule."""
    s = _src("impact_client.py")
    assert "intensité (g/kWh)" in s, (
        "la décomposition ne lit pas l'intensité que le moteur déclare avoir "
        "employée")
    bloc = s[s.index("def _decomposition("):]
    bloc = bloc[:bloc.index("\n\n\n")]
    assert "INTENSITE_RESEAU" not in bloc, (
        "la décomposition relit la table à côté du moteur : deux sources")


def test_chaque_facteur_de_la_decomposition_nomme_sa_source():
    for f in ETUDE["decomposition"]["facteurs"]:
        assert (f.get("source") or "").strip(), f["cle"]
        assert (f.get("pourquoi") or "").strip(), f["cle"]
        assert f["valeur"] and f["valeur"] > 0, f["cle"]


# ═══════════════════════════════════════════════════════════════════════════
#  3. AUCUN CHIFFRE D'EMPREINTE N'EST ÉCRIT — ni au module, ni à la page
# ═══════════════════════════════════════════════════════════════════════════

def _valeurs_notables():
    """Les nombres que la démonstration produit et qui seraient tentants à
    figer : les grands, ceux qui font le titre."""
    out = []
    for c in ETUDE["configurations"]:
        for t in c["indicateurs"].values():
            if t and isinstance(t["valeur"], (int, float)) and abs(t["valeur"]) >= 1000:
                out.append(t["valeur"])
    return out


@pytest.mark.parametrize("fichier", [PAGE, SCRIPT, "impact_client.py"])
def test_aucun_resultat_n_est_fige_dans_le_texte(fichier):
    """UN NOMBRE FIGÉ MENT AU PREMIER RÉGLAGE DU MOTEUR, et personne ne le
    voit : la page continue de l'afficher avec l'assurance d'un chiffre. La
    règle cherche les résultats sous leurs deux écritures — brute et à la
    française — dans la page, le script et le module."""
    src = _src(fichier)
    valeurs = _valeurs_notables()
    assert len(valeurs) >= 6, "trop peu de résultats notables pour mesurer"
    for v in valeurs:
        entier = int(round(v))
        # LES QUATRE ÉCRITURES SOUS LESQUELLES UN RÉSULTAT PEUT SE FIGER.
        # Les trois séparateurs ci-dessous sont VISUELLEMENT IDENTIQUES et
        # distincts en octets : espace fine insécable (U+202F, celle que
        # produit Intl.NumberFormat("fr-FR")), espace insécable (U+00A0,
        # celle qu'on tape en HTML) et espace ordinaire. Ne chercher que
        # la dernière laisserait passer les deux premières — c'est-à-dire
        # justement celles qu'on recopierait depuis la page rendue.
        for forme in (str(entier),
                      "{:,}".format(entier).replace(",", " "),
                      "{:,}".format(entier).replace(",", " "),
                      "{:,}".format(entier).replace(",", " ")):
            assert forme not in src, (
                "%s porte le résultat %s en dur : il cessera d'être vrai sans "
                "que rien ne le signale" % (fichier, forme))


def test_chaque_indicateur_arrive_avec_sa_formule_sa_source_et_son_incertitude():
    """UN NOMBRE SANS ELLES SE CROIT OU SE REJETTE — les deux sont mauvais. Le
    moteur les rend ; le module ne doit pas les perdre en chemin."""
    vus = 0
    for c in ETUDE["configurations"]:
        for cle, t in c["indicateurs"].items():
            assert t is not None, "%s : indicateur %s absent" % (c["cle"], cle)
            assert (t.get("formule") or "").strip(), (c["cle"], cle, "formule")
            assert (t.get("source") or "").strip(), (c["cle"], cle, "source")
            assert (t.get("incertitude") or "").strip(), (c["cle"], cle, "incertitude")
            vus += 1
    assert vus >= 18, "trop peu d'indicateurs pour que la règle mesure"


def test_le_module_ne_recopie_aucune_valeur_du_moteur():
    """Le module lit le moteur ; il ne le double pas. Une table d'empreintes
    écrite ici dériverait de celle de /datacenter au premier réglage."""
    s = _src("impact_client.py")
    for interdit in ("INTENSITE_RESEAU = ", "REFROIDISSEMENT = ",
                     "def energie(", "def carbone(", "def eau("):
        assert interdit not in s, (
            "le module redéfinit « %s » au lieu de le lire dans le moteur"
            % interdit)
    assert "import datacenter" in s


# ═══════════════════════════════════════════════════════════════════════════
#  4. CE QUE LA DÉMONSTRATION REVENDIQUE, ET CE QU'ELLE NE REVENDIQUE PAS
# ═══════════════════════════════════════════════════════════════════════════

def test_aucun_client_n_est_nomme_nulle_part():
    """CETTE PAGE S'INTITULE « RÉFÉRENCES & MISSIONS ». Une fiche chiffrée qui
    laisserait croire à une mission conduite vaudrait mieux ne pas exister."""
    interdits = ("EDF", "RENAULT", "ATOS", "ALSTOM", "GRDF", "TECHNIP",
                 "Orange", "OVH", "Equinix", "Interxion", "Scaleway", "Data4")
    s = _src("impact_client.py") + _src(SCRIPT)
    for mot in interdits:
        assert mot.lower() not in s.lower(), (
            "« %s » est nommé dans la démonstration" % mot)
    assert "mission conduite" in I.NATURE.lower()
    for mot in ("aucun client", "aucune mesure"):
        assert mot in I.NATURE.lower(), mot


def test_la_carte_dit_que_ses_chiffres_sont_CALCULES_et_non_mesures():
    """UN CAS TYPE AVEC DES NOMBRES SE LIT COMME UNE MESURE DE TERRAIN si rien
    ne dit qu'ils sortent d'un moteur. Le badge est dans l'en-tête de la carte,
    là où on lit son nom — pas dans une note de bas de fiche."""
    h = _src(PAGE)
    i = h.index('id="cas-impact-client"')
    entete = h[i:i + 900]
    assert 'class="typ"' in entete, "la carte ne se déclare pas cas type"
    assert 'class="calc"' in entete, (
        "la carte porte des nombres sans dire qu'ils sont calculés")
    assert "chiffres calculés" in entete
    # Et la légende de la page explique la marque, sinon elle est décorative.
    tete = h[:h.index('id="cas-impact-client"')]
    assert 'class="calc"' in tete and "/datacenter" in tete, (
        "la légende de la page n'explique pas la marque « chiffres calculés »")


def test_la_carte_dit_sa_these_SANS_le_script():
    """SI L'INTERFACE NE RÉPOND PAS, le lecteur doit perdre les nombres et
    garder le propos — jamais un bloc vide au milieu d'une page de références."""
    h = _src(PAGE)
    i = h.index('id="cas-impact-client"')
    carte = h[i:h.index("</div>", h.index('id="ci-calcul"'))]
    texte = re.sub(r"<[^>]+>", " ", carte)
    texte = re.sub(r"\s+", " ", texte)
    assert "exactement le même service" in texte, (
        "la thèse n'est pas écrite dans la page")
    assert len(texte) > 700, (
        "la carte ne dit presque rien sans son script : %d signes" % len(texte))


def test_les_reserves_disent_ce_que_la_comparaison_n_etablit_pas():
    """UN CADRE QUI NE DIT QUE SES FORCES N'EST PAS UN CADRE, c'est une
    plaquette. Et la première réserve porte sur la grandeur la MOINS fermement
    établie, qui est justement celle qui devient majoritaire."""
    assert len(I.RESERVES) >= 4
    for r in I.RESERVES:
        assert len(r) > 60, r
    jointes = " ".join(I.RESERVES).lower()
    for sujet in ("moyennes annuelles", "incorporé", "pue", "amont"):
        assert sujet in jointes, "aucune réserve sur « %s »" % sujet


# ═══════════════════════════════════════════════════════════════════════════
#  5. L'ENSEIGNEMENT SUR LES DEUX PÉRIMÈTRES — le plus contre-intuitif
# ═══════════════════════════════════════════════════════════════════════════

def test_le_site_a_certificats_est_PHYSIQUEMENT_le_meme_que_le_site_A():
    """SANS CELA, L'ENSEIGNEMENT COMPARE DEUX SITES et perd tout son sens : il
    ne dit plus « le même site publie deux chiffres », il dit « deux sites
    différents publient deux chiffres », ce qui n'apprend rien."""
    a = [c for c in I.CONFIGURATIONS if c["cle"] == "a"][0]
    ac = [c for c in I.CONFIGURATIONS if c["cle"] == "a_certificats"][0]
    assert ac.get("physiquement_identique_a") == "a"
    physiques = {k: v for k, v in ac["leviers"].items()
                 if k != "part_renouvelable"}
    assert physiques == a["leviers"], (physiques, a["leviers"])


def test_les_deux_perimetres_donnent_bien_deux_chiffres_differents():
    """LE TÉMOIN DE L'ENSEIGNEMENT. S'ils étaient égaux, le constat serait vrai
    et vide — et il resterait affiché."""
    ecart = ETUDE["ecarts"]["meme_site_deux_chiffres"]
    assert ecart["localise_t"] > 0, "le réseau réel n'émet rien : rien à montrer"
    assert ecart["marche_t"] < ecart["localise_t"], (
        "les deux périmètres donnent le même chiffre : l'enseignement est vide")
    perim = [e for e in ETUDE["enseignements"] if e["cle"] == "perimetre"][0]
    assert perim["appui"]["total_avec_certificats_t"] \
        < perim["appui"]["total_sans_certificats_t"], (
        "l'empreinte publiable ne change pas avec les certificats")


def test_chaque_enseignement_est_tenu_par_un_chiffre_calcule():
    """UN CONSTAT SANS APPUI EST UNE OPINION. Chacun nomme les valeurs qui
    l'établissent, et aucune n'est écrite dans le texte du constat."""
    assert len(ETUDE["enseignements"]) >= 5
    for e in ETUDE["enseignements"]:
        assert e["appui"] and all(v is not None for v in e["appui"].values()), e["cle"]
        assert len(e["texte"]) > 80, e["cle"]
        assert not re.search(r"\d{3,}", e["texte"]), (
            "l'enseignement « %s » écrit un chiffre au lieu de s'appuyer "
            "dessus" % e["cle"])


def test_l_incorpore_devient_bien_majoritaire_sur_le_site_le_plus_propre():
    """LE CONSTAT LE PLUS UTILE DE LA FICHE, et il doit rester VRAI : si le
    moteur évoluait au point que l'incorporé reste minoritaire des deux côtés,
    l'enseignement deviendrait faux et il resterait affiché."""
    a, b = _conf("a"), _conf("b")
    pa = a["indicateurs"]["part_incorpore_pct"]["valeur"]
    pb = b["indicateurs"]["part_incorpore_pct"]["valeur"]
    assert pa < 50 < pb, (
        "l'incorporé n'est plus minoritaire d'un côté et majoritaire de "
        "l'autre : %s %% et %s %%" % (pa, pb))


def test_zero_eau_sur_site_ne_veut_pas_dire_zero_eau():
    """L'AUTRE CONSTAT CONTRE-INTUITIF, éprouvé de la même façon : le site sans
    évaporation doit bien afficher zéro au compteur ET consommer de l'eau en
    amont, sans quoi la fiche affirmerait quelque chose de faux."""
    b = _conf("b")["indicateurs"]
    assert b["appoint_m3"]["valeur"] == 0, "le site B consomme de l'eau au compteur"
    assert b["eau_amont_m3"]["valeur"] > 0, (
        "l'eau amont est nulle : le constat n'a plus d'objet")


def test_sante_ne_ment_pas_sur_l_etat_du_module():
    s = I.sante()
    assert s["fautes"] == []
    assert s["configurations"] == len(I.CONFIGURATIONS)
    assert s["indicateurs"] == len(I.INDICATEURS)
    assert s["moteur"] == D.VERSION, (
        "la santé annonce un moteur qui n'est pas celui qui calcule")


# ═══════════════════════════════════════════════════════════════════════════
#  L'ARITHMÉTIQUE AFFICHÉE DOIT TOMBER JUSTE
# ═══════════════════════════════════════════════════════════════════════════
# LE DÉFAUT QUE CETTE PARTIE GARDE, ET IL A ÉTÉ VU À L'ÉCRAN. La décomposition
# s'affichait « Rapport des PUE 1,1 × Rapport des intensités 15,5 = 17,8 ». Or
# 1,1 × 15,5 fait 17,05. Toute cette phrase existe pour être refaite de tête
# par le lecteur : affichée ainsi, elle le conduisait à conclure que la carte
# était fausse — sur la seule ligne dont l'intérêt est d'être vérifiable.
#
# LA CAUSE N'ÉTAIT PAS UN CALCUL FAUX MAIS UN ARRONDI CHOISI AU MAUVAIS
# ENDROIT : le script décidait de sa précision, et l'affichage démentait le
# calcul. La précision appartient désormais à celui qui promet la
# vérification.

def test_le_produit_des_facteurs_AFFICHES_donne_le_resultat_AFFICHE():
    """LA RÈGLE REFAIT LE CALCUL DU LECTEUR, avec les nombres qu'il a sous les
    yeux — arrondis à la précision que le module demande d'afficher. Lire le
    drapeau `arithmetique_verifiable` serait vert parce que le module le dit."""
    d = ETUDE["decomposition"]
    n = d["decimales"]
    assert isinstance(n, int) and 1 <= n <= 4, n
    vu = 1.0
    for f in d["facteurs"]:
        vu *= round(f["valeur"], n)
    np = d["decimales_produit"]
    assert round(vu, np) == round(d["produit"], np), (
        "le lecteur qui multiplie ce qu'il voit trouve %s, la page annonce %s"
        % (round(vu, np), round(d["produit"], np)))
    assert d["arithmetique_verifiable"] is True


def test_la_precision_est_la_PLUS_PETITE_qui_tombe_juste():
    """AFFICHER QUATRE DÉCIMALES SERAIT JUSTE ET ILLISIBLE, et une ligne
    illisible n'est pas vérifiée. Le témoin : à une décimale de moins,
    l'arithmétique NE doit PAS tomber — sinon on affiche du bruit."""
    d = ETUDE["decomposition"]
    n = d["decimales"]
    if n == 1:
        return
    vu = 1.0
    for f in d["facteurs"]:
        vu *= round(f["valeur"], n - 1)
    np = d["decimales_produit"]
    assert round(vu, np) != round(d["produit"], np), (
        "une décimale de moins suffirait : la page en affiche une de trop")


def test_la_page_APPLIQUE_la_precision_du_serveur_et_ne_la_choisit_pas():
    """CHOISIE DANS LE SCRIPT, elle démentait le calcul.

    VÉRIFIER LA SIGNATURE NE SUFFISAIT PAS, et une mutation l'a montré :
    `function facteur(v, dec)` peut recevoir la précision et l'ignorer dans son
    corps. La règle borne donc au CORPS et exige qu'il s'en serve — et qu'il ne
    rebricole pas une règle de précision à lui."""
    js = _src(SCRIPT)
    assert "function facteur(v, dec)" in js, (
        "le formateur ne reçoit plus la précision")
    corps = js[js.index("function facteur(v, dec)"):]
    corps = corps[:corps.index("\n  }")]
    assert "dec" in corps.split("{", 1)[1], (
        "le formateur reçoit la précision et ne s'en sert pas")
    assert "v < " not in corps and "> 10" not in corps, (
        "le formateur rebricole une règle de précision à lui : %r" % corps)
    assert "facteur(f.valeur, d.decimales)" in js
    assert "facteur(d.produit, d.decimales_produit)" in js


def test_quand_aucune_precision_ne_tombe_juste_le_module_le_DIT():
    """LE REPLI EXISTE ET DOIT ÊTRE VIVANT. Sur les données du jour la
    recherche aboutit toujours, donc la branche d'échec n'est jamais empruntée
    — une mutation y survivait sans rien casser. On l'emprunte ici avec des
    facteurs dont aucun arrondi raisonnable ne reconstitue le produit."""
    dec, ok = I._decimales_qui_tombent_juste([1.0000001, 1e6], 1000000.1)
    assert ok is False and dec == 4, (dec, ok)
    # ET LE TÉMOIN : sur un cas qui tombe, le drapeau doit être vrai — sinon
    # la règle serait satisfaite par une fonction qui répond toujours « non ».
    dec, ok = I._decimales_qui_tombent_juste([1.1489, 15.4878], 1.1489 * 15.4878)
    assert ok is True and dec <= 4, (dec, ok)


def test_si_l_arithmetique_ne_se_relit_pas_la_page_retire_la_multiplication():
    """AFFICHER UNE MULTIPLICATION QUE LE LECTEUR NE PEUT PAS REFAIRE est pire
    que ne rien afficher : il conclut que le reste est faux aussi. Le propos
    reste, l'arithmétique part."""
    js = _src(SCRIPT)
    assert "d.identite_verifiee && d.arithmetique_verifiable" in js, (
        "la page affiche l'arithmétique sans vérifier qu'elle se relit")
    # Et le repli existe : identité vraie, arithmétique illisible.
    i = js.index("else if (d && d.identite_verifiee) {")
    repli = js[i:i + 500]
    assert "d.lecture" in repli and "facteur(" not in repli, (
        "le repli réaffiche des facteurs qu'on ne peut pas multiplier")


def _textes_ecrits_par_le_module():
    """Les textes que CE module écrit — pas ceux que le moteur rend. Les
    incertitudes du moteur portent légitimement des décimales : elles sont
    calculées, pas recopiées."""
    yield "NATURE", I.NATURE
    for i, r in enumerate(I.RESERVES):
        yield "RESERVES[%d]" % i, r
    for x in I.INVARIANTS:
        yield "INVARIANTS/%s" % x["cle"], x["pourquoi"]
    for c in I.CONFIGURATIONS:
        for k in ("nom", "resume", "pourquoi"):
            yield "CONFIGURATIONS/%s/%s" % (c["cle"], k), c[k]
    for x in I.INDICATEURS:
        yield "INDICATEURS/%s" % x["cle"], x["lecture"]
    d = ETUDE["decomposition"]
    yield "decomposition/lecture", d["lecture"]
    yield "decomposition/reserve_si_fausse", d["reserve_si_fausse"]
    for f in d["facteurs"]:
        for k in ("libelle", "pourquoi", "source"):
            yield "decomposition/%s/%s" % (f["cle"], k), f[k]
    for e in ETUDE["enseignements"]:
        for k in ("titre", "texte"):
            yield "enseignements/%s/%s" % (e["cle"], k), e[k]


def test_aucun_texte_du_module_ne_porte_de_nombre_decimal():
    """CE MODULE N'ÉCRIT AUCUN CHIFFRE, et il en écrivait un : « il le divise
    par 1,1 », dans la lecture de la décomposition. Il était faux deux fois —
    à la précision corrigée, et le jour où une famille de refroidissement
    change de plage. Une référence de norme (ISO/IEC 30134-2, EN 50600-4-2)
    n'a pas cette forme : le motif ne cherche qu'un nombre À VIRGULE, qui est
    ce à quoi ressemble un rapport calculé."""
    fautifs = [(ou, t) for ou, t in _textes_ecrits_par_le_module()
               if re.search(r"\d+[,.]\d", t or "")]
    assert not fautifs, (
        "des nombres calculés sont écrits en dur : %s"
        % [(o, re.search(r"[^ ]*\d+[,.]\d[^ ]*", t).group(0)) for o, t in fautifs])
