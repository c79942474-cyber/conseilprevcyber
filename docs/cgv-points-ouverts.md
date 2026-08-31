# Conditions de vente — ce qui reste ouvert

Les conditions générales de vente sont **en vigueur depuis la version 2026-09-a**
(page `/cgv`). Ce document tient ce que la page publique ne doit pas porter : les
questions non tranchées et le risque des arbitrages pris. Un contrat n'argumente
pas contre lui-même ; le vendeur, lui, doit savoir où il est exposé.

Il est le pendant de `outils/verifier_cgv.py`, qui porte la grille de
confrontation au corpus de jurisprudence. Une règle d'essai vérifie que les huit
clés de ce document, les marques `<!-- verif:… -->` de `cgv.html` et la grille se
recouvrent exactement : aucune des trois ne peut bouger seule.

> **Aucune décision de justice n'a été lue à ce jour.** Les serveurs juridiques
> (LibreJustice, Legal Data Hunter) ont été refusés puis déconnectés de la
> session où ces conditions ont été rédigées. Rien de ce qui suit n'est tranché,
> et la mise en vigueur ne l'a pas tranché non plus.
>
>     python3 outils/verifier_cgv.py

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
| `retractation` | 5 | **Le plus exposé, et sans filet.** La renonciation vaut-elle pour un service fourni en continu, à durée indéterminée ? Rien n'absorbe le coup si la qualification tombe. |
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
