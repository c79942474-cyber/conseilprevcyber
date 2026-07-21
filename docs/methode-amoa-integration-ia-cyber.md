# Méthode CONSEILPREV — AMOA intégration IA & Cyber SI

Fiche méthode interne (anonymisée — aucune donnée client). Sert de trame aux notes de
cadrage, propositions et livrables des programmes de cyberdéfense augmentée par l'IA,
en environnement régulé (assurance, banque — DORA) comme en environnement industriel
(NIS2, IEC 62443). À charger dans la base de connaissance en visibilité **interne**,
thème « AMOA SI Industriel ».

## Problème type

L'IA accélère la découverte (et l'exploitation) de vulnérabilités : le volume et la
vitesse dépassent les capacités de traitement historiques des équipes. L'organisation
doit passer d'une posture réactive à une posture proactive et anticipative, sans
désorganiser les initiatives existantes (SOC, gestion des vulnérabilités, projets IT).

## Structuration du programme — cinq chantiers

### 1. Cartographie de l'exposition du SI
- Recenser l'ensemble des applications exposées sur internet (périmètre groupe et filiales).
- Qualifier chaque actif : criticité métier, données traitées, surface d'attaque, dépendances.
- Établir la priorité de traitement des remédiations à partir de l'exposition réelle
  (et non du seul score CVSS) : exploitabilité, exposition, criticité, compensations.
- Livrables : inventaire d'exposition consolidé, matrice de priorisation, tableau de bord.

### 2. Chaînes de patching & capacité de remédiation
- Évaluer la capacité du SI et des équipes (DSI, filiales) à absorber une vague de
  vulnérabilités critiques : goulots d'étranglement, fenêtres de maintenance, environnements
  de test, dépendances éditeurs.
- Cartographier les chaînes de patching de bout en bout (veille → qualification → test →
  déploiement → vérification) et mesurer leurs délais réels.
- Définir des scénarios de charge (vague massive) et le mode dégradé associé.
- Livrables : diagnostic de capacité, plan d'industrialisation, procédure « vague critique ».

### 3. SOC & cyberdéfense augmentée par l'IA
- Adapter les moyens humains et logiciels de détection et de réponse à l'accélération
  des découvertes de vulnérabilités.
- Évaluer les cas d'usage IA côté défense : tri des alertes, corrélation, priorisation
  des vulnérabilités, aide à la réponse (playbooks assistés), chasse proactive.
- Cadrer la gouvernance de ces usages : supervision humaine, journalisation, limites
  (AI Act — transparence ; RGPD — minimisation), critères d'escalade.
- Livrables : cible SOC augmenté (organisation + outillage), trajectoire, indicateurs.

### 4. Gouvernance & gestion de crise
- Mettre en place une gouvernance adaptée à des crises rapides et systémiques :
  instances resserrées, délégations pré-établies, seuils de déclenchement clairs.
- Articuler crise cyber et continuité d'activité (métiers, filiales, communication).
- Entraîner le dispositif : exercices sur scénario « vague de vulnérabilités critiques ».
- Livrables : dispositif de crise documenté, fiches réflexes, programme d'exercices.

### 5. Anticipation & stratégie (posture proactive)
- Passer du réactif au proactif : veille augmentée, anticipation des usages offensifs
  de l'IA, évaluation continue de la surface d'attaque.
- Utiliser l'IA pour anticiper les menaces liées à l'IA (analyse de tendances,
  priorisation prédictive) — toujours sous supervision humaine.
- Inscrire la trajectoire dans le cadre réglementaire applicable (DORA pour le secteur
  financier ; NIS2 ; AI Act pour les usages d'IA).
- Livrables : stratégie d'anticipation, feuille de route pluriannuelle, revue périodique.

## Pilotage du programme (rôle AMOA / direction de projet)

- Construction de la roadmap et des jalons ; arbitrages au bon niveau.
- Coordination multi-équipes et multi-filiales ; alignement avec l'existant
  (SOC, gestion des vulnérabilités, projets IT) — pas de dispositif parallèle.
- Pilotage des risques cyber, techniques et organisationnels du programme.
- Mise en place et animation de la gouvernance (comitologie, reporting direction).
- Consolidation des livrables et reportings.

## Indicateurs de pilotage (définitions)

- **TTD** (Time To Detect) : délai moyen de détection d'un incident ou d'une exposition.
- **MTTR** (Mean Time To Respond/Remediate) : délai moyen de réponse / remédiation.
- **MTTP** (Mean Time To Patch) : délai moyen entre publication d'un correctif critique
  et déploiement complet sur le périmètre concerné.
- **Taux d'automatisation** : part des traitements (tri, qualification, déploiement,
  vérification) réalisés sans intervention manuelle.
- Bonnes pratiques : mesurer par criticité et par périmètre (filiale, zone), suivre la
  tendance plutôt que la valeur absolue, associer chaque KPI à un propriétaire.

## Compétences mobilisées

Pilotage de projets complexes ; intelligence artificielle (cas d'usage, outils,
gouvernance) ; data / SI ; cybersécurité ; protection des données ; capacité à fédérer
des équipes pluridisciplinaires.

## Points d'attention (retours d'expérience)

- La priorisation par l'exposition réelle change les arbitrages : l'assumer en gouvernance.
- La capacité de remédiation est presque toujours le facteur limitant — la mesurer avant
  de promettre des délais.
- Les usages IA du SOC exigent un cadre (supervision humaine, traçabilité) dès le départ :
  l'ajouter après coup coûte cher.
- En multi-filiales, l'alignement des initiatives existantes prime sur la création de
  nouveaux dispositifs.
- Confidentialité : aucune donnée client (nom, constats, chiffres) ne doit sortir du
  périmètre de la mission ; toute communication externe est anonymisée et validée.
