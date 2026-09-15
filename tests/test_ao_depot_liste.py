# -*- coding: utf-8 -*-
"""La liste déroulante des pièces choisies, au point de dépôt — et son retrait.

CE QUE CECI AJOUTE, ET LE DÉFAUT QU'IL CORRIGE. Le dépôt ne montrait qu'un
`<input type=file>` brut et un aperçu d'une ligne : on ne pouvait ni voir la
liste des pièces cumulées, ni en ôter UNE avant l'analyse. Le FileList natif
l'interdit — il n'est ni modifiable ni cumulable, et re-choisir REMPLACE tout.
On tient donc une file `AO_EN_ATTENTE`, rendue en liste déroulante, à laquelle
chaque dépôt s'ajoute et dont on retire pièce par pièce.

CES RÈGLES MESURENT L'EFFET, PAS LA PRÉSENCE D'UN WIDGET. Le point qui fait
qu'un retrait n'est pas cosmétique : `aoAnalyser` lit LA MÊME file. Si l'analyse
relisait le FileList brut, ôter une pièce de la liste ne l'ôterait pas de ce qui
part à l'analyse — une case vidée à l'écran, pleine sur le fil. La règle la plus
lourde vérifie donc exactement cela.
"""
import html
import json
import subprocess
import io
import os
import re

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8").read()


from test_ao_formulaires import _js_source                 # noqa: E402

def _fn(nom):
    """Le corps d'une fonction JS, de `function nom(` au `function ` suivant.

    Les fonctions du module sont indentées de deux espaces dans l'IIFE ; on
    borne au prochain `\\n  function ` pour ne pas déborder sur la suivante, et
    mesurer chaque règle dans SON périmètre — pas ailleurs dans le fichier."""
    i = JS.index("function " + nom + "(")
    j = JS.find("\n  function ", i + 1)
    return JS[i:(j if j > 0 else len(JS))]


def _fn_avec_aidantes(nom):
    """Le corps d'une fonction ET celui des fonctions du module qu'elle
    appelle, sur un seul niveau.

    POURQUOI CETTE PORTÉE-LÀ. Les deux règles ci-dessous cherchaient
    `AO_EN_ATTENTE.push(` dans `aoDocuments`. Le jour où le dépôt a gagné une
    SECONDE ZONE — pièces de la consultation d'un côté, documents du cabinet
    de l'autre — le branchement commun est passé dans `aoBrancherDepot`, et
    les règles sont tombées alors que la propriété qu'elles mesurent était
    intacte : la file est toujours partagée, elle est toujours alimentée par
    ajout.

    LA MAUVAISE CORRECTION AURAIT ÉTÉ DE DÉFAIRE LE PARTAGE pour contenter la
    règle — deux écouteurs recopiés, qui auraient divergé au premier
    correctif. La bonne est de suivre la valeur dans l'aidante NOMMÉE, ce qui
    élargit la portée sans ouvrir d'échappatoire : déplacer le code dans une
    fonction que `aoDocuments` n'appelle pas ne suffit toujours pas, puisque
    seules les appelées sont suivies. Une mutation le vérifie.
    """
    corps = _fn(nom)
    vu = [corps]
    for appelee in sorted(set(re.findall(r"\b(ao[A-Z]\w*)\s*\(", corps))):
        if appelee == nom:
            continue
        try:
            vu.append(_fn(appelee))
        except ValueError:
            continue                    # fonction d'un autre fichier
    return "\n".join(vu)


def _rendu_file(fichiers):
    """Le balisage que `aoEnAttenteRendre` produit RÉELLEMENT sur une file.

    `fichiers` : une liste de (nom, côté). Les tailles sont fixées ici — ce
    qu'on mesure est la structure, pas un poids.
    """
    file_js = json.dumps([{"nom": n, "cote": c, "file": {"size": 100000}}
                          for n, c in fichiers])
    # LE BANC APPREND LE GESTE DE CONSERVATION. `aoEnAttenteRendre` pose
    # désormais la case « conserver pour les prochains dossiers » et la
    # branche ; un banc qui les ignore tombe — il EXÉCUTE le rendu, il ne
    # le relit pas.
    prog = (_js_source("esc", "aoOctets", "aoEnAttenteRendre",
                       "aoEtagereGeste", "aoEtagereBrancher",
                       "aoEtagereEtat")
            + "\nfunction fr(n){ return String(Math.round(Number(n)||0)); }"
            + "\nvar AO_TRANSPORT_MAX = 4000000;"
            + "\nvar AO_EN_ATTENTE = " + file_js + ";"
            + "\nvar AO_COTES = " + _cotes_js() + ";"
            + "\nvar zone = { innerHTML: '' };"
            + "\nfunction $(s){ return s === '#ig-ao-liste' ? zone :"
              " { addEventListener: function(){}, value: '0' }; }"
            + "\naoEnAttenteRendre();"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    return html.unescape(out.stdout)


def _cotes_js():
    """LA TABLE DES CÔTÉS, LUE DANS LE SCRIPT et non recopiée ici. La recopier
    ferait passer la règle le jour où le script en déclarerait un troisième
    que la page n'afficherait pas."""
    m = re.search(r"var AO_COTES = (\[.*?\]);", JS, re.S)
    assert m, "la table des côtés a disparu du script"
    return m.group(1)


def test_le_depot_offre_une_liste_deroulante_avec_retrait():
    """Le rendu des pièces choisies est une VRAIE liste déroulante (`<select>`),
    et il porte le bouton de retrait. Un `<ul>` mis à la place ferait tomber la
    première assertion ; un rendu sans bouton, la seconde.

    CETTE RÈGLE EXÉCUTE LE RENDU DEPUIS QUE LES LISTES SONT DEUX. Elle
    cherchait `<select id="ig-ao-sel"` dans le SOURCE ; le jour où les
    identifiants sont devenus une donnée de la table des côtés — une liste
    par zone de dépôt —, la chaîne a disparu du fichier alors que la liste
    déroulante, elle, s'affiche toujours. Lire le balisage produit mesure la
    propriété que la règle nomme ; lire le source mesurait une façon de
    l'écrire.
    """
    h = _rendu_file([("01_RC.pdf", "consultation")])
    assert "<select " in h and "</select>" in h, (
        "le dépôt ne rend pas une liste déroulante des pièces choisies : %s"
        % h[:200])
    assert "<option " in h, "la liste déroulante est vide"
    assert re.search(r"<button[^>]*>Retirer", h), (
        "la liste n'offre pas de bouton pour retirer une pièce")
    assert "AO_EN_ATTENTE.splice(" in _fn("aoEnAttenteRendre"), (
        "le retrait n'ôte pas la pièce de la file : il ne serait que cosmétique")


def test_l_analyse_lit_la_file_d_attente_et_PAS_le_FileList_brut():
    """LA RÈGLE QUI REND LE RETRAIT RÉEL. `aoAnalyser` construit ses lectures
    depuis `AO_EN_ATTENTE`, jamais depuis `f.files`. Relire le FileList brut
    laisserait partir à l'analyse une pièce qu'on vient d'ôter de la liste —
    le retrait deviendrait un mensonge d'écran."""
    tete = _fn("aoAnalyser")
    tete = tete[:tete.index("demander(")]
    assert "AO_EN_ATTENTE[i].file" in tete, (
        "l'analyse ne lit pas la file d'attente : le retrait n'aurait aucun effet")
    assert "f.files" not in tete, (
        "l'analyse relit le FileList brut : une pièce ôtée de la liste "
        "repartirait quand même à l'analyse")


def test_deposer_AJOUTE_a_la_file_sans_la_remplacer():
    """Chaque dépôt s'ajoute au précédent (un même nom remplace le sien), il ne
    remet pas la file à zéro. Une mutation qui réaffecterait `AO_EN_ATTENTE = […]`
    au lieu d'y pousser casserait le cumul — et tomberait ici."""
    corps = _fn_avec_aidantes("aoDocuments")
    assert "AO_EN_ATTENTE.push(" in corps, "le dépôt n'ajoute pas à la file"
    assert "aoEnAttenteIndex(" in corps, (
        "le dépôt ne dédoublonne pas par nom : deux versions d'une même pièce "
        "coexisteraient")
    assert "AO_EN_ATTENTE = [" not in corps, (
        "le dépôt REMPLACE la file au lieu d'y ajouter : les dépôts successifs "
        "ne se cumuleraient plus")


def test_les_trois_gestes_partagent_la_MEME_file():
    """Dépôt, liste et analyse doivent parler de la même `AO_EN_ATTENTE` —
    c'est ce partage, et lui seul, qui fait qu'ajouter et retirer changent ce
    qui est analysé. Trois files séparées se désynchroniseraient en silence."""
    for nom in ("aoDocuments", "aoEnAttenteRendre", "aoAnalyser"):
        assert "AO_EN_ATTENTE" in _fn_avec_aidantes(nom), (
            "%s ne touche pas la file partagée AO_EN_ATTENTE" % nom)


def test_sans_piece_choisie_l_analyse_LE_DIT():
    """LE TÉMOIN NÉGATIF. File vide, l'analyse s'arrête et le dit, au lieu
    d'envoyer une requête sans pièce. Retirer cette garde tomberait ici."""
    tete = _fn("aoAnalyser")
    assert "if (!AO_EN_ATTENTE.length)" in tete, (
        "l'analyse ne vérifie plus qu'une pièce a été choisie")
    assert "Choisissez les pièces de la consultation." in tete


def test_la_file_ne_SURVIT_PAS_a_un_rechargement():
    """LA SÛRETÉ, COMME POUR AO_FOURNIES. La file vit en mémoire : jamais relue
    d'un stockage local, sinon les pièces d'une consultation reparaîtraient sur
    la suivante. Elle démarre vide."""
    assert re.search(r"var AO_EN_ATTENTE = \[\]", JS), "AO_EN_ATTENTE non déclarée vide"
    assert not re.search(r"AO_EN_ATTENTE\s*=\s*JSON\.parse", JS), (
        "AO_EN_ATTENTE est rechargée du stockage local : une pièce fuirait "
        "d'une consultation à l'autre")
    assert "ao-en-attente" not in JS, (
        "une clé de stockage local pour la file d'attente est apparue")


# ==========================================================================
# DEUX LISTES, UNE SOUS CHAQUE ZONE
# ==========================================================================
# POURQUOI SÉPARER. La file était une seule liste où chaque ligne portait
# « [consultation] » ou « [cabinet] » en tête. Ce préfixe faisait lire à l'œil,
# ligne par ligne, ce que la mise en page savait déjà : les deux zones de
# dépôt sont juste au-dessus. Et le retrait était ambigu — un seul bouton sur
# une liste mêlée retirait aussi bien un CCTP pendant qu'on regardait ses
# propres attestations.
#
# CE QUI NE SE SÉPARE PAS : LE POIDS. La limite de transport porte sur l'envoi
# ENTIER. Deux totaux par côté laisseraient lire « 1,8 Mo » puis « 1,9 Mo » et
# conclure qu'on passe — pour se faire refuser.

def test_chaque_cote_a_SA_liste_et_SON_bouton():
    """Deux zones au-dessus, deux listes en-dessous : c'est la structure qui
    dit le côté, plus un préfixe à lire sur chaque ligne."""
    h = _rendu_file([("01_RC.pdf", "consultation"), ("02_CCTP.pdf", "consultation"),
                     ("attestation-rc-pro.pdf", "cabinet")])
    # ON COMPTE LES LISTES DE CÔTÉ, PAS TOUS LES MENUS DE LA ZONE. La zone
    # porte désormais un troisième menu — le régime de publication de
    # l'étagère — qui ne désigne aucun côté. Compter les `<select>` faisait
    # tomber cette règle pour une raison sans rapport avec ce qu'elle mesure :
    # c'est `data-*` et l'identifiant de côté qui disent lesquels comptent.
    selects = [x for x in re.findall(r'<select id="([^"]+)"', h)
               if x.startswith("ig-ao-sel")]
    assert len(selects) == 2, selects
    boutons = re.findall(r'<button[^>]*id="([^"]+)"[^>]*>Retirer', h)
    assert len(boutons) == 2, boutons
    assert len(set(selects)) == 2 and len(set(boutons)) == 2, (
        "deux contrôles partagent un identifiant : le second ne serait jamais "
        "atteint")


def test_le_prefixe_de_cote_a_disparu_des_lignes():
    """C'est le bénéfice mesurable de la séparation : la ligne ne porte plus
    que le nom du fichier et son poids."""
    h = _rendu_file([("01_RC.pdf", "consultation"),
                     ("attestation-rc-pro.pdf", "cabinet")])
    for txt in re.findall(r"<option[^>]*>(.*?)</option>", h):
        assert "[consultation]" not in txt and "[cabinet]" not in txt, txt


def test_chaque_liste_ne_porte_QUE_les_fichiers_de_son_cote():
    """Le point dur. Une liste qui déborderait sur l'autre côté ferait retirer
    le mauvais fichier — et c'est précisément ce que la séparation devait
    empêcher."""
    h = _rendu_file([("01_RC.pdf", "consultation"), ("02_CCTP.pdf", "consultation"),
                     ("attestation-rc-pro.pdf", "cabinet"),
                     ("bilan-2024.pdf", "cabinet")])
    # ON NE RETIENT QUE LES LISTES DE CÔTÉ. La zone porte désormais un
    # troisième menu — le régime de publication de l'étagère — qui ne désigne
    # aucun côté et ne contient aucun fichier. Compter tous les <select>
    # faisait tomber cette règle pour une raison sans rapport avec ce qu'elle
    # mesure : la répartition des fichiers entre les deux listes.
    blocs = [(i, b) for i, b in
             re.findall(r'<select id="([^"]+)"[^>]*>(.*?)</select>', h, re.S)
             if i.startswith("ig-ao-sel")]
    assert len(blocs) == 2, [i for i, _ in blocs]
    par_id = {i: re.findall(r"<option[^>]*>(.*?) ·", b) for i, b in blocs}
    consult = [v for k, v in par_id.items() if "cab" not in k][0]
    cabinet = [v for k, v in par_id.items() if "cab" in k][0]
    assert consult == ["01_RC.pdf", "02_CCTP.pdf"], consult
    assert cabinet == ["attestation-rc-pro.pdf", "bilan-2024.pdf"], cabinet


def test_l_option_porte_l_indice_REEL_de_la_file():
    """LE PIÈGE DE LA SÉPARATION, ET LE SEUL QUI COÛTE DES DONNÉES.
    Renuméroter les options par liste ferait retirer le fichier d'indice 0 de
    la file — un CCTP — en croyant retirer le premier document du cabinet.
    Les valeurs sont donc les indices de `AO_EN_ATTENTE`, pas des rangs
    locaux."""
    h = _rendu_file([("01_RC.pdf", "consultation"),
                     ("attestation-rc-pro.pdf", "cabinet"),
                     ("02_CCTP.pdf", "consultation"),
                     ("bilan-2024.pdf", "cabinet")])
    vus = {}
    for bloc_id, bloc in re.findall(r'<select id="([^"]+)"[^>]*>(.*?)</select>',
                                    h, re.S):
        for v, nom in re.findall(r'<option value="(\d+)">(.*?) ·', bloc):
            vus[nom] = int(v)
    assert vus == {"01_RC.pdf": 0, "attestation-rc-pro.pdf": 1,
                   "02_CCTP.pdf": 2, "bilan-2024.pdf": 3}, vus


def test_une_liste_vide_ne_s_affiche_pas():
    """Un sélecteur sans option et un bouton qui ne retire rien se lisent
    comme une panne."""
    h = _rendu_file([("01_RC.pdf", "consultation")])
    assert len(re.findall(r"<select ", h)) == 1, h
    assert "cabinet" not in h.lower(), (
        "la page parle du cabinet alors qu'aucun document n'en vient")


def test_le_poids_reste_UNIQUE_et_se_lit_contre_la_limite():
    """Deux totaux par côté laisseraient conclure qu'on passe alors que la
    limite porte sur l'envoi entier. Et « 3,7 Mo » seul ne dit pas s'il
    passe : c'est au moment de choisir qu'il faut le savoir."""
    h = _rendu_file([("01_RC.pdf", "consultation"),
                     ("attestation-rc-pro.pdf", "cabinet")])
    poids = re.findall(r'<p class="[^"]*ig-ao-poids[^"]*">(.*?)</p>', h, re.S)
    assert len(poids) == 1, ("le poids est affiché %d fois" % len(poids), poids)
    assert "sur" in poids[0] and "envoi" in poids[0], poids[0]
    # LE TOTAL EST CELUI DES DEUX CÔTÉS, et on le vérifie en le comparant à
    # ce que `aoOctets` rend pour la SOMME — pas en cherchant « 200 » dans un
    # texte que le formateur écrit « 195 Ko ». Comparer à une chaîne écrite
    # ici mesurerait ma lecture du formateur, pas le total affiché.
    assert _octets(200000) in poids[0], (poids[0], _octets(200000))
    # ET IL N'EST PAS CELUI D'UN SEUL CÔTÉ : c'est tout l'objet de la règle.
    assert _octets(100000) not in poids[0], poids[0]


def _octets(n):
    """Ce que `aoOctets` rend pour n octets — demandé au script lui-même."""
    prog = (_js_source("aoOctets")
            + "\nfunction fr(x){ return String(Math.round(Number(x)||0)); }"
            + "\nprocess.stdout.write(aoOctets(%d));\n" % n)
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60)
    assert out.returncode == 0, out.stderr[-1000:]
    return html.unescape(out.stdout)


def test_chaque_liste_est_nommee_pour_un_lecteur_d_ecran():
    """L'`aria-label` disait « Pièces de la consultation choisies » sur la
    liste MÊLÉE : un lecteur d'écran annonçait le mauvais côté pour la moitié
    des lignes. Deux listes, deux libellés, et chacun le sien."""
    h = _rendu_file([("01_RC.pdf", "consultation"),
                     ("attestation-rc-pro.pdf", "cabinet")])
    labels = re.findall(r'aria-label="([^"]+)"', h)
    assert len(labels) == 2 and len(set(labels)) == 2, labels
    assert any("consultation" in x.lower() for x in labels), labels
    assert any("cabinet" in x.lower() for x in labels), labels
