"""Référentiel RGPD & AI Act du site — source unique de vérité.

- REGISTRE : registre des activités de traitement (art. 30 RGPD) du site
  conseilprevcyber. Chaque entrée documente finalité, base légale, données,
  personnes concernées, durée de conservation, destinataires, transferts et
  mesures de sécurité. Affiché et exportable depuis /admin/clients.
- ART50 : mesures de transparence IA (règlement (UE) 2024/1689 — AI Act,
  art. 50, pleinement applicable le 2 août 2026) réellement en place sur le
  site. Chaque mesure reflète l'état du code : ne déclarer ici que ce qui est
  effectivement implémenté.

RÈGLES : aucune donnée personnelle dans ce fichier ; descriptions factuelles,
sans promesse — le registre est un document de conformité opposable (art. 5.2).
"""

VERSION = "2026-07"

REGISTRE = [
    {
        "id": "contact",
        "traitement": "Formulaire de contact",
        "finalite": "Traiter les demandes de contact, de rendez-vous et de devis.",
        "base_legale": "Mesures précontractuelles (art. 6.1.b)",
        "donnees": "Nom, email, organisation, message.",
        "personnes": "Prospects et visiteurs du site.",
        "duree": "12 mois après le dernier échange.",
        "destinataires": "CONSEILPREV ; Brevo (routage email — UE).",
        "transferts": "Aucun transfert hors UE.",
        "securite": "HTTPS, anti-abus (rythme), consentement de contact, accès restreint.",
    },
    {
        "id": "comptes",
        "traitement": "Comptes utilisateurs (espace cockpit)",
        "finalite": "Créer et gérer les accès à l'espace de supervision (démo/pilote).",
        "base_legale": "Exécution du contrat / consentement (art. 6.1.a-b)",
        "donnees": "Nom, email, organisation, mot de passe (haché), horodatages de connexion.",
        "personnes": "Utilisateurs inscrits (professionnels).",
        "duree": "Durée du compte ; revue des comptes inactifs ; suppression sur demande.",
        "destinataires": "CONSEILPREV uniquement.",
        "transferts": "Aucun transfert hors UE (hébergement Render — Francfort).",
        "securite": "Mots de passe hachés, sessions signées, double validation (email + admin), anti-force-brute.",
    },
    {
        "id": "clients",
        "traitement": "Gestion des clients & prospects (outil interne)",
        "finalite": "Suivi de la relation client et de la prospection B2B.",
        "base_legale": "Intérêt légitime (prospection B2B) / exécution du contrat (art. 6.1.b-f)",
        "donnees": "Entreprise, nom du contact, email et téléphone professionnels, secteur, notes de suivi.",
        "personnes": "Contacts professionnels des clients et prospects.",
        "duree": "36 mois après le dernier contact (repère CNIL), paramétrable par fiche ; purge outillée.",
        "destinataires": "CONSEILPREV uniquement (accès administrateur).",
        "transferts": "Aucun transfert hors UE (PostgreSQL — Francfort).",
        "securite": "Accès admin seul, journal des opérations (art. 5.2), export (art. 20), effacement (art. 17).",
    },
    {
        "id": "assistant",
        "traitement": "Assistant IA conversationnel",
        "finalite": "Répondre aux questions des visiteurs (cybersécurité industrielle, conformité).",
        "base_legale": "Consentement par l'usage volontaire (art. 6.1.a)",
        "donnees": "Messages de la conversation en cours (aucun compte requis ; PII déconseillée dans l'interface).",
        "personnes": "Visiteurs utilisant l'assistant.",
        "duree": "Aucune conservation côté site : ni les questions ni les réponses ne sont enregistrées.",
        "destinataires": "Fournisseur du modèle choisi : Mistral (UE) ou Anthropic (USA).",
        "transferts": "Anthropic : USA — encadré (Data Privacy Framework) ; Mistral : UE.",
        "securite": "Pas de stockage, pas d'entraînement sur les échanges, anti-abus, transparence IA.",
    },
    {
        "id": "livrables",
        "traitement": "Génération de livrables (outil interne)",
        "finalite": "Produire des brouillons de documents de conseil ancrés sur la base de connaissance.",
        "base_legale": "Intérêt légitime (art. 6.1.f)",
        "donnees": "Contexte client saisi par l'administrateur (nom, secteur, périmètre).",
        "personnes": "Clients faisant l'objet d'un livrable.",
        "duree": "Historique administrable : suppression à la main, revue périodique.",
        "destinataires": "CONSEILPREV ; fournisseur IA (le temps de la génération).",
        "transferts": "Selon le modèle : Mistral (UE) ou Anthropic (USA — DPF).",
        "securite": "Accès admin, base UE, marquage IA des documents produits.",
    },
    {
        "id": "logs",
        "traitement": "Journaux techniques",
        "finalite": "Sécurité, détection d'abus et diagnostic des incidents.",
        "base_legale": "Intérêt légitime (art. 6.1.f)",
        "donnees": "Adresses IP, horodatages, événements techniques.",
        "personnes": "Visiteurs du site.",
        "duree": "Courte durée (rotation de l'hébergeur).",
        "destinataires": "Render (hébergeur — Francfort, UE).",
        "transferts": "Aucun transfert hors UE.",
        "securite": "Accès restreint à l'hébergement, pas de journalisation du contenu des messages.",
    },
]

# Mesures de transparence IA effectivement en place (AI Act, art. 50).
ART50 = [
    {
        "mesure": "Information d'interaction avec une IA",
        "ref": "art. 50.1",
        "statut": "en place",
        "detail": "L'assistant est explicitement présenté comme une IA : page « Assistant IA », "
                  "badges de transparence (AI Act, RGPD, fournisseurs), lanceur « Assistant IA » "
                  "sur l'ensemble du site. Aucun visiteur ne peut le confondre avec un humain.",
    },
    {
        "mesure": "Marquage des contenus générés par IA",
        "ref": "art. 50.2 / 50.4",
        "statut": "en place",
        "detail": "Chaque livrable exporté (Word / PDF) porte la mention « Brouillon généré avec "
                  "l'aide de l'IA — à relire et valider » ; la consigne de marquage est intégrée "
                  "au prompt de génération.",
    },
    {
        "mesure": "Supervision humaine des contenus",
        "ref": "art. 50 + RGPD art. 22",
        "statut": "en place",
        "detail": "Aucune décision produisant des effets juridiques n'est déléguée à l'IA : les "
                  "livrables sont des brouillons soumis à relecture et validation par un consultant.",
    },
    {
        "mesure": "Aucune conservation des conversations",
        "ref": "RGPD art. 5.1.c-e",
        "statut": "en place",
        "detail": "L'assistant ne conserve ni n'entraîne sur les échanges ; le site ne journalise "
                  "pas le contenu des messages.",
    },
    {
        "mesure": "Contenus synthétiques trompeurs (deepfakes)",
        "ref": "art. 50.4",
        "statut": "sans objet",
        "detail": "Le site ne génère ni image, ni audio, ni vidéo de personnes — contenus "
                  "textuels professionnels uniquement.",
    },
]
