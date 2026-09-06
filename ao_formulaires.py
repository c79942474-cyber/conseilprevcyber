# -*- coding: utf-8 -*-
"""Remplir les formulaires officiels DANS LEUR PROPRE FICHIER, sans jamais
signer ni déclarer.

CE QUE CE MODULE FAIT, ET POURQUOI IL NE REDESSINE RIEN. `ao_dc.remplir()`
produit un report tracé : chaque rubrique, sa valeur, son origine. Ce report se
lit à côté du formulaire ; il ne se dépose pas à sa place. Ici, on va plus
loin : on ouvre LE FORMULAIRE OFFICIEL — le fichier du ministère, dans sa
version, avec sa mise en page et sa date de mise à jour — et on écrit les
valeurs dedans.

LA DIFFÉRENCE AVEC UN FAC-SIMILÉ EST TOUT L'ENJEU. Un formulaire redessiné par
un programme serait refusé, ou pire, accepté et faux. Un formulaire OFFICIEL
rempli reste le formulaire officiel : rien de sa mise en page, de ses mentions
légales ou de sa numérotation de cadres n'est réécrit. On ne touche qu'aux
emplacements que le modèle laisse vides.

TROIS INVARIANTS, ET CE SONT DES INVARIANTS, PAS DES INTENTIONS :

  1. ON N'ÉCRIT QUE DANS UN EMPLACEMENT VIDE. Un paragraphe qui porte du texte
     n'est jamais modifié. Cela rend STRUCTURELLEMENT impossible d'écraser une
     déclaration sur l'honneur, une mention légale ou un intitulé de cadre —
     là où une liste noire de zones à éviter serait une énumération, donc
     oubliable.

  2. LES ZONES DE DÉCLARATION ET DE SIGNATURE SONT HORS D'ATTEINTE. Même vides,
     leurs emplacements sont exclus : une ancre qui glisserait ne peut pas y
     déposer une valeur. C'est la seconde barrière, et elle est là parce que la
     première protège du texte, pas du blanc.

  3. SEULES LES VALEURS AU STATUT « rempli » SONT ÉCRITES. Une déclaration
     ressort toujours au statut `a_declarer` sans valeur : elle ne peut donc
     pas être écrite, même si une ancre la désignait. Troisième barrière,
     posée en amont des deux autres.

L'EMPREINTE DU MODÈLE EST VÉRIFIÉE AVANT D'ÉCRIRE. Les ancres sont des phrases
du formulaire ; un formulaire mis à jour peut les déplacer, les reformuler ou
les supprimer — et le remplissage écrirait alors à côté, sans rien signaler.
Le modèle est donc épinglé par son empreinte : un fichier qui a changé fait
REFUSER le remplissage, avec la raison. Mettre à jour le modèle oblige à
revérifier les ancres, ce qui est exactement le geste qu'on veut imposer.

CE MODULE NE SIGNE RIEN, ET LE DOCUMENT LE DIT. Le fichier produit porte en
tête une ligne qui le nomme pour ce qu'il est : un projet rempli
automatiquement, non signé et non vérifié. Un document qui circule sans dire
cela finirait par être déposé tel quel.
"""
import hashlib
import io
import os
import re

VERSION = "2026-08-a"

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER_MODELES = os.path.join(ICI, "modeles")

# ── LA LIGNE QUE PORTE CHAQUE DOCUMENT PRODUIT ────────────────────────────
# Elle est ajoutée EN TÊTE, jamais insérée dans un cadre : le formulaire n'est
# pas altéré, il est précédé. Elle se retire d'un coup de touche avant
# signature — et si on l'oublie, on dépose un formulaire qui dit qu'il est un
# projet, ce qui est gênant mais honnête. L'inverse ne l'est pas.
BANDEAU = ("PROJET — rempli automatiquement à partir de votre fiche et des "
           "pièces de consultation déposées. NON SIGNÉ, NON VÉRIFIÉ. Les "
           "déclarations sur l'honneur et les blocs de signature sont restés "
           "vides : personne ici ne déclare et ne signe à votre place. "
           "Relisez, complétez, puis supprimez cette ligne.")

# ── LES MODÈLES, ÉPINGLÉS PAR LEUR EMPREINTE ──────────────────────────────
# `maj` est la date que le formulaire porte LUI-MÊME, en dernière page. Elle
# n'est pas décorative : c'est ce qui permet de dire à l'utilisateur quelle
# version il remplit, et de constater qu'elle a vieilli.
MODELES = {
    "dc1": {
        "fichier": "DC1.docx",
        "nom": "DC1 — Lettre de candidature",
        "piece": "dc1",
        "maj": "01/04/2019",
        "source": "Direction des affaires juridiques, ministère chargé de "
                  "l'économie — formulaire type.",
        "empreinte": ("ad6b359b7d42ebb117ac3a89cfab9cf208583980"
                      "9a33f1fd321cec560f31d040"),
    },
    "dc2": {
        "fichier": "DC2.docx",
        "nom": "DC2 — Déclaration du candidat",
        "piece": "dc2",
        "maj": "21/11/2023",
        "source": "Direction des affaires juridiques, ministère chargé de "
                  "l'économie — formulaire type.",
        "empreinte": ("18dddc29e7d8728ff9e6a588056726a6014b0368"
                      "3fcf637e48b2e207eec143d0"),
    },
    "attri1": {
        "fichier": "ATTRI1.docx",
        "nom": "ATTRI1 — Acte d'engagement",
        "piece": "acte_engagement",
        "maj": "01/04/2019",
        "source": "Direction des affaires juridiques, ministère chargé de "
                  "l'économie — formulaire type.",
        "empreinte": ("7a7124984ab11c7ab4728667b791c2e0c6615e77"
                      "9c05e9b9e2ce49c0e697c4e2"),
    },
    "dc4": {
        "fichier": "DC4.docx",
        "nom": "DC4 — Déclaration de sous-traitance",
        "piece": "dc4",
        "maj": "12/10/2023",
        "source": "Direction des affaires juridiques, ministère chargé de "
                  "l'économie — formulaire type, document facultatif.",
        "empreinte": ("b39e32506f672bfc4a37c7121a47e1b7b61eb39b3b73272e"
                      "cc008945a2dd860a"),
    },
}

# ── OÙ CHAQUE VALEUR SE POSE ──────────────────────────────────────────────
# L'ancre est une phrase DU FORMULAIRE, recopiée telle qu'il l'écrit. La valeur
# va dans le premier emplacement vide qui suit, sans jamais franchir l'intitulé
# du cadre suivant : une ancre qui ne trouve rien avant le cadre d'après ne
# place RIEN et le dit. Écrire « quelque part par là » serait pire que ne rien
# écrire, parce que la case aurait l'air remplie.
ANCRES = {
    # ── DC1 — LETTRE DE CANDIDATURE ───────────────────────────────────────
    # L'OBJET ET LA RÉFÉRENCE PARTAGENT LE CADRE B, et c'est le formulaire qui
    # le veut : « l'indication du numéro de référence attribué au dossier par
    # l'acheteur est également une information suffisante ». Les deux ancres
    # visent donc le même intitulé — la première prend la ligne libre, la
    # seconde la suivante, parce qu'un emplacement DÉJÀ PRIS fait glisser au
    # suivant au lieu de faire renoncer.
    "dc1": [
        {"rubrique": "acheteur", "ancre": "A - Identification de l’acheteur"},
        {"rubrique": "objet_consultation",
         "ancre": "B - Objet de la consultation"},
        {"rubrique": "reference", "ancre": "B - Objet de la consultation"},
        # L'ALLOTISSEMENT SE POSE SOUS LA LIGNE DES LOTS, jamais sous la case
        # « pour le marché public » : le lecteur y verrait une candidature au
        # marché entier assortie d'un nombre de lots.
        {"rubrique": "lots", "ancre": "pour le lot n°"},
        {"rubrique": "candidat", "occurrence": 1,
         "ancre": "Nom commercial et dénomination sociale de l’unité ou de "
                  "l’établissement qui exécutera la prestation :"},
        {"rubrique": "adresse", "occurrence": 1,
         "ancre": "Adresses postale et du siège social (si elle est "
                  "différente de l’adresse postale) :"},
        {"rubrique": "siret", "occurrence": 1,
         "ancre": "Numéro SIRET, à défaut, un numéro d’identification "
                  "européen"},
    ],

    # ── DC2 — DÉCLARATION DU CANDIDAT ─────────────────────────────────────
    # LE CADRE C1 PORTE DEUX FOIS LE MÊME INTITULÉ : la ligne longue qui
    # énumère tout ce qu'il faut donner, puis la ligne courte qui ouvre
    # l'emplacement. L'ancre se termine par « la prestation : » — ce que seule
    # la seconde porte —, et le rang reste à 1 : il n'y a qu'un candidat au
    # DC2, un formulaire par membre du groupement.
    "dc2": [
        {"rubrique": "acheteur", "ancre": "A - Identification de l’acheteur"},
        {"rubrique": "objet_consultation",
         "ancre": "B - Objet de la consultation"},
        {"rubrique": "candidat", "occurrence": 1,
         "ancre": "Nom commercial et dénomination sociale de l’unité ou de "
                  "l’établissement qui exécutera la prestation :"},
        {"rubrique": "siret", "occurrence": 1,
         "ancre": "Numéro SIRET, à défaut, un numéro d’identification "
                  "européen"},
        {"rubrique": "forme", "occurrence": 1,
         "ancre": "Forme juridique du candidat individuel ou du membre du "
                  "groupement"},
        # E1 — L'INSCRIPTION AU REGISTRE PROFESSIONNEL. Le cadre est libre :
        # le RCS puis le code NAF s'y posent sur deux lignes.
        {"rubrique": "rcs",
         "ancre": "E1 - Renseignements sur l’inscription sur un registre "
                  "professionnel"},
        {"rubrique": "naf",
         "ancre": "E1 - Renseignements sur l’inscription sur un registre "
                  "professionnel"},
        # F1 — LES TROIS EXERCICES, DANS L'ORDRE DU TABLEAU. Les trois lignes
        # libres qui suivent « Chiffre d'affaires global » sont les trois
        # colonnes d'exercice : N-1, N-2, N-3. L'ordre des ancres EST l'ordre
        # des colonnes, et l'inverser attribuerait le chiffre du dernier
        # exercice à l'avant-dernier — une erreur qui se lit comme une
        # entreprise en déclin ou en croissance, selon le sens.
        {"rubrique": "ca_n1", "ancre": "Chiffre d’affaires global"},
        {"rubrique": "ca_n2", "ancre": "Chiffre d’affaires global"},
        {"rubrique": "ca_n3", "ancre": "Chiffre d’affaires global"},
    ],

    # ── ATTRI1 — ACTE D'ENGAGEMENT ────────────────────────────────────────
    # LE CADRE B1 N'OFFRE QU'UN SEUL BLOC pour toute l'identification — le
    # formulaire demande « le nom commercial et la dénomination sociale […],
    # les adresses […] et son numéro SIRET » dans le même encadré. Les trois
    # ancres visent donc le même intitulé et se posent sur trois lignes
    # consécutives, dans cet ordre.
    #
    # NI LE SIGNATAIRE NI L'ACHETEUR N'ONT D'ANCRE ICI, et c'est délibéré :
    # les cadres C et D sont les blocs de SIGNATURE — celui du titulaire et
    # celui de l'acheteur. Y écrire un nom ferait ressembler à signé un
    # document qui ne l'est pas. Le rapport les nomme dans « sans_ancre ».
    "attri1": [
        {"rubrique": "objet_marche", "ancre": "Objet du marché public"},
        {"rubrique": "reference", "ancre": "Objet du marché public"},
        {"rubrique": "lots", "ancre": "au lot n°"},
        {"rubrique": "titulaire",
         "ancre": "s’engage, sur la base de son offre et pour son propre "
                  "compte"},
        {"rubrique": "adresse",
         "ancre": "s’engage, sur la base de son offre et pour son propre "
                  "compte"},
        {"rubrique": "siret",
         "ancre": "s’engage, sur la base de son offre et pour son propre "
                  "compte"},
        {"rubrique": "compte", "ancre": "Nom de l’établissement bancaire :"},
        {"rubrique": "duree",
         "ancre": "B5 - Durée d’exécution du marché public"},
    ],

    # LES CADRES D ET E PORTENT LES MÊMES INTITULÉS, MOT POUR MOT : « Adresse
    # électronique : », « Numéro SIRET… », « Nom commercial et dénomination
    # sociale… ». L'un identifie le TITULAIRE, l'autre le SOUS-TRAITANT. Une
    # ancre sans rang déposerait donc le SIRET du titulaire dans la case du
    # sous-traitant — une faute que personne ne verrait, puisque la case serait
    # pleine et plausible. `occurrence` est là pour cela, et une règle la
    # mesure sur le document produit.
    "dc4": [
        {"rubrique": "acheteur", "ancre": "Désignation de l’acheteur :"},
        {"rubrique": "objet_marche", "ancre": "B - Objet du marché public"},
        # LE CADRE B PORTE AUSSI LES LOTS : « en cas d'allotissement,
        # identifier également le ou les lots concernés par la présente
        # déclaration de sous-traitance », dit le formulaire.
        {"rubrique": "lots", "ancre": "B - Objet du marché public"},

        # ── cadre D — le titulaire, premier rang ──────────────────────────
        {"rubrique": "titulaire", "occurrence": 1,
         "ancre": "Nom commercial et dénomination sociale de l’unité ou de "
                  "l’établissement qui exécutera la prestation :"},
        {"rubrique": "titulaire_adresse", "occurrence": 1,
         "ancre": "Adresses postale et du siège social (si elle est "
                  "différente de l’adresse postale) :"},
        {"rubrique": "titulaire_courriel", "occurrence": 1,
         "ancre": "Adresse électronique :"},
        {"rubrique": "titulaire_siret", "occurrence": 1,
         "ancre": "Numéro SIRET, à défaut, un numéro d’identification "
                  "européen"},
        {"rubrique": "titulaire_forme", "occurrence": 1,
         "ancre": "Forme juridique du soumissionnaire individuel, du "
                  "titulaire ou du membre du groupement"},
        {"rubrique": "mandataire", "occurrence": 1,
         "ancre": "En cas de groupement momentané d’entreprises, "
                  "identification et coordonnées du mandataire"},

        # ── cadre E — le sous-traitant, second rang ───────────────────────
        {"rubrique": "sous_traitant", "occurrence": 2,
         "ancre": "Nom commercial et dénomination sociale de l’unité ou de "
                  "l’établissement qui exécutera la prestation :"},
        {"rubrique": "sous_traitant_pouvoir", "occurrence": 1,
         "ancre": "Personne(s) physique(s) ayant le pouvoir d’engager le "
                  "sous-traitant :"},

        # ── cadres F à J ──────────────────────────────────────────────────
        {"rubrique": "prestations",
         "ancre": "Nature des prestations sous-traitées :"},
        {"rubrique": "montant",
         "ancre": "Montant des prestations sous-traitées :"},
        {"rubrique": "variation_prix",
         "ancre": "Modalités de variation des prix :"},
        {"rubrique": "compte",
         "ancre": "Nom de l’établissement bancaire :"},
        {"rubrique": "duree_sous_traitance",
         "ancre": "La durée du contrat de sous-traitance en nombre de mois "
                  "est de :"},
        {"rubrique": "capacites",
         "ancre": "J1 - Récapitulatif des informations et renseignements"},
    ],
}

# ── CE QUI EST HORS D'ATTEINTE, MÊME VIDE ─────────────────────────────────
# Chaque entrée ouvre une zone qui court jusqu'à l'intitulé de cadre suivant —
# ou jusqu'à la fin du document quand `jusqu_a_la_fin` est vrai. Les
# déclarations sur l'honneur et les signatures ne se remplissent pas : elles
# s'assument.
ZONES_INTERDITES = {
    "dc1": [
        # F1 PORTE LA DÉCLARATION SUR L'HONNEUR. Rien n'y entre.
        {"ancre": "F1 – Exclusions de la procédure", "jusqu_a_la_fin": False},
    ],
    # LE DC2 N'A NI DÉCLARATION SUR L'HONNEUR NI BLOC DE SIGNATURE — elles
    # vivent au DC1. L'absence d'entrée ici est donc un CONSTAT, pas un oubli :
    # une règle le vérifie plutôt que de laisser croire à une table
    # incomplète.
    "attri1": [
        # LES CADRES C ET D SONT LES SIGNATURES — celle du titulaire, puis
        # celle de l'acheteur. Tout ce qui suit l'ouverture de C est hors
        # d'atteinte, jusqu'à la fin du document.
        {"ancre": "C - Signature du marché public", "jusqu_a_la_fin": True},
    ],
    "dc4": [
        {"ancre": "K1 - Le sous-traitant déclare sur l’honneur",
         "jusqu_a_la_fin": False},
        {"ancre": "M - Acceptation et agrément des conditions de paiement",
         "jusqu_a_la_fin": True},
    ],
}

_CADRE = re.compile(r"^[A-N][0-9]?\s*[-–]\s+\S")
_VIDE = re.compile(r"^[\s.…_· ]*$")


def _net(s):
    """Un texte comparable : espaces normalisés, apostrophes unifiées.

    LES APOSTROPHES SONT LE PIÈGE. Le formulaire écrit « l’acheteur » avec une
    apostrophe typographique ; une ancre saisie au clavier porte souvent
    l'apostrophe droite. Deux chaînes qui se ressemblent à l'œil ne se
    comparent pas — et l'ancre resterait introuvable sans que rien n'explique
    pourquoi.
    """
    # LES PUCES DE POLICE SYMBOLE NE SONT PAS DU TEXTE. Word écrit les
    # puces des DC1 et ATTRI1 avec des glyphes de la zone à usage privé
    # (U+E000–U+F8FF, ici « \uf06e » en Wingdings), suivis d'une espace
    # insécable. Une ancre devrait les recopier pour s'accrocher — illisible
    # dans la table, et cassé au premier changement de police du modèle.
    # Elles sont retirées ici, jamais du document.
    #
    # `_emplacement_libre` N'UTILISE PAS CE NETTOYAGE, et c'est voulu : un
    # paragraphe qui ne porte QUE la puce est une case à cocher, pas un
    # emplacement libre. La nettoyer là ferait écrire dans une case.
    t = (s or "").replace("’", "'").replace("ʼ", "'").replace("\xa0", " ")
    t = "".join(c for c in t if not ("\ue000" <= c <= "\uf8ff"))
    return " ".join(t.split())


def _emplacement_libre(texte):
    """Un emplacement à remplir : vide, ou fait de pointillés."""
    return bool(_VIDE.match((texte or "").replace("’", "'")))


def paragraphes(doc):
    """TOUS les paragraphes, dans l'ordre du document, cellules de tableau
    comprises.

    POURQUOI `doc.paragraphs` NE SUFFIT PAS, ET C'EST UNE CORRECTION. Il ne
    rend que les paragraphes du corps : ceux qui vivent DANS un tableau lui
    échappent. Or les DC1, DC2 et ATTRI1 portent leurs intitulés de cadre
    — « A - Identification de l'acheteur », « F1 – Exclusions de la
    procédure » — dans des tableaux d'une seule cellule qui leur servent
    d'encadré. Avec `doc.paragraphs`, l'arrêt au cadre suivant ne voyait
    AUCUN cadre : une ancre dont l'emplacement a disparu aurait cherché
    jusqu'au bout du document et déposé sa valeur dix cadres plus loin.

    L'ORDRE EST CELUI DU CORPS XML, pas celui de deux listes recollées : un
    tableau intercalé entre deux paragraphes doit se lire à sa place, sinon
    « après l'intitulé » ne veut plus rien dire.

    UNE CELLULE FUSIONNÉE EST RENDUE PLUSIEURS FOIS PAR `row.cells` — deux
    fois au DC2, quatre à l'ATTRI1 —, et le même paragraphe entrerait donc
    deux fois dans la liste : assez pour qu'une valeur soit écrite deux fois,
    ou qu'un indice « déjà pris » en écarte un autre. On dédoublonne sur
    l'ÉLÉMENT DU PARAGRAPHE, et cela suffit.

    UNE SECONDE GARDE A ÉTÉ RETIRÉE ICI, ET IL FAUT DIRE POURQUOI. Elle
    dédoublonnait aussi les CELLULES, pour ne pas les parcourir deux fois. Une
    mutation l'a supprimée sans faire tomber la moindre règle : le
    dédoublonnage des paragraphes attrape déjà tout, la cellule n'étant
    reparcourue que pour rien. Une garde qu'aucune mesure ne distingue n'est
    pas une garde — c'est du code qu'on croit protecteur.
    """
    from docx.table import Table                                # noqa: PLC0415
    from docx.text.paragraph import Paragraph                   # noqa: PLC0415

    out, vus = [], set()

    def _parcourir(parent, element):
        for enfant in element.iterchildren():
            if enfant.tag.endswith("}p"):
                if id(enfant) not in vus:
                    vus.add(id(enfant))
                    out.append(Paragraph(enfant, parent))
            elif enfant.tag.endswith("}tbl"):
                for ligne in Table(enfant, parent).rows:
                    for cellule in ligne.cells:
                        _parcourir(cellule, cellule._tc)

    _parcourir(doc, doc.element.body)
    return out


def empreinte(chemin):
    """L'empreinte du fichier — celle qui dit si le modèle a bougé."""
    with io.open(chemin, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def chemin_modele(cle):
    return os.path.join(DOSSIER_MODELES, MODELES[cle]["fichier"])


def modeles_disponibles():
    """Les modèles présents ET intacts, et ceux qui manquent — dits à part.

    UN MODÈLE ABSENT N'EST PAS UN MODÈLE ALTÉRÉ. Les confondre enverrait
    chercher une corruption là où il n'y a qu'un fichier à déposer.
    """
    prets, manquants, alteres = [], [], []
    for cle, m in sorted(MODELES.items()):
        p = chemin_modele(cle)
        if not os.path.exists(p):
            manquants.append(cle)
        elif empreinte(p) != m["empreinte"]:
            alteres.append(cle)
        else:
            prets.append(cle)
    return {"prets": prets, "manquants": manquants, "alteres": alteres}


def _zones_interdites(paras, cle):
    """Les indices de paragraphes où l'on n'écrira jamais."""
    interdits = set()
    for z in ZONES_INTERDITES.get(cle, []):
        cible = _net(z["ancre"])
        for i, t in enumerate(paras):
            if not _net(t).startswith(cible):
                continue
            j = i + 1
            while j < len(paras):
                if not z["jusqu_a_la_fin"] and _CADRE.match(_net(paras[j])):
                    break
                interdits.add(j)
                j += 1
            interdits.add(i)
    return interdits


def _cible(paras, interdits, pris, ancre, occurrence):
    """L'indice de l'emplacement à remplir, ou None — jamais un « à peu près ».

    ON NE FRANCHIT PAS L'INTITULÉ DU CADRE SUIVANT. Une ancre dont
    l'emplacement a disparu chercherait sinon jusqu'au bout du document et
    déposerait sa valeur dans un cadre qui ne l'attend pas.

    INTERDIT ET DÉJÀ PRIS NE SE TRAITENT PAS PAREIL, et les confondre serait
    une faute dans les deux sens. Un emplacement INTERDIT fait renoncer :
    glisser plus loin reviendrait à contourner la barrière qu'on vient de
    poser. Un emplacement DÉJÀ PRIS fait simplement passer au suivant — un
    cadre offre souvent plusieurs lignes vides d'affilée, et refuser la
    seconde parce que la première est occupée laisserait une case vide sans
    raison.
    """
    cible = _net(ancre)
    vues = 0
    for i in range(len(paras)):
        if not _net(paras[i]).startswith(cible):
            continue
        vues += 1
        if vues < occurrence:
            continue
        for j in range(i + 1, len(paras)):
            if _CADRE.match(_net(paras[j])):
                return None
            if j in interdits:
                return None
            if j in pris:
                continue
            if _emplacement_libre(paras[j]):
                return j
        return None
    return None


def remplir_document(cle, valeurs, bandeau=BANDEAU):
    """Le formulaire officiel, rempli de ce qui est déjà connu. Rend
    (octets, rapport).

    `valeurs` est un dictionnaire {clé de rubrique: valeur} — celles que
    `ao_dc.remplir()` a portées au statut « rempli ». Rien d'autre n'entre.

    LE RAPPORT DIT CE QUI A ÉTÉ PLACÉ ET CE QUI NE L'A PAS ÉTÉ. Un formulaire
    rendu sans dire ce qui manque se lit comme un formulaire complet.
    """
    from docx import Document                                   # noqa: PLC0415

    m = MODELES[cle]
    p = chemin_modele(cle)
    if not os.path.exists(p):
        return None, {"ok": False, "motif": "modele_absent", "modele": cle,
                      "places": [], "non_places": [], "ignores": [],
                      "sans_ancre": []}
    reelle = empreinte(p)
    if reelle != m["empreinte"]:
        # ON REFUSE PLUTÔT QUE DE REMPLIR À CÔTÉ. Les ancres sont des phrases
        # de CE fichier-ci ; un modèle mis à jour les déplace sans prévenir.
        return None, {"ok": False, "motif": "modele_altere", "modele": cle,
                      "attendue": m["empreinte"], "trouvee": reelle,
                      "places": [], "non_places": [], "ignores": [],
                      "sans_ancre": []}

    doc = Document(p)
    blocs = paragraphes(doc)
    paras = [pa.text for pa in blocs]
    interdits = _zones_interdites(paras, cle)
    places, non_places, ignores = [], [], []
    pris = set()

    for a in ANCRES.get(cle, []):
        v = str(valeurs.get(a["rubrique"]) or "").strip()
        if not v:
            ignores.append({"rubrique": a["rubrique"], "motif": "sans_valeur"})
            continue
        i = _cible(paras, interdits, pris, a["ancre"], a.get("occurrence", 1))
        if i is None:
            non_places.append({"rubrique": a["rubrique"], "ancre": a["ancre"],
                               "motif": "emplacement_introuvable"})
            continue
        cible = blocs[i]
        for r in list(cible.runs):
            r._element.getparent().remove(r._element)
        cible.add_run(v)
        paras[i] = v
        pris.add(i)
        places.append({"rubrique": a["rubrique"], "ancre": a["ancre"],
                       "valeur": v, "paragraphe": i})

    # CE QU'ON A ET QUE LE FORMULAIRE N'OFFRE PAS D'ÉCRIRE. L'ATTRI1 n'a pas
    # de case « acheteur » à la main du candidat : son cadre D est le bloc de
    # SIGNATURE de l'acheteur, et le signataire du titulaire est au cadre C —
    # deux zones interdites. Sans cette liste, le rapport annoncerait sept
    # valeurs écrites là où le report en connaît onze, et l'écart resterait
    # inexpliqué. Une valeur qu'on détient et qu'on ne pose pas doit se dire.
    ancrees = {a["rubrique"] for a in ANCRES.get(cle, [])}
    sans_ancre = sorted(k for k, v in valeurs.items()
                        if k not in ancrees and str(v or "").strip())

    if bandeau:
        # EN TÊTE, ET DANS UN PARAGRAPHE À LUI. Insérer le bandeau dans un
        # cadre du formulaire modifierait le formulaire ; le poser devant ne le
        # modifie pas.
        premier = doc.paragraphs[0]
        neuf = premier.insert_paragraph_before(bandeau)
        for r in neuf.runs:
            r.bold = True

    flux = io.BytesIO()
    doc.save(flux)
    return flux.getvalue(), {
        "ok": True, "motif": "ok", "modele": cle, "nom": m["nom"],
        "maj": m["maj"], "source": m["source"], "empreinte": reelle,
        "places": places, "non_places": non_places, "ignores": ignores,
        "sans_ancre": sans_ancre,
        "bandeau": bool(bandeau),
    }


def valeurs_pour(remplissage, piece):
    """Ce qu'on peut écrire, pris dans le report de `ao_dc.remplir()`.

    SEUL CE QUI EST « rempli » PASSE. Une déclaration est toujours
    `a_declarer` et sans valeur ; une case à saisir est `a_saisir`. Ni l'une ni
    l'autre n'entre dans le document — la première parce que personne ne
    déclare à votre place, la seconde parce qu'il n'y a rien à écrire.
    """
    for p in (remplissage or {}).get("pieces", []):
        if p["cle"] != piece:
            continue
        return {l["cle"]: l["valeur"] for l in p["rubriques"]
                if l["statut"] == "rempli" and l["valeur"]}
    return {}
