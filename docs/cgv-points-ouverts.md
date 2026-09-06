# Conditions de vente — ce qui reste ouvert

Les conditions générales de vente sont **en vigueur depuis la version 2026-09-a**
(page `/cgv`). Ce document tient ce que la page publique ne doit pas porter : les
questions non tranchées et le risque des arbitrages pris. Un contrat n'argumente
pas contre lui-même ; le vendeur, lui, doit savoir où il est exposé.

Il est le pendant de `outils/verifier_cgv.py`, qui porte la grille de
confrontation au corpus de jurisprudence. Une règle d'essai vérifie que les huit
clés de ce document, les marques `<!-- verif:… -->` de `cgv.html` et la grille se
recouvrent exactement : aucune des trois ne peut bouger seule.

> **Les huit points sont passés au corpus (6 septembre 2026).** Ce qu'il a
> répondu est consigné ci-dessous, point par point.
>
> **DEUX DEGRÉS, ET ILS NE VALENT PAS LA MÊME CHOSE.** Une décision *lue
> intégralement* est citée avec son motif ; une décision seulement *repérée*
> est nommée sans être citée. Les aperçus rendus par la recherche ne sont pas
> la position de la cour — ils sont écrits par une machine, ou tirés du passage
> où les mots-clés sont tombés, qui peut être l'argument d'une partie et non le
> jugement. **Rien ici n'est opposable tant que la décision n'est pas ouverte**,
> et le degré est dit à chaque fois.
>
> **Deux points ont donné un résultat qui change quelque chose** : `plafond`
> (l'article 10 réunit les trois facteurs qu'une cour a retenus pour écarter une
> clause identique) et `competence` (une cour d'appel juge que le renvoi de
> l'article L221-3 **ne porte pas** sur les clauses abusives — ce que l'article
> 15 supposait).
>
>     python3 outils/verifier_cgv.py

---

## Ce que le corpus a répondu — `retractation` (article 5)

**CJUE, 1re chambre, 9 juillet 2026, C-234/25** —
<https://librejustice.fr/decision/GiyKATM1OyqM>

La Cour dit pour droit, sur renvoi autrichien, que l'article 16, premier alinéa,
sous m), de la directive 2011/83, lu avec son article 2, point 11 :

> doit être interprété en ce sens que : la fourniture d'un service de streaming
> par lequel un consommateur peut accéder, au moyen d'un hyperlien ou d'une
> application numérique, à des données numériques stockées sur un serveur afin
> de les visionner en direct, à la demande, ou encore hors ligne après
> téléchargement sur un dispositif de mémoire propre, relève **non pas de la
> fourniture de « contenus numériques »** au sens de ces dispositions, **mais de
> la fourniture d'un « service numérique »** au sens de l'article 2, point 16,
> de ladite directive, **lorsque l'offre proposée par le professionnel concerné
> présente un caractère dynamique qui va au-delà de la seule mise à disposition
> stable et, le cas échéant, continue de contenus spécifiques**.

**POURQUOI CELA NOUS ATTEINT.** L'article 5 repose sur une renonciation au droit
de rétractation pour un contenu numérique fourni immédiatement — c'est
l'exception de l'article L221-28, 13°, du code de la consommation, qui transpose
l'article 16, m). Cette exception ne joue **que pour un contenu numérique**. Si
la prestation est un *service* numérique, elle ne joue pas : l'acheteur conserve
son droit de rétractation, et le vendeur n'a que l'indemnité proportionnelle de
l'article L221-25 (art. 14 § 3 de la directive), calculée *prorata temporis* ou
sur la valeur marchande de ce qui a été effectivement consommé (points 50 à 52
de l'arrêt).

**ET NOTRE OFFRE RESSEMBLE À CE QUE LA COUR DÉCRIT.** L'accès se fait par une
application, à des données stockées sur un serveur ; l'offre évolue — modules,
mises à jour, veille réglementaire, nouveaux contenus. C'est le « caractère
dynamique allant au-delà de la seule mise à disposition stable et continue de
contenus spécifiques » que l'arrêt retient pour écarter la qualification de
contenu numérique. La Cour laisse la vérification au juge du fond (point 45) ;
elle ne laisse pas le critère.

**DEUX RÉSERVES, ET ELLES COMPTENT.** La directive 2011/83 protège le
*consommateur*, et la vente est réservée aux professionnels depuis le recast
B2B. Le pont est l'article L221-3 du code de la consommation, qui étend la
protection au professionnel employant cinq salariés au plus et contractant hors
de son activité principale — c'est-à-dire exactement l'acheteur que l'article 15
et le point `competence` avaient déjà signalé. Pour tout autre acheteur
professionnel, l'arrêt ne s'applique pas.

**CE QUE CELA CHANGE, ET CE QUI RESTE À DÉCIDER.** La renonciation de l'article 5
n'est pas annulée : elle est **privée de son fondement pour les acheteurs
couverts par L221-3**. Trois voies, et le choix n'appartient pas à la machine :
soit l'article 5 réserve expressément le cas de L221-3 et accepte l'indemnité
proportionnelle pour ces acheteurs-là ; soit la vente exclut contractuellement
les professionnels de moins de six salariés, ce qui restreint le marché ; soit
l'arbitrage est maintenu en connaissance du risque, désormais chiffré par un
arrêt et non plus supposé.

---

---

## Les arbitrages pris, et ce qu'ils coûtent

### 1. Aucun remboursement commercial (article 5)

**Décidé** : le vendeur n'accorde aucun remboursement de faveur en sus du droit
de rétractation.

**Le risque.** L'article 5 ne repose plus que sur la renonciation de l'article
L221-28. Le 13° vise un *contenu* numérique, le 1° un service *pleinement
exécuté* ; un accès à durée indéterminée fourni de manière continue n'entre
parfaitement dans ni l'un ni l'autre. Si la qualification était écartée, un
acheteur relevant de l'article L221-3 pourrait obtenir le remboursement dans les
quatorze jours malgré la case. **Exposition bornée** : un paiement unique,
quatorze jours, aucun abonnement.

### 2. Vente réservée aux professionnels (chapeau, articles 1, 5, 6, 13, 15)

**Décidé** : faute d'adhésion à un dispositif de médiation de la consommation,
l'offre n'est pas ouverte aux consommateurs.

**Ce qui la rend effective, et non décorative** : l'organisation est exigée à
l'inscription (`auth.api_register`), et une déclaration de qualité
professionnelle est exigée **à la vente**, refusée côté serveur si elle manque,
et tracée (`paiement.qualite` au journal d'audit).

**Le risque.** La restriction ne supprime pas la protection : l'article L221-3
l'étend au professionnel de **cinq salariés ou moins** contractant hors de son
activité principale. C'est une part réelle des acheteurs d'un outil de
conformité. La renonciation et sa confirmation sur support durable restent donc
nécessaires — elles servent exactement ceux-là.

**Si l'offre s'ouvrait un jour aux consommateurs**, il faudrait adhérer à un
médiateur **avant**, et rouvrir les articles 5, 6, 13 et 15.

### 3. Cessation du service : préavis de trois mois, aucun remboursement (article 7)

**Décidé** : trois mois de préavis par courriel, l'accès restant ouvert pendant
ce délai ; aucun remboursement.

**Le risque, à écrire plutôt qu'à taire.** Encaisser pour une durée
indéterminée puis fermer avec trois mois de préavis et sans contrepartie est le
type de stipulation qu'un juge peut regarder comme créant un **déséquilibre
significatif** (article 1171 du code civil, et article L442-1 du code de commerce
entre professionnels). Le préavis atténue le grief, il ne l'efface pas. Un
acheteur qui aurait payé quelques semaines avant l'annonce est celui dont la
situation se défend le moins bien.

### 4. Plafond de responsabilité au montant payé (article 10)

**Décidé** : la responsabilité ne peut excéder le montant effectivement payé.

**Le risque.** Une clause limitative qui priverait de sa substance l'obligation
essentielle est réputée non écrite (article 1170 du code civil) — la réserve est
écrite dans l'article. Pour une vente de ce montant, un plafond égal au prix
reste défendable ; il le serait moins si le prix devenait symbolique au regard de
ce que la plateforme sert à décider.

---

## Les huit points à confronter au corpus

Les clés sont celles de `outils/verifier_cgv.py:POINTS` et des marques dans
`cgv.html`.

| clé | article | ce qui se joue |
|---|---|---|
| `retractation` | 5 | **CONFRONTÉ le 1er septembre 2026 — voir ci-dessus.** CJUE C-234/25 : un service accessible par application, à l'offre dynamique, n'est pas un « contenu numérique ». La renonciation perd son fondement pour les acheteurs relevant de L221-3. |
| `plafond` | 10 | **CONFRONTÉ le 6 septembre 2026 — décision LUE.** CA Limoges 21/00432 : clause écartée (art. 1170) sur trois facteurs, dont deux acquis à l'article 10. Deux décisions en sens contraire repérées, non lues. |
| `adhesion` | 11 | **CONFRONTÉ le 6 septembre 2026 — décisions repérées, non lues.** Le corpus juge des CLAUSES (art. 1171), jamais la qualification d'adhésion en elle-même. CA Versailles 22/03581 dit comment se mesure le « significatif ». |
| `abusives` | 9 | **CONFRONTÉ le 6 septembre 2026 — décisions repérées, non lues.** TJ Paris 21/08725 : la clôture du compte est admise, la conservation du solde est abusive. Miroir direct de l'article 9. |
| `competence` | 15 | **CONFRONTÉ le 6 septembre 2026 — décision LUE.** CA Paris 25/19484 : le renvoi de L221-3 NE PORTE PAS sur les clauses abusives — ce que l'article 15 supposait. La clause tombe sur l'art. 48 CPC, donc sur l'écran de caisse. |
| `disponibilite` | 7 | **CONFRONTÉ le 6 septembre 2026 — décisions repérées, non lues.** L'obligation de moyens est retenue (Cass. com. 19-26.100), mais elle est INDIFFÉRENTE quand la faute est une erreur d'exécution et non l'objectif manqué. |
| `extraction` | 8 | **CONFRONTÉ le 6 septembre 2026 — décisions repérées, non lues.** TJ Paris 21/09261 : extraction substantielle établie, protection REFUSÉE faute d'atteinte aux investissements. L'investissement se prouve, il ne se réclame pas. |
| `garantie` | 6 | **CONFRONTÉ le 6 septembre 2026 — AUCUNE DÉCISION TROUVÉE.** Le corpus ne rend rien qui applique L224-25-12 s. à un service numérique. C'est une réponse, pas une validation : l'article 6 est écrit sur un texte non éprouvé. |

---

## Ce qui n'a pas été fait

- **Aucune relecture par un conseil.** Elle a été recommandée ; le vendeur a
  choisi de publier. C'est son document et son commerce.
- **Aucun médiateur n'a été inventé.** L'article 13 dit franchement que le
  dispositif est sans objet et pourquoi.
- **Les conditions de Sentinel** (`conseilprev/cgv.html`) décrivent une autre
  offre — abonnements, SEPA, prorata, résiliation — et mériteraient leur propre
  confrontation. Elles ne sont pas touchées.

---

# Ce que le corpus a répondu — les sept autres points (6 septembre 2026)

## `plafond` — article 10, plafond de responsabilité · **LU INTÉGRALEMENT**

**Cour d'appel de Limoges, chambre économique et sociale, 15 juin 2022, 21/00432** —
<https://librejustice.fr/decision/j88xVqSRtq1P>

Prestataire informatique, perte des données d'un client lors d'une migration.
La cour déclare **non écrites** les clauses limitatives, au visa de l'article
1170 du code civil, et retient **trois facteurs** :

> « les clauses limitatives d'indemnisation en cause figurent dans les
> conditions générales des contrats, **non négociées** […] et **non
> négociables**, s'agissant de contrats d'adhésion. Par ailleurs ces plafonds
> d'indemnisation, qui **ne trouvent aucune contrepartie particulière** […]
> s'appliquent **à toutes causes de préjudices confondues** […] Or il s'agit
> d'une **indemnisation dérisoire** »

Et, sur l'argument que le vendeur serait tenté d'opposer :

> « le caractère dérisoire de l'indemnisation **ne s'apprécie pas à l'aune du
> préjudice potentiellement le plus extrême** »

**Ce que cela dit de l'article 10.** Les deux premiers facteurs lui sont
acquis : des conditions générales publiées sur un site sont par construction
non négociées, et le plafond n'a aucune contrepartie. Le troisième est moins
défavorable — le plafond de CONSEILPREV est « le montant effectivement payé au
titre de la commande en cause », plus étroit que les six mois de redevances de
l'espèce — mais reste un plafond global. La réserve déjà écrite à l'article 10
(« cette limitation ne joue pas lorsqu'elle priverait de sa substance
l'obligation essentielle ») est donc **la bonne réserve** ; ce que la décision
apprend, c'est qu'elle sera lue par un juge et non par le rédacteur.

**Deux décisions en sens contraire, REPÉRÉES et non lues** — elles montrent
qu'un plafond peut tenir, et il faut les ouvrir avant de conclure :
- Cour de cassation, com., 29 juin 2010, 09-11.841 (Faurecia / Oracle),
  **publié au bulletin** — <https://librejustice.fr/decision/UiUYEDBsvT__>
- Cour d'appel de Douai, 24 avril 2025, 23/00858 (incendie du centre de données
  OVH) — <https://librejustice.fr/decision/cnbUnskzeTMv>

---

## `competence` — article 15, juridiction · **LU INTÉGRALEMENT**

**Cour d'appel de Paris, pôle 5 ch. 11, 26 juin 2026, 25/19484** —
<https://librejustice.fr/decision/W7TkevKXwF76>

**CE POINT CONTREDIT UNE HYPOTHÈSE DE L'ARTICLE 15.** Une SARL de moins de cinq
salariés invoquait l'article L221-3 pour se prévaloir de la présomption de
clause abusive de l'article R212-1 1°. La cour écarte le raisonnement :

> « la présomption des clauses abusives irréfragablement acquise en vertu de
> l'article R. 212-1 1° **n'entre pas dans le champ d'application de l'article
> L. 221-3** limité aux dispositions des sections 2, 3, 6 du chapitre relatif
> aux "Contrats conclus à distance et hors établissement" »

Autrement dit : le renvoi de L221-3 porte sur les règles des contrats à
distance — information précontractuelle, rétractation — **pas sur le régime
des clauses abusives**. L'article 15 s'ancre sur R212-2 en supposant qu'il
protège le professionnel de L221-3 ; cette cour dit le contraire.

**La clause est pourtant tombée — sur un autre fondement, et il est
opérationnel :** l'article 48 du code de procédure civile, faute d'être « très
apparente ».

> « l'accumulation en petits caractères ne permet pas de distinguer de manière
> apparente la clause […] la procédure de cette signature n'est pas décrite, ce
> dont il résulte qu'il ne peut non plus être apprécié dans quelles conditions
> la clause est apparue sur écran électronique »

**Ce que cela commande.** L'opposabilité de l'article 15 à un client
professionnel se joue **à l'écran de la caisse**, pas dans la rédaction : ce qui
est montré au moment de l'acceptation, et ce que le service peut prouver avoir
montré. C'est une question d'interface et de journal, pas de clause.

---

## `abusives` — articles 7, 9 et 14 · **REPÉRÉES, non lues**

- **Tribunal judiciaire de Paris, 4 décembre 2025, 21/08725** (opérateur de
  paris en ligne) — <https://librejustice.fr/decision/84gSQXk_2vPA> — la
  clôture du compte pour fraude est admise, mais la clause permettant de
  **conserver le solde** est écartée comme abusive et le solde restitué. C'est
  le miroir de l'article 9 (non-remboursement en cas de suspension).
- **Cour d'appel de Grenoble, 26 mars 2026, 24/00805** —
  <https://librejustice.fr/decision/QsI4gi0sT05Z> — durée et résiliation
  anticipée jugées créer un déséquilibre significatif (art. 1171).
- **Cour d'appel de Versailles, 16 janvier 2024, 22/03581** —
  <https://librejustice.fr/decision/V_fegUgc8OwO> — **en sens inverse** : un
  déséquilibre existe mais n'est pas « significatif au regard de l'économie
  générale du contrat ». À ouvrir en premier : c'est la décision qui dit
  comment le seuil se mesure.

---

## `adhesion` — articles 8 à 11 · **REPÉRÉES, non lues**

Le corpus de l'article 1171 est le même que ci-dessus :

- **Cour d'appel de Versailles, 16 janvier 2024, 22/03581** —
  <https://librejustice.fr/decision/V_fegUgc8OwO>
- **Cour d'appel de Grenoble, 26 mars 2026, 24/00805** —
  <https://librejustice.fr/decision/QsI4gi0sT05Z>
- **Cour d'appel de Limoges, 15 juin 2022, 21/00432** —
  <https://librejustice.fr/decision/j88xVqSRtq1P> (celle-là a été lue)

Rien n'a été trouvé qui traite d'un contrat d'adhésion de service en ligne **en
tant que tel** ; ce qui se juge est toujours une clause précise, pas la
qualification d'adhésion. C'est un enseignement en soi : l'article 1110 sert de
porte d'entrée, l'article 1171 fait le travail.

---

## `disponibilite` — article 7 · **REPÉRÉES, non lues**

- **Cour de cassation, com., 17 novembre 2021, 19-26.100** —
  <https://librejustice.fr/decision/2byYICBvd_YC> — obligation de **moyens**
  retenue pour un prestataire informatique ; pourvoi rejeté.
- **Cour d'appel de Douai, 24 avril 2025, 23/00858** (OVH) —
  <https://librejustice.fr/decision/cnbUnskzeTMv> — manquement retenu, mais
  indemnisation ramenée à 1 800,48 € par les clauses limitatives.
- **Tribunal judiciaire de Versailles, 11 avril 2025, 24/00224** —
  <https://librejustice.fr/decision/p673I3jwHW1o> — inaccessibilité totale des
  données pendant deux périodes : 16 000 € de dommages-intérêts.

La qualification « obligation de moyens » de l'article 7 est donc conforme à ce
que les juges retiennent — mais Limoges rappelle qu'elle est **indifférente**
quand la faute reprochée n'est pas de n'avoir pas atteint l'objectif, mais
d'avoir commis une erreur dans l'exécution.

---

## `extraction` — article 8 · **REPÉRÉES, non lues**

- **Cour de cassation, 1re civ., 5 octobre 2022, 21-16.307**, **publié au
  bulletin** — <https://librejustice.fr/decision/7QssPXDfPuyK>
- **Cour de cassation, 1re civ., 15 octobre 2025, 23-23.167** —
  <https://librejustice.fr/decision/_BmsEJA1hsNu>
- **Tribunal judiciaire de Paris, 21 février 2025, 21/09261** —
  <https://librejustice.fr/decision/-BXPR5iMofYY> — **rejet** : extraction
  substantielle établie, mais **pas d'atteinte aux investissements**.

L'enseignement est net et il coûte : la protection du producteur de base de
données ne se réclame pas, elle **se prouve**, par la démonstration d'un
investissement substantiel dans la constitution, la vérification ou la
présentation. L'article 8 interdit l'extraction ; il ne dispense pas d'établir
l'investissement le jour où il faudra l'opposer.

---

## `garantie` — article 6 · **AUCUNE DÉCISION TROUVÉE**

La recherche sur la garantie légale de conformité des **contenus et services
numériques** (art. L224-25-12 et suivants, transposition de la directive
2019/770) ne rend, dans le corpus interrogé, **aucune décision qui l'applique à
un service numérique**. Les résultats portent sur la garantie des **biens**
(L217-3 et suivants) : véhicule d'occasion, hotte, tablette.

**« Aucune décision trouvée » n'est pas « aucun risque ».** Le régime est entré
en vigueur le 1er janvier 2022 et la jurisprudence n'a pas eu le temps de se
former. L'article 6 est donc écrit sur un texte **non encore éprouvé par les
juges** — c'est la situation la moins confortable de toutes, parce qu'elle ne
donne aucun repère sur la manière dont il sera lu.

---

## Ce qui reste à faire

1. **Ouvrir les décisions repérées** — Versailles 22/03581 et Douai 23/00858 en
   premier : la première dit comment se mesure le « significatif », la seconde
   est le cas le plus proche du nôtre où le plafond a TENU.
2. ~~**Trancher l'article 15.**~~ **TRANCHÉ le 6 septembre 2026** : le renvoi
   de L221-3 ne porte que sur les sections 2, 3 et 6 du chapitre Ier, donc ni
   sur les clauses abusives ni sur les options de compétence. L'ancrage sur
   R212-2 tombe ; l'opposabilité se joue sur l'article 48 CPC, donc sur ce que
   l'écran de caisse montre et sur ce que le service peut prouver avoir montré.
   Voir « Les seize articles cités », constat B.
3. **Décider pour l'article 10** : soit assumer le plafond tel quel en sachant
   que deux des trois facteurs de Limoges lui sont acquis, soit lui donner une
   contrepartie explicite — c'est ce qui a sauvé la clause dans Faurecia.


# Les seize articles cités, ouverts un par un (6 septembre 2026)

Le document annonçait « treize articles cités ». Il y en avait **quinze**, et la
vérification en a ajouté un seizième — L221-1, sans lequel la condition centrale
n'était pas lisible. Chacun a été ouvert sur librejustice.fr dans **sa version
en vigueur** ce jour-là. La table vit dans `cgv_articles.py` ; ce qui suit en est
le rendu, et une règle refuse que les deux divergent.

**Deux phrases sur seize étaient fausses, et les deux au même endroit** : le
renvoi de l'article L221-3. Elles allaient en sens contraire — l'une promettait
à trop peu de monde, l'autre promettait ce que la loi ne donne pas — mais c'est
le même défaut : un renvoi lu de mémoire au lieu d'être ouvert.

| article | code | en vigueur depuis | portée du renvoi L221-3 | ce que la page en tire |
|---|---|---|---|---|
| [1110](https://librejustice.fr/texte/code-civil/1110) | civil | 2018-10-01 | sans objet | la qualification que la page se donne à l'article 1 |
| [1127-1](https://librejustice.fr/texte/code-civil/1127-1) | civil | 2016-10-01 | sans objet | l'accessibilité permanente et imprimable, article 1 — le premier alinéa, seul non dérogeable entre professionnels (1127-3) |
| [1127-2](https://librejustice.fr/texte/code-civil/1127-2) | civil | 2016-10-01 | sans objet | le déroulement de la commande, article 4 — le vendeur s'y tient alors que 1127-3 lui permettrait d'y déroger |
| [1170](https://librejustice.fr/texte/code-civil/1170) | civil | 2016-10-01 | sans objet | la limite du plafond, article 10 |
| [1171](https://librejustice.fr/texte/code-civil/1171) | civil | 2018-10-01 | sans objet | la limite générale posée à l'article 10 |
| [1190](https://librejustice.fr/texte/code-civil/1190) | civil | 2016-10-01 | sans objet | l'interprétation contre le vendeur, article 1 |
| [1604](https://librejustice.fr/texte/code-civil/1604) | civil | 1804-03-21 | sans objet | l'obligation de délivrer un accès conforme, article 6 |
| [1641](https://librejustice.fr/texte/code-civil/1641) | civil | 1804-03-16 | sans objet | la garantie des vices cachés, article 6 |
| [L442-1](https://librejustice.fr/texte/code-de-commerce/l442-1) | commerce | 2026-08-20 | sans objet | le rappel joint à l'article 1171, article 10 |
| [L221-1](https://librejustice.fr/texte/code-de-la-consommation/l221-1) | conso. | 2022-05-28 | sans objet | la condition que le chapeau et l'article 5 ont cessé de taire |
| [L221-18](https://librejustice.fr/texte/code-de-la-consommation/l221-18) | conso. | 2016-07-01 | étendu | le délai de l'article 5 |
| [L221-25](https://librejustice.fr/texte/code-de-la-consommation/l221-25) | conso. | 2022-05-28 | étendu | le premier des deux consentements recueillis à la caisse |
| [L221-28](https://librejustice.fr/texte/code-de-la-consommation/l221-28) | conso. | 2022-05-28 | étendu | le fondement de la renonciation, et le risque nommé à l'article 5 |
| [L221-3](https://librejustice.fr/texte/code-de-la-consommation/l221-3) | conso. | 2016-07-01 | sans objet | la réserve annoncée en tête, et le bénéficiaire des articles 5 et 6 |
| [L224-25-12](https://librejustice.fr/texte/code-de-la-consommation/l224-25-12) | conso. | 2021-10-01 | **non étendu** | la garantie de l'article 6, désormais donnée par le vendeur et non par la loi |
| [L611-1](https://librejustice.fr/texte/code-de-la-consommation/l611-1) | conso. | 2016-07-01 | **non étendu** | l'article 13, qui écarte la médiation faute de consommateurs |

## Constat A — L221-3 exige un contrat conclu **hors établissement**

Le chapeau et l'article 5 énonçaient deux conditions (cinq salariés ou moins ;
objet hors de l'activité principale) et **taisaient la première** : que le
contrat ait été conclu hors établissement. Le texte est sans ambiguïté — « sont
étendues aux contrats conclus **hors établissement** entre deux professionnels »
— et l'article L221-1, I, 2° réserve cette qualification aux contrats conclus en
**présence physique simultanée** des parties, ou à distance immédiatement après
une sollicitation personnelle intervenue dans un tel lieu.

Or ce site vend **en ligne**, ce qui est un contrat *à distance* au sens du
L221-1, I, 1°. La qualification n'est donc jamais acquise du seul fait de la
souscription. Elle reste possible — un prospect rencontré, sollicité en personne,
qui souscrit dans la foulée relève du b) — mais elle doit être établie.

**Ce que le corpus répond, décisions LUES intégralement :**

- [Cour de cassation, chambre commerciale, 4 septembre 2024, n° 23-16.886](https://librejustice.fr/decision/6mme57BKnDNb)
  casse le jugement d'un tribunal de commerce qui avait annulé un contrat
  souscrit « par voie dématérialisée à distance » entre deux professionnels.
  Deux motifs, et les deux nous concernent. Le juge devait rechercher « si les
  parties avaient été physiquement et simultanément présentes, soit au moment
  de la sollicitation, soit au moment de la conclusion » avant d'appliquer
  L221-3 (§ 8). Et surtout : « **le contrat litigieux ayant été conclu entre
  deux professionnels, la société Boole ne pouvait bénéficier des dispositions
  particulières applicables aux contrats à distance** » (§ 12).
- [Cour d'appel de Lyon, 3e chambre A, 13 novembre 2025, n° 22/01141](https://librejustice.fr/decision/amZamF72UKR5)
  montre le régime appliqué correctement : la cour reprend les trois conditions
  une par une — hors établissement, objet étranger à l'activité de caviste,
  moins de cinq salariés à la date du contrat — avant d'étendre au
  professionnel le délai de rétractation prolongé.

**Corrigé.** Le chapeau et l'article 5 énoncent les trois conditions et disent
qu'elles se cumulent ; l'article 5 nomme l'arrêt.

**Ce que cela coûte.** Le droit de rétractation de quatorze jours ne sera dû, en
pratique, qu'à l'acheteur rencontré physiquement avant la souscription. Pour tous
les autres, la vente en ligne entre professionnels n'ouvre rien. C'est une
réduction réelle de ce que le document promettait — et c'est la loi. **Rien
n'interdit au vendeur de l'accorder quand même**, contractuellement, à tout
acheteur de cinq salariés ou moins : c'est une décision commerciale, elle n'a pas
été prise, et elle contredirait l'arbitrage du 31 août 2026 qui a écarté tout
remboursement de faveur.

## Constat B — le renvoi n'atteint pas la garantie du numérique

L221-3 étend « les dispositions des **sections 2, 3, 6 du présent chapitre** ».
Savoir ce que portent ces numéros n'est pas devinable : il a fallu lire
l'arborescence du code, article témoin par article témoin.

| section du chapitre Ier | intitulé | témoin | étendue ? |
|---|---|---|---|
| 2 | Obligation d'information précontractuelle | L221-5 | oui |
| 3 | Dispositions particulières applicables aux contrats conclus hors établissement | L221-10 | oui |
| 4 | Dispositions particulières applicables aux contrats conclus à distance | L221-13 | **non** |
| 6 | Droit de rétractation applicable aux contrats conclus à distance et hors établissement | L221-18 | oui |

Le résultat est cohérent, et c'est ce qui le rend crédible : **le législateur a
étendu au petit professionnel l'appareil « hors établissement » (sections 2, 3
et 6) et rien de l'appareil « à distance » (section 4).** Les constats A et B
n'en font donc qu'un.

Conséquence : l'article **L224-25-12** — la garantie légale de conformité du
contenu et du service numériques — est au **chapitre IV** (« Règles spécifiques
à des contrats ayant un objet particulier », section 2 bis, sous-section 4). Le
renvoi de L221-3 ne l'atteint pas. L'article 6 l'annonçait pourtant comme un dû
légal.

**Corrigé, et l'arbitrage est pris.** La garantie est **maintenue**, mais donnée
par le vendeur *par le contrat* et non par la loi — le document l'avait promise
publiquement, la retirer en silence aurait été pire que l'erreur. Sa portée suit
le texte vérifié : pour un accès fourni de manière continue, le vendeur répond
des défauts qui apparaissent au cours de la période de fourniture, et non
pendant deux ans.

## Ce que la vérification a AUSSI tranché

- **L'article 1604 ne dit pas ce que la page lui fait dire — et la page a
  pourtant raison.** Le texte définit la délivrance comme « le transport de la
  chose vendue en la puissance et possession de l'acheteur » : la *conformité*
  n'y figure pas. Elle est jugée. [Cass. 1re civ., 13 février 2019,
  n° 17-12.580](https://librejustice.fr/decision/xv1yLXbTyhJ5), au visa de l'article 1604 : « **manque à son obligation de
  délivrance le vendeur qui livre une chose non conforme à la chose convenue** ».
  La fiche de l'article porte ce lien, parce qu'une proposition jurisprudentielle
  et une proposition légale ne se vérifient pas de la même façon.
- **Le droit de rétractation EST étendu**, contrairement à ce qu'on pouvait
  craindre en lisant « sections 2, 3, 6 » : les articles L221-18 à L221-28 sont
  en **section 6**, et non dans une section 4 qui aurait été exclue.
- **L'article 15 (juridiction) trouve sa réponse.** Le renvoi de L221-3 ne porte
  ni sur les clauses abusives (livre II, titre Ier) ni sur les options de
  compétence du consommateur : elles sont hors du chapitre Ier. La rédaction
  actuelle reste juste parce qu'elle est conditionnelle — « il conserve les
  options de compétence que la loi lui réserve » — mais l'ancrage sur R212-2
  était à revoir, et il l'est : l'opposabilité se joue sur l'article 48 CPC.
- **La reconnaissance recueillie à la caisse est écrite pour le 13°, et ne peut
  pas l'être pour le 1°.** L221-25 fait reconnaître au client qu'il perdra son
  droit « après [que le professionnel] aura **entièrement exécuté** le
  contrat » ; un accès à durée indéterminée fourni en continu n'est jamais
  entièrement exécuté. La case dit « une fois l'accès ouvert », ce qui est la
  logique du 13° (perte à l'ouverture de la fourniture). **On ne peut pas
  couvrir les deux qualifications avec une seule formule** : le risque nommé à
  l'article 5 ne peut donc pas être couvert par une rédaction plus prudente. Il
  s'assume ou il se supprime.

## Ce que la vérification n'a PAS fait

Elle n'a pas jugé les clauses. Un article exact peut porter une clause nulle ;
c'est l'objet de `outils/verifier_cgv.py` et de la section précédente. Ici on a
seulement établi que les seize textes cités existent, dans cette version, et
disent ce que la page leur fait dire.
