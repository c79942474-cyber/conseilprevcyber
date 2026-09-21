# -*- coding: utf-8 -*-
"""
LA VEILLE DES CHIFFRES — UN AGENT CHERCHE LA RÉFÉRENCE, UNE PERSONNE LA
RETIENT.

LE DÉFAUT CHASSÉ ICI, MESURÉ LE 21 SEPTEMBRE 2026. Les six chiffres du
bandeau /securite-ia étaient tous `frais` — rien à remplacer avant mi-2027.
Mais CINQ SUR SIX portaient `lien: None` et une réserve `a_confirmer`, dont
quatre renvoyant à une même « Enquête sectorielle 2025 » sans référence ni
adresse. Le module socle l'écrit lui-même : « Un cabinet qui publie 7,2 %
sans pouvoir dire d'où il vient se fait reprendre au premier comité. »

CE QUI EST AUTOMATISÉ : chercher le document, dans un nombre de tours qu'on
ne connaît pas d'avance. CE QUI NE L'EST PAS : décider qu'il fait foi.

LA VÉRIFICATION NE FAIT PAS CONFIANCE À L'AGENT, et c'est ce que la moitié
de ces règles mesurent : la page citée est ROUVERTE par le serveur, la
phrase doit s'y retrouver mot pour mot, et contenir le nombre en cause.
Aucun de ces contrôles ne consulte un modèle.
"""

import datetime
import io
import json
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import chiffres_securite_ia as socle      # noqa: E402
import veille_chiffres as v               # noqa: E402
import veille_chiffres_agent as agent     # noqa: E402

SOURCE_APP = io.open(os.path.join(ICI, 'app.py'), encoding='utf-8').read()
SOURCE_AGENT = io.open(os.path.join(ICI, 'veille_chiffres_agent.py'),
                       encoding='utf-8').read()
BUILD_SH = io.open(os.path.join(ICI, 'build.sh'), encoding='utf-8').read()
REQUIREMENTS = io.open(os.path.join(ICI, 'requirements.txt'),
                       encoding='utf-8').read()
ADMIN_HTML = io.open(os.path.join(ICI, 'admin.html'), encoding='utf-8').read()

AUJ = datetime.date(2026, 9, 21)

PAGE = ("Rapport annuel. Notre enquete menee aupres de 412 organisations montre "
        "que 88 % des organisations interrogees rapportent au moins un incident "
        "de securite lie a un agent IA sur les douze derniers mois.")
LIEN = "https://exemple.org/rapport-2026"


@pytest.fixture(autouse=True)
def magasin_propre():
    """Le magasin des sources est un état de PROCESSUS : sans remise à zéro,
    une règle qui valide une référence ferait passer la suivante pour la
    mauvaise raison — « rien à chercher » au lieu de ce qu'elle mesure."""
    for cle in list(socle.sources_confirmees()):
        socle.oublier_source(cle)
    yield
    for cle in list(socle.sources_confirmees()):
        socle.oublier_source(cle)


def _ouvrir(texte=PAGE, adresse=LIEN, compteur=None):
    def ouvrir(u):
        if compteur is not None:
            compteur.append(u)
        if u != adresse:
            raise OSError("404")
        return texte
    return ouvrir


def _rep(**kw):
    d = {"trouve": True, "lien": LIEN, "editeur": "Institut X",
         "titre": "Rapport annuel 2026", "publie_le": "2026-03-15",
         "citation": "88 % des organisations interrogees rapportent au moins "
                     "un incident de securite",
         "echantillon": "412 organisations"}
    d.update(kw)
    return json.dumps(d, ensure_ascii=False)


def _incidents():
    return v.vue("incidents", AUJ)


def _verifiee():
    p = v.verifier(_incidents(), _rep(), _ouvrir(), AUJ)
    assert p["trouve"] is True, (
        "l'ancre de ce fichier ne tient plus : la réponse de référence ne "
        "produit plus de proposition (%s). Toutes les règles de refus "
        "passeraient alors pour une raison sans rapport." % p.get("motif"))
    return p


# ══════════════════════════════════════════════════════════════════════
# 1. CE QUI ATTEND UNE RÉFÉRENCE — DÉTERMINISTE, SANS MODÈLE
# ══════════════════════════════════════════════════════════════════════

def test_les_chiffres_SANS_reference_sont_exactement_ceux_qui_attendent():
    """Le défaut mesuré : cinq chiffres sur six publiés sans adresse
    ouvrable. Si un jour il n'y en a plus, cette règle tombe — et c'est
    exactement ce qu'on veut qu'elle fasse."""
    dus = {d["cle"] for d in v.a_tracer(AUJ)}
    sans_reference = {c["cle"] for c in socle.CHIFFRES
                      if not c.get("recomptable")
                      and (not c.get("lien") or c.get("a_confirmer"))}
    assert dus == sans_reference, dus ^ sans_reference
    assert dus, "plus aucun chiffre n'attend de référence"


def test_un_chiffre_qui_se_RECOMPTE_n_est_jamais_confie_a_l_agent():
    """Le registre MCP a sa propre fonction de comptage. Lui chercher une
    « référence » ferait faire à un agent, et payer, ce qu'une pagination
    fait exactement."""
    mcp = socle.CHIFFRES_PAR_CLE["mcp"]
    assert v.besoin(mcp, AUJ)["cle"] == "se_recompte"
    assert "mcp" not in {d["cle"] for d in v.a_tracer(AUJ)}


def test_un_chiffre_dont_la_reference_VIENT_D_ETRE_POSEE_sort_de_la_liste():
    """DÉFAUT TROUVÉ EN MESURANT, pas en relisant. `besoin()` lisait la
    table `CHIFFRES` — le chiffre tel qu'il a été ÉCRIT — et non le chiffre
    SERVI. Un chiffre dont la source venait d'être validée restait proposé
    à la recherche : l'agent serait reparti chercher ce qu'on venait de
    trouver."""
    assert "incidents" in {d["cle"] for d in v.a_tracer(AUJ)}
    v.appliquer(_incidents(), _verifiee(), "valider", "C. Cerf")
    assert "incidents" not in {d["cle"] for d in v.a_tracer(AUJ)}
    assert v.besoin(v.vue("incidents", AUJ), AUJ)["cle"] == "rien"


def test_chaque_besoin_dit_POURQUOI_il_appelle_du_travail():
    for b in v.BESOINS.values():
        assert len(b["pourquoi"]) > 40, b


# ══════════════════════════════════════════════════════════════════════
# 2. LA VÉRIFICATION — ELLE ROUVRE LA PAGE
# ══════════════════════════════════════════════════════════════════════

def test_la_page_citee_est_ROUVERTE_et_non_crue_sur_parole():
    """LA RÈGLE CENTRALE. Sans cette relecture, la seule preuve qu'un
    document dit ce qu'on lui fait dire serait la parole de l'agent qui
    prétend l'avoir lu."""
    vus = []
    p = v.verifier(_incidents(), _rep(), _ouvrir(compteur=vus), AUJ)
    assert p["trouve"] is True, p.get("motif")
    assert vus == [LIEN], vus


def test_une_citation_PARAPHRASEE_fait_tomber_la_reference():
    """Une phrase reformulée peut être juste ; elle n'est pas VÉRIFIABLE,
    et c'est sur elle que repose la référence entière."""
    p = v.verifier(_incidents(),
                   _rep(citation="pres de 88 % des entreprises declarent un "
                                 "incident lie a un agent"),
                   _ouvrir(), AUJ)
    assert p["motif"] == "citation_introuvable", p["motif"]
    assert p["lien"] is None
    # GARDE-FOU : la même réponse, citation exacte, passe.
    assert _verifiee()["lien"] == LIEN


def test_une_citation_SANS_le_nombre_est_refusee():
    """Une phrase réellement présente dans la page, mais qui parle d'autre
    chose, prouverait seulement que la page existe."""
    p = v.verifier(_incidents(),
                   _rep(citation="Notre enquete menee aupres de 412 organisations"),
                   _ouvrir(), AUJ)
    assert p["motif"] == "citation_sans_le_chiffre", p["motif"]


def test_le_nombre_ne_se_confond_pas_avec_une_ANNEE():
    """« 13 » est contenu dans « 2013 ». Sans frontière de nombre, une
    citation parlant d'une année validerait le chiffre 13 %."""
    gouv = socle.CHIFFRES_PAR_CLE["gouvernance"]      # 13 %
    page = "Depuis 2013, la gouvernance des systemes agentiques progresse lentement."
    p = v.verifier(gouv,
                   _rep(citation="Depuis 2013, la gouvernance des systemes "
                                 "agentiques progresse"),
                   _ouvrir(page), AUJ)
    assert p["motif"] == "citation_sans_le_chiffre", p["motif"]
    # GARDE-FOU : le vrai 13 %, lui, passe.
    page2 = "Seules 13 % des organisations estiment disposer d'une gouvernance adequate."
    ok = v.verifier(gouv,
                    _rep(citation="Seules 13 % des organisations estiment "
                                  "disposer d'une gouvernance adequate"),
                    _ouvrir(page2), AUJ)
    assert ok["trouve"] is True, ok.get("motif")


def test_une_decimale_s_ecrit_a_la_francaise_ou_a_l_anglaise():
    """« 7,2 » et « 7.2 » sont le même chiffre. Refuser l'une des deux
    ferait tomber des citations justes, et on désactiverait le contrôle."""
    resp = socle.CHIFFRES_PAR_CLE["responsable"]      # 7,2 %
    for ecriture in ("7,2 % ont designe un responsable formel du comportement",
                     "7.2 % ont designe un responsable formel du comportement"):
        page = "Sur 1 204 repondants, " + ecriture + " de leurs agents."
        p = v.verifier(resp, _rep(citation=ecriture, publie_le="2026-02-01"),
                       _ouvrir(page), AUJ)
        assert p["trouve"] is True, (ecriture, p.get("motif"))


def test_les_accents_et_la_casse_ne_font_PAS_tomber_une_vraie_citation():
    page = ("Notre enquête montre que 88 % des organisations interrogées "
            "rapportent au moins un incident de sécurité.")
    p = v.verifier(_incidents(),
                   _rep(citation="88 % DES ORGANISATIONS INTERROGEES rapportent "
                                 "au moins un incident de securite"),
                   _ouvrir(page), AUJ)
    assert p["trouve"] is True, p.get("motif")


def test_une_adresse_injoignable_est_refusee():
    p = v.verifier(_incidents(), _rep(lien="https://ailleurs.org/x"),
                   _ouvrir(), AUJ)
    assert p["motif"] == "lien_injoignable", p["motif"]


def test_une_adresse_qui_n_en_est_pas_une_est_refusee():
    for mauvais in ("/rapport-2026", "exemple.org/r", "javascript:alert(1)"):
        p = v.verifier(_incidents(), _rep(lien=mauvais), _ouvrir(), AUJ)
        assert p["motif"] == "lien_invalide", (mauvais, p["motif"])


def test_un_document_publie_AVANT_la_mesure_qu_il_rapporte_est_refuse():
    p = v.verifier(_incidents(), _rep(publie_le="2024-06-01"), _ouvrir(), AUJ)
    assert p["motif"] == "date_impossible", p["motif"]


def test_une_date_illisible_est_refusee():
    p = v.verifier(_incidents(), _rep(publie_le="mars 2026"), _ouvrir(), AUJ)
    assert p["motif"] == "date_illisible", p["motif"]


def test_pour_une_EDITION_SUIVANTE_un_document_pas_plus_recent_est_refuse():
    """La question n'est pas la même selon le besoin, et le module doit le
    traduire : chercher l'édition suivante d'un rapport, c'est refuser
    celui qu'on a déjà."""
    vieux = dict(socle.CHIFFRES_PAR_CLE["incidents"],
                 lien=LIEN, a_confirmer=None, mesure_le="2022-01-01")
    assert v.besoin(vieux, AUJ)["cle"] == "edition_suivante"
    p = v.verifier(dict(vieux, cle="incidents"),
                   _rep(publie_le="2021-01-01"), _ouvrir(), AUJ)
    # La vue servie commande : « incidents » n'a pas de lien, donc le besoin
    # reste « source_absente » et la date refusée est celle d'avant la mesure.
    assert p["motif"] in ("date_impossible", "edition_pas_plus_recente"), p["motif"]


def test_un_champ_manquant_nomme_ce_qui_manque():
    for champ in ("lien", "editeur", "titre", "publie_le", "citation"):
        p = v.verifier(_incidents(), _rep(**{champ: ""}), _ouvrir(), AUJ)
        assert p["motif"] == "reference_incomplete", (champ, p["motif"])
        assert champ in (p.get("detail") or ""), (champ, p.get("detail"))


def test_une_citation_trop_courte_est_refusee():
    p = v.verifier(_incidents(), _rep(citation="88 %"), _ouvrir(), AUJ)
    assert p["motif"] == "citation_trop_courte", p["motif"]


def test_la_BREDOUILLE_a_son_propre_motif_et_n_est_pas_un_echec():
    """Si aucun document public ne porte « 88 % », le chiffre doit être
    retiré ou réécrit, pas republié avec une attribution vague. C'est une
    information que personne n'avait."""
    p = v.verifier(_incidents(),
                   json.dumps({"trouve": False, "cherche": "enquete agents IA 2025"}),
                   _ouvrir(), AUJ)
    assert p["motif"] == "aucune_source_publique", p["motif"]
    assert p["bredouille"] is True
    assert p["cherche"] == "enquete agents IA 2025"
    assert "pas un échec" in p["motif_texte"] or "résultat" in p["motif_texte"]


def test_une_reponse_bavarde_ne_devient_JAMAIS_une_reference():
    for brut, attendu in ((" ", "reponse_vide"),
                          ("J'ai trouvé le rapport de l'institut.", "reponse_illisible"),
                          ("[]", "reponse_illisible")):
        p = v.verifier(_incidents(), brut, _ouvrir(), AUJ)
        assert p["motif"] == attendu, (brut, p["motif"])
        assert p["lien"] is None


# ══════════════════════════════════════════════════════════════════════
# 3. LA PORTE VERS LE BANDEAU
# ══════════════════════════════════════════════════════════════════════

def test_valider_SANS_nom_ne_pose_RIEN():
    p = _verifiee()
    for vide in ("", "   ", None):
        r = v.appliquer(_incidents(), p, "valider", vide)
        assert r["ok"] is False and r["motif"] == "decideur_absent", vide
    assert "incidents" not in socle.sources_confirmees()
    # GARDE-FOU : avec un nom, la même proposition se pose.
    assert v.appliquer(_incidents(), p, "valider", "C. Cerf")["ok"] is True


def test_ecarter_ne_pose_RIEN():
    r = v.appliquer(_incidents(), _verifiee(), "ecarter", "C. Cerf")
    assert r["ok"] is True and r["statut"] == "ecartee"
    assert r["pose"] is None
    assert "incidents" not in socle.sources_confirmees()


def test_une_proposition_DEJA_decidee_ne_se_decide_pas_deux_fois():
    p = dict(_verifiee(), statut="validee")
    r = v.appliquer(_incidents(), p, "valider", "Quelqu'un")
    assert r["ok"] is False and r["motif"] == "deja_decidee", r


def test_valider_un_REFUS_est_refuse():
    refus = v.verifier(_incidents(), _rep(lien="/relatif"), _ouvrir(), AUJ)
    r = v.appliquer(_incidents(), refus, "valider", "C. Cerf")
    assert r["ok"] is False and r["motif"] == "rien_a_valider", r


def test_la_reference_posee_LEVE_la_reserve_du_bandeau():
    """C'est tout l'objet de l'opération. Garder « référence à établir » à
    côté du lien qui l'établit rendrait l'opération invisible."""
    avant = socle.bandeau(AUJ)["sources_a_confirmer"]
    assert "incidents" in avant
    v.appliquer(_incidents(), _verifiee(), "valider", "C. Cerf — associé")
    apres = socle.bandeau(AUJ)["sources_a_confirmer"]
    assert "incidents" not in apres
    # Et les autres n'ont pas bougé : on lève UNE réserve, pas toutes.
    assert set(apres) == set(avant) - {"incidents"}, (avant, apres)


def test_le_NOM_du_valideur_voyage_avec_la_reference():
    v.appliquer(_incidents(), _verifiee(), "valider", "M. Dupont — RSSI")
    c = [x for x in socle.chiffres(AUJ) if x["cle"] == "incidents"][0]
    assert c["source_validee_par"] == "M. Dupont — RSSI", c
    assert c["source_validee_le"], c
    assert c["lien"] == LIEN and c["a_confirmer"] is None


def test_le_RECHARGEMENT_restitue_ce_qu_une_personne_avait_valide():
    """Sans lui, un redémarrage ramènerait en silence « source à confirmer »
    sur une page où quelqu'un l'avait levée."""
    v.appliquer(_incidents(), _verifiee(), "valider", "C. Cerf")
    garde = socle.sources_confirmees()
    socle.oublier_source("incidents")
    assert "incidents" in socle.bandeau(AUJ)["sources_a_confirmer"]
    assert socle.charger_sources(garde) == 1
    assert "incidents" not in socle.bandeau(AUJ)["sources_a_confirmer"]
    assert socle.sources_confirmees()["incidents"]["valide_par"] == "C. Cerf"


def test_une_cle_inconnue_ne_se_pose_pas():
    assert socle.poser_source("pas_un_chiffre", {"lien": "x"}, "C. Cerf") is None
    assert "pas_un_chiffre" not in socle.sources_confirmees()


# ══════════════════════════════════════════════════════════════════════
# 4. LA LAISSE DE L'AGENT — ICI LES OUTILS SONT LE SUJET
# ══════════════════════════════════════════════════════════════════════

def test_l_agent_a_WebSearch_et_WebFetch_et_RIEN_d_autre():
    """Contrairement à la qualification assistée, où la liste est vide : là
    -bas les lignes voyagent en données, ici il faut aller lire."""
    assert agent.OUTILS_AUTORISES == ["WebSearch", "WebFetch"]


@pytest.mark.parametrize("outil", ["Read", "Write", "Edit", "Bash"])
def test_les_outils_qui_touchent_la_machine_sont_refuses_NOMMEMENT(outil):
    assert outil in agent.OUTILS_INTERDITS, outil
    assert outil not in agent.OUTILS_AUTORISES, outil


def test_les_options_REELLEMENT_passees_au_SDK_portent_les_deux_outils():
    """Mesuré sur l'OBJET passé au SDK, pas sur le code source : une règle
    qui lirait le source passerait encore le jour où une autre ligne, plus
    bas, remplit la liste."""
    o = agent.options_sdk("systeme")
    assert list(o.allowed_tools) == ["WebSearch", "WebFetch"], o.allowed_tools
    for interdit in ("Read", "Write", "Edit", "Bash"):
        assert interdit in o.disallowed_tools, interdit
    assert o.max_turns == agent.TOURS_MAX and o.max_turns > 1
    assert list(o.setting_sources) == [], (
        "l'agent hériterait des consignes du dépôt, écrites pour tout autre "
        "chose")


def test_le_chemin_du_CLI_est_DONNE_au_SDK():
    o = agent.options_sdk("systeme")
    assert o.cli_path == agent.chemin_cli(), (o.cli_path, agent.chemin_cli())


def test_re_verifier_un_chiffre_DEJA_source_est_refuse():
    """Une référence validée ne se re-valide pas : l'agent serait reparti
    chercher ce qu'on vient de trouver, et une seconde décision écraserait
    la première sans que personne l'ait demandé."""
    v.appliquer(_incidents(), _verifiee(), "valider", "C. Cerf")
    p = v.verifier(socle.CHIFFRES_PAR_CLE["incidents"], _rep(), _ouvrir(), AUJ)
    assert p["motif"] == "rien_a_chercher", p["motif"]


def test_l_agent_a_PLUSIEURS_tours_et_un_plafond():
    """Chercher, lire, reformuler, relire : un tour ne suffit pas. Mais une
    recherche sans fond coûte sans rendre."""
    assert agent.TOURS_MAX > 1
    assert agent.TOURS_MAX <= 20


def test_il_n_y_a_AUCUN_repli_quand_l_agent_manque():
    """Un modèle sans accès au web ne retrouve pas un document : il en
    invente un plausible. L'absence de repli est la bonne réponse."""
    e = agent.etat()
    assert e["repli"] is None
    assert "invente" in e["repli_texte"]
    assert "ai_complete" not in SOURCE_AGENT
    assert "mistral" not in SOURCE_AGENT.lower()


def test_le_module_ne_depend_PAS_d_un_fichier_de_l_AUTRE_depot():
    """PREMIÈRE ÉCRITURE, ET POURQUOI ELLE ÉTAIT FAUSSE. Elle importait
    `qualification_moteur`, qui vit dans le dépôt conseilprev. L'import
    échouait silencieusement ici et retombait sur `shutil.which` : la
    résolution paraissait marcher sur ma machine et n'aurait rien résolu en
    ligne."""
    assert "import qualification_moteur" not in SOURCE_AGENT
    assert os.path.exists(os.path.join(ICI, "veille_chiffres_agent.py"))


def test_le_paquet_est_declare_et_le_build_installe_le_CLI():
    assert "claude-agent-sdk" in REQUIREMENTS
    assert "pip install -r" in BUILD_SH
    apres_pip = BUILD_SH[BUILD_SH.index("Exécutable Claude Code"):]
    assert "exit 1" not in apres_pip, (
        "le build peut échouer à cause du CLI : le site entier deviendrait "
        "indéployable pour une fonction qui sait attendre")
    assert apres_pip.rstrip().endswith("exit 0")


def test_la_relecture_de_page_retire_scripts_et_balises():
    """Un `<script>` laissé dans le texte ferait passer pour une citation
    une chaîne qui n'est pas lisible sur la page."""
    class Faux:
        def __init__(self, b):
            self.b = b

        def read(self, n):
            return self.b

        def __enter__(self):
            return self

        def __exit__(self, *e):
            return False

    brut = (b"<html><style>p{color:red}</style><body><p>88 &#37; des "
            b"organisations</p><script>var x=1</script></body></html>")
    t = agent.ouvrir_page("x", ouvrir=lambda u: Faux(brut))
    assert "88 % des organisations" in t
    assert "color:red" not in t and "var x" not in t


# ══════════════════════════════════════════════════════════════════════
# 5. LES ROUTES
# ══════════════════════════════════════════════════════════════════════

def _corps(nom):
    m = re.search(r'def %s\(.*?\n(?=\n@app\.route|\ndef |\Z)' % nom,
                  SOURCE_APP, re.S)
    assert m, nom
    return m.group(0)


def _code_seul(corps):
    sans_doc = re.sub(r'""".*?"""', '', corps, flags=re.S)
    return re.sub(r'#[^\n]*', '', sans_doc)


def test_les_trois_routes_sont_derriere_admin_required():
    """Poser une référence change ce qu'une page publique affirme de ses
    sources. Ce n'est pas une action de visiteur, ni même de client."""
    for nom in ('api_veille_chiffres_referentiel', 'api_veille_chiffres_chercher',
                'api_veille_chiffres_decider'):
        bloc = re.search(r'((?:@[^\n]+\n)+)def %s\(' % nom, SOURCE_APP)
        assert bloc, nom
        assert '@admin_required' in bloc.group(1), nom


def test_la_POLITIQUE_d_acces_exige_aussi_le_niveau_administrateur():
    """LACUNE TROUVÉE EN MESURANT. Le décorateur `@admin_required` est posé
    sur les trois routes, et le démarrage de l'application refuse une
    interface `/api/` laissée ouverte. Mais le DÉFAUT de la politique est
    « client » : elle aurait accepté, sans rien signaler, qu'on descende
    ces routes d'un cran. Les y déclarer fait que le garde de démarrage
    exige ce que le décorateur promet."""
    import acces
    for chemin in ("/api/veille-chiffres/referentiel",
                   "/api/veille-chiffres/chercher",
                   "/api/veille-chiffres/decider"):
        assert acces.api_statut(chemin) == "admin", chemin
        assert acces.API_ADMIN[chemin].strip(), (
            "%s est déclarée sans motif écrit" % chemin)


def test_la_route_qui_CHERCHE_ne_pose_aucune_reference():
    cherche = _code_seul(_corps('api_veille_chiffres_chercher'))
    assert 'poser_source' not in cherche
    assert 'appliquer' not in cherche
    assert 'bandeau_modifie": False' in cherche or '"bandeau_modifie": False' in cherche

    # L'AUTRE MOITIÉ : celle qui décide, elle, applique bien.
    decide = _code_seul(_corps('api_veille_chiffres_decider'))
    assert 'veille_chiffres.appliquer' in decide, (
        "la route qui décide n'applique rien : la règle ci-dessus passerait "
        "parce que personne ne pose jamais de référence")


def test_le_bandeau_PUBLIC_declenche_le_rechargement():
    """DÉFAUT TROUVÉ EN MESURANT. Le rechargement était appelé depuis
    `_init_automation`, qui tourne dans un thread lancé au milieu du
    chargement du module — donc avant que la fonction, définie plus bas,
    n'existe. Il n'avait jamais lieu."""
    bandeau = _code_seul(_corps('api_securite_ia_chiffres'))
    assert '_veille_charger_sources()' in bandeau, (
        "un visiteur lirait « source à confirmer » sur un chiffre dont la "
        "référence est établie depuis des semaines")
    assert '_veille_charger_sources()' not in _code_seul(_corps('_init_automation'))


def test_l_ecran_d_administration_porte_les_deux_commandes():
    assert 'id="vc-liste"' in ADMIN_HTML
    assert 'data-vc-chercher' in ADMIN_HTML
    assert 'data-vc-retenir' in ADMIN_HTML
    assert 'id="vc-decideur"' in ADMIN_HTML
    # ET IL DIT CE QUE L'AGENT NE FAIT PAS.
    assert 'rouverte par le serveur' in ADMIN_HTML
    assert 'ne modifie aucune valeur' in ADMIN_HTML


def test_chaque_ancre_de_la_batterie_de_mutations_EXISTE_ENCORE():
    """Une mutation dont l'ancre ne se retrouve plus ne mute rien : elle
    passe pour « survivante » au prochain passage, et on cherche un défaut
    qui n'existe pas."""
    table = json.load(io.open(os.path.join(ICI, 'tests',
                                           'mutations_veille_chiffres.json'),
                              encoding='utf-8'))
    sources, problemes = {}, []
    for m in table['mutations']:
        f = m['fichier']
        if f not in sources:
            sources[f] = io.open(os.path.join(ICI, f), encoding='utf-8').read()
        n = sources[f].count(m['avant'])
        if n != 1:
            problemes.append("%s : %d occurrence(s) dans %s" % (m['nom'], n, f))
    assert not problemes, "\n".join(problemes)
    assert len(table['mutations']) >= 30, len(table['mutations'])


def test_les_deux_ecritures_portent_un_PLAFOND_de_cadence():
    """OMISSION ATTRAPÉE PAR UNE RÈGLE DÉJÀ EN PLACE — `test_surface_attaque`
    énumère les routes POST au lieu de les nommer, et c'est pour cela qu'elle
    a vu les miennes. Chercher coûte un agent : plusieurs tours de modèle et
    autant de lectures du web."""
    table = re.search(r'_RATE_EXACT = \{(.*?)\n\}', SOURCE_APP, re.S)
    assert table, "la table des plafonds n'a pas été retrouvée"
    for chemin in ("/api/veille-chiffres/chercher", "/api/veille-chiffres/decider"):
        m = re.search(re.escape('"%s"' % chemin) + r':\s*\((\d+),\s*(\d+)\)',
                      table.group(1))
        assert m, chemin
        limite, fenetre = int(m.group(1)), int(m.group(2))
        assert 1 <= limite <= 60 and fenetre >= 60, (chemin, limite, fenetre)
    # Chercher coûte plus cher que décider : son plafond doit être plus bas.
    cherche = int(re.search(r'"/api/veille-chiffres/chercher":\s*\((\d+)',
                            table.group(1)).group(1))
    decide = int(re.search(r'"/api/veille-chiffres/decider":\s*\((\d+)',
                           table.group(1)).group(1))
    assert cherche < decide, (cherche, decide)
