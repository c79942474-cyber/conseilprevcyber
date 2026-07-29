/* CONSEILPREV Cyber — parcours guidés par rôle.

   POURQUOI. Le site compte une trentaine de pages, chacune juste à sa place et
   aucune évidente pour un premier visiteur : un RSSI, un acheteur et un
   directeur général n'ont ni la même question ni le même ordre de lecture.
   Une arborescence répond « où est telle page ? » ; elle ne répond pas « par où
   je commence ». Les parcours répondent à la seconde question.

   D'OÙ VIENNENT-ILS. Pas d'une idée de la navigation idéale : des MISSIONS
   RÉELLES publiées en études de cas — Grand Paris Express, REM de Montréal,
   GRDF Biométhane, FPSO Karish & Tanin, sous-station électrique offshore.
   Chaque parcours porte le nom de la mission dont il tient sa séquence. Un
   ordre de lecture inventé se reconnaît vite ; un ordre éprouvé sur le terrain
   se défend.

   DIFFÉRENCE AVEC SENTINEL. Sentinel est une application à page unique : y
   changer d'étape est un simple appel de fonction. Ici les pages sont de
   vraies URL, et le parcours doit SURVIVRE À LA NAVIGATION. L'étape courante
   est donc conservée dans sessionStorage, et le bandeau se reconstruit à
   chaque chargement de page. Deux conséquences assumées :
     - sessionStorage et non localStorage : un parcours est une session de
       travail, pas une préférence durable. Fermer l'onglet le termine.
     - aucune donnée personnelle n'y est écrite, seulement l'identifiant du
       parcours et le numéro d'étape.

   Autonome : aucune dépendance, aucune balise à ajouter aux pages, le style
   est injecté d'ici. */
(function () {
  "use strict";

  var CLE = "cp_parcours";

  /* Pages réservées aux comptes connectés. Une bonne part de la substance du
     site — toute la section IEC 62443, la méthodologie, l'audit — est derrière
     l'inscription. Un parcours qui l'ignorerait enverrait le visiteur contre un
     mur de connexion sans prévenir : on l'annonce AVANT le clic. La liste est
     tenue à un seul endroit plutôt que recopiée sur chaque étape, sinon elle
     divergerait au premier ajout de page. */
  var RESERVE = {
    "/referentiel": 1, "/analyse-de-risque": 1, "/programme-securite": 1,
    "/exigences-systeme": 1, "/exigences-composants": 1, "/exigences-prestataires": 1,
    "/developpement-securise": 1, "/technologies-securite": 1, "/gestion-correctifs": 1,
    "/glossaire-62443": 1, "/metriques-62443": 1, "/methodologie": 1,
    "/audit-conformite": 1, "/juridique": 1
  };
  function reserve(url) { return RESERVE[url] === 1; }

  /* ═══════════════════════════════════════════════════════════════════════
     LES PARCOURS
     Chaque étape porte trois choses, et les trois comptent :
       action — ce qu'on fait sur la page (sinon on la survole) ;
       gain   — ce qu'on en retire (sinon on ne voit pas pourquoi la lire) ;
       tip    — le conseil de terrain qu'un sommaire ne donne jamais.
     ═══════════════════════════════════════════════════════════════════════ */
  var PARCOURS = [
    {
      id: "rssi",
      icone: "🛡️",
      role: "RSSI · Responsable cybersécurité industrielle",
      cas: "Inspiré de la mission GRDF — Projet Biométhane (PSSI industrielle, EBIOS, analyse d’écarts)",
      pitch: "Vous devez construire un programme de sécurité industrielle qui tienne devant un auditeur " +
             "comme devant un exploitant. Ce parcours suit l’ordre d’une mission réelle : constater, " +
             "mesurer, analyser, structurer, planifier, prouver.",
      etapes: [
        { url: "/diagnostic", label: "Diagnostic express",
          action: "Répondez aux questions de cadrage sur votre installation et vos pratiques actuelles.",
          gain: "Un point de départ chiffré en quelques minutes, avant d’engager quoi que ce soit.",
          tip: "Faites-le AVANT de solliciter vos équipes : arriver avec un constat chiffré change la nature de la conversation." },
        { url: "/maturite-ot", label: "Assessment de maturité OT",
          action: "Évaluez votre organisation sur les dimensions de la sécurité OT, sans indulgence.",
          gain: "Les angles morts organisationnels apparaissent avant même d’entrer dans la technique.",
          tip: "Un score flatteur en atelier ne vaut rien : faites évaluer par ceux qui exploitent, pas par ceux qui pilotent." },
        { url: "/analyse-de-risque", label: "Analyse de risque · IEC 62443-3-2",
          action: "Découpez en zones et conduits, puis déterminez le niveau de sécurité cible (SL-T) de chaque zone.",
          gain: "La méthode qui transforme « il faut sécuriser » en exigences opposables, zone par zone.",
          tip: "Le découpage en zones est la décision structurante de tout le programme — une zone mal tracée se paie pendant des années." },
        { url: "/programme-securite", label: "Programme de sécurité · 2-1",
          action: "Structurez le CSMS : politiques, rôles, processus, revue.",
          gain: "Ce qui distingue un programme d’une collection de mesures : quelqu’un en répond, et il se révise.",
          tip: "Adossez-le à votre SMSI existant plutôt que d’en créer un parallèle — deux systèmes de management finissent toujours par diverger." },
        { url: "/feuille-de-route", label: "Feuille de route",
          action: "Séquencez les chantiers avec leurs jalons et leurs dépendances.",
          gain: "Une trajectoire défendable en comité, où chaque euro demandé porte une échéance.",
          tip: "Découpez en jalons trimestriels : un programme sans étape intermédiaire perd sa visibilité au bout de trois mois." },
        { url: "/metriques-62443", label: "Métriques · 1-3",
          action: "Choisissez le petit nombre d’indicateurs que vous saurez tenir dans la durée.",
          gain: "De quoi démontrer une progression, et non une intention renouvelée chaque année.",
          tip: "Cinq indicateurs suivis valent mieux que vingt déclarés — on ne pilote que ce qu’on mesure vraiment." }
      ]
    },
    {
      id: "ot",
      icone: "⚙️",
      role: "Responsable OT · exploitation industrielle",
      cas: "Inspiré des missions FPSO Karish & Tanin et sous-station électrique offshore (IEC 62443, PLC / HMI / SCADA / DCS)",
      pitch: "Votre installation tourne, et elle doit continuer. Ce parcours part de la contrainte qui prime " +
             "sur toutes les autres en milieu industriel : la sûreté et la disponibilité du procédé.",
      etapes: [
        { url: "/referentiel", label: "Référentiel IEC 62443",
          action: "Situez les normes qui vous concernent : ce qui relève de l’exploitant, de l’intégrateur, du fournisseur.",
          gain: "La carte du référentiel avant d’en ouvrir une partie — on évite d’appliquer la mauvaise norme au bon problème.",
          tip: "En exploitation, la 2-1 et la 3-3 sont vos deux points d’entrée ; le reste vient après." },
        { url: "/analyse-de-risque", label: "Analyse de risque · 3-2",
          action: "Identifiez les zones et conduits de votre installation existante, telle qu’elle est câblée aujourd’hui.",
          gain: "Une lecture du réseau réel, pas du schéma d’origine — l’écart entre les deux est souvent la vraie surprise.",
          tip: "Partez du terrain, pas de la documentation : un bypass posé un dimanche de maintenance ne figure sur aucun plan." },
        { url: "/exigences-systeme", label: "Exigences système · 3-3",
          action: "Confrontez votre système à chaque exigence fondamentale et à son niveau de sécurité.",
          gain: "L’écart entre ce que vous avez et ce que la norme attend, exigence par exigence.",
          tip: "Une exigence non tenue ET assumée par écrit vaut mieux qu’une exigence cochée par optimisme." },
        { url: "/technologies-securite", label: "Technologies de sécurité · TR 3-1",
          action: "Évaluez quelles technologies sont réellement applicables à votre parc, avec son âge et ses contraintes.",
          gain: "Un tri entre ce qui se déploie en environnement industriel et ce qui n’existe qu’en salle de démonstration.",
          tip: "Un automate hors support ne se met pas à jour : la compensation par l’architecture est souvent la seule voie." },
        { url: "/gestion-correctifs", label: "Gestion des correctifs · 2-3",
          action: "Construisez un processus de correctifs compatible avec vos fenêtres d’arrêt.",
          gain: "Une chaîne de patching réaliste plutôt qu’une politique inapplicable que personne ne suivra.",
          tip: "En OT, le calendrier de maintenance commande le calendrier de sécurité — l’inverse ne se produit jamais." },
        { url: "/demo", label: "Cockpit de supervision",
          action: "Regardez à quoi ressemble la supervision d’un parc industriel, événements et indicateurs.",
          gain: "De quoi juger si la détection apporte quelque chose chez vous, avant d’engager un projet.",
          tip: "Sans inventaire à jour, la supervision produit du bruit : la cartographie vient d’abord." }
      ]
    },
    {
      id: "projet",
      icone: "🏗️",
      role: "Chef de projet · ingénierie, EPC, intégrateur",
      cas: "Inspiré des missions ATOS — Société du Grand Paris et ALSTOM — Projet REM Montréal (réseau multi-services, vidéosurveillance, SIEM)",
      pitch: "Sur une installation neuve, la sécurité se gagne ou se perd dans les spécifications. " +
             "Ce parcours suit la chaîne d’un projet : méthode, exigences système, exigences composants, " +
             "développement, cascade fournisseurs.",
      etapes: [
        { url: "/methodologie", label: "Méthodologie",
          action: "Repérez où chaque activité de sécurité s’insère dans le cycle du projet.",
          gain: "Le calendrier de sécurité aligné sur celui du projet, au lieu de le suivre en retard.",
          tip: "Une exigence de sécurité arrivée après les études de détail coûte dix fois son prix — et se négocie mal." },
        { url: "/exigences-systeme", label: "Exigences système · 3-3",
          action: "Traduisez le niveau de sécurité cible en exigences vérifiables pour le CCTP.",
          gain: "Des exigences qu’un fournisseur peut chiffrer et qu’un recetteur peut contrôler.",
          tip: "Écrivez le critère de recette en même temps que l’exigence : une exigence non vérifiable n’est pas une exigence." },
        { url: "/exigences-composants", label: "Exigences composants · 4-2",
          action: "Fixez ce que doivent porter les équipements eux-mêmes — automates, IHM, équipements réseau.",
          gain: "Un filtre de sélection au catalogue, avant que le choix ne soit figé par un lot déjà attribué.",
          tip: "Exigez les certificats et la durée de support ANNONCÉE : un équipement en fin de vie contamine tout le cycle." },
        { url: "/developpement-securise", label: "Développement sécurisé · 4-1",
          action: "Vérifiez ce que votre fournisseur doit démontrer sur son propre processus de développement.",
          gain: "La sécurité d’un produit se joue chez celui qui le fabrique — cette étape le rend contrôlable.",
          tip: "Demandez les preuves de processus, pas une déclaration de conformité : la seconde ne s’audite pas." },
        { url: "/exigences-prestataires", label: "Exigences prestataires · 2-4",
          action: "Cadrez les obligations de vos prestataires d’intégration et de maintenance.",
          gain: "La cascade fournisseurs traitée à la source, quand elle se contractualise encore.",
          tip: "L’accès distant de maintenance est le point d’entrée le plus fréquent : traitez-le explicitement, jamais par renvoi." },
        { url: "/etudes-de-cas", label: "Études de cas",
          action: "Lisez comment ces sujets ont été traités sur des projets d’infrastructure comparables.",
          gain: "Des points de comparaison concrets pour arbitrer, plutôt que des principes généraux.",
          tip: "Les projets de transport ferroviaire concentrent la plupart des difficultés : multi-lots, multi-fournisseurs, longue durée." }
      ]
    },
    {
      id: "achats",
      icone: "📄",
      role: "Achats · contractualisation, appels d’offres",
      cas: "Inspiré de la mission Management OT — sous-station offshore (prestataire de services IACS, cascade fournisseurs)",
      pitch: "Vous devez qualifier des prestataires sur un sujet dont vous n’êtes pas expert, et l’écrire " +
             "dans un contrat. Ce parcours donne les critères, puis la manière de les rendre opposables.",
      etapes: [
        { url: "/exigences-prestataires", label: "Exigences prestataires · 2-4",
          action: "Prenez les exigences que la norme adresse aux prestataires de services IACS.",
          gain: "Une grille de qualification déjà normée — pas une liste maison discutable en négociation.",
          tip: "Citez la clause de la norme dans le CCTP : une exigence sourcée se discute moins qu’une exigence maison." },
        { url: "/referentiel", label: "Référentiel IEC 62443",
          action: "Vérifiez quelle partie de la norme s’applique à qui : exploitant, intégrateur, fournisseur de produit.",
          gain: "Vous cessez de demander à un fournisseur ce qui relève de l’intégrateur, et inversement.",
          tip: "Une certification produit ne couvre pas l’intégration : ce sont deux engagements distincts." },
        { url: "/audit-conformite", label: "Audit 62443",
          action: "Servez-vous de la grille d’audit comme grille d’évaluation des offres.",
          gain: "Une notation défendable en commission, point par point, avec sa référence normative.",
          tip: "Annoncez la grille dans le dossier de consultation : les réponses gagnent en précision." },
        { url: "/juridique", label: "Conseil juridique assisté",
          action: "Passez le projet de contrat au clausier fournisseurs et à la revue clause par clause.",
          gain: "Les clauses manquantes ou déséquilibrées repérées avant signature, avec leur fondement.",
          tip: "Réservé aux comptes connectés. La revue s’effectue en mémoire : le contrat n’est jamais conservé." },
        { url: "/contact", label: "Prendre contact",
          action: "Faites relire votre dossier de consultation avant publication.",
          gain: "Une exigence mal écrite se corrige avant l’appel d’offres ; après, elle se paie en avenants.",
          tip: "Le meilleur moment pour cet échange est celui où le CCTP est encore modifiable." }
      ]
    },
    {
      id: "direction",
      icone: "📊",
      role: "Direction générale · COMEX",
      cas: "Ancré sur l’art. 20 de NIS 2 : l’organe de direction approuve les mesures et en répond personnellement",
      pitch: "Vous n’avez ni le temps ni l’envie d’entrer dans la technique — mais NIS 2 vous rend " +
             "personnellement responsable de l’approbation des mesures. Ce parcours va droit aux décisions " +
             "qui vous reviennent.",
      etapes: [
        { url: "/nis2", label: "NIS 2",
          action: "Vérifiez si votre entité est concernée, à quel titre, et ce que le texte met à votre charge.",
          gain: "La réponse à la seule question qui décide de tout le reste : sommes-nous dans le champ ?",
          tip: "L’art. 20 ne délègue pas : l’organe de direction approuve les mesures et sa responsabilité peut être engagée." },
        { url: "/diagnostic", label: "Diagnostic express",
          action: "Obtenez en quelques minutes une évaluation de votre situation actuelle.",
          gain: "Un ordre de grandeur, sans mobiliser vos équipes ni lancer d’étude.",
          tip: "Suffisant pour décider s’il faut engager une démarche — pas pour la dimensionner." },
        { url: "/operating-model", label: "Operating Model & gouvernance",
          action: "Regardez qui doit décider quoi : direction, IT, OT, achats, juridique.",
          gain: "La répartition des rôles, première cause de blocage d’un programme quand elle reste implicite.",
          tip: "Le point de friction est presque toujours la frontière IT / OT : tranchez-la explicitement, par écrit." },
        { url: "/feuille-de-route", label: "Feuille de route",
          action: "Situez les jalons et les points de décision qui remonteront jusqu’à vous.",
          gain: "Les arbitrages anticipés au lieu d’être découverts en urgence à quinze jours d’une échéance.",
          tip: "Demandez que chaque jalon porte un nom de responsable — un jalon sans porteur glisse." },
        { url: "/etudes-de-cas", label: "Études de cas",
          action: "Voyez ce qu’ont réellement produit des missions comparables à la vôtre.",
          gain: "De quoi calibrer une ambition et un budget sur des références, pas sur une brochure.",
          tip: "Comparez à l’échelle et au secteur, pas au nom : un FPSO et une usine agroalimentaire ne se pilotent pas pareil." }
      ]
    },
    {
      id: "conformite",
      icone: "⚖️",
      role: "DPO · conformité, juridique, données",
      cas: "Inspiré de la mission Cybersécurité & Sûreté · IA Risk Management du SI (PIA / AIPD / RGPD, mapping des exigences)",
      pitch: "Vos textes se chevauchent sans se confondre : NIS 2, RGPD, IA Act, IEC 62443. Ce parcours " +
             "clarifie qui exige quoi, et où l’un s’arrête quand l’autre commence.",
      etapes: [
        { url: "/nis2", label: "NIS 2",
          action: "Identifiez le régime applicable, les obligations de notification et leurs délais.",
          gain: "Les échéances réglementaires — 24 h, 72 h, un mois — qui commandent tout dispositif de crise.",
          tip: "Le délai de 24 h court dès la connaissance de l’incident, pas dès sa qualification." },
        { url: "/conformite", label: "Dossier de conformité",
          action: "Regardez un registre de traitements et une qualification IA Act motivée, article par article.",
          gain: "Un modèle de ce qu’un contrôle attend, sur un cas réel plutôt que sur un gabarit vide.",
          tip: "Notez la forme autant que le fond : une classification IA Act non motivée équivaut à son absence." },
        { url: "/juridique", label: "Conseil juridique assisté",
          action: "Qualifiez votre entité, puis explorez les lectures possibles des textes qui vous concernent.",
          gain: "La qualification est calculée par règles, sans IA : le résultat est reproductible et chaque rattachement porte sa motivation.",
          tip: "Réservé aux comptes connectés. Les points d’interprétation ouverts sont présentés avec leurs lectures concurrentes, pas tranchés d’autorité." },
        { url: "/audit-conformite", label: "Audit 62443",
          action: "Reliez chaque obligation à une preuve documentaire existante.",
          gain: "Le passage de la déclaration d’intention au dispositif opposable en inspection.",
          tip: "Une obligation sans preuve rattachée est un point ouvert, quelle que soit la conviction de l’équipe." },
        { url: "/veille", label: "Veille cyber",
          action: "Suivez les évolutions réglementaires et les avis d’autorité.",
          gain: "Les changements anticipés au lieu d’être subis en urgence de mise en conformité.",
          tip: "Une lecture hebdomadaire suffit ; le mensuel arrive systématiquement trop tard sur les avis de sécurité." }
      ]
    },
    {
      id: "decouverte",
      icone: "🧭",
      role: "Première visite · comprendre l’essentiel",
      cas: "Parcours d’entrée — aucune connaissance préalable de l’IEC 62443 requise",
      pitch: "Vous entendez parler d’IEC 62443, de zones, de niveaux de sécurité, et vous voulez comprendre " +
             "de quoi il s’agit avant d’en discuter avec qui que ce soit. Cinq pages, dans l’ordre.",
      etapes: [
        { url: "/referentiel", label: "Référentiel IEC 62443",
          action: "Prenez la vue d’ensemble : à quoi sert chaque partie de la norme et à qui elle s’adresse.",
          gain: "La structure d’ensemble avant le détail — c’est ce qui manque le plus souvent au démarrage.",
          tip: "Ne cherchez pas à tout retenir : repérez seulement les deux ou trois parties qui vous concernent." },
        { url: "/glossaire-62443", label: "Glossaire · 1-2",
          action: "Fixez le vocabulaire : zone, conduit, SL-T, SL-A, IACS, CSMS.",
          gain: "De quoi suivre une réunion technique sans perdre le fil au troisième sigle.",
          tip: "La confusion SL-T (cible) / SL-A (atteint) est la plus fréquente, et la plus lourde de conséquences." },
        { url: "/secteurs", label: "Secteurs",
          action: "Trouvez votre secteur et ses contraintes propres.",
          gain: "Ce qui change réellement d’un secteur à l’autre — les principes, eux, ne changent pas.",
          tip: "Si votre secteur relève des infrastructures critiques, lisez NIS 2 immédiatement après." },
        { url: "/etudes-de-cas", label: "Études de cas",
          action: "Regardez à quoi ressemble une mission réelle, de son cadrage à ses livrables.",
          gain: "Le passage du concept au concret : ce qui se produit vraiment, et en combien de temps.",
          tip: "Repérez le livrable qui ressemble à ce dont vous avez besoin — c’est le meilleur point de départ d’une discussion." },
        { url: "/diagnostic", label: "Diagnostic express",
          action: "Situez votre installation en quelques questions.",
          gain: "Un premier repère chiffré, sans engagement et sans mobiliser personne.",
          tip: "Refaites-le après six mois de travaux : l’écart entre les deux mesures est plus parlant que chaque score isolé." }
      ]
    }
  ];

  /* ═══════════════════════════════════════════════════════════════════════
     État — conservé entre les pages
     ═══════════════════════════════════════════════════════════════════════ */
  function lire() {
    try {
      var v = JSON.parse(sessionStorage.getItem(CLE) || "null");
      if (!v || !trouver(v.id) || typeof v.i !== "number") return null;
      var p = trouver(v.id);
      if (v.i < 0 || v.i >= p.etapes.length) return null;
      return v;
    } catch (e) { return null; }
  }
  function ecrire(v) {
    try {
      if (v) sessionStorage.setItem(CLE, JSON.stringify(v));
      else sessionStorage.removeItem(CLE);
    } catch (e) { /* navigation privée : le parcours reste utilisable, sans mémoire */ }
  }
  function trouver(id) {
    for (var k = 0; k < PARCOURS.length; k++) if (PARCOURS[k].id === id) return PARCOURS[k];
    return null;
  }
  function esc(t) {
    return String(t == null ? "" : t)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function chemin() { return location.pathname.replace(/\/+$/, "") || "/"; }

  /* ═══════════════════════════════════════════════════════════════════════
     Style — injecté ici pour qu'aucune page n'ait à être modifiée
     ═══════════════════════════════════════════════════════════════════════ */
  var CSS = [
    /* Bouton du menu : pulsation LENTE (3,4 s). Un clignotement rapide est un
       signal d'alarme ; ici on veut attirer l'œil sans presser, et ne jamais
       gêner la lecture du reste du tiroir. */
    "@keyframes pcPulse{0%,100%{border-color:var(--line);box-shadow:0 0 0 0 rgba(45,212,191,0)}",
    "50%{border-color:var(--teal);box-shadow:0 0 14px 0 rgba(45,212,191,.35)}}",
    ".pc-open{display:flex;align-items:center;gap:9px;width:100%;margin:0 0 14px;padding:11px 13px;",
    "background:var(--panel2);border:1px solid var(--line);border-radius:9px;color:var(--ink);",
    "font:inherit;font-size:13px;font-weight:600;text-align:left;cursor:pointer;animation:pcPulse 3.4s ease-in-out infinite}",
    ".pc-open:hover{animation:none;border-color:var(--teal);color:var(--teal)}",
    ".pc-open .pc-sub{display:block;font-size:11px;font-weight:400;color:var(--muted2);margin-top:2px}",
    "@media(prefers-reduced-motion:reduce){.pc-open{animation:none}}",
    /* Modale */
    ".pc-modal{position:fixed;inset:0;z-index:4000;display:none;align-items:flex-start;justify-content:center;",
    "padding:24px 16px;background:rgba(20,8,4,.72);overflow-y:auto}",
    ".pc-modal.on{display:flex}",
    ".pc-card{width:100%;max-width:780px;background:var(--panel);border:1px solid var(--line);",
    "border-radius:14px;padding:22px 24px;margin:auto;min-width:0}",
    ".pc-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;margin-bottom:6px}",
    ".pc-eyebrow{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted2)}",
    ".pc-title{font-size:19px;font-weight:700;color:var(--ink);margin-top:3px}",
    ".pc-x{background:none;border:none;color:var(--muted2);font-size:26px;line-height:1;cursor:pointer;padding:0 4px}",
    ".pc-x:hover{color:var(--ink)}",
    ".pc-intro{font-size:13px;color:var(--muted);line-height:1.65;margin:8px 0 16px}",
    ".pc-select{width:100%;padding:11px 13px;font:inherit;font-size:13.5px;font-weight:600;color:var(--ink);",
    "background:var(--bg2);border:1px solid var(--line);border-radius:9px;cursor:pointer}",
    ".pc-select:focus{outline:2px solid var(--teal);outline-offset:2px}",
    /* Fiche du parcours */
    ".pc-fiche{margin-top:18px}",
    ".pc-fiche-head{display:flex;gap:12px;align-items:flex-start;margin-bottom:8px}",
    ".pc-fiche-ic{font-size:24px;line-height:1;flex-shrink:0}",
    ".pc-fiche-role{font-size:15px;font-weight:700;color:var(--ink)}",
    ".pc-fiche-pitch{font-size:12.5px;color:var(--muted);line-height:1.6;margin-top:4px}",
    ".pc-cas{font-size:11.5px;color:var(--muted2);border-left:2px solid var(--teal);padding-left:10px;",
    "margin:12px 0 16px;line-height:1.55}",
    ".pc-etape{border:1px solid var(--line);border-radius:10px;padding:13px 15px;background:var(--bg2);min-width:0}",
    ".pc-etape.pc-ici{border-color:var(--teal);background:rgba(45,212,191,.07)}",
    ".pc-e-top{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}",
    ".pc-num{flex-shrink:0;width:24px;height:24px;border-radius:50%;background:var(--panel2);color:var(--ink);",
    "font-family:var(--mono);font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center}",
    ".pc-etape.pc-ici .pc-num{background:var(--teal);color:#0d2b28}",
    ".pc-e-label{font-size:13.5px;font-weight:600;color:var(--ink);flex:1;min-width:0}",
    ".pc-go{flex-shrink:0;font:inherit;font-size:12px;font-weight:600;padding:6px 11px;border-radius:7px;",
    "cursor:pointer;border:1px solid var(--teal);background:rgba(45,212,191,.12);color:var(--teal);text-decoration:none}",
    ".pc-go:hover{filter:brightness(1.18)}",
    ".pc-cle{flex-shrink:0;font-family:var(--mono);font-size:9.5px;letter-spacing:.06em;",
    "text-transform:uppercase;color:var(--amber);border:1px solid var(--amber);border-radius:999px;",
    "padding:3px 8px;white-space:nowrap}",
    ".pc-e-d{font-size:12.5px;color:var(--muted);line-height:1.6;margin-bottom:5px;overflow-wrap:anywhere}",
    ".pc-e-d b{color:var(--ink)}",
    ".pc-e-tip{font-size:12px;color:var(--muted2);line-height:1.55;margin-top:7px;padding-left:10px;",
    "border-left:2px solid var(--line)}",
    ".pc-fleche{text-align:center;color:var(--muted2);font-size:15px;line-height:1;margin:7px 0}",
    /* Bandeau de continuité */
    "@keyframes pcDot{0%,100%{opacity:1}50%{opacity:.3}}",
    ".pc-bandeau{position:fixed;left:0;right:0;bottom:0;z-index:3900;display:none;align-items:center;",
    "justify-content:space-between;gap:14px;flex-wrap:wrap;padding:10px 16px;background:var(--panel);",
    "border-top:1px solid var(--line);box-shadow:0 -6px 22px rgba(0,0,0,.34)}",
    ".pc-bandeau.on{display:flex}",
    ".pc-b-g{display:flex;align-items:center;gap:13px;flex-wrap:wrap;min-width:0}",
    ".pc-live{display:inline-flex;align-items:center;gap:7px;padding:4px 10px;border:1px solid var(--line);border-radius:20px}",
    ".pc-live i{width:8px;height:8px;border-radius:50%;background:var(--teal);animation:pcDot 1.5s ease-in-out infinite}",
    ".pc-live span{font-family:var(--mono);font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted2)}",
    ".pc-b-role{font:inherit;font-size:12px;font-weight:600;color:var(--ink);background:none;",
    "border:1px solid var(--line);border-radius:20px;padding:5px 11px;cursor:pointer;max-width:260px;",
    "overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    ".pc-b-role:hover{border-color:var(--teal);color:var(--teal)}",
    ".pc-b-prog{display:flex;flex-direction:column;gap:5px;min-width:0}",
    ".pc-b-step{font-size:12.5px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    ".pc-b-dots{display:flex;gap:5px}",
    ".pc-dot{width:8px;height:8px;border-radius:50%;background:var(--line)}",
    ".pc-dot.fait{background:var(--green)}",
    ".pc-dot.ici{background:var(--teal);box-shadow:0 0 0 2px rgba(45,212,191,.28)}",
    ".pc-b-d{display:flex;align-items:center;gap:8px;flex-wrap:wrap}",
    ".pc-b-btn{font:inherit;font-size:12px;font-weight:600;padding:7px 12px;border-radius:8px;cursor:pointer;",
    "border:1px solid var(--line);background:var(--panel2);color:var(--ink);text-decoration:none;",
    "max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    ".pc-b-btn:hover{border-color:var(--teal);color:var(--teal)}",
    ".pc-b-suiv{border-color:var(--teal);background:rgba(45,212,191,.14);color:var(--teal)}",
    ".pc-b-x{background:none;border:none;color:var(--muted2);font-size:22px;line-height:1;cursor:pointer;padding:0 5px}",
    ".pc-b-x:hover{color:var(--ink)}",
    "@media(max-width:640px){.pc-b-btn{max-width:130px}.pc-live span{display:none}.pc-b-role{max-width:140px}",
    ".pc-card{padding:18px 16px}}",
    "@media(prefers-reduced-motion:reduce){.pc-live i{animation:none}}"
  ].join("");

  function poserStyle() {
    if (document.getElementById("pc-style")) return;
    var s = document.createElement("style");
    s.id = "pc-style";
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     Modale de sélection
     ═══════════════════════════════════════════════════════════════════════ */
  function ouvrir(idPre) {
    poserStyle();
    var m = document.getElementById("pc-modal");
    if (!m) {
      m = document.createElement("div");
      m.id = "pc-modal";
      m.className = "pc-modal";
      document.body.appendChild(m);
      m.addEventListener("click", function (e) { if (e.target === m) fermer(); });
    }
    var opts = '<option value="">— Sélectionnez votre rôle —</option>'
      + PARCOURS.map(function (p) {
          return '<option value="' + esc(p.id) + '">' + esc(p.icone + "  " + p.role) + "</option>";
        }).join("");
    m.innerHTML = '<div class="pc-card" role="dialog" aria-modal="true" aria-label="Parcours guidés">'
      + '<div class="pc-head"><div><div class="pc-eyebrow">Par où commencer</div>'
      + '<div class="pc-title">Parcours guidés</div></div>'
      + '<button class="pc-x" type="button" aria-label="Fermer">×</button></div>'
      + '<p class="pc-intro">Une trentaine de pages, et aucune évidente au premier abord : un RSSI, '
      + 'un acheteur et un directeur général n’ont ni la même question ni le même ordre de lecture. '
      + 'Choisissez votre rôle — chaque parcours reprend la séquence d’une mission réellement conduite. '
      + 'Les étapes marquées <b>🔒 Compte requis</b> ouvrent le référentiel détaillé, réservé aux comptes : vous le savez avant de cliquer.</p>'
      + '<select class="pc-select" id="pc-select" aria-label="Votre rôle">' + opts + "</select>"
      + '<div id="pc-fiche"></div></div>';
    m.querySelector(".pc-x").addEventListener("click", fermer);
    var sel = m.querySelector("#pc-select");
    sel.addEventListener("change", function () { fiche(this.value); });
    m.classList.add("on");
    if (idPre) { sel.value = idPre; fiche(idPre); }
    else sel.focus();
    document.addEventListener("keydown", echap);
  }
  function echap(e) { if (e.key === "Escape") fermer(); }
  function fermer() {
    var m = document.getElementById("pc-modal");
    if (m) m.classList.remove("on");
    document.removeEventListener("keydown", echap);
  }

  function fiche(id) {
    var h = document.getElementById("pc-fiche");
    if (!h) return;
    if (!id) { h.innerHTML = ""; return; }
    var p = trouver(id);
    if (!p) { h.innerHTML = ""; return; }
    var ici = chemin();
    var etapes = p.etapes.map(function (e, i) {
      var courante = e.url === ici;
      return '<div class="pc-etape' + (courante ? " pc-ici" : "") + '">'
        + '<div class="pc-e-top"><span class="pc-num">' + (i + 1) + "</span>"
        + '<span class="pc-e-label">' + esc(e.label) + (courante ? " · vous y êtes" : "") + "</span>"
        + (reserve(e.url) ? '<span class="pc-cle" title="Cette page demande un compte">🔒 Compte requis</span>' : "")
        + '<a class="pc-go" href="' + esc(e.url) + '" data-pc-go="' + esc(p.id) + "|" + i + '">'
        + (courante ? "Rester ici" : "Aller à cette page") + " →</a></div>"
        + '<div class="pc-e-d"><b>À faire :</b> ' + esc(e.action) + "</div>"
        + '<div class="pc-e-d"><b>Ce que vous y gagnez :</b> ' + esc(e.gain) + "</div>"
        + (e.tip ? '<div class="pc-e-tip">' + esc(e.tip) + "</div>" : "")
        + "</div>";
    }).join('<div class="pc-fleche">↓</div>');

    h.innerHTML = '<div class="pc-fiche">'
      + '<div class="pc-fiche-head"><span class="pc-fiche-ic">' + esc(p.icone) + "</span>"
      + '<div><div class="pc-fiche-role">' + esc(p.role) + "</div>"
      + '<div class="pc-fiche-pitch">' + esc(p.pitch) + "</div></div></div>"
      + '<div class="pc-cas">' + esc(p.cas) + "</div>"
      + etapes + "</div>";

    h.querySelectorAll("[data-pc-go]").forEach(function (a) {
      a.addEventListener("click", function (ev) {
        var d = this.getAttribute("data-pc-go").split("|");
        ecrire({ id: d[0], i: parseInt(d[1], 10) });
        if (this.getAttribute("href") === ici) {   // déjà sur la page : pas de rechargement
          ev.preventDefault();
          fermer();
          bandeau();
        }
      });
    });
  }

  /* ═══════════════════════════════════════════════════════════════════════
     Bandeau de continuité — reconstruit à chaque page
     ═══════════════════════════════════════════════════════════════════════ */
  function bandeau() {
    poserStyle();
    var b = document.getElementById("pc-bandeau");
    if (!b) {
      b = document.createElement("div");
      b.id = "pc-bandeau";
      b.className = "pc-bandeau";
      document.body.appendChild(b);
    }
    var g = lire();
    if (!g) { b.classList.remove("on"); b.innerHTML = ""; return; }
    var p = trouver(g.id), n = p.etapes.length, i = g.i;
    var e = p.etapes[i], prec = i > 0 ? p.etapes[i - 1] : null, suiv = i < n - 1 ? p.etapes[i + 1] : null;

    var dots = "";
    for (var k = 0; k < n; k++) {
      dots += '<span class="pc-dot' + (k === i ? " ici" : (k < i ? " fait" : "")) + '"></span>';
    }
    var h = '<div class="pc-b-g">'
      + '<span class="pc-live" title="Parcours en cours"><i></i><span>Parcours en cours</span></span>'
      + '<button class="pc-b-role" type="button" data-pc-rouvrir="' + esc(p.id) + '" '
      + 'title="Revoir le parcours complet">' + esc(p.icone + " " + p.role) + "</button>"
      + '<div class="pc-b-prog"><span class="pc-b-step">Étape ' + (i + 1) + " / " + n
      + " · " + esc(e.label) + '</span><span class="pc-b-dots">' + dots + "</span></div></div>"
      + '<div class="pc-b-d">';
    if (prec) {
      h += '<a class="pc-b-btn" href="' + esc(prec.url) + '" data-pc-aller="' + (i - 1)
        + '" title="' + esc(prec.label) + '">← Précédent</a>';
    }
    if (suiv) {
      h += '<a class="pc-b-btn pc-b-suiv" href="' + esc(suiv.url) + '" data-pc-aller="' + (i + 1)
        + '" title="' + (reserve(suiv.url) ? "Cette page demande un compte" : esc(suiv.label))
        + '">Suivant : ' + (reserve(suiv.url) ? "🔒 " : "") + esc(suiv.label) + " →</a>";
    } else {
      h += '<button class="pc-b-btn pc-b-suiv" type="button" data-pc-fin="1">Terminer ✓</button>';
    }
    h += '<button class="pc-b-x" type="button" data-pc-fin="1" aria-label="Quitter le parcours" '
      + 'title="Quitter le parcours">×</button></div>';
    b.innerHTML = h;
    b.classList.add("on");

    b.querySelectorAll("[data-pc-aller]").forEach(function (a) {
      a.addEventListener("click", function () {
        ecrire({ id: g.id, i: parseInt(this.getAttribute("data-pc-aller"), 10) });
      });
    });
    b.querySelectorAll("[data-pc-fin]").forEach(function (x) {
      x.addEventListener("click", function () { ecrire(null); bandeau(); });
    });
    var r = b.querySelector("[data-pc-rouvrir]");
    if (r) r.addEventListener("click", function () { ouvrir(this.getAttribute("data-pc-rouvrir")); });
  }

  /* Si l'utilisateur navigue AILLEURS que vers l'étape prévue (un lien du menu,
     un retour arrière), le parcours ne le suit pas de force : le bandeau reste
     affiché sur la dernière étape connue. On se contente de recaler l'index
     quand la page atteinte correspond bien à une étape du parcours — le retour
     arrière du navigateur redevient alors cohérent avec la progression. */
  function recaler() {
    var g = lire();
    if (!g) return;
    var p = trouver(g.id), ici = chemin();
    for (var k = 0; k < p.etapes.length; k++) {
      if (p.etapes[k].url === ici && k !== g.i) { ecrire({ id: g.id, i: k }); return; }
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     Amorçage
     ═══════════════════════════════════════════════════════════════════════ */
  window.parcoursOuvrir = function (id) { ouvrir(id || null); };
  window.parcoursActif = function () { return lire(); };

  /* Révélation du bouton du menu. Appelée dans les deux sens, parce que l'ordre
     de chargement des deux scripts n'est pas garanti : nav.js appelle cette
     fonction s'il construit le tiroir après nous, et nous la rappelons à
     l'amorçage si le tiroir existait déjà. */
  window.parcoursPret = function () {
    var b = document.getElementById("pc-open-drawer");
    if (b) b.removeAttribute("hidden");
  };

  function init() {
    poserStyle();
    window.parcoursPret();
    recaler();
    bandeau();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
