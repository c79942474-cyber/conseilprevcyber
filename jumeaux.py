# -*- coding: utf-8 -*-
"""LES MODULES PARTAGÉS ENTRE LES DEUX DÉPÔTS — le manifeste, et ce qu'il peut.

CE QU'UNE RÈGLE D'ESSAI NE PEUT PAS FAIRE, ET QU'IL FAUT DIRE
─────────────────────────────────────────────────────────────
Elle ne peut pas lire l'autre dépôt. Les deux sont des copies de travail
distinctes, et l'intégration n'en voit qu'une. Toute règle qui prétendrait
garantir depuis ici que les deux copies sont identiques serait verte pour une
raison sans rapport avec ce qu'elle prétend — le défaut qu'on corrige partout
ailleurs dans ces dépôts.

CE QU'ELLE PEUT FAIRE, ET QUI SUFFIT À RENDRE LA DÉRIVE VISIBLE
──────────────────────────────────────────────────────────────
Ce manifeste porte, pour chaque module partagé, l'empreinte de son contenu.
Modifier une copie sans re-tamponner fait tomber la règle DU DÉPÔT MODIFIÉ,
tout de suite — et le tampon, lui, part au dépôt jumeau avec le reste. Les deux
manifestes se comparent ensuite d'un coup d'œil, ou par
`outils/verifier_jumeaux.py`, qui est le seul endroit à voir les deux.

CE QUI A MOTIVÉ CE MANIFESTE, RELEVÉ LE 8 SEPTEMBRE 2026
───────────────────────────────────────────────────────
`equipements_it.py` annonçait depuis son en-tête être « PARTAGÉ À L'IDENTIQUE »,
et ses deux copies divergeaient de trente-six lignes. L'écart n'était pas
cosmétique : la copie cyber requalifiait ses sources en « HYPOTHÈSE DU CABINET,
PAS UNE MESURE », celle de Sentinel annonçait encore des empreintes produit
constructeurs et la base Boavizta. Le même module, servi par deux sites, avec
deux vérités — et c'était le site le plus exposé qui portait la plus flatteuse.
Un commentaire qui dit « partagé » ne partage rien.

`moe_dc.py`, lui, était identique. Par discipline : aucune règle ne le tenait.

UN HOMONYME N'EST PAS UN JUMEAU, ET LES CONFONDRE COÛTERAIT PLUS QUE LA DÉRIVE
─────────────────────────────────────────────────────────────────────────────
`base_carbone.py` porte le même nom des deux côtés et diverge de trente-huit
lignes — et il DOIT diverger. C'est un module de confrontation : il oppose les
facteurs de l'ADEME à la table de référence du site où il tourne. Sentinel
confronte aux moyennes Ember employées par son module d'empreinte, le site
cyber confronte à INTENSITE_RESEAU. Les nombres cités diffèrent parce que
l'objet comparé diffère, et la copie cyber porte en plus une réserve sur le
Luxembourg propre à SA table. Aligner les deux ferait décrire à un site la
table de l'autre.

Les divergences voulues sont donc DÉCLARÉES ici, avec leur raison — et une
règle exige que la raison en soit une, pas une ligne de politesse.
"""
import hashlib
import io
import os
import re

VERSION = "2026-09-a"

_ICI = os.path.dirname(os.path.abspath(__file__))

#: Les modules qui doivent être identiques dans les deux dépôts, et l'empreinte
#: de leur contenu. `jumeaux.py` s'y inclut : son empreinte est calculée sur
#: lui-même, empreintes mises à blanc — sans quoi elle se référencerait.
JUMEAUX = {
    "empreinte_ia.py": {
        "empreinte": "14711f48fa5d52b8",
        "porte": "Les facteurs d'empreinte de l'IA et leurs sources, les trois "
                 "méthodes, l'ajustement fin déclaré, les trajectoires.",
    },
    "equipements_it.py": {
        "empreinte": "368054d0a8daa6ba",
        "porte": "Les quantités, prix et carbone de cycle de vie des équipements "
                 "informatiques. L'enveloppe d'investissement et l'empreinte "
                 "doivent lire les MÊMES quantités.",
    },
    "moe_dc.py": {
        "empreinte": "51b23dcb5c5f64e1",
        "porte": "La maîtrise d'œuvre : missions, taux, répartition des honoraires.",
    },
    "jumeaux.py": {
        "empreinte": "454073553f904cb0",
        "porte": "Ce manifeste lui-même — sans quoi la liste des jumeaux pourrait "
                 "diverger sans que rien ne le voie.",
    },
}

#: Les homonymes qui divergent VOLONTAIREMENT, avec la raison qui les en
#: dispense. Une raison courte n'en est pas une : la règle mesure sa longueur.
DIVERGENTS_ASSUMES = {
    "base_carbone.py":
        "Module de CONFRONTATION : il oppose les facteurs de l'ADEME à la table "
        "de référence du site où il tourne — les moyennes Ember du module "
        "d'empreinte côté Sentinel, INTENSITE_RESEAU côté cyber. Les écarts "
        "cités diffèrent parce que l'objet comparé diffère, et la copie cyber "
        "porte une réserve sur le Luxembourg propre à sa table. Les aligner "
        "ferait décrire à un site la table de l'autre.",
}


def _sans_empreintes(texte):
    """Le texte, toutes les empreintes déclarées mises à blanc.

    C'est ce qui rend le tampon possible : une empreinte calculée SUR sa propre
    déclaration ne peut jamais tomber juste."""
    return re.sub(r'"empreinte": "[0-9a-f]*"', '"empreinte": ""', texte)


def empreinte_du_fichier(nom, dossier=None):
    """L'empreinte d'un module partagé, tel qu'il est sur le disque."""
    chemin = os.path.join(dossier or _ICI, nom)
    if not os.path.exists(chemin):
        return None
    brut = io.open(chemin, encoding="utf-8").read()
    return hashlib.sha256(_sans_empreintes(brut).encode("utf-8")).hexdigest()[:16]


def verifier(dossier=None):
    """Ce que ce dépôt peut dire de ses jumeaux : lesquels manquent, et
    lesquels ont été modifiés sans être re-tamponnés."""
    absents, derive = [], []
    for nom, d in JUMEAUX.items():
        e = empreinte_du_fichier(nom, dossier)
        if e is None:
            absents.append(nom)
        elif e != d["empreinte"]:
            derive.append({"module": nom, "declaree": d["empreinte"], "reelle": e})
    return {"jumeaux": len(JUMEAUX), "absents": absents, "derive": derive,
            "divergents_assumes": sorted(DIVERGENTS_ASSUMES)}
