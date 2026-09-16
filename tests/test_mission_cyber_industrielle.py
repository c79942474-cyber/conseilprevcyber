# -*- coding: utf-8 -*-
"""LA MISSION DE CONSEIL EN CYBERSÉCURITÉ INDUSTRIELLE — ce qui manquait, mesuré.

TROIS CONSTATS, LE 16 SEPTEMBRE 2026, EN COMPARANT LE CATALOGUE À LA FICHE
D'UNE MISSION DE MANAGEMENT ICS/OT.

1. LE FONDS ÉTAIT CONNECTÉ ET À MOITIÉ MUET. 83 des 116 thèmes déclarés dans
   `rag_store` n'étaient interrogés par AUCUN groupe de livrables. Côté cyber,
   cela faisait 31 documents et 4 406 fragments indexés — chargés dans la base
   et lus par personne. Le défaut n'était pas la connexion, c'était le
   POINTAGE.

2. TROIS THÈMES SUR CINQ MÉRITAIENT D'ÊTRE BRANCHÉS, ET C'EST LE CONTENU QUI
   L'A DIT. « Normes IEC » promet la famille de la 62443 ; ses dix documents
   sont de l'ATEX et de l'électrotechnique — IEC 60079 atmosphères explosives,
   60034 machines tournantes, 60445 couleurs de câbles. Les brancher ferait
   remonter de la sécurité intrinsèque antidéflagrante dans un livrable de
   cybersécurité. Même défaut que « Fournisseurs & fiches techniques » du côté
   centre de données : le nom promet, seul le contenu engage.

3. QUATORZE ACTIVITÉS SUR SEIZE ÉTAIENT DÉJÀ COUVERTES. Le catalogue est
   riche ; ces règles ne mesurent donc pas une refonte mais CINQ TROUS, dont
   un seul était franc — l'interface sûreté / sécurité, zéro livrable, alors
   que les cinq parties de l'IEC 61508 dormaient en base.

ET LE MANQUE STRUCTUREL. `PAGES_CONSEIL` est une liste PLATE de huit domaines
présentés côte à côte comme s'ils étaient interchangeables. Rien ne disait dans
quel ordre une mission se conduit ni ce que chaque phase exige de la
précédente — alors qu'un operating model écrit avant le diagnostic
organisationnel décrit une organisation qu'on n'a pas regardée, et qu'une
feuille de route écrite avant l'analyse d'écarts séquence des actions dont on
ignore l'ampleur. Ces deux fautes ne se voient pas à la relecture : le livrable
est bien écrit, complet, et faux.
"""
import io
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import livrables                                                 # noqa: E402
import parcours_mission as PM                                    # noqa: E402
import rag_store                                                 # noqa: E402

import pytest                                                    # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE POINTAGE — les thèmes branchés rapportent-ils vraiment ?
# ═══════════════════════════════════════════════════════════════════════════
ANSSI_REF = "ANSSI / Référentiels & qualification"
SURETE = "Sûreté fonctionnelle (IEC 61508/61511)"
SCADA = "SCADA"

# LES TITRES SONT CEUX DE LA BASE DE PRODUCTION, lus le 16 septembre 2026, et
# le texte résume ce que le titre annonce. Des titres inventés auraient mesuré
# mon imagination — c'est en regardant les VRAIS qu'on a vu que « Normes IEC »
# était de l'ATEX.
FONDS = [
    (ANSSI_REF, "pssi-section2-methodologie",
     "Methodologie d'elaboration d'une politique de securite des systemes "
     "d'information : demarche, acteurs, etapes de construction."),
    (ANSSI_REF, "pssi-section3-principes",
     "Principes de securite a decliner dans une PSSI : organisation, "
     "responsabilites, regles par domaine."),
    (ANSSI_REF, "tdbssi-section1-methodologie",
     "Methodologie de construction d'un tableau de bord de la securite des "
     "systemes d'information : choix des indicateurs, collecte, restitution "
     "aux instances de direction."),
    (ANSSI_REF, "Guide ANSSI formation cybersecurite des systemes industriels",
     "Guide de formation a la cybersecurite des systemes industriels : "
     "profils a former, contenus par profil, progression et evaluation."),
    (SURETE, "Sil IEC61508-1",
     "Exigences generales de securite fonctionnelle : cycle de vie de "
     "securite, niveaux d'integrite SIL, allocation des fonctions "
     "instrumentees de securite."),
    (SURETE, "Sil IEC61508-6",
     "Lignes directrices d'application : probabilite de defaillance a la "
     "demande, defaillances de cause commune."),
    (SCADA, "NP ANSSI SDE automate court terme",
     "Securisation des automates programmables a court terme : comptes, "
     "protocoles, sauvegarde des programmes, journalisation."),
]


@pytest.fixture(scope="module")
def fonds():
    rag = rag_store.MemoryRagStore()
    for theme, titre, texte in FONDS:
        rag.ingest_bytes(titre.replace(" ", "-") + ".txt",
                         texte.encode("utf-8"), title=titre, theme=theme,
                         visibility="internal")
    return rag


def _remonte(rag, type_id, requete):
    _groupe, themes = livrables.themes_du_type(type_id)
    hits = rag.search(requete, k=6, public_only=False, theme=themes)
    _bloc, retenus = rag_store.build_context_retenus(hits, max_chars=4000)
    return [h.get("title") for h in retenus]


# CHAQUE LIGNE EST UN LIVRABLE QUI S'ÉCRIVAIT SANS SA PROPRE MÉTHODE, et le
# document qui la porte. Ce ne sont pas des exemples : ce sont les cas qui ont
# motivé le branchement.
APPORTS = [
    ("pssi-ot", "politique de securite des systemes d'information industriels "
                "organisation responsabilites", "pssi-section3-principes"),
    ("form-programme-profils", "programme de formation par profil "
                               "cybersecurite des systemes industriels",
     "Guide ANSSI formation cybersecurite des systemes industriels"),
    ("fdr-tableau-bord", "tableau de bord indicateurs pilotage instances",
     "tdbssi-section1-methodologie"),
    ("sr-interface-surete-securite", "surete fonctionnelle SIL fonctions "
                                     "instrumentees de securite", "Sil IEC61508-1"),
    ("moc-formulaire-impact", "automate programmable changement sauvegarde du "
                              "programme", "NP ANSSI SDE automate court terme"),
]


@pytest.mark.parametrize("type_id,requete,attendu", APPORTS,
                         ids=[t for t, _q, _a in APPORTS])
def test_le_livrable_ATTEINT_le_document_qui_porte_sa_methode(
        type_id, requete, attendu, fonds):
    """LA RÈGLE QUI PORTE LE POINTAGE. Elle ne demande pas que la recherche
    rende « quelque chose » — elle nomme le document, parce que c'est lui qui
    manquait. La trame PSSI s'écrivait sans la méthode PSSI de l'ANSSI, le
    programme de formation sans le guide ANSSI qui le décrit."""
    vus = _remonte(fonds, type_id, requete)
    assert attendu in vus, (
        "%s ne remonte pas « %s », qui porte sa méthode — remontés : %s"
        % (type_id, attendu, vus))


def test_fdr_tableau_de_bord_ne_remontait_RIEN_avant(fonds):
    """CE CAS-LÀ EST NOMMÉ À PART parce qu'il a été trouvé APRÈS le premier
    branchement : quatre livrables remontaient six documents sur six et
    celui-ci zéro. Son groupe n'avait pas été branché — l'oubli ne se voyait
    pas, la mesure l'a dit."""
    assert ANSSI_REF in livrables.themes_du_type("fdr-tableau-bord")[1]


def test_AUCUN_groupe_ne_nomme_un_theme_qui_n_existe_pas():
    """UN THÈME MAL ORTHOGRAPHIÉ NE RAMÈNE RIEN, EN SILENCE.

    LA PREMIÈRE VERSION NE POUVAIT PAS LE VOIR. Elle vérifiait que les trois
    thèmes branchés figuraient dans l'UNION des groupes — or un même thème est
    nommé par cinq groupes, et l'écorcher dans un seul les laissait tous les
    autres corrects. Une mutation qui écrivait « Referentiels et
    qualification » dans le groupe Maturité a traversé la règle.

    ON VÉRIFIE DONC CHAQUE NOM ÉCRIT, DANS CHAQUE GROUPE : c'est là que la
    faute se commet, et c'est là qu'elle doit se voir.

    ET LA PROTECTION EXISTAIT DÉJÀ, PLUS FORTE QUE MA RÈGLE.

    En cherchant pourquoi la mutation survivait, j'ai trouvé
    `_verifier_groupe_themes`, qui lève une `RuntimeError` AU CHARGEMENT du
    module : le thème écorché ne fait pas tomber une règle, il empêche le
    service de démarrer. C'est mieux qu'une règle — et aucune règle ne
    mesurait cette garde-là. On mesure donc la GARDE, puisque c'est elle qui
    protège, et non une vérification parallèle qui ferait doublon.
    """
    # 1. LA GARDE EST ARMÉE : aucune faute aujourd'hui.
    assert livrables.armer_la_garde_des_themes() == []
    # 2. ET ELLE REFUSE DE DÉMARRER SUR UNE FAUTE. Sans ce second temps, une
    #    garde désarmée rendrait la même liste vide qu'une garde qui
    #    travaille — et c'est exactement ce qu'une mutation a montré : elle
    #    remplaçait l'appel par `[]` et aucune règle ne tombait.
    vraie = livrables.GROUPE_THEMES
    try:
        livrables.GROUPE_THEMES = dict(
            vraie, **{"Groupe d'essai": ["Thème qui n'existe pas"]})
        with pytest.raises(RuntimeError) as exc:
            livrables.armer_la_garde_des_themes()
    finally:
        livrables.GROUPE_THEMES = vraie
    assert "Thème qui n'existe pas" in str(exc.value), exc.value
    # 3. LES TROIS THÈMES BRANCHÉS LE SONT BIEN.
    for t in (ANSSI_REF, SURETE, SCADA):
        assert any(t in th for th in livrables.GROUPE_THEMES.values()), (
            "« %s » n'est interrogé par aucun groupe" % t)


def test_la_garde_est_bien_ARMEE_au_chargement():
    """LA LIGNE QUI RELIE, ET QU'AUCUNE AUTRE RÈGLE NE PEUT VOIR.

    La garde peut être juste et n'être jamais appelée : après le chargement,
    `_FAUTES_GROUPE_THEMES` vaut `[]` que la garde ait travaillé ou qu'on lui
    ait substitué une liste vide. Une mutation l'a montré — et aucune
    vérification en mémoire ne peut la distinguer, puisque les deux états sont
    littéralement le même objet.

    ON LIT DONC LA SOURCE, ET C'EST ASSUMÉ. C'est le seul endroit où le
    branchement s'observe. Même procédé que pour le corpus descendu jusqu'au
    socle : mesurer une LIGNE, faute de pouvoir mesurer son effet.
    """
    src = io.open(os.path.join(ICI, "livrables.py"), encoding="utf-8").read()
    assert "_FAUTES_GROUPE_THEMES = armer_la_garde_des_themes()" in src, (
        "la garde des thèmes n'est plus armée au chargement du module : un "
        "thème écorché ne ramènerait rien, en silence")


def test_les_normes_ATEX_restent_DEHORS():
    """LE POINT QUI DEMANDE UNE DÉCISION, ET QUI DOIT LE RESTER.

    « Normes IEC » porte dix documents d'ATEX et d'électrotechnique — 60079
    atmosphères explosives, 60034 machines tournantes, 60445 couleurs de
    câbles. Le nom fait croire à la famille de la 62443. Les brancher un jour
    « pour compléter le fonds cyber » ferait remonter de la sécurité
    intrinsèque antidéflagrante dans un mémoire de cybersécurité, et rien à
    l'écran ne le signalerait."""
    lus = set()
    for _g, themes in livrables.GROUPE_THEMES.items():
        lus |= set(themes)
    assert "Normes IEC" not in lus, (
        "« Normes IEC » est branché : ses documents sont de l'ATEX, pas de "
        "la cybersécurité")


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES CINQ LIVRABLES QUI MANQUAIENT.
# ═══════════════════════════════════════════════════════════════════════════
NEUFS = {
    "sr-interface-surete-securite": "Conseil — Continuité & crise OT",
    "diag-organisationnel-ot": "Conseil — Maturité",
    "revue-dispositif-ot": "Conseil — Maturité",
    "ecarts-62443": "Conformité & risques",
    "atelier-direction": "Conseil — Operating Model",
}


# L'IDENTIFIANT DU CAS EST LA CLÉ SEULE. Composé avec le nom du groupe, il
# porte des espaces, et pytest le tronque au premier : une batterie ne peut
# plus viser un cas précis et croit la règle mal visée alors qu'elle est
# tombée. Même correction que pour les noms de fichiers du cabinet.
@pytest.mark.parametrize("tid,groupe", sorted(NEUFS.items()),
                         ids=sorted(NEUFS))
def test_chaque_livrable_neuf_EXISTE_et_a_son_groupe(tid, groupe):
    t = livrables.get_type(tid)
    assert t, "%s n'est pas au catalogue" % tid
    assert t["groupe"] == groupe, (tid, t["groupe"])
    assert len(t.get("sections") or []) >= 6, (tid, t.get("sections"))
    assert t.get("mots_cles"), tid
    # LES SECTIONS SONT DISTINCTES ET NON VIDES. Une section répétée produit
    # deux fois le même paragraphe dans un livrable remis à un client, et une
    # section vide un titre sans contenu : ni l'une ni l'autre ne se voit à la
    # relecture d'une liste.
    sections = [x.strip() for x in t["sections"]]
    assert all(sections), (tid, t["sections"])
    assert len(set(sections)) == len(sections), (
        "%s répète une section : %s" % (tid, sections))


def test_le_groupe_de_chaque_neuf_EST_INTERROGEABLE():
    """UN LIVRABLE DONT LE GROUPE N'A PAS DE THÈMES SE RÉDIGE SANS FONDS, et
    cela ne se voit pas : le texte sort, il est simplement générique."""
    for tid in NEUFS:
        _g, themes = livrables.themes_du_type(tid)
        assert themes, "%s n'interroge aucun thème" % tid


def test_l_interface_SURETE_securite_atteint_bien_la_61508(fonds):
    """LE SEUL TROU FRANC DE LA MESURE, et sa matière était déjà en base : le
    livrable n'existait pas ET les cinq parties de la 61508 n'étaient lues par
    personne. Les deux se corrigent ensemble ou aucun ne sert."""
    vus = _remonte(fonds, "sr-interface-surete-securite",
                   "surete fonctionnelle SIL cycle de vie de securite "
                   "fonctions instrumentees")
    assert any("61508" in (v or "") for v in vus), vus


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE PARCOURS DE MISSION.
# ═══════════════════════════════════════════════════════════════════════════
def test_aucune_phase_ne_promet_un_livrable_INEXISTANT():
    """UNE CARTE QUI NE PEUT PAS SE TROMPER EST UNE CARTE QU'ON NE PEUT PAS
    CROIRE.

    Cette vérification a attrapé une faute dès son premier appel : la phase
    « cible » nommait « architecture-cible », qui est une URL de page et non
    un identifiant de livrable. L'écran aurait affiché un bouton menant nulle
    part."""
    assert PM.verifier_le_catalogue() == [], PM.verifier_le_catalogue()


def test_la_verification_du_catalogue_SAIT_ATTRAPER_une_promesse_morte(
        monkeypatch):
    """LA RÈGLE PRÉCÉDENTE NE PEUT PAS MESURER CELA, et une mutation l'a
    montré : l'état correct est une liste VIDE, si bien qu'une vérification
    désarmée — `if False: …` — rend exactement le même résultat qu'une
    vérification qui travaille.

    ON INJECTE DONC UNE PROMESSE MORTE et l'on exige qu'elle ressorte. Sans
    cette règle, la garde pourrait être neutralisée sans que rien ne bouge au
    vert."""
    faux = list(PM.PHASES) + [{
        "cle": "phase-d-essai", "titre": "Essai", "question": "Essai ?",
        "livrables": ["livrable-qui-n-existe-pas"], "prealables": [],
        "ce_qui_se_decide": "", "piege": ""}]
    monkeypatch.setattr(PM, "PHASES", faux)
    assert ("phase-d-essai", "livrable-qui-n-existe-pas") in \
        PM.verifier_le_catalogue()


def test_le_parcours_couvre_les_livrables_de_CONSEIL_OT():
    """UN LIVRABLE DE CONSEIL HORS PARCOURS EST UN LIVRABLE QU'ON N'OUVRE
    JAMAIS : la page le liste, mais rien ne dit à quel moment il se produit.

    LES NEUF LIVRABLES DE GOUVERNANCE IA SONT NOMMÉS À PART, et c'est une
    décision, pas un oubli : ils relèvent d'une autre mission — un cadre
    d'usage de l'IA n'est pas une étape d'une mission OT."""
    sequences = set()
    for p in PM.PHASES:
        sequences |= set(p["livrables"])
    # L'EXCLUSION SE NOMME PAR SON GROUPE, PAS PAR LA FORME DES IDENTIFIANTS.
    # La première version écartait ce qui finit par « -ia » : elle a laissé
    # passer « regles-ia-generative », qui ne finit pas ainsi. Deviner la
    # nature d'un livrable à son nom de fichier est le genre de règle qui
    # tombe pour une raison sans rapport avec ce qu'elle mesure.
    HORS_MISSION_OT = "Conseil — Gouvernance IA"
    hors = sorted(t["id"] for t in livrables.TYPES
                  if t["id"] not in sequences
                  and str(t.get("groupe") or "").startswith("Conseil")
                  and t.get("groupe") != HORS_MISSION_OT)
    assert not hors, (
        "ces livrables de conseil ne sont dans aucune phase : %s" % hors)


def test_les_prealables_se_LISENT_et_ne_bloquent_PAS():
    """UNE MISSION RÉELLE COMMENCE RAREMENT AU DÉBUT. Un parcours qui
    refuserait d'avancer serait abandonné au premier dossier repris en cours
    de programme. Il DIT ce qui manque ; il ne l'interdit pas."""
    e = PM.etat(faites=[])
    cible = next(l for l in e["phases"] if l["cle"] == "cible")
    assert not cible["prete"]
    assert {m["cle"] for m in cible["manque"]} == {"etat_des_lieux",
                                                   "evaluation"}
    # ET CE QUI MANQUE EST NOMMÉ, pas compté : « 2 prérequis manquants » ne
    # dit pas lesquels, donc ne permet pas de décider.
    assert all(m["titre"] for m in cible["manque"])
    # LES LIVRABLES RESTENT ACCESSIBLES : on peut travailler une phase qui
    # n'est pas prête, en sachant sur quoi l'on s'avance.
    assert cible["livrables"]


def test_chaque_phase_NOMME_son_piege():
    """UN ÉCRAN QUI DIT « PRÉREQUIS MANQUANT » NE DIT RIEN. C'est la
    CONSÉQUENCE qui fait décider, et chacune de ces phrases vient d'une faute
    qu'on peut commettre sans s'en apercevoir."""
    for p in PM.PHASES:
        assert len(p["piege"]) > 60, p["cle"]
        assert len(p["ce_qui_se_decide"]) > 40, p["cle"]
        assert p["question"].endswith("?"), p["cle"]


def test_la_phase_courante_est_la_premiere_NON_FAITE():
    """ELLE REVIENT SUR CE QUI EST COMMENCÉ ET NON FINI, et ne saute pas."""
    e = PM.etat(faites=["cadrage", "evaluation"])
    assert e["courante"] == "etat_des_lieux", e["courante"]
    e2 = PM.etat(faites=[c["cle"] for c in PM.PHASES])
    assert e2["courante"] is None and e2["achevee"]


def test_la_phase_courante_est_TOUJOURS_prete():
    """L'INVARIANT DU GRAPHE, ET UNE CLAIRE CORRECTION DE MA PART.

    J'AVAIS ÉCRIT QUE LA COURANTE EST « LA PREMIÈRE NON FAITE ET NON LA
    PREMIÈRE PRÊTE ». La distinction n'est pas observable : les préalables
    d'une phase sont tous des phases ANTÉRIEURES, donc si l'une d'elles
    n'était pas faite, c'est ELLE qui serait la première non faite. La
    première non faite a donc toujours tous ses préalables faits. Une mutation
    qui remplaçait un critère par l'autre a survécu, et elle avait raison :
    les deux définitions coïncident sur les 256 états possibles.

    CE QUI EST VRAI ET MÉRITE D'ÊTRE TENU, c'est l'invariant lui-même. Il
    tomberait le jour où l'on ajouterait un préalable pointant vers une phase
    POSTÉRIEURE — un interblocage que rien d'autre ne signalerait à l'écran.
    """
    import itertools
    cles = [p["cle"] for p in PM.PHASES]
    vus = 0
    for n in range(len(cles) + 1):
        for combo in itertools.combinations(cles, n):
            e = PM.etat(faites=list(combo))
            if e["courante"] is None:
                continue
            vus += 1
            ligne = next(l for l in e["phases"] if l["cle"] == e["courante"])
            assert ligne["prete"], (
                "la phase courante « %s » n'est pas prête avec %s : un "
                "préalable pointe vers une phase postérieure"
                % (e["courante"], list(combo)))
    assert vus > 200, vus


def test_l_etat_est_PUR_et_ne_lit_rien():
    """FONCTION PURE : une règle l'éprouve sans base ni session, et deux
    appels identiques rendent la même chose."""
    a = PM.etat(faites=["cadrage"])
    b = PM.etat(faites=["cadrage"])
    assert a == b
    # UNE CLÉ INCONNUE EST IGNORÉE, pas acceptée : sinon un état bricolé
    # déclarerait faite une phase qui n'existe pas.
    assert PM.etat(faites=["zzz"])["faites"] == []


def test_les_phases_sont_ORDONNEES_et_leurs_prealables_les_precedent():
    """UN PRÉALABLE QUI VIENT APRÈS EST UN INTERBLOCAGE : la phase ne serait
    jamais prête, et rien à l'écran ne dirait pourquoi."""
    rang = {p["cle"]: i for i, p in enumerate(PM.PHASES)}
    for p in PM.PHASES:
        for pre in p["prealables"]:
            assert pre in rang, (p["cle"], pre)
            assert rang[pre] < rang[p["cle"]], (
                "« %s » exige « %s », qui vient après" % (p["cle"], pre))


def test_livrables_de_phase_LIT_le_catalogue():
    """ON LIT LES INTITULÉS, ON NE LES RECOPIE PAS. Deux tables des mêmes
    libellés divergent au premier renommage, et c'est la page qui afficherait
    un titre que plus aucune console ne porte."""
    ls = PM.livrables_de_phase("cible")
    assert ls
    for l in ls:
        assert l["label"] == livrables.get_type(l["id"])["label"]
    assert PM.livrables_de_phase("phase-qui-n-existe-pas") == []


def test_un_livrable_sait_DANS_QUELLE_PHASE_il_se_produit():
    assert PM.phase_du_livrable("mat-radar") == "evaluation"
    assert PM.phase_du_livrable("om-operating-model") == "cible"
    # LE BUSINESS CASE EST ARBITRÉ EN DÉCISION MAIS S'ÉCRIT À LA TRAJECTOIRE :
    # on rend la PREMIÈRE phase, qui est celle où il faut l'ouvrir.
    assert PM.phase_du_livrable("fdr-business-case") == "trajectoire"
    assert PM.phase_du_livrable("inconnu") is None
