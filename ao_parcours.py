# -*- coding: utf-8 -*-
"""Le parcours guidé d'une réponse à appel d'offres — mesuré, jamais rédigé.

POURQUOI UN PARCOURS À PART. Le site en a déjà un, dans `ingenierie_dc.guide`,
et il ne convient pas ici : il parle PHASES et DISCIPLINES — APS, APD, PRO,
DCE — c'est-à-dire la production documentaire d'un projet d'ingénierie. Une
réponse à consultation ne suit pas cet axe. Elle a son propre ordre, dicté par
les délais d'obtention et par ce qui rend une offre irrecevable : on rassemble
le dossier de consultation, on lit ce qui départage, on réunit ce qui met trois
semaines à venir, on remplit, on assume, on emporte. Plaquer les phases d'un
projet sur cette séquence aurait produit un parcours qui a l'air juste et ne
correspond à rien.

CE QUI DISTINGUE CE MODULE D'UNE LISTE DE CONSEILS. Chaque étape se dit FAITE
ou NON FAITE sur une MESURE, jamais sur une impression, et rend le nombre qui
la justifie : « 7 pièces identifiées sur 12 attendues, 2 bloquantes
manquantes » et non « le dossier semble incomplet ». Une étape sans nombre
n'est pas une étape franchie — c'est un encouragement, et un encouragement ne
dit pas si l'on peut déposer.

L'ORDRE EST CELUI DU RISQUE, PAS CELUI DU CONFORT. Les formulaires viennent en
dernier : ils se remplissent en une heure dès lors que le reste existe, et les
mettre en tête donne le sentiment d'avancer pendant que l'attestation fiscale,
qui met trois semaines, n'est pas demandée. C'est ainsi qu'on rate une remise.

CE MODULE NE VA CHERCHER AUCUN ÉTAT LUI-MÊME. Il reçoit ce que la page a déjà,
et il le mesure. Aller lire le magasin d'ici ferait un module intestable et,
pire, un parcours qui changerait sous les yeux de l'utilisateur pour des
raisons qu'il ne verrait pas.

ET IL N'IMPORTE PAS `dossier_entreprise`, DÉLIBÉRÉMENT. Ce module-là porte le
dossier de CONSEILPREV — ses attestations, leurs dates — et il est réservé à
l'administrateur. Celui-ci sert des CLIENTS, qui répondent à LEURS
consultations avec LEURS attestations : y lire la table de la maison mesurerait
la mauvaise entreprise, en plus de faire fuiter la bonne. L'étape des
attestations mesure donc ce que l'appelant lui remet, et quand on ne lui remet
rien elle le DIT au lieu de se déclarer faite.
"""
import ao_dc
import ao_formulaires

VERSION = "2026-09-b"

# Ce qu'on attend d'un dossier de consultation complet : le référentiel le
# dit, on ne le recopie pas.
PIECES_ATTENDUES = len(ao_dc.PIECES_MARCHE)


def _n(x):
    """Un entier sûr : une mesure absente vaut zéro, jamais None au milieu
    d'une phrase rendue à l'écran."""
    try:
        return int(x or 0)
    except (TypeError, ValueError):
        return 0


# ── LES MESURES, UNE PAR ÉTAPE ────────────────────────────────────────────
# Chacune reçoit l'état et rend {fait, mesure, reste}. `reste` est la liste de
# ce qui manque NOMMÉMENT : « il reste 3 choses » n'aide personne à savoir
# lesquelles, et c'est précisément l'information qu'on cherche à cette étape.

def _m_consultation(e):
    a = e.get("analyse") or {}
    trouvees = len(a.get("pieces") or [])
    manquantes = a.get("manquantes") or []
    bloquantes = [m for m in manquantes if m.get("gravite") == "bloquante"]
    if not a:
        return {"fait": False, "reste": [],
                "mesure": "aucune pièce déposée ; %d attendues au dossier de "
                          "consultation" % PIECES_ATTENDUES}
    return {
        "fait": not bloquantes,
        "reste": [m["sigle"] for m in bloquantes],
        "mesure": "%d pièce(s) identifiée(s) sur %d attendues · "
                  "%d bloquante(s) manquante(s)"
                  % (trouvees, PIECES_ATTENDUES, len(bloquantes)),
    }


def _m_lire(e):
    a = e.get("analyse") or {}
    pieces = a.get("pieces") or []
    # UNE PIÈCE SANS TEXTE N'A PAS ÉTÉ LUE. Un plan DWG ou un PDF scanné est
    # identifié sur son nom : compter cela comme « lu » ferait passer pour
    # dépouillé un dossier dont on ne connaît que les titres.
    lues = [p for p in pieces if _n(p.get("octets_texte"))]
    releves = sum(len(p.get("releves") or []) for p in pieces)
    muettes = [p.get("sigle") or p.get("fichier") for p in pieces
               if not _n(p.get("octets_texte"))]
    return {
        "fait": bool(pieces) and not muettes,
        "reste": muettes,
        "mesure": "%d pièce(s) dépouillée(s) sur %d déposée(s) · "
                  "%d relevé(s) cité(s) avec leur position"
                  % (len(lues), len(pieces), releves),
    }


def _m_fiche(e):
    r = e.get("remplissage") or {}
    fiche = e.get("fiche") or {}
    attendus = [c["cle"] for c in ao_dc.CHAMPS_CANDIDAT]
    tenus = [c for c in attendus if str(fiche.get(c) or "").strip()]
    invalides = _n((r.get("etat") or {}).get("invalides"))
    vides = [c["nom"] for c in ao_dc.CHAMPS_CANDIDAT
             if not str(fiche.get(c["cle"]) or "").strip()]
    return {
        "fait": len(tenus) == len(attendus) and not invalides,
        "reste": vides[:8],
        "mesure": "%d champ(s) d'identité sur %d · %d valeur(s) refusée(s) "
                  "par leur contrôle" % (len(tenus), len(attendus), invalides),
    }


def _m_attestations(e):
    at = e.get("attestations")
    if not at:
        return {"fait": False, "reste": [],
                "mesure": "non mesurée ici — ce site ne détient pas vos "
                          "attestations ; leur validité se vérifie sur vos "
                          "propres pièces, à la date de remise"}
    absentes = list(at.get("absentes") or [])
    perimees = list(at.get("perimees") or [])
    return {
        "fait": not absentes and not perimees,
        "reste": absentes + perimees,
        "mesure": "%d attestation(s) valide(s) sur %d · %d absente(s) · "
                  "%d périmée(s)"
                  % (len(at.get("valides") or []), _n(at.get("total")),
                     len(absentes), len(perimees)),
    }


def _m_remplir(e):
    et = (e.get("remplissage") or {}).get("etat") or {}
    rub = _n(et.get("rubriques"))
    return {
        "fait": bool(rub) and _n(et.get("a_saisir")) == 0
                and _n(et.get("invalides")) == 0,
        "reste": list(et.get("bloquantes_incompletes") or [])[:8],
        "mesure": "%d rubrique(s) remplie(s) sur %d · %d à saisir · "
                  "%d pièce(s) complète(s) sur %d"
                  % (_n(et.get("remplies")), rub, _n(et.get("a_saisir")),
                     _n(et.get("pieces_completes")), _n(et.get("mesurables"))),
    }


def _m_declarer(e):
    total = len(ao_dc.declarations())
    lignes = (e.get("affirmations") or {}).get("lignes") or []
    assumees = [x for x in lignes if x.get("affirmee") and not x.get("perimee")]
    manquantes = [x.get("libelle") or x.get("cle") for x in lignes
                  if not (x.get("affirmee") and not x.get("perimee"))]
    return {
        # SANS DOSSIER CONSERVÉ, RIEN N'EST ASSUMÉ, et c'est la vérité : une
        # affirmation qui ne laisse pas de trace n'engage personne.
        "fait": bool(lignes) and len(assumees) == total,
        "reste": manquantes[:8] or ([d["libelle"] for d in ao_dc.declarations()]
                                    if not lignes else []),
        "mesure": "%d déclaration(s) assumée(s) sur %d, preuve à l'appui"
                  % (len(assumees), total),
    }


def _m_emporter(e):
    f = e.get("formulaires") or ao_formulaires.modeles_disponibles()
    prets = list(f.get("prets") or [])
    empeches = list(f.get("manquants") or []) + list(f.get("alteres") or [])
    et = (e.get("remplissage") or {}).get("etat") or {}
    return {
        "fait": bool(et.get("rubriques")) and not empeches,
        "reste": empeches,
        "mesure": "%d formulaire(s) officiel(s) remplissable(s) sur %d · "
                  "le report couvre %d pièce(s)"
                  % (len(prets), len(prets) + len(empeches),
                     _n(et.get("pieces"))),
    }


# ── LES ÉTAPES ────────────────────────────────────────────────────────────
# `ancre` désigne le vrai contrôle de la page. Une étape qui dit quoi faire
# sans dire OÙ le faire renvoie l'utilisateur chercher dans une page longue,
# et c'est là qu'on abandonne un parcours.
ETAPES = [
    {
        # « dce » AURAIT ÉTÉ UN MAUVAIS NOM, et la règle qui compare les deux
        # parcours l'a dit : dans la séquence de maîtrise d'œuvre, DCE est la
        # phase où l'ACHETEUR produit le dossier de consultation. Ici, c'est
        # l'étape où le CANDIDAT le reçoit. Le même sigle pour les deux, dans
        # la même page, aurait fait croire à un lien qui n'existe pas.
        "id": "consultation",
        "nom": "Rassembler le dossier de consultation",
        "question": "Ai-je bien reçu tout ce que l'acheteur a publié ?",
        "pourquoi": "Un DCE sans règlement de consultation ni CCAP n'est pas "
                    "un DCE. C'est le genre de constat qu'on fait trois jours "
                    "avant la remise si personne ne le fait le premier jour.",
        "geste": "Déposez les pièces du dossier de consultation : "
                 "l'identification se fait sur le nom et sur le texte.",
        "piege": "Une pièce identifiée sur son seul nom n'a pas été lue. "
                 "Un PDF scanné passe pour présent et ne dit rien.",
        "ancre": "#ig-ao-depot",
        "bloquant": True,
        "mesurer": _m_consultation,
    },
    {
        "id": "lire",
        "nom": "Lire ce qui départage",
        "question": "Sur quoi cette consultation se gagne-t-elle ou se perd-elle ?",
        "pourquoi": "Critères de jugement, pénalités, priorité des pièces, "
                    "variantes : ce sont les passages qui décident, et ils "
                    "sont rarement là où on les cherche.",
        "geste": "Ouvrez les relevés de chaque pièce : chaque citation porte "
                 "sa position, pour être vérifiée sur le document.",
        "piege": "Un passage relevé peut être une clause abrogée, un renvoi, "
                 "ou l'inverse de ce qu'il semble dire. Le relevé oriente, il "
                 "ne conclut pas.",
        "ancre": "#ig-ao-out",
        "bloquant": False,
        "mesurer": _m_lire,
    },
    {
        "id": "fiche",
        "nom": "Renseigner l'identité du candidat",
        "question": "Qui répond, et sous quelle forme ?",
        "pourquoi": "Tout le remplissage en découle. Un SIRET faux se propage "
                    "dans quatre formulaires avant qu'on s'en aperçoive.",
        "geste": "Complétez la fiche du candidat : les valeurs sont "
                 "contrôlées à la saisie, pas à la remise.",
        "piege": "En groupement, la fiche est celle du MANDATAIRE, et chaque "
                 "membre a la sienne. Un membre oublié rend la candidature "
                 "incomplète pour tous.",
        "ancre": "#ig-ao-fiche",
        "bloquant": True,
        "mesurer": _m_fiche,
    },
    {
        "id": "attestations",
        "nom": "Réunir ce qui met des semaines à venir",
        "question": "Mes attestations sont-elles valides À LA DATE DE REMISE ?",
        "pourquoi": "C'est la seule étape qu'on ne peut pas rattraper la "
                    "dernière nuit : une attestation fiscale se demande, elle "
                    "ne se rédige pas. Elle est donc placée AVANT le "
                    "remplissage, qui est rapide.",
        "geste": "Renseignez les dates de délivrance et de validité sur "
                 "l'écran du dossier d'entreprise.",
        "piege": "« Présente » ne veut rien dire : une attestation de "
                 "vigilance de l'an dernier est présente et sans valeur. "
                 "C'est l'échéance comparée au jour de la remise qui décide.",
        "ancre": "/admin/dossier-entreprise",
        "bloquant": True,
        "mesurer": _m_attestations,
    },
    {
        "id": "remplir",
        "nom": "Remplir les rubriques",
        "question": "Que reste-t-il à saisir, et qu'est-ce qui se reprend tout seul ?",
        "pourquoi": "La plupart des rubriques se déduisent de la fiche et de "
                    "l'analyse. Ce qui reste à saisir est court, et c'est là "
                    "qu'il faut mettre l'attention.",
        "geste": "Parcourez les pièces : chaque valeur porte son origine — "
                 "reprise de la fiche, relevée du DCE, ou à saisir.",
        "piege": "Une rubrique remplie n'est pas une pièce prête : il reste "
                 "les déclarations, qui ne se pré-remplissent jamais.",
        "ancre": "#ig-ao-rempli",
        "bloquant": True,
        "mesurer": _m_remplir,
    },
    {
        "id": "declarer",
        "nom": "Assumer les six déclarations",
        "question": "Qui affirme, sur quel texte, et avec quelle preuve ?",
        "pourquoi": "Quatre des six engagent pénalement. Elles ne se "
                    "pré-remplissent pas — un document qui circule se "
                    "signerait sans être lu.",
        "geste": "Affirmez chaque déclaration après avoir lu son texte : "
                 "l'affirmation est horodatée avec l'empreinte du texte lu.",
        "piege": "Une affirmation n'est pas acquise pour toujours. Le texte "
                 "peut changer, la preuve peut expirer : les deux sont "
                 "mesurés, et l'affirmation redevient à reprendre.",
        "ancre": "#ig-ao-projet",
        "bloquant": True,
        "mesurer": _m_declarer,
    },
    {
        "id": "emporter",
        "nom": "Emporter le dossier complet",
        "question": "Ai-je tout, en un seul geste ?",
        "pourquoi": "Le dossier partait jusqu'ici en cinq téléchargements — "
                    "le report, puis les quatre formulaires — et autant "
                    "d'occasions d'en oublier un.",
        "geste": "Prenez l'archive complète : le report dans le format de "
                 "votre choix, et les quatre formulaires officiels.",
        "piege": "Les formulaires officiels restent en Word, et c'est voulu : "
                 "ce qui sort EST le fichier du ministère. Un fac-similé "
                 "serait refusé — ou pire, accepté et faux.",
        "ancre": "#ig-ao-cand-out",
        "bloquant": False,
        "mesurer": _m_emporter,
    },
]


def etapes():
    """Le catalogue sans les callables — sérialisable, et lisible d'ailleurs."""
    return [{k: v for k, v in e.items() if k != "mesurer"} for e in ETAPES]


def parcours(etat=None):
    """Où en est cette réponse, étape par étape, sur des nombres.

    `etat` porte ce que la page a déjà sous la main, et rien de plus :

      · `analyse`      — le retour de `ao_dc.analyser`, ou None ;
      · `remplissage`  — le retour de `ao_dc.remplir`, ou None ;
      · `fiche`        — la fiche du candidat, telle qu'elle est saisie ;
      · `attestations` — un état d'attestations de la MÊME forme que celui
        que rend `dossier_entreprise.etat_attestations`, quand l'appelant en
        détient un pour l'entreprise qui répond. Absent, l'étape se déclare
        non mesurée ;
      · `affirmations` — le retour de `ao_projet.etat_affirmations`, ou None ;
      · `formulaires`  — le retour de `ao_formulaires.modeles_disponibles`.

    Tout est facultatif : un parcours ouvert avant le premier dépôt doit dire
    « 0 sur 12 » et non refuser de répondre. Une étape qu'on ne peut pas
    mesurer se déclare NON FAITE — jamais faite par défaut, ce qui laisserait
    croire à un dossier prêt.
    """
    etat = dict(etat or {})
    lignes = []
    for e in ETAPES:
        try:
            m = e["mesurer"](etat)
        except Exception as exc:                                # pragma: no cover
            # UNE ÉTAPE QUI NE SE MESURE PAS N'EST PAS UNE ÉTAPE FRANCHIE.
            # Rendre « fait » sur une exception ferait déclarer prêt un dossier
            # dont on ne sait rien — le pire des deux sens possibles.
            m = {"fait": False, "reste": [],
                 "mesure": "non mesurable (%s)" % type(exc).__name__}
        ligne = {k: v for k, v in e.items() if k != "mesurer"}
        ligne.update({"fait": bool(m["fait"]), "mesure": m["mesure"],
                      "reste": list(m.get("reste") or [])})
        lignes.append(ligne)

    bloquants = [l for l in lignes if l["bloquant"] and not l["fait"]]
    # OÙ L'ON EN EST : la PREMIÈRE étape non faite, bloquante ou non. Désigner
    # la première BLOQUANTE seulement sauterait « lire ce qui départage », qui
    # ne bloque pas la remise mais décide de la gagner.
    encours = next((l["id"] for l in lignes if not l["fait"]), None)
    return {
        "version": VERSION,
        "etapes": lignes,
        "total": len(lignes),
        "faites": sum(1 for l in lignes if l["fait"]),
        "ou_en_est": encours,
        "bloquants": [l["id"] for l in bloquants],
        "pret": not bloquants,
        # LA RÉSERVE VOYAGE AVEC LE PARCOURS. Un parcours vert ne dit pas que
        # l'offre est bonne : il dit que rien de MESURABLE ne manque.
        "reserve": RESERVE,
    }


RESERVE = (
    "CE PARCOURS NE JUGE PAS L'OFFRE. Il mesure ce qui est mesurable : les "
    "pièces présentes, les champs tenus, les attestations à date, les "
    "rubriques remplies, les déclarations assumées. Un parcours entièrement "
    "vert dit qu'aucun manque MESURABLE ne subsiste — pas que le mémoire "
    "technique est bon, ni que le prix est juste. Ces deux-là décident de "
    "l'attribution, et aucun compteur ne les remplace.")
