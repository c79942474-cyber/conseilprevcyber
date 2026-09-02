# Conditions de vente — ce qui reste ouvert

Les conditions générales de vente sont **en vigueur depuis la version 2026-09-a**
(page `/cgv`). Ce document tient ce que la page publique ne doit pas porter : les
questions non tranchées et le risque des arbitrages pris. Un contrat n'argumente
pas contre lui-même ; le vendeur, lui, doit savoir où il est exposé.

Il est le pendant de `outils/verifier_cgv.py`, qui porte la grille de
confrontation au corpus de jurisprudence. Une règle d'essai vérifie que les huit
clés de ce document, les marques `<!-- verif:… -->` de `cgv.html` et la grille se
recouvrent exactement : aucune des trois ne peut bouger seule.

> **Le corpus a été rouvert le 1er septembre 2026, et le premier point y est
> passé.** Les serveurs juridiques avaient été refusés puis déconnectés de la
> session où ces conditions ont été rédigées ; ils ont répondu depuis. Le point
> `retractation` — le plus exposé — a été confronté : voir « Ce que le corpus a
> répondu » plus bas. **Les sept autres restent non confrontés**, et la mise en
> vigueur ne les a pas tranchés.
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
| `plafond` | 10 | Le plafond au montant payé laisse-t-il subsister l'obligation essentielle ? |
| `adhesion` | 11 | Déséquilibre significatif dans un contrat non négocié, entre professionnels. |
| `abusives` | 9 | Suspension, absence de remboursement, modification unilatérale — désormais sous l'angle des articles 1171 C. civ. et L442-1 C. com., et non plus R212-1. |
| `competence` | 15 | L'attribution à Paris tient-elle face à un acheteur relevant de L221-3 ? |
| `disponibilite` | 7 | Moyens ou résultat : la qualification ne s'impose pas au juge. |
| `extraction` | 8 | L'interdiction suppose un investissement substantiel dans la base (art. L342-1 CPI). |
| `garantie` | 6 | Régime de 2021 : jurisprudence rare. Une liste vide sera une **réponse**, pas une validation. |

---

## Ce qui n'a pas été fait

- **Aucune relecture par un conseil.** Elle a été recommandée ; le vendeur a
  choisi de publier. C'est son document et son commerce.
- **Aucun médiateur n'a été inventé.** L'article 13 dit franchement que le
  dispositif est sans objet et pourquoi.
- **Les conditions de Sentinel** (`conseilprev/cgv.html`) décrivent une autre
  offre — abonnements, SEPA, prorata, résiliation — et mériteraient leur propre
  confrontation. Elles ne sont pas touchées.
