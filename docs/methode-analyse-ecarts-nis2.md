# Méthode CONSEILPREV — Analyse d'écarts NIS2 (IT & OT)

Fiche méthode interne (anonymisée — aucune donnée client). Sert de trame aux analyses
d'écarts NIS2 et aux plans de mise en conformité produits par le générateur de
livrables. À charger dans la base de connaissance en visibilité **interne**, thème
« NIS2 ». Contenu paraphrasé : ne jamais reproduire le texte de la directive — citer
les références (directive (UE) 2022/2555, transposition française pilotée par l'ANSSI).

## Étape 1 — Assujettissement

- Déterminer le régime : **entité essentielle** (grandes entreprises des secteurs
  hautement critiques — énergie, transports, banque, santé, eau, infrastructure
  numérique, gestion des services TIC, administration, spatial) ou **entité
  importante** (moyennes entreprises de ces secteurs, et moyennes/grandes des autres
  secteurs critiques — chimie, agroalimentaire, fabrication, déchets, postes,
  numérique, recherche).
- Seuils simplifiés : moyenne entreprise ≥ 50 salariés ou > 10 M€ de CA ; grande
  ≥ 250 salariés ou > 50 M€. Attention aux cas particuliers désignés sans condition
  de taille et à l'entraînement par les donneurs d'ordre (chaîne d'approvisionnement).
- Vérifier l'enregistrement auprès de l'autorité nationale (France : ANSSI,
  portail MonEspaceNIS2) et les obligations déclaratives associées.
- Sortie : fiche d'assujettissement motivée (régime, secteur, seuils, cas particuliers).

## Étape 2 — Périmètre d'analyse

- Couvrir IT **et** OT : sites industriels, filiales, services externalisés.
- Recenser les systèmes critiques pour la fourniture du service (dépendances incluses).
- Tracer les interconnexions et les responsabilités (RACI par domaine).

## Étape 3 — Écarts par famille d'exigences

Évaluer, par famille de mesures de gestion des risques (approche « tous risques »,
proportionnée), l'existant, l'écart et la cible :

1. **Politiques** d'analyse de risques et de sécurité des SI.
2. **Gestion des incidents** (détection, qualification, réponse).
3. **Continuité d'activité** : sauvegardes, reprise, gestion de crise.
4. **Chaîne d'approvisionnement** : sécurité des relations fournisseurs et prestataires.
5. **Acquisition, développement et maintenance** : exigences de sécurité, gestion des
   vulnérabilités et des correctifs.
6. **Évaluation d'efficacité** des mesures (audits, indicateurs, revues).
7. **Hygiène informatique** de base et formation.
8. **Cryptographie** : politiques d'usage et de chiffrement.
9. **Ressources humaines, contrôle d'accès et gestion des actifs**.
10. **Authentification multifacteur** et communications sécurisées.

Ajouter la **gouvernance** : approbation des mesures par les organes de direction,
supervision de la mise en œuvre, formation des dirigeants — leur responsabilité est
engagée en cas de manquement.

Notation recommandée : conforme / partiel / absent / non applicable (motivé), avec
preuve à l'appui pour chaque constat. Aucun constat sans preuve.

## Étape 4 — Notification d'incidents

- Vérifier la capacité à tenir les délais : **alerte précoce ≤ 24 h** après
  connaissance d'un incident important, **notification ≤ 72 h** (évaluation initiale),
  **rapport final ≤ 1 mois**. Information des clients affectés le cas échéant.
- Points de contrôle : définition interne de l'« incident important », astreinte,
  canaux de déclaration à l'autorité, modèles de notification prêts, exercices.

## Étape 5 — Spécificité OT : correspondance IEC 62443

Pour le périmètre industriel, adosser chaque écart à la réponse technique IEC 62443 :
zones & conduits et SL-T (analyse de risques), SR de la 62443-3-3 (détection,
contrôle d'accès, MFA), 62443-2-4 (prestataires), 62443-4-1 (développement sécurisé),
62443-4-2 (composants), audit SL-A vs SL-T (évaluation d'efficacité). NIS2 dit quoi ;
l'IEC 62443 dit comment, côté OT.

## Étape 6 — Plan de mise en conformité

- Prioriser par l'exposition réelle et la criticité pour la continuité du service
  (pas uniquement par la facilité de mise en œuvre).
- Structurer en jalons datés avec responsables ; distinguer vite-fait (quick wins),
  chantiers structurants et dépendances fournisseurs.
- Indicateurs de suivi : taux de couverture par famille d'exigences, délais de
  notification testés en exercice, MTTP sur les correctifs critiques, taux de
  comptes avec MFA, couverture de la supervision.

## Sanctions (repères, paraphrasés)

Jusqu'à 10 M€ ou 2 % du CA annuel mondial (montant le plus élevé) pour les entités
essentielles ; 7 M€ ou 1,4 % pour les entités importantes ; injonctions et astreintes ;
possibilité de suspension de dirigeants pour les EE. À rappeler dans la synthèse
direction pour dimensionner l'effort.

## Points d'attention (retours d'expérience)

- L'assujettissement se juge au niveau groupe ET filiale : une filiale peut être
  concernée seule.
- Le périmètre OT est souvent oublié des analyses NIS2 « IT only » — c'est pourtant
  là que se joue la continuité du service pour un industriel.
- Les délais 24 h/72 h ne se tiennent pas sans exercice préalable : tester le
  dispositif de notification au moins une fois par an.
- La chaîne d'approvisionnement est le chantier le plus long : commencer par les
  prestataires ayant un accès distant aux systèmes critiques.
- Ne jamais promettre « la conformité » comme un état binaire : c'est une trajectoire
  documentée, proportionnée et démontrable.
