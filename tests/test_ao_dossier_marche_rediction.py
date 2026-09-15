# -*- coding: utf-8 -*-
"""LE BROUILLON LIT LE DOSSIER DU MARCHÉ — ET PAS SEULEMENT SES PROPRES MOTS.

CE QUI ÉTAIT EN CAUSE, MESURÉ LE 15 SEPTEMBRE 2026 sur un dossier de maîtrise
d'œuvre pour un centre de données de 12 MW. Pour chaque pièce rédigeable, on a
nommé les passages du dossier qu'un répondant DOIT avoir sous les yeux —
trente-cinq en tout, repérés par un mot-témoin. Le ramassage en rapportait
VINGT-DEUX. Le mémoire technique, qui porte 60 % de la note, en rapportait
QUATRE SUR NEUF : ni le PUE cible, ni la redondance N+1, ni le niveau de BIM,
ni le référentiel ANSSI, ni le phasage sur site occupé.

TROIS CAUSES, EMPILÉES, ET AUCUNE VISIBLE À L'ÉCRAN.

  1. UN PLAFOND MUET. Le ramassage s'arrêtait à CINQ paragraphes, en plus du
     budget de six mille caractères. Un paragraphe de CCTP en fait trois à cinq
     cents : le budget n'était jamais atteint et ne servait donc à rien. Les
     onze pièces ramassaient 20 609 caractères là où 66 000 étaient permis.
     Ce n'était pas une erreur de valeur mais d'UNITÉ — `SOCLE_K` et `FONDS_K`
     bornent des extraits de base, dix fois plus gros qu'un paragraphe.

  2. LA MOITIÉ DU DOSSIER HORS D'ATTEINTE. La recherche ne connaît que NOS
     mots — ceux par lesquels nous décrivons la pièce à rédiger. « PUE cible
     1,25 », « redondance N+1 », « BIM de niveau 2 », « référentiel ANSSI » ne
     partagent aucun mot avec « la méthodologie, l'organisation et les moyens
     propres à cette consultation ». Ces articles-là n'étaient ramassés par
     personne, quel que soit le budget.

  3. LES ACCENTS, ENCORE. La requête vient du nom français de la pièce —
     « Références », « sécurité », « décomposition » — et le texte d'un PDF,
     qui rend « references », « securite », « decomposition ». Sur la note QSE,
     14 des 37 mots de la requête étaient morts d'avance, dont « qualité » et
     « sécurité », c'est-à-dire son sujet. C'est MOT POUR MOT le défaut qui
     avait rendu le fonds du cabinet muet un étage plus haut.

ET UNE QUATRIÈME, QUI NE SE VOYAIT NULLE PART. La route `/marche/rediger`
n'avait pas les documents dans sa charge : elle rédigeait les onze pièces avec
ZÉRO source de consultation. Le Markdown qu'elle rendait se lit exactement
comme celui de l'atelier.

APRÈS : 33 passages sur 35, le mémoire technique à 9 sur 9, la note QSE à 4
sur 4, et chaque bloc dans son budget.

CE QUE CES RÈGLES NE FONT PAS. Elles ne jugent pas le texte rendu par le
modèle — il n'est pas de nous. Elles mesurent CE QU'ON LUI DONNE, qui l'est.
"""
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                     # noqa: E402
import ao_extraction                                             # noqa: E402
import ao_redaction as R                                         # noqa: E402

import pytest                                                    # noqa: E402

from conftest import ORIGINE                                     # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
#  LE DOSSIER D'ESSAI
#
#  SANS ACCENTS, PARCE QUE C'EST CE QUE REND L'EXTRACTION D'UN PDF. Un dossier
#  d'essai accentué aurait rendu VERTES des règles que le défaut n° 3 fait
#  tomber — et c'est précisément ainsi que ce défaut a survécu jusqu'ici.
#
#  VINGT ARTICLES, dont la plupart ne concernent aucune pièce donnée : c'est
#  ce qui rend la SÉLECTION mesurable. Un extrait de trois phrases aurait rendu
#  bon n'importe quel ramassage.
# ═══════════════════════════════════════════════════════════════════════════
RC = u"""REGLEMENT DE LA CONSULTATION

Article 1 - Objet de la consultation
La presente consultation porte sur un marche de maitrise d'oeuvre pour la
conception et la realisation d'un centre de donnees de 12 MW IT, comprenant une
tranche ferme de 6 MW et une tranche optionnelle de 6 MW.

Article 3 - Presentation des candidatures
Le candidat produit une note de presentation de l'equipe affectee a la mission
precisant les qualifications de chaque intervenant, un organigramme
fonctionnel, les curriculum vitae des intervenants cles, et six references au
minimum de moins de cinq ans portant sur des ouvrages comparables.

Article 5 - Jugement des offres
Les offres sont jugees au vu des criteres ponderes suivants : valeur technique
60 %, prix 40 %. La valeur technique se decompose en trois sous-criteres : la
methodologie proposee, notee sur 25 ; les moyens humains affectes a la mission,
notes sur 20 ; la maitrise des delais et le phasage propose, note sur 15.
Le memoire technique repond point par point a ces sous-criteres. Il est limite
a 30 pages hors annexes.

Article 6 - Remise des offres
Date et heure limites de remise des offres : 25/10/2026 a 12h00.
"""

CCTP = u"""CAHIER DES CLAUSES TECHNIQUES PARTICULIERES

Article 3 - Performance energetique
Le PUE cible en regime nominal est de 1,25 mesure sur une annee glissante a
charge IT de 70 pour cent. Le titulaire justifie cette cible par une note de
calcul remise a l'avant-projet definitif.

Article 4 - Redondance et disponibilite
La redondance attendue est N+1 sur la production de froid et 2N sur la
distribution electrique. Le niveau de disponibilite vise correspond au niveau
Tier III de l'Uptime Institute.

Article 5 - Commissionnement
Le titulaire produit un plan de commissionnement couvrant les niveaux 1 a 5 et
conduit les essais de charge a 100 pour cent de la puissance IT au moyen de
bancs de charge resistifs.

Article 6 - Maquette numerique
Les etudes sont conduites en BIM de niveau 2. Le titulaire designe un referent
BIM parmi les intervenants cles et precise son taux d'affectation.

Article 7 - Securite des systemes d'information
La conception respecte le referentiel d'hygiene informatique de l'ANSSI. La
segmentation des reseaux de gestion technique du batiment est etanche vis-a-vis
des reseaux de production.

Article 9 - Environnement et qualite
La demarche environnementale vise la certification HQE niveau excellent. Le
titulaire remet un plan de management de la qualite propre a l'operation,
precisant les points d'arret et le traitement des non-conformites.
"""

CCAP = u"""CAHIER DES CLAUSES ADMINISTRATIVES PARTICULIERES

Article 2 - Delais d'execution
Le delai global d'execution de la mission est de 26 mois a compter de la
notification du marche.

Article 4 - Remuneration
La remuneration du maitre d'oeuvre est forfaitaire. Elle est decomposee par
element de mission selon la decomposition du prix global et forfaitaire jointe
au dossier. Le candidat renseigne, pour chaque element de mission, le montant
hors taxes correspondant.

Article 7 - Groupement
En cas de groupement, la forme imposee est le groupement solidaire. Le
mandataire est solidaire de chacun des membres. La repartition des prestations
entre cotraitants figure a l'acte d'engagement.

Article 8 - Conventions collectives
Le titulaire indique la convention collective dont relevent les personnels
affectes a l'execution du marche et atteste du respect des obligations en
matiere de travail dissimule.
"""

DOCUMENTS = [{"nom": "RC-2026.pdf", "texte": RC, "extension": ".pdf"},
             {"nom": "CCTP-2026.pdf", "texte": CCTP, "extension": ".pdf"},
             {"nom": "CCAP-2026.pdf", "texte": CCAP, "extension": ".pdf"}]


# CE QU'UN RÉPONDANT DOIT AVOIR SOUS LES YEUX, PIÈCE PAR PIÈCE.
#
# CHAQUE MOT-TÉMOIN N'APPARAÎT QU'À UN ENDROIT DU DOSSIER : le retrouver dans
# le bloc prouve que CE passage-là a été ramassé, pas qu'un mot courant s'y
# promène. C'est la différence entre mesurer un ramassage et constater qu'il
# rend une chaîne non vide.
ATTENDUS = {
    "memoire_technique": ["sous-criteres", "PUE", "N+1", "commissionnement",
                          "BIM de niveau 2", "ANSSI", "HQE"],
    "moyens": ["PUE", "commissionnement", "bancs de charge", "referent BIM"],
    "qse": ["HQE", "plan de management de la qualite", "ANSSI"],
    "equipe": ["intervenants cles", "moyens humains affectes"],
    "organigramme": ["organigramme\nfonctionnel"],
    "dpgf": ["montant\nhors taxes", "tranche optionnelle"],
    "conventions": ["convention collective", "travail dissimule"],
    "convention_groupement": ["groupement solidaire"],
    "repartition_competences": ["repartition des prestations"],
}


@pytest.fixture(scope="module")
def dossier():
    a = ao_dc.analyser(DOCUMENTS)
    r = ao_dc.remplir(fiche={"raison_sociale": "CONSEILPREV",
                             "siret": "12345678900011"}, analyse=a)
    return a, r, ao_extraction.corpus(DOCUMENTS, a)


def _bloc(cle, dossier):
    _a, r, corp = dossier
    piece = next(p for p in R.pieces_redigeables(r) if p["cle"] == cle)
    return R.chercher_dossier(piece, corp)


def _paragraphes(corp):
    out = []
    for p in corp["pieces"]:
        for para in re.split(r"\n\s*\n", p["texte"]):
            t = para.strip()
            if len(t) >= 40:
                out.append(t)
    return out


def _note(piece, texte):
    """La note lexicale, telle que le module la calcule — dépliée des deux
    côtés. La recopier accentuée ici aurait fait mesurer autre chose."""
    mots = [m for m in re.split(r"[^0-9A-Za-zÀ-ÿ]+",
                                ao_dc._sans_accent(R.requete_socle(piece).lower()))
            if len(m) > 3]
    bas = ao_dc._sans_accent(texte.lower())
    return sum(1 for m in set(mots) if m in bas)


def _corpus_plus_gros_que_le_budget(corp):
    """Le dossier d'essai, répété jusqu'à dépasser franchement le budget.

    ON RÉPÈTE LE DOSSIER PLUTÔT QUE D'INVENTER DU REMPLISSAGE : ce qu'on veut
    éprouver est la BORNE, et du texte hors sujet serait écarté avant elle.
    Le suffixe rend chaque copie distincte.
    """
    pieces = []
    for n in range(6):
        for x in corp["pieces"]:
            pieces.append(dict(x, fichier="%s-%d" % (x["fichier"], n),
                               texte=x["texte"].replace(
                                   "Article", "Article %d.x" % n)))
    return {"pieces": pieces,
            "octets": sum(len(x["texte"]) for x in pieces)}


def _plat(t):
    """LE TÉMOIN SE CHERCHE À ESPACES NORMALISÉS, et c'est nécessaire.

    L'extraction d'un PDF coupe les lignes où elle veut : « un referent\nBIM »,
    « organigramme\nfonctionnel ». Un témoin écrit d'une traite ne s'y retrouve
    pas — et la règle tomberait alors pour une raison sans rapport avec ce
    qu'elle mesure : le passage EST ramassé, c'est le témoin qui est mal écrit.
    """
    return " ".join((t or "").split())


# ═══════════════════════════════════════════════════════════════════════════
#  1. CE QUE LE RAMASSAGE RAPPORTE — la mesure, pas le constat.
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("cle", sorted(ATTENDUS))
def test_chaque_piece_ramasse_les_passages_QU_ELLE_DOIT_AVOIR(cle, dossier):
    """LA RÈGLE QUI PORTE TOUT LE TOUR. Elle ne demande pas que le bloc soit
    non vide — il l'était déjà, et il manquait les deux tiers de ce qu'il
    fallait. Elle nomme les passages et les compte."""
    d = _bloc(cle, dossier)
    bloc = _plat(d["bloc"])
    manque = [m for m in ATTENDUS[cle] if _plat(m) not in bloc]
    assert not manque, (
        "%s : le dossier exige ces passages et le ramassage ne les rapporte "
        "pas — %s" % (cle, manque))


def test_le_memoire_technique_rapporte_TOUTES_les_exigences_du_CCTP(dossier):
    """LA PIÈCE QUI PORTE 60 % DE LA NOTE, et celle qui ramassait le moins.

    Elle est nommée à part parce qu'elle est le cas limite : sa description
    parle de méthodologie et d'organisation, le CCTP parle de PUE et de
    redondance, et les deux vocabulaires ne se touchent pas."""
    d = _bloc("memoire_technique", dossier)
    bloc = _plat(d["bloc"])
    for exigence in ("PUE", "N+1", "commissionnement", "BIM", "ANSSI", "HQE"):
        assert exigence in bloc, (
            "le mémoire technique se rédige sans l'exigence « %s » du CCTP "
            "auquel il répond" % exigence)
    # ET LES TROIS PIÈCES DU DOSSIER SONT CITÉES, pas seulement le règlement.
    assert {s["titre"] for s in d["sources"]} == {"RC", "CCTP", "CCAP"}, \
        d["sources"]


def test_rien_de_retenu_n_est_ABANDONNE_quand_le_budget_le_permet(dossier):
    """LE PLAFOND MUET, MESURÉ POUR CE QU'IL ÉTAIT.

    LA PREMIÈRE VERSION DE CETTE RÈGLE MESURAIT LE DOSSIER D'ESSAI, PAS LE
    RAMASSAGE. Elle exigeait que le bloc emploie plus de la moitié du budget —
    or ce dossier-ci fait 3 434 caractères pour un budget de 6 000 : aucun
    ramassage, si bon soit-il, ne peut en écrire davantage. Elle aurait viré au
    rouge le jour où l'on RACCOURCIT le dossier d'essai, et au vert le jour où
    on l'allonge, sans que le ramassage ait changé d'un caractère.

    CE QUE LE PLAFOND CASSAIT VRAIMENT : des paragraphes retenus, qui tenaient
    dans le budget, étaient jetés — parce qu'ils arrivaient après le cinquième.
    C'est cela qu'on mesure : quand le budget n'est pas atteint, RIEN de ce qui
    est retenu n'est laissé dehors.
    """
    _a, r, corp = dossier
    for cle in sorted(ATTENDUS):
        piece = next(p for p in R.pieces_redigeables(r) if p["cle"] == cle)
        retenus = [t for t in _paragraphes(corp)
                   if _note(piece, t) or R.impose(t)]
        bloc = _plat(_bloc(cle, dossier)["bloc"])
        dehors = [t for t in retenus if _plat(t) not in bloc]
        assert not dehors, (
            "%s : %d paragraphe(s) retenu(s) laissé(s) dehors alors que le "
            "bloc n'emploie que %d caractères sur %d — %s"
            % (cle, len(dehors), len(bloc), R.DOSSIER_CARACTERES,
               [t[:60] for t in dehors]))
        # ET LA BORNE D'AVANT EST BIEN FRANCHIE : cinq paragraphes.
        assert len(retenus) > 5, (
            "le dossier d'essai ne retient que %d paragraphes pour %s : il ne "
            "peut pas mesurer un plafond de cinq" % (len(retenus), cle))


def test_le_bloc_NE_DEPASSE_JAMAIS_son_budget(dossier):
    """L'AUTRE MOITIÉ DE LA MÊME RÈGLE. Un ramassage qui remplit son budget
    n'a de valeur que s'il s'y tient : c'est ce budget qui borne ce qu'on paie
    au modèle, et le sigle et le séparateur se paient comme le reste.

    CETTE RÈGLE ÉTAIT VERTE POUR RIEN, ET DEUX MUTATIONS L'ONT MONTRÉ. Le
    dossier d'essai fait 3 434 caractères pour un budget de 6 000 : le budget
    n'y est jamais atteint, si bien que SUPPRIMER la borne, ou cesser de
    compter le sigle, ne changeait rien au bloc rendu. Une règle qui mesure un
    plafond doit l'atteindre. On gonfle donc le dossier.
    """
    _a, r, corp = dossier
    gros = _corpus_plus_gros_que_le_budget(corp)
    assert gros["octets"] > R.DOSSIER_CARACTERES * 2, "le dossier doit déborder"
    for cle in sorted(ATTENDUS):
        piece = next(x for x in R.pieces_redigeables(r) if x["cle"] == cle)
        n = len(R.chercher_dossier(piece, gros)["bloc"])
        assert n <= R.DOSSIER_CARACTERES, (
            "%s écrit %d caractères pour un budget de %d"
            % (cle, n, R.DOSSIER_CARACTERES))


def test_un_paragraphe_trop_long_NE_TUE_PAS_la_suite(dossier):
    """LE `break` D'AVANT RENDAIT LE RAMASSAGE OTAGE D'UN SEUL ARTICLE.

    Un long article bien classé arrêtait tout ce qui venait après, y compris
    des paragraphes courts qui tenaient dans ce qui restait. Le dossier d'essai
    ne le déclenche pas — on le déclenche ici exprès, sinon la correction ne
    serait mesurée par rien."""
    _a, r, corp = dossier
    piece = next(p for p in R.pieces_redigeables(r)
                 if p["cle"] == "memoire_technique")
    # Un article ÉNORME, très bien classé (il reprend les mots de la pièce),
    # suivi d'un article court qui porte un témoin unique.
    enorme = (u"Le titulaire expose sa methodologie, son organisation et ses "
              u"moyens propres a cette consultation. " * 200)
    court = (u"Article 99 - Le titulaire remet un plan de reprise dont le "
             u"delai de bascule est de 4 heures. Le temoin est ZORGLUB.")
    gonfle = dict(corp, pieces=list(corp["pieces"]) + [{
        "fichier": "ANNEXE.pdf", "sigle": "ANNEXE",
        "texte": enorme + "\n\n" + court, "cote": "consultation"}])
    d = R.chercher_dossier(piece, gonfle)
    assert len(enorme) > R.DOSSIER_CARACTERES, "l'article d'essai doit déborder"
    assert "ZORGLUB" in d["bloc"], (
        "un seul paragraphe trop long a fait abandonner tout le reste du "
        "ramassage — c'est un vrai CCTP qui le déclenchera")


# ═══════════════════════════════════════════════════════════════════════════
#  2. LE REGISTRE DE L'OBLIGATION — ce que l'acheteur IMPOSE.
# ═══════════════════════════════════════════════════════════════════════════
def test_impose_distingue_une_exigence_d_un_titre():
    """CE QUE LA NOTE SÉPARE VRAIMENT. Un titre de document n'engage personne
    et n'a rien à faire dans un mémoire ; il était pourtant ramassé, parce
    qu'il contient le mot « techniques »."""
    assert R.impose(u"CAHIER DES CLAUSES TECHNIQUES PARTICULIERES") == 0
    assert R.impose(u"Article 4 - Remuneration") == 0
    exigence = (u"Le titulaire produit un plan de commissionnement et conduit "
                u"les essais. Le delai est de 26 mois.")
    assert R.impose(exigence) >= 3, R.impose(exigence)


def test_impose_lit_le_texte_SANS_ACCENTS_comme_avec():
    """LE TEXTE ARRIVE D'UN PDF. Une liste de marques accentuées ne
    rencontrerait jamais « penalite », « designe », « etablit »."""
    accentue = u"Le titulaire désigne un référent et établit le pénalité."
    nu = u"Le titulaire designe un referent et etablit le penalite."
    assert R.impose(accentue) == R.impose(nu) >= 3


def test_le_registre_ne_nomme_AUCUN_terme_de_metier():
    """CE QUI REND CETTE LISTE RÉUTILISABLE. Elle reconnaît un REGISTRE — ce
    qui engage quelqu'un — pas un SUJET. Y glisser « PUE » ou « redondance »
    l'aurait rendue juste sur ce marché-ci et fausse au suivant, sans que rien
    ne le signale : elle continuerait de ramasser QUELQUE CHOSE."""
    metier = ("pue", "redondance", "bim", "anssi", "datacenter", "onduleur",
              "climatisation", "hqe", "tier", "kilowatt", "voirie", "beton")
    for m in metier:
        assert not any(m in x.lower() for x in R.OBLIGATIONS), (
            "« %s » est un terme de métier : le registre ne doit reconnaître "
            "que ce qui ENGAGE, sinon il est à réécrire à chaque marché" % m)


def test_l_obligation_DEPARTAGE_mais_ne_commande_pas(dossier):
    """L'ORDRE DES DEUX LECTURES, ET POURQUOI IL EST DANS CE SENS.

    Additionner les deux notes aurait mis l'article « pénalités » — bourré de
    marques d'obligation et étranger à la pièce — devant la présentation de
    l'équipe dans une note d'équipe. On mesure la conséquence : le premier
    passage cité doit venir de ce que la pièce demande.

    LA PREMIÈRE VERSION REGARDAIT LE DOSSIER D'ESSAI et n'y voyait rien : les
    deux ordres y donnent le même premier passage, et la mutation survivait.
    On construit donc le cas qui les SÉPARE — un article étranger à la pièce,
    saturé d'obligations, contre un article qui parle d'équipe et n'en porte
    presque aucune. Sous une somme, le premier passerait devant.
    """
    _a, r, _corp = dossier
    piece = next(x for x in R.pieces_redigeables(r) if x["cle"] == "equipe")
    etranger = (u"Le titulaire produit, remet et transmet les pieces. Il "
                u"justifie, etablit, designe, indique et atteste. Le delai est "
                u"de 30 jours et la penalite est due par jour de retard au "
                u"prorata. Le candidat doit respecter ce qui precede.")
    lapiece = (u"Note de presentation de l'equipe : l'equipe affectee a la "
               u"mission comprend les intervenants cles dont les "
               u"qualifications et l'experience sont annexees.")
    assert R.impose(etranger) > R.impose(lapiece), (
        "le cas d'essai ne sépare pas les deux ordres")
    corp = {"pieces": [{"fichier": "T.pdf", "sigle": "T",
                        "cote": "consultation",
                        "texte": etranger + "\n\n" + lapiece}]}
    premier = _plat(R.chercher_dossier(piece, corp)["bloc"].split("\n\n")[0])
    assert "equipe" in premier.lower(), (
        "la note d'équipe ouvre sur un passage qui ne parle pas d'équipe : "
        "l'obligation a pris le pas sur la pièce — %s" % premier[:160])


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES ACCENTS — le défaut qui se reproduit d'un étage à l'autre.
# ═══════════════════════════════════════════════════════════════════════════
def test_une_requete_accentuee_trouve_un_texte_de_PDF(dossier):
    """LE DÉFAUT N° 3, ISOLÉ. « Références », « sécurité », « décomposition »
    sont les mots des pièces ; un PDF rend « references », « securite »,
    « decomposition ». Comparés tels quels, ils ne se rencontrent jamais."""
    d = _bloc("qse", dossier)
    # Le nom de la pièce porte « qualité » et « sécurité », accentués ; les
    # deux articles qu'ils doivent trouver ne le sont pas.
    assert "ANSSI" in _plat(d["bloc"]) and "HQE" in _plat(d["bloc"]), (
        "la note QSE ne trouve ni l'article sécurité ni l'article qualité : "
        "ses propres mots sont accentués et le dossier ne l'est pas")


# LES DEUX CÔTÉS SE MESURENT SÉPARÉMENT, ET IL LE FAUT.
#
# La comparaison a deux moitiés — la requête et le texte — et déplier une seule
# des deux ne rapproche rien. Une règle unique aurait laissé survivre la
# mutation qui n'enlève que l'autre : c'est arrivé.
#
# LE TÉMOIN NE PORTE AUCUNE MARQUE D'OBLIGATION, et c'est ce qui rend ces deux
# règles valides. La première version employait « Le titulaire décrit sa
# démarche… » : ce paragraphe-là est ramassé par le REGISTRE quoi qu'il
# advienne de la recherche lexicale, et la règle restait donc verte en mesurant
# l'autre chemin. La mutation qui laissait la requête accentuée a survécu à
# cette version-là.
# ET LE TÉMOIN NE DOIT PARTAGER AVEC LA REQUÊTE QUE DES MOTS ACCENTUÉS.
#
# Deuxième version, deuxième survie. Le témoin disait « Demarche qualite
# securite ENVIRONNEMENT » — or « environnement » n'a pas d'accent : il se
# rencontrait donc des deux côtés quoi qu'il arrive aux accents, le bloc
# n'était jamais vide, et les deux mutations passaient au travers. Le témoin ne
# retient plus que des mots que l'accent sépare, et `_qse_sur` le VÉRIFIE —
# sinon la règle redeviendrait verte pour rien au premier remaniement du nom
# de la pièce.
_TEMOIN_NU = (u"Demarche qualite securite : validite des attestations "
              u"detenues, perimetre reel du systeme, etudes menees.")
_TEMOIN_ACCENTUE = (u"Démarche qualité sécurité : validité des attestations "
                    u"détenues, périmètre réel du système, études menées.")


def _qse_sur(texte):
    """Le ramassage sur un corpus d'un seul paragraphe — avec ses deux gardes.

    SANS CES GARDES, LA RÈGLE MESURE UN AUTRE CHEMIN. Un témoin qui porte une
    marque d'obligation est ramassé par le registre ; un témoin qui partage un
    mot NON accentué avec la requête est ramassé quoi qu'il advienne des
    accents. Dans les deux cas le bloc est non vide et la règle est verte sans
    rien avoir éprouvé. Les deux cas se sont produits.
    """
    r = ao_dc.remplir(fiche={"raison_sociale": "X"}, analyse=None)
    piece = next(x for x in R.pieces_redigeables(r) if x["cle"] == "qse")
    assert R.impose(texte) == 0, (
        "le témoin porte une marque d'obligation : il serait ramassé par le "
        "registre, et cette règle ne mesurerait plus la recherche lexicale")
    requete = set(m for m in re.split(r"[^0-9A-Za-zÀ-ÿ]+",
                                      R.requete_socle(piece).lower())
                  if len(m) > 3)
    nus = set(m for m in requete if m == ao_dc._sans_accent(m))
    bas = texte.lower()
    partages = sorted(m for m in nus if m in bas)
    assert not partages, (
        "le témoin partage avec la requête des mots sans accent (%s) : il "
        "serait trouvé même sans déplier quoi que ce soit" % partages)
    return R.chercher_dossier(piece, {"pieces": [
        {"fichier": "T.pdf", "sigle": "T", "cote": "consultation",
         "texte": texte}]})


def test_la_REQUETE_de_la_piece_est_depliee_avant_la_comparaison():
    """LA REQUÊTE VIENT DU NOM FRANÇAIS DE LA PIÈCE — « démarche qualité,
    sécurité ». Laissée accentuée, elle ne rencontre jamais le texte d'un PDF,
    même quand celui-ci reprend le nom de la pièce mot pour mot."""
    assert _qse_sur(_TEMOIN_NU)["bloc"], (
        "un paragraphe sans accents qui reprend le nom de la pièce n'est pas "
        "trouvé : la requête n'est pas dépliée")


def test_le_TEXTE_du_dossier_est_deplie_avant_la_comparaison():
    """ET L'AUTRE MOITIÉ. Tous les dossiers ne sortent pas d'un PDF : un
    règlement déposé en Word garde ses accents. La requête dépliée ne le
    rencontrerait pas davantage si le texte ne l'était pas aussi."""
    assert _qse_sur(_TEMOIN_ACCENTUE)["bloc"], (
        "un paragraphe accentué qui reprend le nom de la pièce n'est pas "
        "trouvé : le texte du dossier n'est pas déplié")


# ═══════════════════════════════════════════════════════════════════════════
#  4. LA ROUTE — elle reçoit les documents, et les trois sources se croisent.
# ═══════════════════════════════════════════════════════════════════════════
def test_la_route_rediger_ACCEPTE_les_documents_du_marche(marche, monkeypatch):
    """LE FIL ENTIER, EXÉCUTÉ. Les fonctions peuvent être justes et la ligne
    qui les relie manquer : c'est ce qu'une mutation a déjà montré au tour
    précédent, sur le fonds du cabinet."""
    import app as A
    vus = {}

    def _faux_rediger(cle, remplissage, analyse=None, rag=None,
                      corpus_dossier=None):
        vus["corpus"] = corpus_dossier
        return {"cle": cle, "nom": "X", "markdown": "## X", "socle_sources": [],
                "socle_absent": "", "fonds_sources": [], "fonds_absent": "",
                "socles": {"consultation": len(
                    (corpus_dossier or {}).get("pieces") or []),
                    "cabinet": 0, "doctrine": 0, "manques": []},
                "modele": "faux", "tronque": False, "a_completer": 0,
                "jetons": {"entree": 1, "sortie": 1, "cache_ecrit": 0,
                           "cache_lu": 0}}

    monkeypatch.setattr(A.ao_redaction, "rediger", _faux_rediger)
    analyse = ao_dc.analyser(DOCUMENTS)
    rep = marche.post("/api/datacenter/marche/rediger", json={
        "piece": "memoire_technique", "fiche": {"raison_sociale": "CONSEILPREV"},
        "analyse": analyse,
        "documents": [{"nom": d["nom"], "texte": d["texte"]} for d in DOCUMENTS],
    }, headers=ORIGINE)
    assert rep.status_code == 200, rep.get_json()
    corp = vus.get("corpus")
    assert corp, "la route n'a pas transmis les documents à la rédaction"
    assert len(corp["pieces"]) == 3, corp["pieces"]
    # LE SIGLE EST CE QUI PERMET À UNE CITATION DE NOMMER « CCTP ». Composer le
    # corpus à la main ici aurait rendu « document 2 ».
    assert {p["sigle"] for p in corp["pieces"]} == {"RC", "CCTP", "CCAP"}
    assert rep.get_json()["socles"]["consultation"] == 3


def test_la_route_rediger_REDIGE_ENCORE_sans_documents(marche, monkeypatch):
    """ELLE NE DEVIENT PAS EXIGEANTE. C'est le seul geste dont dispose qui n'a
    pas encore déposé ses pièces ; le brouillon DIT alors qu'il n'a pas lu la
    consultation, plutôt que d'être refusé."""
    import app as A
    vus = {}

    def _faux_rediger(cle, remplissage, analyse=None, rag=None,
                      corpus_dossier=None):
        vus["corpus"] = corpus_dossier
        return {"cle": cle, "nom": "X", "markdown": "## X", "socle_sources": [],
                "socle_absent": "", "fonds_sources": [], "fonds_absent": "",
                "socles": {"consultation": 0, "cabinet": 0, "doctrine": 0,
                           "manques": ["dossier_absent"]},
                "modele": "faux", "tronque": False, "a_completer": 0,
                "jetons": {"entree": 1, "sortie": 1, "cache_ecrit": 0,
                           "cache_lu": 0}}

    monkeypatch.setattr(A.ao_redaction, "rediger", _faux_rediger)
    rep = marche.post("/api/datacenter/marche/rediger", json={
        "piece": "memoire_technique", "fiche": {"raison_sociale": "CONSEILPREV"},
    }, headers=ORIGINE)
    assert rep.status_code == 200, rep.get_json()
    assert vus["corpus"] is None
    assert "dossier_absent" in rep.get_json()["socles"]["manques"]


def test_les_deux_routes_BORNENT_les_documents_au_meme_endroit():
    """QUARANTE PIÈCES, DEUX CENTS CARACTÈRES DE NOM. Recopiées à deux
    endroits, c'est celle qu'on oublie d'élargir qui tronque un dossier — et un
    dossier tronqué rédige quand même, sans rien dire."""
    src = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    # LA BORNE N'EST ÉCRITE QU'UNE FOIS. On ne compte pas les appels : on
    # vérifie qu'aucune route ne la réécrit chez elle.
    assert src.count("for d in documents[:40]") == 1, (
        "la borne des quarante pièces est écrite plus d'une fois")
    for route in ("api_datacenter_marche_atelier", "api_datacenter_marche_rediger"):
        corps = src.split("def %s(" % route, 1)[1].split("\n@app.route")[0]
        assert "_ao_documents(data)" in corps, (
            "%s lit les documents autrement que par la fonction commune" % route)


def test_la_page_ENVOIE_les_documents_au_bouton_rediger():
    """LA PAGE LES TIENT DÉJÀ. `AO_TEXTES` est posé par l'analyse et complété
    par le coffre ; `atelierDocuments` est l'appariement que l'atelier envoie.
    Le bouton « rédiger » ne les envoyait pas, et rien à l'écran ne l'a dit."""
    js = io.open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8").read()
    i = js.index("/api/datacenter/marche/rediger")
    corps = js[i:js.index("}, DELAI_LONG)", i)]
    assert "documents: atelierDocuments()" in corps, (
        "le bouton « rédiger » appelle la route sans les documents du marché : "
        "le brouillon sortira sans une seule source de consultation")
    # ET C'EST LA MÊME FONCTION QUE L'ATELIER. Une seconde collecte aurait
    # divergé — l'une prenant AO_DOCS, l'autre AO_TEXTES, comme c'est déjà
    # arrivé et a fait partir l'atelier sur un dossier sans un caractère.
    assert js.count("function atelierDocuments()") == 1


def test_le_journal_dit_COMBIEN_de_pieces_ont_servi():
    """SANS CE COMPTE, un brouillon maigre et un brouillon nourri laissent la
    même trace. C'est le maigre qu'on relirait le moins : il a l'air fini."""
    src = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    corps = src.split("def api_datacenter_marche_rediger(", 1)[1] \
               .split("\n@app.route")[0]
    ligne = [l for l in corps.splitlines() if "marche.rediger" in l]
    assert ligne, "la rédaction n'est plus journalisée"
    bloc = corps[corps.index(ligne[0]):][:400]
    assert "len(documents)" in bloc, (
        "le journal ne dit pas combien de pièces du marché ont servi")
