# Base Carbone® ADEME — fichier d'origine, conservé tel quel

`base_carbone_v22.csv` n'est pas de nous. Il est déposé ici **dans sa forme
d'origine**, sans retraitement, pour que les facteurs d'émission servis par ce
site soient **lus** et jamais recopiés dans du code — un facteur recopié cesse
d'être vérifiable le jour où sa source change.

- 8,5 Mo · 15 264 lignes · 67 colonnes · 31 pays pour « Électricité / mix moyen ».

## Pourquoi le fichier est aussi dans l'autre dépôt

L'autre site du cabinet (`conseilprev`) le porte également, et il y est en
outre accompagné des trois classeurs *Procédés* que ce site-ci n'exploite pas.
Les huit méga-octets sont donc dupliqués, **et c'est assumé** : les deux sites
sont déployés séparément, et une référence réglementaire disponible d'un seul
côté produirait exactement l'asymétrie entre les deux référentiels que le
module cherche à faire voir.

## Provenance et licence

- **Éditeur** : ADEME (Agence de la transition écologique).
- **Portail** : <https://base-empreinte.ademe.fr/>
- **Licence annoncée par l'éditeur** : Licence Ouverte / Open Licence (Etalab),
  qui impose la **mention de la paternité** — « Base Carbone® — ADEME ».
  `Base Carbone` est une marque déposée de l'ADEME : la citer telle quelle fait
  partie des conditions d'emploi.

> **Ce que nous n'avons pas vérifié.** Ces mentions reprennent ce que l'éditeur
> annonce sur son portail. Elles n'ont **pas** été revérifiées en ligne depuis
> l'environnement où ce dépôt est construit, qui n'a pas d'accès sortant. Avant
> toute rediffusion de ce fichier hors du présent dépôt, rouvrir le portail et
> lire les conditions en vigueur.

## Encodage — le piège

Le fichier est publié en **Windows-1252**, séparateur `;`, décimale française.
Le lire en UTF-8 ne lève pas toujours d'erreur : cela abîme silencieusement les
accents, et « Tchéquie » cesse alors de correspondre à « Tchéquie ».
`base_carbone.py` déclare donc l'encodage explicitement.

## Millésime — à lire avant de s'en servir

Les facteurs « Électricité / mix moyen » portent une validité de **décembre
2017** pour la plupart des pays, **décembre 2019** pour six d'entre eux, quand
`datacenter.INTENSITE_RESEAU` retient 2023-2024. Écart **médian de 37,7 %** sur
28 pays.

Ce sont les valeurs de l'ADEME qui **font foi** pour un bilan d'émissions
français (BEGES, art. L229-25 du code de l'environnement) ; ce ne sont **pas**
celles qui décrivent le réseau européen d'aujourd'hui. Le site sert donc les
deux et nomme l'usage de chacune — il ne substitue rien. Le raisonnement est
dans l'en-tête de `base_carbone.py` ; la confrontation est servie par
`/api/base-carbone?table=reseau`, et la réserve du pays étudié part avec chaque
étude.
