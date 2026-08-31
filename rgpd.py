"""Référentiel RGPD & IA Act du site — source unique de vérité.

Ce fichier est un document de conformité opposable : il alimente à la fois la
page publique /conformite et la console d'administration. Une divergence entre
ce qu'il déclare et ce que le code fait serait pire que l'absence de document —
c'est exactement ce qu'un contrôle cherche.

RÈGLE DE RÉDACTION, sans exception : ne déclarer QUE ce qui est effectivement
implémenté. Ce qui reste à faire va dans ACTIONS, ce qui ne peut pas être
affirmé depuis le code porte `a_verifier`. Aucune donnée personnelle ici.

Contenu :
  REGISTRE        — activités de traitement (art. 30 RGPD)
  SOUS_TRAITANTS  — destinataires, rôles et transferts (art. 28 et chap. V)
  CLASSIFICATION  — qualification IA Act motivée (art. 5, 6, annexe III, 50)
  TRANSPARENCE_IA — à qui l'art. 50 parle, et ce qu'il ne dit pas
  ART50           — mesures de transparence effectivement en place
  MESURES_RGPD    — mesures techniques et organisationnelles (art. 32)
  DROITS          — exercice des droits (art. 15 à 22)
  AIPD            — appréciation du besoin d'analyse d'impact (art. 35)
  ACTIONS         — ce qui reste à faire, avec son échéance
"""

VERSION = "2026-08-a"
RESPONSABLE = "CONSEILPREV"
CONTACT_DONNEES = "christophe.cerf@outlook.com"

# ═══════════════════════════════════════════════════════════════════════════
# Registre des activités de traitement — art. 30 RGPD
# ═══════════════════════════════════════════════════════════════════════════
REGISTRE = [
    {
        "id": "contact",
        "traitement": "Formulaire de contact",
        "finalite": "Traiter les demandes de contact, de rendez-vous et de devis.",
        "base_legale": "Mesures précontractuelles (art. 6.1.b)",
        "donnees": "Nom, email, organisation, message.",
        "personnes": "Prospects et visiteurs du site.",
        "duree": "12 mois après le dernier échange.",
        "destinataires": "CONSEILPREV ; Brevo (routage email — UE) ; "
                         "fournisseur du modèle de langage pour la "
                         "qualification automatique de la demande — données "
                         "identifiantes masquées côté serveur avant envoi.",
        "transferts": "Aucun transfert hors UE.",
        "securite": "HTTPS, limitation de débit, contrôle d'origine, accès restreint.",
    },
    {
        "id": "comptes",
        "traitement": "Comptes utilisateurs (espace client)",
        "finalite": "Créer et gérer les accès à l'espace client et aux outils réservés.",
        "base_legale": "Exécution du contrat / consentement (art. 6.1.a-b)",
        "donnees": "Nom, email, organisation, mot de passe haché, horodatages de connexion.",
        "personnes": "Utilisateurs inscrits (professionnels).",
        "duree": "Durée du compte ; suppression sur demande ; revue des comptes inactifs.",
        "destinataires": "CONSEILPREV uniquement.",
        "transferts": "Aucun (hébergement Render — Francfort, UE).",
        "securite": "Mots de passe hachés, sessions signées, cookie « Secure », double "
                    "validation (email + administrateur), anti-force-brute, journal des connexions.",
    },
    {
        "id": "clients",
        "traitement": "Gestion des clients et prospects",
        "finalite": "Suivi de la relation client et de la prospection professionnelle.",
        "base_legale": "Intérêt légitime (prospection B2B) / exécution du contrat (art. 6.1.b-f)",
        "donnees": "Entreprise, nom du contact, coordonnées professionnelles, secteur, notes de suivi.",
        "personnes": "Contacts professionnels des clients et prospects.",
        "duree": "36 mois après le dernier contact (repère CNIL), paramétrable par fiche ; purge outillée.",
        "destinataires": "CONSEILPREV uniquement (accès administrateur).",
        "transferts": "Aucun (PostgreSQL — Francfort, UE).",
        "securite": "Accès administrateur seul, journal des opérations, export (art. 20), "
                    "effacement outillé (art. 17).",
    },
    {
        "id": "assistant",
        "traitement": "Assistant conversationnel (IA)",
        "finalite": "Répondre aux questions des visiteurs sur la cybersécurité industrielle "
                    "et la conformité.",
        "base_legale": "Consentement par l'usage volontaire (art. 6.1.a)",
        "donnees": "Messages de la conversation en cours. Aucun compte requis. L'interface "
                   "détecte et signale les données personnelles avant envoi.",
        "personnes": "Visiteurs utilisant l'assistant.",
        "duree": "AUCUNE conservation : ni les questions ni les réponses ne sont enregistrées "
                 "par le site, et le contenu des messages n'est pas journalisé.",
        "destinataires": "Fournisseur du modèle choisi : Mistral AI (UE) ou Anthropic (États-Unis).",
        "transferts": "Anthropic : États-Unis — mécanisme de transfert à documenter (voir ACTIONS). "
                      "Mistral AI : Union européenne, aucun transfert.",
        "securite": "Sans état, pas d'entraînement sur les échanges, limitation de débit, "
                    "avertissement de minimisation avant envoi.",
    },
    {
        "id": "juridique",
        "traitement": "Conseil juridique assisté",
        "finalite": "Qualification réglementaire, analyse juridique argumentée, clausier et "
                    "préparation de décisions, pour les clients connectés.",
        "base_legale": "Exécution du contrat / mesures précontractuelles (art. 6.1.b)",
        "donnees": "Profil d'entreprise (secteur, taille, rôles), question posée, contexte saisi. "
                   "La qualification et le routage sont calculés localement, sans IA.",
        "personnes": "Utilisateurs connectés (professionnels).",
        "duree": "Aucune conservation des questions ni des analyses ; seule une trace "
                 "d'événement sans contenu est journalisée.",
        "destinataires": "CONSEILPREV ; fournisseur du modèle le temps de la génération.",
        "transferts": "Selon le modèle retenu : Mistral AI (UE) ou Anthropic (États-Unis).",
        "securite": "Accès réservé aux comptes, périmètre documentaire lié à l'identité, "
                    "référentiel de citations fermé, contrôle automatique des références.",
    },
    {
        "id": "contrats",
        "traitement": "Revue de contrat et dossiers d'arbitrage",
        "finalite": "Analyser un contrat fournisseur clause par clause, ou préparer une "
                    "décision à partir des pièces d'un dossier.",
        "base_legale": "Exécution du contrat (art. 6.1.b)",
        "donnees": "Texte du contrat ou des pièces soumis par l'utilisateur. Ces documents "
                   "peuvent contenir des données personnelles (signataires, contacts) : "
                   "l'utilisateur est invité à les retirer avant soumission.",
        "personnes": "Personnes mentionnées dans les pièces soumises.",
        "duree": "AUCUNE : la pièce est analysée EN MÉMOIRE, jamais écrite en base ni indexée. "
                 "Le journal enregistre la taille analysée, jamais le contenu.",
        "destinataires": "Fournisseur du modèle, le temps de l'analyse.",
        "transferts": "Selon le modèle retenu : Mistral AI (UE) ou Anthropic (États-Unis).",
        "securite": "Analyse en mémoire, format et taille contrôlés (6 Mo), accès réservé "
                    "aux comptes, limitation de débit renforcée.",
    },
    {
        "id": "base-connaissance",
        "traitement": "Base de connaissance documentaire",
        "finalite": "Ancrer les réponses de l'assistant et les livrables sur des documents "
                    "de référence choisis par CONSEILPREV.",
        "base_legale": "Intérêt légitime (art. 6.1.f)",
        "donnees": "Documents professionnels chargés par l'administrateur. Ils peuvent "
                   "contenir des données personnelles selon leur nature.",
        "personnes": "Personnes éventuellement mentionnées dans les documents chargés.",
        "duree": "Jusqu'à suppression par l'administrateur ; contrôle d'intégrité et "
                 "inventaire outillés.",
        "destinataires": "CONSEILPREV ; extraits transmis au modèle lors d'une réponse.",
        "transferts": "Base hébergée en UE (Francfort). Extraits transmis selon le modèle retenu.",
        "securite": "Deux niveaux de visibilité (public / interne), périmètre de recherche lié "
                    "à l'identité, journal des chargements, suppressions et changements de visibilité.",
    },
    {
        "id": "livrables",
        "traitement": "Génération de livrables",
        "finalite": "Produire des brouillons de documents de conseil ancrés sur la base de connaissance.",
        "base_legale": "Intérêt légitime (art. 6.1.f)",
        "donnees": "Contexte client saisi par l'administrateur (organisation, secteur, périmètre).",
        "personnes": "Clients faisant l'objet d'un livrable.",
        "duree": "Historique administrable : suppression à la main, revue périodique.",
        "destinataires": "CONSEILPREV ; fournisseur du modèle le temps de la génération.",
        "transferts": "Selon le modèle retenu : Mistral AI (UE) ou Anthropic (États-Unis).",
        "securite": "Accès administrateur, base en UE, marquage IA visible ET lisible par "
                    "machine dans les documents exportés.",
    },
    {
        "id": "journal",
        "traitement": "Journal d'audit des actions sensibles",
        "finalite": "Tracer les opérations à effet durable (chargement, suppression, "
                    "changement de visibilité, purge, connexions) — exigence de responsabilité.",
        "base_legale": "Obligation de responsabilité et intérêt légitime (art. 5.2 et 6.1.f)",
        "donnees": "Auteur (email du compte), rôle, action, cible, horodatage, adresse IP "
                   "ANONYMISÉE. Jamais le contenu des documents ni des messages.",
        "personnes": "Administrateurs et utilisateurs connectés.",
        "duree": "12 mois. Effacement automatique par tâche quotidienne, et non au seul "
                 "moment où l'on écrit : un plafond de volume borne la place occupée, "
                 "il ne tient pas lieu de durée de conservation.",
        "destinataires": "CONSEILPREV uniquement.",
        "transferts": "Aucun (base en UE).",
        "securite": "Journal en ajout seul, non modifiable depuis l'interface, "
                    "adresse IP tronquée dès l'écriture.",
    },
    {
        "id": "logs",
        "traitement": "Journaux techniques d'hébergement",
        "finalite": "Sécurité, détection d'abus et diagnostic des incidents.",
        "base_legale": "Intérêt légitime (art. 6.1.f)",
        "donnees": "Adresses IP, horodatages, événements techniques.",
        "personnes": "Visiteurs du site.",
        "duree": "Courte durée (rotation de l'hébergeur).",
        "destinataires": "Render (hébergeur — Francfort, UE).",
        "transferts": "Aucun.",
        "securite": "Accès restreint à l'hébergement ; le contenu des messages n'est jamais journalisé.",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
# Destinataires, rôles et transferts — art. 28 et chapitre V
# ═══════════════════════════════════════════════════════════════════════════
SOUS_TRAITANTS = [
    {"nom": "Render", "role": "Hébergement de l'application et de la base de données",
     "localisation": "Francfort (Allemagne) — Union européenne",
     "transfert": "Aucun transfert hors UE.", "donnees": "Ensemble des données du site."},
    {"nom": "Mistral AI", "role": "Fournisseur de modèle de langage",
     "localisation": "France — Union européenne",
     "transfert": "Aucun transfert hors UE.",
     "donnees": "Messages et extraits transmis le temps de la réponse."},
    {"nom": "Anthropic", "role": "Fournisseur de modèle de langage",
     "localisation": "États-Unis",
     "transfert": "Transfert hors UE : le mécanisme applicable doit être documenté et "
                  "tenu à jour (décision d'adéquation si l'organisme y est éligible, "
                  "à défaut clauses contractuelles types et analyse d'impact du transfert).",
     "donnees": "Messages et extraits transmis le temps de la réponse.",
     "a_verifier": True},
    {"nom": "Brevo", "role": "Routage des courriels transactionnels",
     "localisation": "France — Union européenne",
     "transfert": "Aucun transfert hors UE.",
     "donnees": "Adresse email et contenu du message envoyé."},
]

# ═══════════════════════════════════════════════════════════════════════════
# Qualification IA Act — règlement (UE) 2024/1689
# ═══════════════════════════════════════════════════════════════════════════
#
# C'est la pièce maîtresse du dossier : un contrôle ne demande pas « avez-vous
# de l'IA ? » mais « comment l'avez-vous qualifiée, et sur quel fondement ? ».
# Une classification non documentée équivaut à une absence de classification.
CLASSIFICATION = {
    "systemes": [
        {"nom": "Assistant conversationnel",
         "description": "Chat public répondant aux questions de cybersécurité industrielle "
                        "et de conformité, adossé à une base documentaire.",
         "role": "CONSEILPREV met ce système en service sous son propre nom : il en est "
                 "FOURNISSEUR au sens de l'art. 3.3, tout en étant DÉPLOYEUR du modèle "
                 "sous-jacent fourni par un tiers."},
        {"nom": "Générateur de livrables",
         "description": "Production de brouillons de documents de conseil, à usage interne, "
                        "relus et validés par un consultant avant toute remise.",
         "role": "Fournisseur et déployeur, usage interne."},
        {"nom": "Conseil juridique assisté",
         "description": "Qualification réglementaire et routage calculés par règles, sans IA ; "
                        "analyse, revue de contrat et note d'arbitrage rédigées par un modèle "
                        "sous contrainte de référentiel fermé.",
         "role": "Fournisseur et déployeur, à destination des clients connectés."},
    ],
    "pratiques_interdites": {
        "ref": "art. 5", "verdict": "Aucune pratique interdite",
        "motif": "Aucun des systèmes ne met en œuvre de technique subliminale ou manipulatrice, "
                 "n'exploite la vulnérabilité d'un groupe, ne procède à une notation sociale, "
                 "n'infère les émotions sur le lieu de travail ou en éducation, ne catégorise "
                 "biométriquement des personnes, ne moissonne d'images faciales, ni n'assure "
                 "d'identification biométrique à distance. Aucune donnée biométrique n'est "
                 "traitée à aucun stade.",
    },
    "haut_risque": {
        "ref": "art. 6", "verdict": "Non — aucun système à haut risque",
        "art_6_1": "Aucun système n'est un composant de sécurité d'un produit couvert par la "
                   "législation d'harmonisation de l'annexe I, ni n'est lui-même un tel produit. "
                   "Les systèmes produisent des textes d'information et d'aide à la décision ; "
                   "ils ne commandent aucun équipement et ne sont intégrés à aucun produit.",
        "annexe_iii": "Aucun des huit domaines de l'annexe III n'est en cause : pas de biométrie ; "
                      "pas de composant de sécurité dans la gestion ou l'exploitation "
                      "d'infrastructures critiques — le conseil PORTE sur la sécurité "
                      "d'installations industrielles, il n'y participe pas techniquement ; pas "
                      "d'éducation, d'emploi, d'accès aux services essentiels, de répression, "
                      "de migration ni de justice.",
        "consequence": "Les obligations applicables sont celles de la TRANSPARENCE (art. 50) et "
                       "de la LITTÉRATIE (art. 4), non celles du chapitre III.",
        "revision": "Cette qualification est réexaminée à chaque évolution fonctionnelle "
                    "significative, et au plus tard chaque année.",
    },
    "gpai": {
        "ref": "chapitre V", "verdict": "Non applicable à CONSEILPREV",
        "motif": "CONSEILPREV ne développe ni ne met sur le marché de modèle d'IA à usage "
                 "général. Les obligations du chapitre V pèsent sur les fournisseurs des "
                 "modèles utilisés (Anthropic, Mistral AI).",
    },
    "jalons": [
        "2 février 2025 — pratiques interdites (art. 5) et littératie en IA (art. 4)",
        "2 août 2025 — modèles à usage général, gouvernance et sanctions",
        "2 août 2026 — application générale, dont les obligations de transparence de l'art. 50",
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# Trois obligations à ne pas confondre
# ═══════════════════════════════════════════════════════════════════════════
#
#     marquage technique du fournisseur
#   ≠ obligation légale de transparence du déployeur
#   ≠ obligations contractuelles
#
# La confusion est fréquente et coûteuse dans les deux sens : elle fait
# apposer un marquage d'article 50 sur des documents qu'aucun modèle n'a
# écrits, et elle fait croire qu'une note remise à un client doit porter
# « rédigé avec une IA ». Ce bloc dit, pour chaque obligation, QUI elle vise,
# ce qu'elle DIT et ce qu'elle NE DIT PAS — le même patron que les textes de
# `decarbonation.TEXTES`, parce qu'un texte cité sans sa portée sert d'alibi.
TRANSPARENCE_IA = [
    {
        "role": "Marquage technique du fournisseur",
        "qui": "Le FOURNISSEUR du système d'IA qui génère le contenu.",
        "ref": "Règlement (UE) 2024/1689, art. 50 §2",
        "dit": "Les sorties du système doivent être marquées dans un format "
               "LISIBLE PAR UNE MACHINE et détectables comme artificiellement "
               "générées ou manipulées, par des solutions techniques efficaces, "
               "interopérables, robustes et fiables dans la mesure où cela est "
               "techniquement possible.",
        "ne_dit_pas": "Il n'impose aucune phrase à écrire DANS le document. Un "
                      "marquage lisible par une machine et une mention lisible "
                      "par un lecteur sont deux choses différentes, et le §2 ne "
                      "demande que la première.",
        "chez_nous": "CONSEILPREV est fournisseur de son propre générateur de "
                     "livrables — voir la qualification ci-dessus — et déployeur "
                     "des modèles tiers qu'il appelle. Le marquage est posé dans "
                     "les PROPRIÉTÉS des fichiers Word et PDF, où il survit à la "
                     "copie. Il n'est pas apposé sur les documents produits par "
                     "calcul déterministe : y apposer un marquage de contenu "
                     "synthétique serait une déclaration fausse.",
    },
    {
        "role": "Transparence du déployeur",
        "qui": "Le DÉPLOYEUR qui se sert d'un système d'IA.",
        "ref": "Règlement (UE) 2024/1689, art. 50 §1, §3 et §4",
        "dit": "Des obligations d'information dans des cas NOMMÉS : informer la "
               "personne qu'elle interagit avec une machine (§1) ; informer les "
               "personnes exposées à un système de reconnaissance des émotions "
               "ou de catégorisation biométrique (§3) ; révéler qu'un contenu "
               "est un hypertrucage, et qu'un texte publié pour informer le "
               "public sur des questions d'intérêt public a été généré "
               "artificiellement (§4).",
        "ne_dit_pas": "AUCUNE obligation générale d'indiquer qu'un contenu a été "
                      "produit avec l'aide d'une IA. Une note, une analyse ou un "
                      "livrable remis à un client ne relève d'aucun des cas "
                      "nommés ; et le §4 excepte de surcroît le texte qui a fait "
                      "l'objet d'un contrôle humain et dont une personne assume "
                      "la responsabilité éditoriale.",
        "chez_nous": "Le §1 est tenu sur l'assistant, dès la première "
                     "interaction. Le §3 est sans objet : aucune reconnaissance "
                     "d'émotions, aucune catégorisation biométrique, aucune "
                     "donnée biométrique traitée. Le §4 est sans objet : ni "
                     "image, ni son, ni vidéo, et les textes publiés le sont "
                     "sous responsabilité éditoriale après relecture humaine.",
    },
    {
        "role": "Obligations contractuelles et de confidentialité",
        "qui": "Les parties au contrat — et elles seules.",
        "ref": "Hors IA Act : contrat de prestation, engagement de "
               "confidentialité, politique fournisseurs du client",
        "dit": "Un engagement de confidentialité, la politique fournisseurs du "
               "client, une clause du marché ou, selon les circonstances, "
               "l'exécution de bonne foi du contrat peuvent conduire à devoir "
               "informer le cocontractant de l'usage d'une IA — voire à "
               "l'interdire.",
        "ne_dit_pas": "Rien de général. Cela ne se déduit pas de l'IA Act et ne "
                      "se présume pas : cela se vérifie CONTRAT PAR CONTRAT, "
                      "avant la première ligne écrite avec un modèle.",
        "chez_nous": "C'est cette troisième catégorie, et non l'art. 50, qui "
                     "décide en pratique de ce qu'un livrable doit dire. La "
                     "mention d'assistance portée par défaut sur nos brouillons "
                     "est un engagement de la maison, pas l'exécution d'une "
                     "obligation légale.",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
# Transparence IA effectivement en place — art. 50
# ═══════════════════════════════════════════════════════════════════════════
ART50 = [
    {
        "mesure": "Information d'interaction avec une IA",
        "ref": "art. 50.1", "statut": "en place",
        "detail": "L'utilisateur est informé DÈS LA PREMIÈRE INTERACTION : le premier message "
                  "de l'assistant l'annonce, la page porte le titre « Assistant IA », un "
                  "avertissement permanent figure sous la zone de saisie et le lanceur présent "
                  "sur tout le site est nommé « Assistant IA ». Aucune confusion possible avec "
                  "un interlocuteur humain.",
    },
    {
        "mesure": "Mention visible d'assistance par IA sur les documents",
        "ref": "engagement CONSEILPREV — hors art. 50", "statut": "en place",
        "detail": "Deux choses distinctes, et une seule relève d'une obligation. Le STATUT — "
                  "« brouillon, à relire et valider » — figure sur tout document non visé : "
                  "c'est une nécessité professionnelle, sans rapport avec l'IA Act, et elle "
                  "vaut aussi pour les documents calculés sans modèle. La MENTION D'ASSISTANCE "
                  "PAR IA, elle, est portée par défaut sur les documents qu'un modèle a rédigés "
                  "— mais l'art. 50 ne l'impose pas au déployeur : c'est un engagement de la "
                  "maison, que le contrat du client peut renforcer ou écarter.",
        "limite": "Aucune obligation générale d'indiquer qu'un contenu a été produit avec une "
                  "IA ne pèse sur le déployeur : voir le bloc des trois obligations.",
    },
    {
        "mesure": "Marquage des contenus générés, lisible par une machine",
        "ref": "art. 50.2", "statut": "en place",
        "detail": "Obligation du FOURNISSEUR du système, que CONSEILPREV est pour son propre "
                  "générateur. Les documents Word et PDF rédigés par un modèle portent dans "
                  "leurs PROPRIÉTÉS un marquage exploitable automatiquement : mention "
                  "« AI-generated », outil producteur, modèle utilisé et référence au règlement. "
                  "Le marquage survit à la copie du fichier, contrairement à une mention de bas "
                  "de page.",
        "limite": "Il n'est PAS apposé sur les documents produits par calcul déterministe — "
                  "checklist, auto-évaluation de maturité, bilan de décarbonation : leurs "
                  "propriétés déclarent le moteur et son référentiel. Un marquage apposé "
                  "partout ne signale plus rien.",
    },
    {
        "mesure": "Supervision humaine — aucune décision automatisée",
        "ref": "art. 50 ; RGPD art. 22", "statut": "en place",
        "detail": "Aucune décision produisant des effets juridiques ou affectant significativement "
                  "une personne n'est prise par un système automatisé. Les livrables et notes sont "
                  "des brouillons relus et validés par un consultant ; le conseil juridique assisté "
                  "produit une analyse documentaire, jamais un acte.",
    },
    {
        "mesure": "Minimisation avant transmission au modèle",
        "ref": "RGPD art. 5.1.c", "statut": "en place",
        "detail": "Avant tout envoi à un fournisseur de modèle, le texte saisi est contrôlé et "
                  "les données directement identifiantes sont signalées : adresse électronique, "
                  "téléphone, IBAN, carte de paiement, numéro de sécurité sociale. L'utilisateur "
                  "corrige, demande le caviardage automatique, ou confirme l'envoi. Le contrôle "
                  "est fait CÔTÉ SERVEUR — un avertissement contournable depuis le navigateur "
                  "ne serait pas une mesure — par expressions régulières et clés de contrôle "
                  "(IBAN, Luhn, clé du NIR), sans modèle et sans conserver le texte analysé. "
                  "Le journal retient les catégories et leur nombre, jamais le contenu.",
        "limite": "La détection porte sur des formats stables, non sur les noms, adresses "
                  "postales ou données de santé : les repérer supposerait de soumettre le texte "
                  "à un modèle, c'est-à-dire de faire ce que la mesure vise à éviter.",
    },
    {
        "mesure": "Aucune conservation des échanges",
        "ref": "RGPD art. 5.1.c-e", "statut": "en place",
        "detail": "L'assistant est sans état : ni les questions ni les réponses ne sont "
                  "enregistrées. Les contrats et pièces soumis sont analysés en mémoire et "
                  "jamais écrits en base. Le journal d'audit enregistre l'événement, jamais "
                  "le contenu.",
    },
    {
        "mesure": "Littératie en intelligence artificielle",
        "ref": "art. 4", "statut": "en place",
        "detail": "Les personnes qui exploitent les outils connaissent leurs limites : les "
                  "interfaces rappellent la nature d'aide à la décision, signalent les "
                  "références non reconnues et imposent une validation humaine. La culture IA "
                  "fait partie de l'activité de conseil de CONSEILPREV.",
    },
    {
        "mesure": "Contenus synthétiques trompeurs",
        "ref": "art. 50.4", "statut": "sans objet",
        "detail": "Le site ne génère ni image, ni audio, ni vidéo, et ne produit aucun contenu "
                  "imitant une personne réelle. Les textes publiés le sont sous la responsabilité "
                  "éditoriale de CONSEILPREV, après relecture humaine.",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
# Mesures de sécurité — art. 32
# ═══════════════════════════════════════════════════════════════════════════
MESURES_RGPD = [
    {"mesure": "Chiffrement des échanges", "detail": "HTTPS sur l'ensemble du site ; "
     "cookie de session marqué « Secure » et « SameSite »."},
    {"mesure": "Authentification", "detail": "Mots de passe hachés, sessions signées, "
     "double validation à l'inscription, protection contre la force brute."},
    {"mesure": "Cloisonnement des accès", "detail": "Les outils de conseil exigent un compte ; "
     "les documents internes ne sont accessibles qu'à l'administrateur ; le périmètre de "
     "recherche suit l'identité de l'appelant."},
    {"mesure": "Journalisation", "detail": "Journal en ajout seul des actions sensibles, "
     "adresse IP anonymisée, contenu jamais enregistré."},
    {"mesure": "Intégrité", "detail": "Contrôle d'intégrité des documents par empreinte, "
     "vérifiable à la demande depuis la console."},
    {"mesure": "Disponibilité", "detail": "Sonde de santé, reprise automatique sur incident "
     "de base, sauvegarde exportable de la base documentaire."},
    {"mesure": "Minimisation", "detail": "Aucune conservation des conversations ni des pièces "
     "analysées ; avertissement avant transmission de données personnelles."},
    {"mesure": "Absence de traceurs", "detail": "Aucun cookie publicitaire ni de mesure "
     "d'audience ; un unique cookie technique de session."},
]

# ═══════════════════════════════════════════════════════════════════════════
# Exercice des droits — art. 15 à 22
# ═══════════════════════════════════════════════════════════════════════════
DROITS = [
    {"droit": "Accès", "ref": "art. 15",
     "modalite": "Copie des données détenues, transmise sous un mois."},
    {"droit": "Rectification", "ref": "art. 16",
     "modalite": "Correction directe pour un compte, sur demande sinon."},
    {"droit": "Effacement", "ref": "art. 17",
     "modalite": "Suppression outillée ; seule une preuve pseudonymisée de l'effacement est conservée."},
    {"droit": "Limitation", "ref": "art. 18",
     "modalite": "Gel du traitement pendant l'examen d'une contestation."},
    {"droit": "Portabilité", "ref": "art. 20",
     "modalite": "Export structuré et lisible par machine (JSON) des données d'un compte ou d'une fiche client."},
    {"droit": "Opposition", "ref": "art. 21",
     "modalite": "Opposition à la prospection : effet immédiat, sans justification à fournir."},
    {"droit": "Décision automatisée", "ref": "art. 22",
     "modalite": "Sans objet : aucune décision automatisée produisant des effets juridiques n'est mise en œuvre."},
]

# Une liste de droits sans procédure pour les exercer n'engage à rien. Voici
# comment ils s'exercent réellement — délai, preuve d'identité et recours
# compris, y compris le recours CONTRE nous.
PROCEDURE_DROITS = {
    "canal": "Par courriel à " + CONTACT_DONNEES + ", en précisant le droit exercé.",
    "delai": "Réponse sous un mois à compter de la réception (art. 12.3), prolongeable "
             "de deux mois pour une demande complexe, la prolongation étant alors motivée "
             "et notifiée dans le premier mois.",
    "identite": "Aucune pièce d'identité n'est demandée par principe : la demande émanant de "
                "l'adresse électronique enregistrée suffit. Une preuve n'est réclamée qu'en "
                "cas de doute raisonnable sur l'identité du demandeur (art. 12.6) — exiger "
                "systématiquement une carte d'identité reviendrait à collecter plus de "
                "données pour en faire respecter la protection.",
    "gratuite": "Gratuit. Une demande manifestement infondée ou répétitive peut donner lieu "
                "à des frais ou à un refus motivé (art. 12.5).",
    "recours": "En cas de réponse insatisfaisante ou d'absence de réponse : réclamation "
               "auprès de la CNIL (3 place de Fontenoy, 75007 Paris — cnil.fr), et recours "
               "juridictionnel (art. 77 et 79).",
}

# ═══════════════════════════════════════════════════════════════════════════
# Analyse d'impact — art. 35
# ═══════════════════════════════════════════════════════════════════════════
AIPD = {
    "verdict": "Non requise en l'état, appréciation documentée et réexaminée",
    "motif": "Aucun des critères imposant une analyse d'impact n'est réuni : pas d'évaluation "
             "systématique et approfondie d'aspects personnels, pas de décision automatisée à "
             "effet juridique, pas de traitement à grande échelle de données sensibles, pas de "
             "surveillance systématique d'une zone accessible au public, pas de croisement de "
             "fichiers, pas de données de personnes vulnérables. Les traitements portent sur des "
             "contacts professionnels et sur des échanges non conservés.",
    "reserve": "Cette appréciation serait à refaire si le site venait à conserver les "
               "conversations, à profiler les visiteurs, ou à traiter à grande échelle des "
               "documents clients contenant des données sensibles.",
}

# ═══════════════════════════════════════════════════════════════════════════
# Ce qui reste à faire — la partie honnête du dossier
# ═══════════════════════════════════════════════════════════════════════════
# Un référentiel de conformité qui ne comporte aucune action ouverte n'est pas
# un référentiel, c'est une plaquette. Ces points relèvent de démarches
# contractuelles ou organisationnelles : le code ne peut pas les réaliser seul.
ACTIONS = [
    {"action": "Documenter le mécanisme de transfert vers Anthropic (États-Unis)",
     "ref": "RGPD, chapitre V", "priorite": "haute",
     "detail": "Vérifier le régime applicable au fournisseur, conserver la preuve du mécanisme "
               "retenu et l'analyse d'impact du transfert. À défaut, privilégier le modèle "
               "européen par configuration."},
    {"action": "Formaliser les contrats de sous-traitance",
     "ref": "RGPD, art. 28.3", "priorite": "haute",
     "detail": "Conserver pour chaque fournisseur (hébergeur, modèles, routage email) l'accord "
               "de traitement, la liste des sous-traitants ultérieurs et les engagements de "
               "non-réutilisation des données."},
    {"action": "Obtenir l'engagement écrit de non-entraînement sur les données transmises",
     "ref": "RGPD, art. 28.3.a", "priorite": "haute",
     "detail": "Le site l'affirme aux visiteurs : cette affirmation doit être adossée aux "
               "conditions contractuelles des fournisseurs, et revérifiée à chaque évolution."},
    {"action": "Réexaminer annuellement la classification IA Act",
     "ref": "Règlement (UE) 2024/1689, art. 6", "priorite": "moyenne",
     "detail": "Toute nouvelle fonctionnalité peut faire basculer un système dans l'annexe III. "
               "Le réexamen se documente, même lorsqu'il conclut à l'absence de changement."},
    {"action": "Tracer la formation à l'IA des personnes concernées",
     "ref": "Règlement (UE) 2024/1689, art. 4", "priorite": "moyenne",
     "detail": "La littératie est une obligation depuis le 2 février 2025 : elle se démontre "
               "par une trace, pas par une déclaration."},
]


def etat():
    """Vue consolidée, pour la page publique et la console."""
    return {
        "version": VERSION,
        "responsable": RESPONSABLE,
        "contact": CONTACT_DONNEES,
        "registre": REGISTRE,
        "sous_traitants": SOUS_TRAITANTS,
        "classification": CLASSIFICATION,
        "transparence_ia": TRANSPARENCE_IA,
        "art50": ART50,
        "mesures": MESURES_RGPD,
        "droits": DROITS,
        "procedure_droits": PROCEDURE_DROITS,
        "aipd": AIPD,
        "actions": ACTIONS,
    }
