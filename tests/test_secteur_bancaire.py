"""LE SECTEUR BANCAIRE — CE QU'IL APPORTE QUE L'ASSURANCE N'APPORTE PAS.

CE QUI S'EST PASSÉ, ET QUE RIEN NE SIGNALAIT. Le site ne connaissait qu'un seul
seau financier — « Assurance & services financiers » côté parcours, « Assurance
& banque » côté diagnostic. Son propre moteur d'usine IA, lui, distingue depuis
toujours `banque` et `assurance` : les deux n'ont ni les mêmes cas d'usage, ni
le même point de l'annexe III du règlement sur l'IA, ni le même calendrier. Le
seau unique ne plantait nulle part. Il rendait simplement, à un directeur de
banque, un cadre réglementaire où manquait le texte qui le vise.

CE QUE CES RÈGLES REFUSENT DE MESURER : la simple PRÉSENCE du secteur. Un
parcours bancaire qui serait une copie du parcours assurance passerait un
contrôle de présence et n'apporterait rien — et il coûterait une entrée de plus
dans une liste déjà longue, ce qui fait hésiter là où il faut orienter.

CE QU'ELLES MESURENT DONC :
  1. le secteur bancaire dit quelque chose que l'assurance ne dit PAS, et
     réciproquement — les deux ne se recouvrent pas ;
  2. il nomme le point de l'annexe III qui le vise, et l'exception qui va
     avec — une exclusion citée sans sa condition est un contresens utile ;
  3. le diagnostic le propose, le restitue, et lui rend un cadre où figure le
     texte de plus ;
  4. le seau unique a bien disparu : plus aucune surface ne revendique la
     banque sous l'étiquette de l'assurance ;
  5. le profil de poids est PROPRE au secteur, pas recopié du voisin ;
  6. les deux surfaces qui listent les secteurs les listent dans le MÊME ordre.
"""
import io
import json
import os
import re
import subprocess
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ia_factory  # noqa: E402


def _lire(nom):
    with io.open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


def _module():
    """SECTEURS et POIDS, tels que le navigateur les verra."""
    chemin = os.path.join(ICI, "tests", "_banque_lire.js")
    with io.open(chemin, "w", encoding="utf-8") as f:
        f.write("const m=require('%s/parcours.js');"
                "process.stdout.write(JSON.stringify("
                "{s:m.SECTEURS,p:m.PARCOURS,w:m.POIDS||null}));" % ICI)
    try:
        out = subprocess.run(["node", chemin], capture_output=True,
                             text=True, timeout=60)
        assert out.returncode == 0, out.stderr
        return json.loads(out.stdout)
    finally:
        os.remove(chemin)


MOD = _module()
SECTEURS = {s["id"]: s for s in MOD["s"]}


def _blocs(secteur):
    """Chaque texte du secteur, pris SÉPARÉMENT.

    POURQUOI SÉPARÉMENT, ET NON CONCATÉNÉS. Concaténer permet à une règle de
    trouver une affirmation dans une note et sa condition dans un conseil
    d'étape trois écrans plus bas — et de conclure qu'elles sont dites
    ensemble. Elles ne le sont pas : personne ne lit un site dans l'ordre où
    un `json.dumps` le sérialise.
    """
    out = [secteur.get("enjeu", ""), secteur.get("textes", ""),
           secteur.get("piege", "")]
    out += list((secteur.get("notes") or {}).values())
    for e in secteur.get("etapes", []):
        out += [e.get("action", ""), e.get("gain", ""), e.get("tip", "")]
    return [t for t in out if t]


def _mots(texte):
    """Les mots significatifs d'un secteur, pour comparer deux discours."""
    brut = " ".join(str(x) for x in (
        [texte.get("enjeu", ""), texte.get("textes", ""), texte.get("piege", "")]
        + list((texte.get("notes") or {}).values())
        + [e.get("tip", "") + " " + e.get("action", "") + " " + e.get("gain", "")
           for e in texte.get("etapes", [])]))
    brut = brut.lower().replace("’", "'")
    petits = {"dans", "pour", "avec", "sans", "cette", "leur", "elle", "sont",
              "être", "plus", "mais", "tout", "tous", "deux", "chaque", "votre",
              "vous", "nous", "qui", "que", "les", "des", "une", "aux", "par",
              "sur", "est", "pas", "ces", "son", "ses", "lui", "ont", "fait",
              "peut", "doit", "donc", "ainsi", "celui", "ceux", "avant", "après"}
    return {m for m in re.findall(r"[a-zàâçéèêëîïôûùüÿñæœ']{4,}", brut)
            if m not in petits}


# ══════════════════════════════════════════════════════════════════════════
#  1. LA BANQUE N'EST PAS UNE COPIE DE L'ASSURANCE
# ══════════════════════════════════════════════════════════════════════════

def test_le_secteur_bancaire_EXISTE_et_porte_un_parcours():
    assert "banque" in SECTEURS, (
        "aucun secteur bancaire : le site ne connaît que %s"
        % sorted(SECTEURS))
    assert len(SECTEURS["banque"]["etapes"]) >= 5


def test_la_banque_et_l_assurance_ne_DISENT_PAS_la_meme_chose():
    """UN SECTEUR RECOPIÉ NE SERT QU'À ALLONGER LA LISTE.

    La règle compare les deux discours — enjeu, textes, piège, notes et
    conseils d'étapes — et exige que CHACUN porte un vocabulaire que l'autre
    n'a pas. Sans la réciproque, un secteur bancaire qui contiendrait tout
    l'assurance plus trois mots passerait.
    """
    b, f = _mots(SECTEURS["banque"]), _mots(SECTEURS["finance"])
    propre_b, propre_f = b - f, f - b
    assert len(propre_b) >= 20, (
        "le secteur bancaire n'apporte que %d mots que l'assurance n'a pas : %s"
        % (len(propre_b), sorted(propre_b)))
    assert len(propre_f) >= 20, (
        "l'assurance a été vidée de ce qui lui était propre : %d mots restants"
        % len(propre_f))


def test_les_deux_secteurs_financiers_ne_visent_pas_les_MEMES_pages():
    """SINON LE CHOIX ENTRE LES DEUX NE CHANGE RIEN À CE QU'ON LIT.

    Deux parcours qui mènent aux mêmes pages dans le même ordre sont un seul
    parcours affiché deux fois — et le lecteur qui a hésité entre les deux
    découvre qu'il n'avait pas à hésiter.
    """
    b = [e["url"] for e in SECTEURS["banque"]["etapes"]]
    f = [e["url"] for e in SECTEURS["finance"]["etapes"]]
    assert b != f, "les deux parcours financiers visent la même suite de pages"
    assert set(b) - set(f), (
        "le parcours bancaire ne mène nulle part où l'assurance ne mène déjà")


def test_le_profil_de_poids_bancaire_est_PROPRE():
    """UN PROFIL RECOPIÉ REND LE MÊME CROISEMENT RÔLE × SECTEUR.

    Et il le rend sans le dire : l'écran affiche un secteur distinct qui
    pondère exactement comme son voisin.
    """
    poids = MOD["w"]
    if poids is None:
        pytest.skip("POIDS n'est pas exporté par le module")
    assert "banque" in poids, "le secteur bancaire n'est pas pondéré"
    assert poids["banque"] != poids["finance"], (
        "le profil bancaire est identique à celui de l'assurance")
    for axe, v in poids["banque"].items():
        assert isinstance(v, int) and 0 <= v <= 3, (axe, v)


# ══════════════════════════════════════════════════════════════════════════
#  2. LE TEXTE QUI VISE LA BANQUE, ET L'EXCEPTION QUI VA AVEC
# ══════════════════════════════════════════════════════════════════════════

def test_le_secteur_bancaire_NOMME_le_point_de_l_annexe_III():
    """« ANNEXE III » SANS SON POINT N'EST PAS UNE RÉFÉRENCE.

    L'annexe compte huit domaines ; dire qu'un cas d'usage « relève de
    l'annexe III » sans dire lequel oblige le lecteur à rouvrir le texte —
    c'est-à-dire, en pratique, à ne pas le vérifier.
    """
    textes = SECTEURS["banque"]["textes"]
    assert "annexe III" in textes, (
        "le champ qui répond à « quels textes s'appliquent » ne cite pas "
        "l'annexe III : %s" % textes)
    assert re.search(r"annexe III,\s*point\s*5\s*b", textes), (
        "l'annexe III est citée sans le point qui vise la notation de crédit. "
        "Elle compte huit domaines : sans le point, le lecteur doit rouvrir le "
        "texte, c'est-à-dire qu'il ne vérifiera pas. Champ : %s" % textes)


def test_l_exclusion_de_la_fraude_est_citee_AVEC_sa_condition():
    """UNE EXCLUSION CITÉE NUE EST UN CONTRESENS UTILE.

    « La détection de fraude est exclue » se retient, s'oppose en réunion, et
    dispense de qualifier. L'exclusion tient à la FINALITÉ du système, pas à
    sa famille : un même moteur servant au scoring et à la fraude ne se
    qualifie pas en bloc. Citer l'exclusion sans cette condition arme celui
    qui ne veut pas qualifier.
    """
    # LA CONDITION DOIT TENIR DANS LE MÊME BLOC DE TEXTE QUE L'EXCLUSION.
    # Une réserve posée trois paragraphes plus loin ne se lit pas avec ce
    # qu'elle réserve : on retient « la fraude est exclue » et on s'arrête là.
    blocs = _blocs(SECTEURS["banque"])
    # LA RÈGLE VISE L'AFFIRMATION, PAS LE SUJET. Un bloc qui demande de
    # qualifier la fraude parmi les autres cas d'usage la mentionne sans rien
    # en exclure : l'exiger d'accompagner une condition n'aurait pas de sens.
    portant = [t for t in blocs
               if "fraude" in t.lower() and "exclu" in t.lower()]
    assert portant, "l'exclusion de la fraude n'est affirmée nulle part"
    # CHAQUE BLOC, ET NON « AU MOINS UN ». Une seule mention nue suffit à
    # armer celui qui ne veut pas qualifier : c'est celle-là qu'il citera, et
    # il n'aura pas tort de dire qu'elle est écrite sur le site.
    nus = [t for t in portant if "finalit" not in t.lower()]
    assert not nus, (
        "%d bloc(s) sur %d énoncent l'exclusion de la fraude sans la "
        "condition de finalité qui la borne. Lus seuls, ils dispensent de "
        "qualifier : %s" % (len(nus), len(portant), [t[:110] for t in nus]))


def test_le_secteur_bancaire_ARTICULE_les_trois_textes():
    """DORA, LE RÈGLEMENT SUR L'IA, ET NIS 2 QUI S'EFFACE EN PARTIE.

    Aucun des trois ne se déduit des deux autres, et l'article 4 de NIS 2
    n'efface que les matières et les entités couvertes. Un secteur qui
    nommerait DORA seul laisserait croire le cadre complet.
    """
    tout = json.dumps(SECTEURS["banque"], ensure_ascii=False)
    for texte in ("DORA", "2024/1689", "NIS 2"):
        assert texte in tout, "le secteur bancaire ne nomme pas %s" % texte
    # ET L'ARTICLE DOIT ACCOMPAGNER L'AFFIRMATION QU'IL FONDE. « DORA prime
    # sur NIS 2 » est une affirmation ; « au titre de l'article 4 » est ce qui
    # permet de la vérifier. Séparées, la première circule seule.
    blocs = _blocs(SECTEURS["banque"])
    ecarte = [t for t in blocs
              if re.search(r"(écarte|efface|prime)", t, re.I) and "NIS 2" in t]
    assert ecarte, "le secteur ne dit nulle part que DORA écarte NIS 2"
    # L'ARTICLE EST NOMMÉ QUELQUE PART — une affirmation invérifiable ne se
    # défend pas en réunion.
    fondes = [t for t in ecarte if re.search(r"article 4|art\. 4", t)]
    assert fondes, (
        "l'effacement de NIS 2 est affirmé %d fois sans jamais nommer, dans le "
        "même bloc, l'article qui le fonde : %s"
        % (len(ecarte), [t[:90] for t in ecarte]))
    # ET CHAQUE AFFIRMATION PORTE SA BORNE. « DORA prime sur NIS 2 » énoncé
    # nu fait croire qu'un groupe bancaire sort entièrement de NIS 2. Il n'en
    # sort que pour les matières couvertes, et que pour les entités couvertes
    # — les filiales non financières y restent.
    borne = r"article 4|art\. 4|là où|que pour|matières couvertes|ne couvre pas|selon l'entité|correspondantes"
    sans = [t for t in ecarte if not re.search(borne, t, re.I)]
    assert not sans, (
        "%d bloc(s) affirment que DORA écarte NIS 2 sans dire jusqu'où : lus "
        "seuls, ils font sortir tout un groupe du régime. %s"
        % (len(sans), [t[:110] for t in sans]))


def test_le_parcours_bancaire_s_accorde_avec_le_moteur_d_usine_IA():
    """DEUX TABLES QUI PARLENT DU MÊME SECTEUR DOIVENT S'ACCORDER.

    `ia_factory` tient depuis longtemps un secteur `banque` avec ses cas
    d'usage qualifiés. Si le parcours inventait un autre cadre, le visiteur
    lirait deux réponses différentes à la même question selon la page où il
    est entré.
    """
    assert "banque" in ia_factory.SECTEURS, (
        "le moteur d'usine IA ne connaît plus de secteur bancaire")
    moteur = json.dumps(ia_factory.SECTEURS["banque"], ensure_ascii=False)
    assert re.search(r"[Aa]nnexe III,\s*point\s*5\s*b", moteur), (
        "le moteur ne qualifie plus la notation de crédit au point 5 b : "
        "le parcours s'appuie sur lui")


# ══════════════════════════════════════════════════════════════════════════
#  3. LE DIAGNOSTIC
# ══════════════════════════════════════════════════════════════════════════

def test_le_diagnostic_PROPOSE_la_banque():
    page = _lire("diagnostic.html")
    assert 'name="secteur" value="banque"' in page, (
        "le questionnaire ne propose pas la banque : un directeur de banque "
        "doit cocher « assurance » pour obtenir un cadre")


def test_le_diagnostic_rend_a_la_banque_le_TEXTE_DE_PLUS():
    """SANS CETTE RÈGLE, L'OPTION EXISTERAIT SANS RIEN CHANGER.

    Une option de plus qui retomberait dans la branche de l'assurance rendrait
    « DORA + NIS2 » — c'est-à-dire un cadre où manque précisément le texte
    pour lequel on a créé l'option.
    """
    page = _lire("diagnostic.html")
    m = re.search(r"if\(sect==='banque'\)(.{0,1400}?)if\(sect===", page, re.S)
    assert m, "aucune branche de cadre propre à la banque"
    branche = m.group(1)
    # LES PASTILLES SONT CE QUE LE LECTEUR VOIT AVANT DE LIRE LA PROSE.
    # Un cadre dont les pastilles annoncent « DORA, NIS2 » et dont seul le
    # paragraphe mentionne le règlement sur l'IA se retient comme deux textes.
    pastilles = re.search(r"b:\s*\[(.*?)\]", branche, re.S)
    assert pastilles, "la branche bancaire ne porte pas de pastilles de cadre"
    assert re.search(r"r[èe]glement sur l'IA|annexe III", pastilles.group(1), re.I), (
        "les pastilles du cadre bancaire ne nomment pas le règlement sur "
        "l'IA : %s" % pastilles.group(1))
    assert re.search(r"point\s*5\s*b", branche), (
        "le cadre bancaire cite l'annexe III sans son point")
    assert "DORA" in branche and "NIS2" in branche


def test_la_banque_est_un_secteur_de_l_annexe_I_de_NIS_2():
    """LA QUALIFICATION, PAS UNE PRÉFÉRENCE COMMERCIALE.

    Le tableau des secteurs hautement critiques commande la suite du
    questionnaire ; un secteur bancaire absent de ce tableau serait traité
    comme un secteur ordinaire par tout ce qui vient après.
    """
    page = _lire("diagnostic.html")
    m = re.search(r"var ANNEXE1=\{([^}]*)\}", page)
    assert m, "le tableau de l'annexe I a disparu"
    assert "banque:1" in m.group(1).replace(" ", ""), (
        "la banque ne figure pas parmi les secteurs hautement critiques : %s"
        % m.group(1))


# ══════════════════════════════════════════════════════════════════════════
#  4. LE SEAU UNIQUE A DISPARU DE TOUTES LES SURFACES
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("fichier", ["diagnostic.html", "parcours.js",
                                     "secteurs.html"])
def test_aucune_surface_ne_range_plus_la_banque_SOUS_l_assurance(fichier):
    """L'ÉTIQUETTE QUI REVENDIQUAIT LES DEUX.

    Tant qu'une surface annonce « Assurance & banque », le visiteur bancaire
    qui la lit conclut que son secteur est traité — et il l'est, mais par le
    cadre de l'autre.
    """
    page = _lire(fichier).replace("’", "'")
    for etiquette in ("Assurance & banque", "Assurance &amp; banque"):
        assert etiquette not in page, (
            "%s range encore la banque sous l'assurance : « %s »"
            % (fichier, etiquette))


def test_la_page_secteurs_PORTE_une_carte_bancaire():
    page = _lire("secteurs.html")
    assert "Banque de détail et de financement" in page, (
        "la page des secteurs ne montre pas la banque")


def test_les_deux_surfaces_listent_les_secteurs_dans_le_MEME_ordre():
    """DEUX ORDRES DIFFÉRENTS FONT DOUTER DE LA PREMIÈRE LISTE LUE.

    La règle ne compare que les secteurs présents des deux côtés : la page
    d'accueil des secteurs en montre qui n'ont pas de parcours, et c'est
    voulu.
    """
    page = _lire("secteurs.html")
    titres = [t.replace("&amp;", "&").strip()
              for t in re.findall(r"<h3>([^<]+)</h3>", page)]
    noms = {s["nom"].replace("’", "'"): s["id"] for s in MOD["s"]}
    vus = [noms[t] for t in titres if t in noms]
    attendu = [s["id"] for s in MOD["s"] if s["id"] in vus]
    assert vus == attendu, (
        "la page des secteurs les ordonne autrement que les parcours : "
        "%s contre %s" % (vus, attendu))
    assert "banque" in vus and "finance" in vus, vus


def test_les_accents_de_cartes_ne_se_REPETENT_pas_entre_voisines():
    """LA GRILLE FAIT TOURNER QUATRE ACCENTS.

    Insérer une carte sans renuméroter en laisse deux côte à côte : la
    rotation se lit comme un regroupement, et le lecteur cherche ce que les
    deux cartes ont en commun.
    """
    page = _lire("secteurs.html")
    acc = re.findall(r'class="card (a\d)"', page)
    jumelles = [(i, acc[i]) for i in range(1, len(acc)) if acc[i] == acc[i - 1]]
    assert not jumelles, "cartes voisines de même accent : %s" % jumelles


# ══════════════════════════════════════════════════════════════════════════
#  5. LA VEILLE — UNE FACETTE QUI NE SÉPARE RIEN NE SERT À RIEN
# ══════════════════════════════════════════════════════════════════════════

import veille_facettes  # noqa: E402

BANQUE_VF = "Banque de détail et de financement"
ASSUR_VF = "Assurance & services financiers"


def _secteurs_de(titre):
    return veille_facettes.classer({"title": titre, "resume": ""},
                                   source=None)["secteurs"]


def test_la_facette_bancaire_EXISTE_dans_la_veille():
    noms = [n for n, _ in veille_facettes.SECTEURS]
    assert BANQUE_VF in noms, (
        "le filtre de veille ne propose pas la banque : un lecteur bancaire "
        "doit filtrer sur « assurance » pour trouver l'avis de son "
        "superviseur. Facettes : %s" % noms)


@pytest.mark.parametrize("titre,attendu,exclu", [
    pytest.param("L'EBA publie ses orientations sur le scoring de crédit",
                 BANQUE_VF, ASSUR_VF, id="EBA-scoring-credit"),
    pytest.param("La BCE renforce la supervision prudentielle des établissements",
                 BANQUE_VF, ASSUR_VF, id="BCE-supervision"),
    pytest.param("EIOPA consulte sur l'usage de l'IA en assurance vie",
                 ASSUR_VF, BANQUE_VF, id="EIOPA-assurance-vie"),
])
def test_la_veille_SEPARE_la_banque_de_l_assurance(titre, attendu, exclu):
    """UNE FACETTE EN PLUS QUI ATTRAPERAIT LA MÊME CHOSE N'EST PAS UNE FACETTE.

    Elle double la liste de filtres sans rien trier, et le lecteur qui choisit
    entre les deux obtient le même flux — ce qui lui apprend, à tort, que le
    filtre ne marche pas.
    """
    vus = _secteurs_de(titre)
    assert attendu in vus, (
        "« %s » ne tombe pas dans « %s » : %s" % (titre, attendu, vus))
    assert exclu not in vus, (
        "« %s » tombe AUSSI dans « %s » : la facette ne sépare rien"
        % (titre, exclu))


def test_DORA_reste_dans_les_DEUX_facettes():
    """CE QUI SE CHEVAUCHE VRAIMENT DOIT CHEVAUCHER.

    DORA s'applique aux banques comme aux assureurs. Une facette bancaire qui
    l'accaparerait ferait disparaître du filtre assurance le texte qui la
    structure — et le tri paraîtrait net tout en perdant des éléments.
    """
    vus = _secteurs_de("DORA : publication des normes techniques sur le "
                       "registre des prestataires TIC")
    assert BANQUE_VF in vus and ASSUR_VF in vus, (
        "DORA ne relève que de %s : le chevauchement réel a été supprimé "
        "pour faire joli" % vus)
