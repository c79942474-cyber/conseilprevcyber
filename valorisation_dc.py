"""CE QUE VAUT UNE PERFORMANCE — dispositifs fiscaux, aides, accès au financement.

CE QUI A DÉCLENCHÉ CE MODULE
───────────────────────────
Recherche sur les six modules de la pratique centre de données — 835 187 octets
de code d'ingénierie — avec frontières de mot :

    subvention      0        TICFE           0
    aides           0        ROI, payback    0
    CEE             0        financement     2
                             rentabilité     1

`datacenter.py` calcule une énergie, une eau, un carbone. `decarbonation.py`
range onze leviers et dit ce que chacun déplace. `econome_dc.py` chiffre des
travaux. AUCUN NE DIT CE QU'UNE PERFORMANCE RAPPORTE. Un levier annonce son
effet sur le carbone ; il ne dit pas quelle exonération il déclenche, quelle
aide il ouvre, ni à quel financement il donne accès.

C'est le chaînon qui sépare un bureau d'études d'un cabinet de conseil. Un
maître d'ouvrage n'arbitre pas entre deux familles de refroidissement sur un
gramme de CO₂ : il arbitre sur un coût complet, dans lequel l'aide obtenue et
l'impôt évité pèsent autant que la facture d'électricité.

CE QUE CE MODULE FAIT
─────────────────────
Il déclare les dispositifs qui récompensent une performance — allègement
fiscal, subvention, financement, accès à la commande publique — et les RELIE
AUX LEVIERS du moteur de décarbonation. Déplacer `part_chaleur_reutilisee`
n'ouvre pas les mêmes portes que déplacer `part_renouvelable` : le module dit
lesquelles.

CE QU'IL REFUSE DE FAIRE, ET POURQUOI C'EST LE POINT LE PLUS IMPORTANT
─────────────────────────────────────────────────────────────────────
IL NE CALCULE AUCUN MONTANT. Pas un euro, pas un pourcentage, pas un seuil
chiffré.

Les valeurs qui circulent sur ces dispositifs — « jusqu'à 50 % des audits »,
« 25 % du CAPEX », « un PUE inférieur à 1,2 » — proviennent de notes de
synthèse et d'articles professionnels. Aucune n'a été relevée sur une source
primaire. Or les lecteurs de ce site sont des professionnels de
l'investissement et du crédit : un taux d'aide faux se retrouve dans un plan
de financement, et un plan de financement faux se retrouve devant un comité
d'engagement.

UNE SOURCE QU'ON NE PEUT PAS ATTEINDRE EST UNE INTENTION, PAS UNE SOURCE. Le
module porte donc, pour chaque dispositif, la source PRIMAIRE à consulter et
l'état de cette consultation. Un dispositif « à instruire » est publié comme
tel — nommé, relié aux bons leviers, utile pour savoir où chercher — mais sans
le moindre chiffre. `instruction()` rend la liste de ce qui reste à établir, et
`sante()` la compte : le manque est visible, pas dissimulé.

C'est la même règle que celle appliquée aux référentiels non branchés ailleurs
dans la maison. Instruire un dispositif est un travail de conseil, pas une
recopie — et c'est précisément la prestation qui se vend.
"""

VERSION = "2026-08-a"

# ── LA NATURE D'UN DISPOSITIF ─────────────────────────────────────────────
# Quatre familles, parce qu'elles ne s'instruisent pas de la même façon et ne
# se présentent pas au même interlocuteur : un allègement fiscal se plaide
# devant l'administration, une subvention se dépose, un financement se
# négocie, un marché se gagne.
NATURES = {
    'allegement': "Allègement fiscal. Réduit un impôt ou une taxe déjà due. "
                  "S'obtient sur justification, souvent a posteriori.",
    'subvention': "Aide directe ou certificat valorisable. Se dépose avant "
                  "engagement des dépenses, sur dossier technique.",
    'financement': "Accès à un financement, ou à de meilleures conditions. "
                   "Ne réduit pas la dépense : il en change le coût.",
    'marche': "Accès à la commande. Ne rapporte rien en soi — mais son absence "
              "ferme des appels d'offres.",
}

# ── L'ÉTAT D'INSTRUCTION ──────────────────────────────────────────────────
INSTRUCTION = {
    'instruit': "Source primaire consultée. Conditions et montants relevés sur "
                "le texte lui-même.",
    'a_instruire': "Dispositif rapporté par une source secondaire. Le nom, le "
                   "pays et la nature sont repris ; AUCUN montant ni seuil ne "
                   "l'est. La source primaire reste à consulter.",
}

# ── LES DISPOSITIFS ───────────────────────────────────────────────────────
# `condition` dit CE QUI DÉCLENCHE le dispositif, en langage de performance —
# jamais en chiffres tant que la source primaire n'a pas été lue.
# `leviers` renvoie aux clés de `decarbonation.LEVIERS` : c'est ce qui rend le
# module actionnable au lieu d'informatif.
DISPOSITIFS = [
    {
        'cle': 'ticfe_chaleur',
        'nom': "Fiscalité de l'électricité et valorisation de chaleur fatale",
        'pays': 'FR',
        'nature': 'allegement',
        'condition': "Raccordement à un réseau de chaleur, ou valorisation "
                     "avérée de la chaleur fatale du site.",
        'leviers': ['chaleur'],
        'source': "Code des impositions sur les biens et services (CIBS), "
                  "régime de l'accise sur l'électricité — et la doctrine "
                  "fiscale applicable aux centres de données.",
        'etat': 'a_instruire',
        'annonce': "Une note professionnelle fait état d'une exonération "
                   "partielle sous conditions. Ni le taux, ni le périmètre, "
                   "ni les conditions n'ont été relevés sur le texte.",
        'piege': "Le régime de l'accise sur l'électricité a changé de véhicule "
                 "juridique et de nom ces dernières années. Citer « la TICFE » "
                 "sans vérifier l'intitulé en vigueur date un dossier "
                 "instantanément.",
    },
    {
        'cle': 'cee',
        'nom': "Certificats d'économies d'énergie",
        'pays': 'FR',
        'nature': 'subvention',
        'condition': "Action d'efficacité énergétique correspondant à une fiche "
                     "d'opération standardisée, ou opération spécifique sur "
                     "dossier.",
        'leviers': ['famille', 'ashrae', 'charge', 'cycles'],
        'source': "Fiches d'opérations standardisées publiées au Journal "
                  "officiel ; dispositif piloté par la DGEC.",
        'etat': 'a_instruire',
        'annonce': "Une note professionnelle avance un taux de financement "
                   "des audits et travaux. Il n'est pas repris : il dépend de "
                   "la fiche d'opération, du volume et du cours du certificat, "
                   "et aucune de ces trois valeurs n'a été relevée.",
        'piege': "Le dossier se dépose AVANT engagement des dépenses. Un "
                 "marché signé avant le dépôt ferme le dispositif — c'est la "
                 "cause d'échec la plus banale, et elle est irrattrapable.",
    },
    {
        'cle': 'fonds_chaleur',
        'nom': "Fonds Chaleur (ADEME)",
        'pays': 'FR',
        'nature': 'subvention',
        'condition': "Projet de récupération et de livraison de chaleur fatale "
                     "à un réseau ou à un tiers.",
        'leviers': ['chaleur'],
        'source': "Modalités du Fonds Chaleur publiées par l'ADEME.",
        'etat': 'a_instruire',
        'annonce': "Dispositif nommé par une note professionnelle, sans "
                   "taux ni seuil relevé sur la source primaire.",
        'piege': "Une valorisation de chaleur sans preneur signé n'est pas un "
                 "projet : c'est une intention. Le piège est déjà nommé par le "
                 "levier `chaleur` du moteur de décarbonation.",
    },
    {
        'cle': 'bundesfoerderung',
        'nom': "Bundesförderung für effiziente Rechenzentren",
        'pays': 'DE',
        'nature': 'subvention',
        'condition': "Investissement dans des équipements à haute efficacité "
                     "énergétique, ou recours à une énergie renouvelable "
                     "locale.",
        'leviers': ['famille', 'ashrae', 'contrat', 'reseau_contrat'],
        'source': "Directive de financement fédérale allemande "
                  "(Förderrichtlinie) et son organisme instructeur.",
        'etat': 'a_instruire',
        'annonce': "Une note professionnelle avance un taux d'aide rapporté "
                   "au CAPEX. Le taux n'est pas repris.",
        'piege': "Un dispositif national s'instruit dans la langue et devant "
                 "l'administration du pays. Le supposer transposable depuis la "
                 "France fait perdre le dossier avant de l'avoir déposé.",
    },
    {
        'cle': 'chaleur_nordique',
        'nom': "Régimes nordiques de valorisation de chaleur (DK, FI)",
        'pays': 'DK,FI',
        'nature': 'allegement',
        'condition': "Alimentation d'un réseau urbain de chaleur.",
        'leviers': ['chaleur'],
        'source': "Régimes fiscaux nationaux danois et finlandais applicables "
                  "aux centres de données.",
        'etat': 'a_instruire',
        'annonce': "Réductions fiscales rapportées par une note "
                   "professionnelle. Ni le taux ni les conditions ne sont "
                   "repris.",
        'piege': "Ces régimes supposent un réseau de chaleur dense à proximité. "
                 "Ils ne se transposent pas à une implantation isolée, quelle "
                 "que soit la performance du site.",
    },
    {
        'cle': 'nl_performance',
        'nom': "Avantages fiscaux liés à la performance (NL)",
        'pays': 'NL',
        'nature': 'allegement',
        'condition': "Atteinte d'un niveau d'efficacité, ou part majoritaire "
                     "d'électricité renouvelable.",
        'leviers': ['famille', 'ashrae', 'contrat'],
        'source': "Régimes néerlandais d'amortissement et de déduction pour "
                  "investissements environnementaux.",
        'etat': 'a_instruire',
        'annonce': "Une note professionnelle cite un seuil de PUE et une part "
                   "renouvelable. Aucun des deux n'est repris : un seuil faux "
                   "oriente une conception entière.",
        'piege': "Un seuil de PUE ne se compare qu'à performance mesurée dans "
                 "les mêmes conditions. Le moteur d'ingénierie porte déjà cette "
                 "réserve : un PUE de plage de conception n'est pas un PUE "
                 "d'exploitation.",
    },
    {
        'cle': 'taxonomie_acces',
        'nom': "Alignement Taxonomie — accès au financement vert",
        'pays': 'UE',
        'nature': 'financement',
        'condition': "Conformité aux critères de l'activité 8.1 (traitement de "
                     "données, hébergement) : contribution substantielle et "
                     "absence de préjudice important.",
        'leviers': ['famille', 'ashrae', 'contrat', 'chaleur', 'reseau_contrat'],
        'source': "Règlement (UE) 2020/852 et règlement délégué (UE) 2021/2139 "
                  "— déjà déclarés dans `decarbonation.TEXTES` sous la clé "
                  "`taxonomie`.",
        'etat': 'a_instruire',
        'annonce': "L'alignement est présenté comme ouvrant des taux "
                   "préférentiels et le marché des obligations vertes. Le "
                   "TEXTE, lui, est déjà déclaré ailleurs dans la maison ; "
                   "c'est le lien avec le FINANCEMENT qui reste à établir.",
        'piege': "L'alignement Taxonomie n'est pas un label qu'on obtient : "
                 "c'est une démonstration qu'on refait à chaque exercice, et "
                 "qui se perd si un critère d'absence de préjudice cesse d'être "
                 "tenu.",
    },
    {
        'cle': 'investeu_bei',
        'nom': "InvestEU et Banque européenne d'investissement",
        'pays': 'UE',
        'nature': 'financement',
        'condition': "Projet répondant aux objectifs climatiques de l'Union, "
                     "généralement adossé à la Taxonomie.",
        'leviers': ['famille', 'contrat', 'chaleur'],
        'source': "Critères d'éligibilité publiés par la BEI et par le "
                  "programme InvestEU.",
        'etat': 'a_instruire',
        'annonce': "Mécanismes nommés par une note professionnelle. Ni les "
                   "seuils d'éligibilité ni les conditions financières n'ont "
                   "été relevés.",
        'piege': "Ces financements s'adressent à des tailles d'opération "
                 "précises. Les faire figurer dans un plan de financement sans "
                 "avoir vérifié le ticket minimal fait perdre du temps à tout "
                 "le monde.",
    },
    {
        'cle': 'eco_conditionnalite',
        'nom': "Éco-conditionnalité des marchés publics",
        'pays': 'UE',
        'nature': 'marche',
        'condition': "Capacité à PROUVER, dans une offre : part d'énergie "
                     "renouvelable, performance mesurée, politique de "
                     "réemploi des équipements.",
        'leviers': ['contrat', 'reseau_contrat', 'famille', 'ashrae'],
        'source': "Cahiers des charges des acheteurs publics ; directives "
                  "européennes sur la commande publique.",
        'etat': 'a_instruire',
        'annonce': "Une note professionnelle annonce une généralisation à "
                   "l'échelle de l'Union à horizon 2027. La date n'est pas "
                   "reprise : une échéance fausse dans un argumentaire "
                   "commercial se retourne contre celui qui l'avance.",
        'piege': "Ce dispositif ne rapporte rien et n'exonère de rien. Il "
                 "décide seulement si l'on peut concourir — ce qui, pour un "
                 "exploitant dont la clientèle est publique, pèse plus que "
                 "toutes les aides réunies.",
    },
]

_PAR_CLE = {d['cle']: d for d in DISPOSITIFS}

# Les clés de levier reconnues, telles qu'elles existent dans le moteur de
# décarbonation. Déclarées ici pour que `sante()` puisse signaler un renvoi
# vers un levier qui n'existe plus — une liaison morte ne se voit pas
# autrement, et c'est tout l'intérêt du module qui disparaît en silence.
LEVIERS_ATTENDUS = (
    'puissance', 'charge', 'famille', 'ashrae', 'evaporation', 'cycles',
    'pays', 'contrat', 'chaleur', 'reseau_contrat', 'credits',
)


def dispositifs(pays=None, nature=None, levier=None):
    """Les dispositifs, filtrés. Aucun filtre : tous.

    `pays` accepte un code seul ('FR') et retrouve aussi les régimes déclarés
    pour plusieurs pays ('DK,FI') — un dispositif danois doit sortir quand on
    interroge le Danemark, pas seulement quand on interroge « DK,FI ».
    """
    sortie = []
    for d in DISPOSITIFS:
        if pays and str(pays).upper() not in [p.strip().upper()
                                              for p in d['pays'].split(',')]:
            continue
        if nature and d['nature'] != nature:
            continue
        if levier and levier not in d['leviers']:
            continue
        sortie.append(dict(d))
    return sortie


def pour_levier(cle):
    """CE QUE CE LEVIER PEUT OUVRIR — la question qui n'avait pas de réponse.

    Un levier de décarbonation dit ce qu'il déplace. Il ne disait pas ce que
    ce déplacement vaut. C'est le point d'accroche entre l'ingénierie et le
    conseil : `part_chaleur_reutilisee` et `part_renouvelable` déplacent tous
    deux le carbone, et n'ouvrent pas du tout les mêmes portes.
    """
    return dispositifs(levier=cle)


def leviers_couverts():
    """Les leviers qui ouvrent au moins un dispositif, et les autres.

    UN AXE QUI NE TROUVE RIEN DOIT LE DIRE. Quatre leviers sur onze n'ouvrent
    aucun dispositif connu — la puissance qu'on n'installe pas, la part rejetée
    par évaporation, le choix du pays, les crédits carbone. Ce n'est pas un
    oubli à combler par du remplissage : c'est un constat, et il est utile.
    Renoncer à de la puissance installée est le levier le plus efficace du
    moteur, et aucun guichet ne le récompense — l'économie est entière en
    exploitation, sans aide pour l'amorcer. Le dire évite de vendre une aide
    qui n'existe pas.
    """
    ouvrants = {}
    for d in DISPOSITIFS:
        for l in d['leviers']:
            ouvrants.setdefault(l, []).append(d['cle'])
    return {
        'ouvrants': ouvrants,
        'sans_dispositif': [l for l in LEVIERS_ATTENDUS if l not in ouvrants],
    }


def instruction():
    """CE QUI RESTE À ÉTABLIR — et c'est la prestation elle-même.

    Rend, pour chaque dispositif non instruit, la source primaire à consulter
    et ce qu'une source secondaire en dit. Cette liste n'est pas une dette
    technique à résorber discrètement : c'est le plan de travail d'une mission
    de conseil, et le fait de la publier dit au client ce qu'il achète.
    """
    reste = [d for d in DISPOSITIFS if d['etat'] != 'instruit']
    return {
        'a_instruire': [
            {'cle': d['cle'], 'nom': d['nom'], 'pays': d['pays'],
             'source': d['source'], 'annonce': d['annonce']}
            for d in reste
        ],
        'instruits': [d['cle'] for d in DISPOSITIFS if d['etat'] == 'instruit'],
        'part_instruite': round(
            100.0 * (len(DISPOSITIFS) - len(reste)) / len(DISPOSITIFS), 1),
    }


def montant(*_args, **_kwargs):
    """IL N'Y A PAS DE CALCUL DE MONTANT, ET CE N'EST PAS UN MANQUE.

    Cette fonction existe pour que la question reçoive une réponse explicite
    plutôt qu'un `AttributeError` : quelqu'un cherchera un jour à chiffrer une
    aide depuis ce module, et doit apprendre POURQUOI il n'y parviendra pas.

    Aucun taux, aucun seuil, aucun plafond n'a été relevé sur une source
    primaire. Les valeurs qui circulent viennent de notes de synthèse. Un taux
    d'aide faux entre dans un plan de financement, et un plan de financement
    faux passe devant un comité d'engagement. Tant qu'un dispositif n'est pas
    instruit, il n'a pas de montant — il a une source à consulter.
    """
    raise NotImplementedError(
        "Aucun montant n'est calculable : aucun dispositif n'est instruit sur "
        "source primaire. Voir valorisation_dc.instruction() pour la liste des "
        "sources a consulter, et la note du module pour la raison.")


def referentiel():
    """Tout ce que le module déclare, en une fois — pour une page ou un export."""
    return {
        'version': VERSION,
        'natures': NATURES,
        'instruction': INSTRUCTION,
        'dispositifs': [dict(d) for d in DISPOSITIFS],
        'leviers': leviers_couverts(),
        'reste_a_instruire': instruction(),
    }


def sante():
    """L'état du module, et ce qui cloche dedans.

    `problemes` n'est pas décoratif : une liaison vers un levier disparu rend
    `pour_levier` muet sans qu'aucune page ne change d'apparence.
    """
    problemes = []
    vus = set()
    for d in DISPOSITIFS:
        if d['cle'] in vus:
            problemes.append("cle en double : %s" % d['cle'])
        vus.add(d['cle'])
        if d['nature'] not in NATURES:
            problemes.append("%s : nature inconnue « %s »" % (d['cle'], d['nature']))
        if d['etat'] not in INSTRUCTION:
            problemes.append("%s : etat inconnu « %s »" % (d['cle'], d['etat']))
        if not d['leviers']:
            problemes.append("%s : relie a aucun levier — invisible depuis "
                             "l'ingenierie" % d['cle'])
        for l in d['leviers']:
            if l not in LEVIERS_ATTENDUS:
                problemes.append("%s : renvoie au levier inconnu « %s »"
                                 % (d['cle'], l))
        if d['etat'] != 'instruit' and not d.get('annonce'):
            problemes.append("%s : non instruit et sans mention d'origine"
                             % d['cle'])
        if not d.get('source'):
            problemes.append("%s : sans source primaire a consulter" % d['cle'])

    par_nature = {}
    for d in DISPOSITIFS:
        par_nature[d['nature']] = par_nature.get(d['nature'], 0) + 1

    couverture = leviers_couverts()
    return {
        'module': 'valorisation_dc',
        'version': VERSION,
        'dispositifs': len(DISPOSITIFS),
        'par_nature': par_nature,
        'pays': sorted({p.strip() for d in DISPOSITIFS
                        for p in d['pays'].split(',')}),
        'instruits': len([d for d in DISPOSITIFS if d['etat'] == 'instruit']),
        'a_instruire': len([d for d in DISPOSITIFS if d['etat'] != 'instruit']),
        'leviers_ouvrants': len(couverture['ouvrants']),
        'leviers_sans_dispositif': couverture['sans_dispositif'],
        'calcule_des_montants': False,
        'problemes': problemes,
    }
