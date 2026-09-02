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

  /* Pages réservées aux comptes connectés. L'essentiel de la substance du site
     — la section IEC 62443, la méthodologie, l'audit, le conseil, les trois
     pages « centres de données » — est derrière l'inscription. Un parcours qui
     l'ignorerait enverrait le visiteur contre un mur de connexion sans
     prévenir : on l'annonce AVANT le clic, et la modale le promet en toutes
     lettres.

     CETTE LISTE A MENTI, ET VOICI COMMENT. Elle était écrite à la main, et la
     politique d'accès du site a changé sans elle : neuf pages visitées par des
     parcours — le diagnostic, NIS 2, le cockpit, la feuille de route,
     l'operating model, la maturité OT et les trois pages de centres de données
     — étaient devenues réservées et continuaient de s'annoncer libres. Rien
     n'avait planté ; la promesse « vous le savez avant de cliquer » était
     simplement devenue fausse pour un tiers des étapes.

     DEUX PROTECTIONS, PARCE QU'UNE SEULE NE SUFFIT PAS.
       1. La liste ci-dessous est comparée à `acces.py` par la recette : elle ne
          peut plus diverger en silence d'un déploiement à l'autre.
       2. Elle est RAFRAÎCHIE À L'EXÉCUTION depuis /api/acces — la route écrite
          précisément pour permettre de signaler avant le clic. La liste écrite
          ici n'est plus la vérité : elle est la réponse immédiate, celle qui
          tient tant que le serveur n'a pas répondu, et celle qui reste si le
          réseau ne répond pas du tout. */
  /* VINGT-NEUF ENTRÉES, IL EN RESTE TROIS. Le 2 septembre 2026 le site s'est
     ouvert, sauf l'ingénierie de projet Data Center. Vingt-six cadenas
     désignaient dès lors des pages qui s'ouvrent sans compte — et un cadenas
     de trop n'est pas une prudence : il décourage un clic qui aboutirait, et
     il use le cadenas là où il est mérité. C'est le défaut symétrique de celui
     que ce bloc corrigeait, et la même recette l'a vu. */
  var RESERVE = {
    "/strategie-durable-datacenter": 1, "/datacenter": 1,
    "/ingenierie-datacenter": 1,
    /* La quatrième page vendue, du 2 septembre 2026 : l'ingénierie de projet
       IA Factory rejoint la famille « ingénierie de projet », et son cadenas
       avec elle. */
    "/ingenierie-ia-factory": 1
  };
  /* Vrai tant qu'on ne sait pas le contraire. Un client connecté n'a aucun mur
     devant lui : lui coller un cadenas sur presque chaque étape serait un bruit
     qui, à force, ferait ignorer le cadenas là où il compte. */
  var CONNECTE = false;
  function reserve(url) { return !CONNECTE && RESERVE[url] === 1; }

  /* ═══════════════════════════════════════════════════════════════════════
     LE MOTEUR DE PERTINENCE — le croisement rôle × secteur, calculé

     POURQUOI UN ALGORITHME ET NON UNE IA À L'EXÉCUTION. Croiser un rôle et un
     secteur pour dire « ici, insistez sur ceci » est une DÉDUCTION, pas une
     interprétation : la bonne réponse est stable, vérifiable, et ne doit pas
     changer d'un visiteur à l'autre. Sur un contenu réglementaire et de
     sécurité, un modèle de langage appelé à chaud apporterait trois défauts et
     aucun avantage : une latence de plusieurs secondes à chaque ouverture, un
     coût par visiteur, et surtout le risque d'inventer une priorité fausse que
     personne ne pourrait auditer. Le site tient déjà cette ligne partout
     ailleurs (le juridique qualifie en Python, l'IA n'interprète que sur
     référentiel fermé). On reste dans cette ligne : ce moteur est déterministe,
     instantané, hors-ligne, et se relit.

     COMMENT. Chaque page porte un ou plusieurs AXES (gouvernance, analyse,
     technique…). Chaque secteur porte un PROFIL DE POIDS sur ces mêmes axes,
     tiré de son enjeu et de son piège réels. Le score d'une étape pour un
     croisement est la somme des poids du secteur sur les axes de l'étape. Trois
     sorties en découlent :
       - les PRIORITÉS : les étapes de l'itinéraire du rôle qui pèsent le plus
         pour CE secteur (l'ordre pédagogique du rôle est conservé — on met en
         relief, on ne ré-ordonne pas une séquence éprouvée) ;
       - l'AXE DOMINANT du croisement : là où l'itinéraire du rôle et les
         priorités du secteur se renforcent le plus (poids × présence) ;
       - le DÉTOUR : une étape propre au parcours du secteur, absente de
         l'itinéraire type du rôle, mais décisive ici — la vraie valeur ajoutée
         du croisement, celle qu'un simple placage de notes ne produit pas.
     ═══════════════════════════════════════════════════════════════════════ */

  /* Axes portés par chaque page. Un tableau VIDE est un choix explicite (page
     utilitaire, neutre pour le croisement), pas un oubli — la recette vérifie
     que toute URL de parcours a une entrée ici, vide ou non. */
  var AXES_URL = {
    "/diagnostic": ["analyse"],
    "/maturite-ot": ["analyse", "gouvernance"],
    "/analyse-de-risque": ["analyse", "technique"],
    "/programme-securite": ["gouvernance"],
    "/operating-model": ["gouvernance"],
    "/feuille-de-route": ["gouvernance", "continuite"],
    "/metriques-62443": ["preuve"],
    "/referentiel": ["gouvernance"],
    "/glossaire-62443": [],
    "/secteurs": ["analyse"],
    "/methodologie": ["exigences", "gouvernance"],
    "/exigences-systeme": ["exigences"],
    "/exigences-composants": ["exigences", "technique"],
    "/developpement-securise": ["exigences", "technique"],
    "/exigences-prestataires": ["tiers", "exigences"],
    "/technologies-securite": ["technique"],
    "/gestion-correctifs": ["technique", "continuite"],
    "/continuite-ot": ["continuite", "gouvernance"],
    "/gestion-des-changements": ["technique", "continuite", "gouvernance"],
    "/architecture-cible": ["technique", "tiers"],
    "/formation": ["gouvernance"],
    "/gouvernance-ia": ["gouvernance", "juridique"],
    "/demo": ["technique", "continuite"],
    "/veille": ["preuve"],
    "/audit-conformite": ["preuve", "juridique"],
    "/conformite": ["juridique", "preuve"],
    "/juridique": ["juridique", "tiers"],
    "/relecture-contrat": ["juridique", "tiers"],
    "/nis2": ["juridique"],
    "/etudes-de-cas": ["analyse"],
    /* Les trois pages « centres de données ». Elles ne relèvent pas de la
       cybersécurité : leur axe est l'analyse (ce qu'on mesure), la preuve (ce
       qu'on peut opposer) et la gouvernance (ce qu'on décide). Sans ces
       entrées, un parcours qui les traverse ne pondérait rien. */
    "/strategie-durable-datacenter": ["analyse", "gouvernance"],
    "/datacenter": ["analyse", "preuve"],
    "/ingenierie-datacenter": ["exigences", "preuve"],
    "/ingenierie-ia-factory": ["gouvernance", "analyse"],
    "/contact": []
  };

  /* Profil de poids de chaque secteur sur les axes (0 à 3). Tiré de l'enjeu et
     du piège DÉCLARÉS plus bas pour ce secteur — pas d'une intuition. Un poids
     de 3 désigne ce qui, dans ce secteur, fait tomber les installations. */
  var POIDS = {
    /* télémaintenance jamais refermée + disponibilité réseau */
    energie:       { gouvernance:1, analyse:2, technique:2, exigences:1, tiers:3, juridique:2, continuite:3, preuve:1 },
    /* inventaire d'un parc dispersé + continuité du service public */
    eau:           { gouvernance:2, analyse:3, technique:2, exigences:1, tiers:1, juridique:1, continuite:2, preuve:2 },
    /* segmenter sans arrêter les lignes + IIoT hors circuit */
    manufacturing: { gouvernance:1, analyse:3, technique:3, exigences:2, tiers:1, juridique:1, continuite:2, preuve:2 },
    /* procédés continus + équipements hors support */
    agro:          { gouvernance:1, analyse:2, technique:3, exigences:1, tiers:1, juridique:1, continuite:3, preuve:1 },
    /* sûreté du procédé (SIS) + qualification à ne pas invalider */
    chimie:        { gouvernance:1, analyse:2, technique:2, exigences:3, tiers:1, juridique:2, continuite:3, preuve:2 },
    /* accès prestataires nombreux et permanents + flux M2M */
    transport:     { gouvernance:1, analyse:2, technique:2, exigences:1, tiers:3, juridique:2, continuite:2, preuve:1 },
    /* DORA + registre des prestataires TIC */
    finance:       { gouvernance:2, analyse:1, technique:1, exigences:1, tiers:3, juridique:3, continuite:2, preuve:2 },
    /* sûreté classée + qualification rigoureuse des accès */
    nucleaire:     { gouvernance:2, analyse:2, technique:2, exigences:3, tiers:1, juridique:2, continuite:3, preuve:2 },
    /* cascade des donneurs d'ordre + souveraineté / secret défense */
    aero:          { gouvernance:2, analyse:1, technique:1, exigences:3, tiers:3, juridique:2, continuite:1, preuve:2 }
  };

  var AXE_LABEL = {
    gouvernance: "la gouvernance du programme",
    analyse: "l’analyse de risque et la cartographie",
    technique: "les moyens techniques et l’architecture",
    exigences: "les exigences opposables",
    tiers: "la maîtrise des tiers et des accès distants",
    juridique: "le cadre réglementaire",
    continuite: "la continuité et la sûreté du procédé",
    preuve: "la preuve et la mesure"
  };
  var AXE_COURT = {
    gouvernance: "Gouvernance", analyse: "Analyse de risque",
    technique: "Technique & architecture", exigences: "Exigences",
    tiers: "Tiers & accès", juridique: "Réglementaire",
    continuite: "Continuité & sûreté", preuve: "Preuve & mesure"
  };

  /* Cœur du moteur. Prend l'itinéraire du rôle, l'identifiant du secteur et le
     parcours court du secteur ; rend un objet exploitable tel quel par le rendu.
     N'ouvre rien, ne dépend d'aucun DOM : pur, donc éprouvable en recette. */
  function personnaliser(etapes, secId, secteurEtapes) {
    var poids = POIDS[secId];
    if (!poids || !etapes || !etapes.length) return null;

    var scored = etapes.map(function (e, i) {
      var axes = AXES_URL[e.url] || [];
      var score = 0, axeCle = null, wmax = -1;
      for (var k = 0; k < axes.length; k++) {
        var w = poids[axes[k]] || 0;
        score += w;
        if (w > wmax) { wmax = w; axeCle = axes[k]; }
      }
      return { i: i, url: e.url, label: e.label, score: score, axe: axeCle, axes: axes };
    });

    var total = 0, max = 0;
    scored.forEach(function (x) { total += x.score; if (x.score > max) max = x.score; });
    var moy = total / scored.length;

    /* Priorités : au plus deux étapes, nettement au-dessus de la moyenne de CET
       itinéraire. Le seuil dépend du croisement, jamais d'une constante — un
       itinéraire homogène ne désigne rien de force, un itinéraire contrasté
       fait ressortir ses points forts. */
    var seuil = Math.max(moy + 1, max * 0.7);
    var ranked = scored.slice().sort(function (a, b) { return b.score - a.score || a.i - b.i; });
    var prio = ranked.filter(function (x) { return x.score > 0 && x.score >= seuil; }).slice(0, 2);
    if (!prio.length && max > 0) {
      prio = ranked.filter(function (x) { return x.score === max; }).slice(0, 1);
    }

    /* Axe dominant du CROISEMENT : poids du secteur × nombre d'étapes du rôle
       qui le portent. Élevé seulement quand le secteur y tient ET que le chemin
       du rôle y passe — c'est précisément le « réglage fin » recherché. */
    var domAxe = null, domVal = -1;
    for (var a in poids) {
      if (!poids.hasOwnProperty(a)) continue;
      var occ = 0;
      scored.forEach(function (x) { if (x.axes.indexOf(a) >= 0) occ++; });
      var v = poids[a] * occ;
      if (v > domVal) { domVal = v; domAxe = a; }
    }

    /* Détour : une étape du parcours SECTEUR absente de l'itinéraire du rôle et
       qui pèse fort ici. C'est l'apport que le placage de notes ne donnait pas :
       le croisement peut AJOUTER une étape, pas seulement annoter les siennes. */
    var detour = null;
    if (secteurEtapes && secteurEtapes.length) {
      var presentes = {};
      etapes.forEach(function (e) { presentes[e.url] = 1; });
      var cand = secteurEtapes.map(function (e) {
        var axes = AXES_URL[e.url] || [], s = 0, ax = null, wm = -1;
        for (var k = 0; k < axes.length; k++) {
          var w = poids[axes[k]] || 0; s += w;
          if (w > wm) { wm = w; ax = axes[k]; }
        }
        return { url: e.url, label: e.label, score: s, axe: ax };
      }).filter(function (x) { return !presentes[x.url] && x.score > 0; })
        .sort(function (a, b) { return b.score - a.score; });
      if (cand.length) detour = cand[0];
    }

    var prioIdx = {};
    prio.forEach(function (x) { prioIdx[x.i] = x.axe; });
    return { scored: scored, prio: prio, prioIdx: prioIdx,
             domAxe: domAxe, detour: detour, moy: moy, max: max };
  }

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
             "mesurer, analyser, structurer, planifier, transmettre, prouver.",
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
        { url: "/formation", label: "Formation & transfert de compétences",
          action: "Confrontez chaque chantier de la feuille de route à la compétence qu’il suppose, " +
                  "chez l’exploitant comme chez l’intégrateur.",
          gain: "Le chaînon qui décide si les mesures seront appliquées ou contournées — une mesure " +
                "qui n’est pas comprise finit toujours par être contournée.",
          tip: "Formez les équipes d’exploitation AVANT la mise en service, pas après : une consigne " +
               "découverte le jour du démarrage est une consigne qui sera contournée le lendemain." },
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
        { url: "/gestion-des-changements", label: "Gestion des changements (MOC)",
          action: "Posez le circuit qui encadre toute modification sur le procédé : ce qui déclenche " +
                  "un MOC, qui l’instruit, qui l’autorise, ce qu’on en garde.",
          gain: "Le processus qui empêche votre architecture de dériver — un zonage juste à la mise " +
                "en service et faux dix-huit mois plus tard n’a protégé personne.",
          tip: "Le déclencheur le plus oublié n’est pas une modification technique : c’est un " +
               "changement de prestataire, qui apporte ses outils, ses accès et ses habitudes." },
        { url: "/demo", label: "Cockpit de supervision",
          action: "Regardez à quoi ressemble la supervision d’un parc industriel, événements et indicateurs.",
          gain: "De quoi juger si la détection apporte quelque chose chez vous, avant d’engager un projet.",
          tip: "Sans inventaire à jour, la supervision produit du bruit : la cartographie vient d’abord." },
        { url: "/continuite-ot", label: "Continuité d’activité & crise OT",
          action: "Fixez les objectifs de reprise en langage d’exploitant — combien de temps sans " +
                  "produire, combien de données de procédé perdues — puis éprouvez-les par un exercice.",
          gain: "La réponse à la question que toutes les autres étapes laissent ouverte : et si " +
                "malgré tout ça s’arrête, redémarre-t-on, et en combien de temps ?",
          tip: "Le PCA informatique ne couvre pas l’OT : une sauvegarde de serveurs sans sauvegarde " +
               "des CONFIGURATIONS d’automates ne redémarre pas une ligne." }
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
        { url: "/architecture-cible", label: "Architecture cible OT",
          action: "Traduisez les zones et les conduits en modèle en couches : DMZ industrielle, " +
                  "bastion, diode, et ce qui traverse réellement chaque frontière.",
          gain: "Le plan que les lots suivants devront respecter — c’est lui qui rend les exigences " +
                "composants chiffrables, et non l’inverse.",
          tip: "La console d’ingénierie est l’angle mort classique : elle parle à toutes les zones " +
               "et ne figure dans aucune. Placez-la explicitement, ou elle les reliera toutes." },
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
        { url: "/relecture-contrat", label: "Relecture de contrat assistée",
          action: "Passez la version reçue au playbook : les écarts sont relevés clause par clause, " +
                  "avec la position de repli et la ligne rouge de chacune.",
          gain: "Une position de négociation préparée avant la séance, et non improvisée pendant — " +
                "avec, pour chaque écart, ce que vous pouvez concéder et ce que vous ne pouvez pas.",
          tip: "Les écarts sont calculés par règles, pas interprétés : deux relectures du même " +
               "contrat donnent le même résultat, ce qu’une lecture humaine ne garantit jamais." },
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
          tip: "Comparez à l’échelle et au secteur, pas au nom : un FPSO et une usine agroalimentaire ne se pilotent pas pareil." },
        { url: "/ingenierie-ia-factory", label: "L’usine IA — étude de faisabilité chiffrée",
          action: "Choisissez votre secteur — banque, assurance, marchés, entité NIS 2 : il ajoute ses postes, " +
                  "ses jalons et ses cas d’usage typiques. Renseignez vos quantités et VOS prix unitaires, " +
                  "puis lisez la part non chiffrée AVANT le total.",
          gain: "Une étude de faisabilité assise sur vos chiffres, avec les dates réglementaires qui ne " +
                "glissent pas quand le projet glisse — et le compte de ce qui n’est pas encore chiffré.",
          tip: "Ouvrez d’abord le parcours guidé de la page : six rôles, et il met en relief la section qui " +
               "vous concerne au lieu de vous laisser devant dix." }
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
        { url: "/gouvernance-ia", label: "Governance by Design IA",
          action: "Posez les quatre volets attendus autour d’un usage d’IA : qui décide de son " +
                  "ouverture, qui en répond, ce qu’on journalise, et comment un nouvel usage entre.",
          gain: "Le passage de la QUALIFICATION d’un système IA à sa gouvernance — la classification " +
                "dit ce que le texte exige, elle ne dit pas qui l’applique ni quand.",
          tip: "Le point de contrôle qui manque presque toujours : la porte d’entrée des NOUVEAUX " +
               "usages. Sans elle, le registre est juste le jour où on l’écrit, et faux un trimestre après." },
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
      id: "dc-projet",
      icone: "🏗️",
      role: "Direction de projet · centre de données",
      cas: "Le fil d'un projet de centre de données, du document d'ouverture d'étude à la séquence d'ingénierie",
      pitch: "Vous portez un projet de centre de données et vous devez tenir trois promesses à la fois : " +
             "un site défendable devant un territoire, des chiffres opposables devant un vérificateur, et " +
             "un dossier qui passe les phases. Ce parcours suit l'ordre du PROJET — on choisit avant de " +
             "calculer, on calcule avant de s'engager.",
      etapes: [
        { url: "/strategie-durable-datacenter", label: "La stratégie de développement durable",
          action: "Répondez au questionnaire des quatre perspectives : ce que le projet défend, ce que " +
                  "ses parties prenantes disent, ce qui affecte ses résultats. La quatrième — la science — " +
                  "n'est pas demandée : elle est établie par les données.",
          gain: "Le document d'ouverture d'étude : les enjeux retenus, ceux qu'on écarte, et le programme " +
                "de travail qui en découle.",
          tip: "Répondez avec ceux qui exploiteront, pas seulement avec ceux qui décident : un enjeu " +
               "noté en comité et démenti sur site se paie à l'enquête publique." },
        { url: "/datacenter", label: "Énergie, eau et carbone — puis la décarbonation",
          action: "Saisissez le profil de l'installation, lancez le calcul, comparez les familles de " +
                  "refroidissement, puis suivez les deux voies : compter et déclarer d'un côté, réduire " +
                  "de l'autre.",
          gain: "Les trois grandeurs calculées ENSEMBLE, avec leur incertitude — et l'ordre dans lequel " +
                "les leviers doivent être épuisés.",
          tip: "Le taux de charge ne change pas le PUE au-dessus de 0,6, mais il commande l'énergie " +
               "annuelle : le laisser par défaut sur un site bien rempli sous-estime la facture d'un tiers." },
        { url: "/ingenierie-datacenter", label: "La séquence projet — MOE et ingénierie",
          action: "Choisissez votre filière et votre phase, et lisez ce que le moteur peut verser à ce " +
                  "stade — et ce qu'il faut avoir remplacé par une donnée réelle. Puis descendez la " +
                  "chaîne d'argent : section 6, les honoraires assis sur l'enveloppe reportée ; " +
                  "section 7, le coût des travaux poste par poste, prolongé par les honoraires " +
                  "que ces travaux portent.",
          gain: "La distinction entre un chiffre recevable en avant-projet et un chiffre opposable en " +
                "pièce contractuelle — et, en regard, ce que coûte l'ingénierie qui produira ces pièces.",
          tip: "Le facteur eau amont porte ±40 % et le carbone incorporé ±50 % — deux valeurs qui " +
               "passent en APS et ne passent plus en DCE. Repérez-les avant, pas après." }
      ]
    },
    {
      /* LE PARCOURS QUI MANQUAIT. Les deux parcours de centre de données mènent
         à la page d'ingénierie et s'arrêtent à sa porte : ils promettent « ce
         que coûte l'ingénierie » sans jamais dire par où l'on obtient un coût.
         Or l'ordre y est contraignant — quantités, puis travaux, puis
         honoraires — et le prendre à l'envers fait asseoir des honoraires sur
         une assiette qu'on n'a pas. */
      id: "dc-couts",
      icone: "📐",
      role: "Économie de la construction · le coût d’un centre de données",
      cas: "Du profil de l’installation au coût d’opération : les travaux d’abord, les honoraires qu’ils portent ensuite",
      pitch: "Vous devez produire un coût défendable, et le défendre poste par poste plutôt que par un " +
             "ratio au kilowatt. Ce parcours suit l’ordre qui contraint : on chiffre des quantités " +
             "avant des travaux, et des travaux avant des honoraires. Il ne vous donnera aucun prix — " +
             "le référentiel n’en porte pas, et il vous dira pourquoi.",
      etapes: [
        { url: "/datacenter", label: "Le profil de l’installation",
          action: "Saisissez la puissance informatique et lancez le calcul : c’est la grandeur dont " +
                  "tout le reste découle, et la seule qui n’a pas de valeur par défaut.",
          gain: "Les quantités qui se reprendront ensuite dans le chiffrage des travaux sans être " +
                "retapées — donc sans diverger.",
          tip: "Jamais la puissance souscrite, qui comprend le refroidissement : la confondre avec la " +
               "puissance informatique gonfle toutes les quantités qui en dépendent." },
        /* UNE SEULE ÉTAPE POUR LA PAGE D'INGÉNIERIE, et c'est une contrainte du
           moteur autant qu'un choix : la progression se compte par URL VISITÉE.
           Deux étapes pointant la même page seraient toutes deux cochées après
           une seule visite, et le parcours annoncerait deux tiers faits quand
           rien ne l'est. La suite — travaux puis honoraires — est portée par le
           fil vertical DANS la page, qui, lui, constate chaque calcul. */
        { url: "/ingenierie-datacenter", label: "Les travaux, puis les honoraires qu’ils portent",
          action: "Section 7 : choisissez la nature de l’opération — neuf, extension, réhabilitation des " +
                  "lots techniques, reprise d’un chantier interrompu, maintenance —, chiffrez les postes " +
                  "qu’elle porte avec VOS prix unitaires en disant d’où vient chacun, puis prolongez ce " +
                  "chiffrage par celui de la maîtrise d’œuvre, juste en dessous. Le fil vertical de la " +
                  "page marque où vous en êtes à chaque calcul.",
          gain: "Un total qui tient le compte de ce qui n’est PAS chiffré, une part technique calculée " +
                "au lieu d’être supposée, et le coût d’opération complet — travaux plus honoraires.",
          tip: "Ce qui change d’une nature à l’autre n’est pas un coefficient, c’est la liste des postes. " +
               "Et une mission dont un seul des deux taux est saisi reste OUVERTE : la moitié d’un taux " +
               "n’en est pas un, et un zéro silencieux ferait croire la mission gratuite." }
      ]
    },
    {
      id: "dc-durabilite",
      icone: "🌍",
      role: "Direction durabilité · RSE d'un exploitant de centres de données",
      cas: "Produire une déclaration opposable, et une trajectoire qui la suive",
      pitch: "Vous devez publier des chiffres qu'un tiers vérifiera, et démontrer une trajectoire. " +
             "Ce sont deux exercices distincts, et leur confusion produit les dossiers qu'un " +
             "vérificateur renvoie. Ce parcours les sépare, puis les rejoint à leurs points de " +
             "rendez-vous obligés.",
      etapes: [
        { url: "/datacenter", label: "Compter — le bilan énergie, eau et carbone",
          action: "Établissez le bilan de l'installation, puis suivez la voie « compter et déclarer » : " +
                  "périmètre, année de référence, inventaire, indicateurs normalisés, déclaration " +
                  "européenne, vérification.",
          gain: "La structure de l'exercice de déclaration, et la liste de ce qui bloque encore " +
                "chaque étape.",
          tip: "Une année de référence établie sur le taux de charge par défaut d'un formulaire n'est " +
               "pas une référence : toute réduction mesurée contre elle serait fictive." },
        { url: "/strategie-durable-datacenter", label: "Arbitrer — la matérialité au croisement",
          action: "Notez les vingt enjeux sur les trois perspectives qui vous appartiennent, et lisez " +
                  "les deux tensions nommées pour votre projet.",
          gain: "Ce que vous retenez, ce que vous écartez, et surtout ce que personne n'a encore " +
                "regardé — un enjeu non instruit n'est pas un enjeu mineur.",
          tip: "Un enjeu que les données donnent pour structurant et que personne ne soulève est le " +
               "cas le plus dangereux : il n'arrivera pas par une plainte, il arrivera par un fait." },
        { url: "/ingenierie-datacenter", label: "Prouver — les pièces, phase par phase",
          action: "Situez vos indicateurs dans la séquence projet et repérez le registre des pièces " +
                  "à remettre.",
          gain: "Le passage du tableau de bord au dossier : ce qu'on écrit, et ce qu'on REMET.",
          tip: "Les points de comptage se posent à la conception. Découvrir l'obligation de déclarer " +
               "après avoir figé le plan de comptage coûte une année de mesure." }
      ]
    },
    {
      id: "decouverte",
      icone: "🧭",
      role: "Première visite · comprendre l’essentiel",
      cas: "Parcours d’entrée — aucune connaissance préalable de l’IEC 62443 requise",
      pitch: "Vous entendez parler d’IEC 62443, de zones, de niveaux de sécurité, et vous voulez comprendre " +
             "de quoi il s’agit avant d’en discuter avec qui que ce soit. Cinq pages, dans l’ordre : " +
             "les deux premières sont en accès libre, les trois suivantes demandent un compte — vous " +
             "aurez donc de quoi juger avant d’en demander un.",
      /* L'ORDRE A CHANGÉ, ET POUR UNE RAISON QUI N'EST PAS PÉDAGOGIQUE. Ce
         parcours commençait par le référentiel, le glossaire, puis les
         secteurs. Depuis que la politique d'accès a fermé le référentiel
         détaillé, ses trois premières étapes ouvraient un formulaire de
         connexion : le parcours écrit pour celui qui n'a RIEN — pas même un
         compte — était le seul à ne rien lui montrer. Les deux pages ouvertes
         passent donc devant. La progression y perd un peu (on part du concret
         plutôt que de la structure) et le premier visiteur y gagne beaucoup :
         il voit avant de s'inscrire. */
      etapes: [
        { url: "/secteurs", label: "Secteurs",
          action: "Trouvez votre secteur et ses contraintes propres.",
          gain: "Ce qui change réellement d’un secteur à l’autre — les principes, eux, ne changent pas.",
          tip: "Commencez par ce qui vous est familier : le vocabulaire de la norme se retient beaucoup mieux posé sur une installation que vous connaissez." },
        { url: "/etudes-de-cas", label: "Études de cas",
          action: "Regardez à quoi ressemble une mission réelle, de son cadrage à ses livrables.",
          gain: "Le passage du concept au concret : ce qui se produit vraiment, et en combien de temps.",
          tip: "Repérez le livrable qui ressemble à ce dont vous avez besoin — c’est le meilleur point de départ d’une discussion." },
        { url: "/referentiel", label: "Référentiel IEC 62443",
          action: "Prenez la vue d’ensemble : à quoi sert chaque partie de la norme et à qui elle s’adresse.",
          gain: "La structure d’ensemble avant le détail — c’est ce qui manque le plus souvent au démarrage.",
          tip: "Ne cherchez pas à tout retenir : repérez seulement les deux ou trois parties qui vous concernent." },
        { url: "/glossaire-62443", label: "Glossaire · 1-2",
          action: "Fixez le vocabulaire : zone, conduit, SL-T, SL-A, IACS, CSMS.",
          gain: "De quoi suivre une réunion technique sans perdre le fil au troisième sigle.",
          tip: "La confusion SL-T (cible) / SL-A (atteint) est la plus fréquente, et la plus lourde de conséquences." },
        { url: "/diagnostic", label: "Diagnostic express",
          action: "Situez votre installation en quelques questions.",
          gain: "Un premier repère chiffré, sans engagement et sans mobiliser personne.",
          tip: "Refaites-le après six mois de travaux : l’écart entre les deux mesures est plus parlant que chaque score isolé." }
      ]
    }
  ];


  /* ═══════════════════════════════════════════════════════════════════════
     LES SECTEURS — liste indépendante, croisée avec les rôles

     COMMENT LES DEUX SE CROISENT, et pourquoi ainsi. Neuf rôles et neuf
     secteurs feraient quatre-vingt-un parcours à écrire à la main : personne
     ne les tiendrait à jour, et les trois quarts seraient du remplissage.
     (Ce commentaire annonçait « sept rôles » et « soixante-trois » : trois
     rôles ont été ajoutés depuis — dc-projet, dc-couts et dc-durabilite —
     sans que le compte soit repris. Une recette le mesure désormais sur les
     listes, et c'est pourquoi les chiffres ci-dessus ne sont plus écrits ici.)
     La division du travail est donc franche :

        LE RÔLE DONNE L'ITINÉRAIRE — quelles pages, dans quel ordre. C'est ce
        dont un rôle a besoin : un acheteur et un exploitant ne lisent pas les
        mêmes pages, et surtout pas dans le même ordre.

        LE SECTEUR DONNE CE QUI CHANGE EN ROUTE — le texte qui s'impose ici et
        pas ailleurs, la contrainte qui prime, le piège du métier. Un secteur
        ne réordonne pas la démarche : il en modifie le contenu.

     Concrètement, `notes` porte un commentaire sectoriel PAR PAGE, et seulement
     là où le secteur a réellement quelque chose à dire. Une note sur chaque
     page de chaque secteur serait vite du bruit — mieux vaut quatre notes
     justes que douze convenues.

     Chaque secteur garde par ailleurs son propre parcours court : choisi seul,
     il mène quelque part plutôt que d'afficher une fiche de lecture.
     ═══════════════════════════════════════════════════════════════════════ */
  var SECTEURS = [
    {
      id: "energie", icone: "⚡", nom: "Énergie & utilities",
      enjeu: "La disponibilité du réseau et la maîtrise des accès distants de télémaintenance, " +
             "sur des postes souvent isolés et sans personnel.",
      textes: "NIS 2 (entité essentielle dans la plupart des cas), directive CER sur la résilience " +
              "des entités critiques, IEC 62443, et le régime français des opérateurs d’importance vitale.",
      piege: "L’accès distant du constructeur, ouvert « le temps d’une intervention » il y a trois " +
             "ans et jamais refermé. C’est le point d’entrée le plus banal, et le plus efficace.",
      notes: {
        "/nis2": "Énergie : entité ESSENTIELLE dans la plupart des cas, pas simplement importante — " +
                 "le régime de contrôle est le plus strict, avec supervision a priori.",
        "/analyse-de-risque": "Les postes distants forment souvent une zone à eux seuls : leur " +
                              "isolement physique n’est pas un cloisonnement logique.",
        "/technologies-securite": "Le télécontrôle impose des protocoles anciens (IEC 60870-5-104, " +
                                  "DNP3) rarement authentifiés : la compensation passe par l’architecture.",
        "/gestion-correctifs": "Une fenêtre d’arrêt sur un poste source se négocie des mois à " +
                               "l’avance : le calendrier de correctifs suit celui du réseau, jamais l’inverse.",
        "/continuite-ot": "Sur des postes sans personnel, la reprise commence par un déplacement : " +
                          "comptez le temps de route dans vos objectifs, sinon ils sont faux dès l’écriture.",
        "/diagnostic": "Regardez d’abord vos accès distants de télémaintenance : c’est le point où l’écart entre le déclaré et le réel est le plus grand dans ce secteur.",
        "/etudes-de-cas": "La mission GRDF — Projet Biométhane est la plus proche de votre contexte : SI industriel réparti, EBIOS, PSSI industrielle.",
        "/feuille-de-route": "Adossez chaque chantier à un arrêt réseau déjà programmé : un arrêt supplémentaire ne se négocie pas deux fois.",
        "/referentiel": "Entrez par la 2-1 (programme) et la 3-3 (exigences système) : le télécontrôle relève surtout de ces deux parties.",
        "/audit-conformite": "Le point le plus souvent en écart : la gestion des accès distants — comptes partagés, absence de révocation, aucune traçabilité des interventions."
      },
      etapes: [
        { url: "/nis2", label: "NIS 2",
          action: "Vérifiez votre qualification — essentielle ou importante — et les obligations qui en découlent.",
          gain: "Le régime applicable, qui commande le niveau d’exigence de tout le reste.",
          tip: "L’énergie relève presque toujours des entités essentielles : partez de cette hypothèse et cherchez à l’infirmer." },
        { url: "/secteurs", label: "Secteurs · Énergie & utilities",
          action: "Lisez les contraintes propres au télécontrôle et aux postes distants.",
          gain: "Les points de vigilance de votre métier, avant d’ouvrir la norme.",
          tip: "Comparez avec votre parc réel : les écarts pointent vos priorités." },
        { url: "/analyse-de-risque", label: "Analyse de risque · 3-2",
          action: "Découpez votre réseau en zones, en traitant les postes distants comme un cas à part.",
          gain: "Une segmentation qui tient compte de la dispersion géographique, pas seulement du synoptique.",
          tip: "Une liaison louée n’est pas un cloisonnement : elle traverse des infrastructures que vous ne maîtrisez pas." },
        { url: "/demo", label: "Cockpit de supervision",
          action: "Regardez la détection d’anomalies sur des flux de télécontrôle.",
          gain: "De quoi juger si la supervision apporte quelque chose sur un réseau dispersé.",
          tip: "Sur des sites sans personnel, la détection est souvent la seule alerte possible." },
        { url: "/feuille-de-route", label: "Feuille de route",
          action: "Séquencez en tenant compte des fenêtres d’arrêt réseau.",
          gain: "Un calendrier compatible avec l’exploitation, donc tenable.",
          tip: "Adossez chaque chantier à un arrêt déjà programmé plutôt que d’en demander un nouveau." }
      ]
    },
    {
      id: "eau", icone: "💧", nom: "Eau & assainissement",
      enjeu: "Inventorier un parc dispersé et sécuriser des liaisons hétérogènes sans coupure de service.",
      textes: "NIS 2 (eau potable et eaux usées sont deux secteurs distincts de l’annexe I), " +
              "IEC 62443, et les obligations de continuité du service public.",
      piege: "Le parc réel dépasse toujours l’inventaire connu : postes de relevage oubliés, " +
             "modems installés par un exploitant précédent, capteurs ajoutés au fil de l’eau.",
      notes: {
        /* Une seule note par page — cette clé était écrite DEUX fois ici, et la
           seconde effaçait la première sans bruit : le lecteur ne voyait qu’une
           moitié de ce qu’on avait à lui dire. Les deux sont réunies. */
        "/nis2": "Eau potable et eaux usées relèvent de DEUX entrées distinctes de l’annexe I : " +
                 "vérifiez les deux si vous exploitez les deux. Le régime est celui des entités " +
                 "essentielles dès que les seuils de taille sont atteints.",
        "/analyse-de-risque": "Commencez par l’inventaire : une analyse de risque sur un parc " +
                              "incomplet produit une fausse assurance, pire que pas d’analyse.",
        "/continuite-ot": "Votre objectif de reprise n’est pas un choix d’exploitant : il est fixé " +
                          "par la continuité du service public, et se défend devant la collectivité.",
        "/technologies-securite": "Les liaisons hétérogènes — GSM, radio, fibre, ADSL — n’offrent " +
                                  "pas le même niveau de confiance : le traitement doit être différencié.",
        "/diagnostic": "Commencez par une question simple : savez-vous dire combien de postes distants vous exploitez ? Si non, c’est le premier chantier, avant toute mesure de sécurité.",
        "/etudes-de-cas": "Aucune mission publiée dans l’eau à ce jour. La plus transposable est GRDF — Biométhane : même problématique de SI industriel réparti sur un large territoire.",
        "/feuille-de-route": "Priorisez par criticité pour la continuité du service public : c’est l’argument qui porte devant une collectivité, plus que le risque cyber en soi.",
        "/referentiel": "Entrez par la 2-1 : sans programme ni inventaire, les exigences techniques n’ont rien sur quoi s’appliquer.",
        "/audit-conformite": "Le point le plus souvent en écart : l’inventaire des actifs, incomplet sur les postes distants ajoutés au fil des années."
      },
      etapes: [
        { url: "/secteurs", label: "Secteurs · Eau & assainissement",
          action: "Situez les contraintes de la télégestion étendue.",
          gain: "Le cadre métier avant la technique : ce qu’un parc dispersé sur un territoire impose, " +
                "et qu’aucune démarche pensée pour un site unique ne prévoit.",
          tip: "La dispersion du parc est ici la difficulté première, avant la sophistication des attaques." },
        { url: "/diagnostic", label: "Diagnostic express",
          action: "Évaluez votre situation, inventaire compris.",
          gain: "Un constat de départ, y compris sur ce que vous ne connaissez pas encore.",
          tip: "Si vous ne savez pas dire combien de postes distants vous exploitez, c’est le premier chantier." },
        { url: "/analyse-de-risque", label: "Analyse de risque · 3-2",
          action: "Segmentez en tenant compte de la dispersion et de l’hétérogénéité des liaisons.",
          gain: "Des zones qui reflètent la réalité du terrain, pas l’organigramme.",
          tip: "Un poste de relevage isolé et un site central ne relèvent pas du même niveau de sécurité cible." },
        { url: "/maturite-ot", label: "Assessment de maturité OT",
          action: "Mesurez votre capacité à exploiter et maintenir ce parc dans la durée.",
          gain: "L’écart entre ce que vous déployez et ce que vous saurez tenir.",
          tip: "Une mesure que personne ne maintiendra n’est pas une mesure, c’est une dette." },
        { url: "/feuille-de-route", label: "Feuille de route",
          action: "Priorisez les sites selon leur criticité pour la continuité du service.",
          gain: "Un ordre de traitement défendable devant une collectivité.",
          tip: "La continuité du service public est votre argument le plus solide en commission." }
      ]
    },
    {
      id: "manufacturing", icone: "🏭", nom: "Manufacturing & usine connectée",
      enjeu: "Segmenter sans arrêter les lignes, et encadrer les nouveaux usages connectés (MES, IIoT).",
      textes: "NIS 2 pour la fabrication de certains produits, directive Machines pour les " +
              "équipements neufs, IEC 62443 pour l’ensemble.",
      piege: "La segmentation décidée sur plan et jamais appliquée, parce qu’aucun arrêt de ligne " +
             "n’a pu être obtenu. Un schéma cible sans jalon d’application reste un schéma.",
      notes: {
        "/analyse-de-risque": "Segmentez par ligne de production plutôt que par atelier : c’est le " +
                              "découpage qui correspond à l’impact réel d’un arrêt.",
        "/exigences-composants": "L’IIoT arrive souvent par les achats métier, hors du circuit IT : " +
                                 "les exigences composants sont votre seul point de contrôle en amont.",
        "/architecture-cible": "Votre piège se joue ici : une cible dessinée sans jalon d’application " +
                               "reste un schéma. Datez chaque frontière sur un arrêt de ligne déjà " +
                               "programmé, sinon elle ne sera jamais posée.",
        "/gestion-correctifs": "Adossez les correctifs aux arrêts de maintenance planifiés — un " +
                               "arrêt supplémentaire ne vous sera pas accordé deux fois.",
        "/technologies-securite": "La segmentation par pare-feu industriel se déploie sans arrêt si " +
                                  "elle est posée en coupure transparente d’abord, filtrante ensuite.",
        "/diagnostic": "Chiffrez d’abord le coût d’un arrêt de ligne : c’est ce chiffre qui débloquera le budget, pas le niveau de risque théorique.",
        "/etudes-de-cas": "Aucune mission manufacturing publiée telle quelle. La sous-station offshore en est proche par la démarche : management de sécurité OT chez un prestataire IACS.",
        "/feuille-de-route": "Construisez le plan autour des arrêts de maintenance déjà planifiés — un arrêt supplémentaire pour la sécurité s’obtient rarement.",
        "/referentiel": "Entrez par la 3-2 (zones et conduits) : la segmentation IT/OT est le sujet dominant de l’usine connectée.",
        "/audit-conformite": "Le point le plus souvent en écart : une segmentation définie sur plan mais jamais appliquée, faute d’arrêt de ligne obtenu.",
        "/nis2": "La fabrication relève de l’annexe II (entités importantes) — sauf activités spécifiques renvoyant à l’annexe I. Le seuil de taille décide."
      },
      etapes: [
        { url: "/secteurs", label: "Secteurs · Manufacturing",
          action: "Repérez les contraintes de l’usine connectée : MES, IIoT, interconnexion IT/OT.",
          gain: "Le cadre avant la méthode : d’où vient réellement l’interconnexion — rarement d’une " +
                "décision unique, presque toujours d’une accumulation de projets métier.",
          tip: "L’interconnexion croissante est ici le moteur du risque : elle vient rarement d’une décision unique." },
        { url: "/analyse-de-risque", label: "Analyse de risque · 3-2",
          action: "Découpez par ligne de production et identifiez les conduits entre IT et OT.",
          gain: "Une cible de segmentation reliée à l’impact d’exploitation.",
          tip: "Chiffrez l’arrêt d’une ligne : c’est ce chiffre qui débloque le budget, pas le risque théorique." },
        { url: "/exigences-systeme", label: "Exigences système · 3-3",
          action: "Fixez le niveau de sécurité cible par zone de production.",
          gain: "Des exigences opposables aux intégrateurs de vos lignes.",
          tip: "Un même atelier peut porter deux niveaux cibles : ne nivelez pas par le haut sans le justifier." },
        { url: "/exigences-composants", label: "Exigences composants · 4-2",
          action: "Cadrez ce que doivent porter les équipements IIoT avant leur achat.",
          gain: "Un filtre en amont, quand le choix est encore ouvert.",
          tip: "Associez les achats métier : l’IIoT entre le plus souvent par eux, pas par la DSI." },
        { url: "/feuille-de-route", label: "Feuille de route",
          action: "Séquencez la segmentation sur les arrêts déjà planifiés.",
          gain: "Un déploiement qui n’exige aucun arrêt supplémentaire.",
          tip: "Une segmentation déployée en coupure transparente puis activée progressivement évite l’arrêt sec." }
      ]
    },
    {
      id: "agro", icone: "🥫", nom: "Agroalimentaire",
      enjeu: "Protéger des procédés continus avec des équipements de générations multiples, " +
             "difficiles voire impossibles à corriger.",
      textes: "NIS 2 (production et transformation de denrées alimentaires), " +
              "IEC 62443, et les obligations de traçabilité sanitaire.",
      piege: "L’automate de 1998 qui pilote la chaîne du froid, hors support depuis dix ans, " +
             "et dont personne ne connaît plus le programme. Le patcher est exclu ; l’ignorer aussi.",
      notes: {
        "/technologies-securite": "Un équipement hors support ne se corrige pas : la compensation " +
                                  "par l’architecture — cloisonnement, filtrage, surveillance — est la seule voie.",
        "/gestion-correctifs": "Sur procédé continu, l’arrêt se compte en pertes de production : " +
                               "distinguez ce qui doit être corrigé de ce qui doit être isolé.",
        "/analyse-de-risque": "La chaîne du froid mérite sa propre zone : son impact n’est pas " +
                              "qu’économique, il est sanitaire et donc réglementaire.",
        "/continuite-ot": "Votre objectif de reprise se heurte à une horloge qui ne se négocie " +
                          "pas : celle de la chaîne du froid. Au-delà, le redémarrage n’est plus " +
                          "un enjeu de production mais un rappel produit.",
        "/diagnostic": "Recensez d’abord les équipements hors support : ils déterminent ce qui est possible, bien avant le niveau de maturité de l’organisation.",
        "/etudes-de-cas": "Aucune mission agroalimentaire publiée. GRDF — Biométhane s’en rapproche par la nature du procédé : continu, avec des automates de générations diverses.",
        "/feuille-de-route": "Les arrêts saisonniers sont vos seules vraies fenêtres d’intervention : le plan se construit autour d’eux, pas l’inverse.",
        "/referentiel": "Entrez par la 2-3 (correctifs) et la TR 3-1 (technologies) : votre difficulté est le parc ancien, pas la doctrine.",
        "/audit-conformite": "Le point le plus souvent en écart : des équipements hors support sans mesure de compensation documentée.",
        "/nis2": "Production et transformation de denrées alimentaires relèvent de l’annexe II : entité importante, sous réserve des seuils de taille."
      },
      etapes: [
        { url: "/secteurs", label: "Secteurs · Agroalimentaire",
          action: "Repérez les contraintes des procédés continus et du parc de générations multiples.",
          gain: "Le cadre métier, avant d’ouvrir la norme.",
          tip: "Le legacy est ici la règle, pas l’exception : une démarche qui suppose un parc récent ne s’appliquera pas." },
        { url: "/analyse-de-risque", label: "Analyse de risque · 3-2",
          action: "Isolez les procédés continus et la chaîne du froid dans des zones dédiées.",
          gain: "Une segmentation qui reflète l’impact sanitaire, pas seulement industriel.",
          tip: "Un incident sur la chaîne du froid devient un rappel produit : l’impact déborde largement l’usine." },
        { url: "/technologies-securite", label: "Technologies de sécurité · TR 3-1",
          action: "Identifiez ce qui compense l’impossibilité de corriger un équipement ancien.",
          gain: "Des mesures applicables à un parc qu’on ne remplacera pas demain.",
          tip: "Cloisonner autour d’un équipement vulnérable vaut mieux qu’attendre un remplacement qui ne viendra pas." },
        { url: "/gestion-correctifs", label: "Gestion des correctifs · 2-3",
          action: "Distinguez ce qui se corrige de ce qui doit être isolé faute de correctif.",
          gain: "Une politique tenable, plutôt qu’un objectif que le parc rend inatteignable.",
          tip: "Écrivez noir sur blanc les équipements non corrigeables et leur compensation : c’est ce qu’un auditeur cherche." },
        { url: "/feuille-de-route", label: "Feuille de route",
          action: "Alignez les chantiers sur les arrêts saisonniers de production.",
          gain: "Un calendrier qui épouse celui de l’usine.",
          tip: "Les arrêts saisonniers sont vos seules vraies fenêtres : construisez le plan autour d’eux." }
      ]
    },
    {
      id: "chimie", icone: "⚗️", nom: "Chimie & pharma",
      enjeu: "Concilier cybersécurité, intégrité des procédés et contraintes de qualification " +
             "des systèmes en environnement réglementé.",
      textes: "NIS 2, directive Seveso III pour les sites classés, IEC 61511 pour les systèmes " +
              "instrumentés de sécurité, IEC 62443, et les référentiels GxP pour le pharmaceutique.",
      piege: "La modification de sécurité qui invalide une qualification. En environnement " +
             "réglementé, un correctif non qualifié peut coûter plus cher que la vulnérabilité.",
      notes: {
        "/analyse-de-risque": "La SÛRETÉ prime sur la sécurité : une mesure qui dégraderait un " +
                              "système instrumenté de sécurité (SIS) est à écarter, pas à arbitrer.",
        "/gestion-correctifs": "Tout correctif sur un système qualifié entraîne une requalification : " +
                               "le coût réel d’un patch n’est pas celui du patch.",
        "/gestion-des-changements": "Ne créez pas un MOC parallèle : le change control GxP existe " +
                                    "déjà et fait autorité. Ajoutez-y l’instruction cyber comme un " +
                                    "avis, plutôt qu’un second circuit qui le contredira.",
        "/programme-securite": "Articulez le CSMS avec le système qualité existant plutôt que de " +
                               "le doubler — en environnement GxP, deux systèmes de management s’annulent.",
        "/exigences-systeme": "Séparez explicitement les fonctions de sûreté des fonctions de " +
                              "contrôle : leur mélange est le défaut de conception le plus coûteux à corriger.",
        "/diagnostic": "Distinguez dès le départ les systèmes instrumentés de sécurité du contrôle-commande : le régime applicable n’est pas le même, et le mélange coûte cher à défaire.",
        "/etudes-de-cas": "Aucune mission chimie ou pharma publiée. La plus proche par les contraintes de sûreté est le FPSO Karish & Tanin : procédé, sûreté, environnement réglementé.",
        "/feuille-de-route": "Groupez les chantiers par campagne de requalification : dix modifications requalifiées ensemble coûtent le prix d’une seule.",
        "/referentiel": "Entrez par la 3-2, en tenant compte de l’IEC 61511 : la frontière entre sûreté et contrôle-commande structure tout le reste.",
        "/audit-conformite": "Le point le plus souvent en écart : la traçabilité des modifications sur systèmes qualifiés, exigée par le régime réglementaire autant que par la norme.",
        "/nis2": "La fabrication de produits chimiques relève de l’annexe II. Attention : le classement Seveso ne vaut PAS qualification NIS 2 — les deux régimes se cumulent sans se recouvrir."
      },
      etapes: [
        { url: "/secteurs", label: "Secteurs · Chimie & pharma",
          action: "Repérez l’articulation entre sûreté, qualité et cybersécurité.",
          gain: "Les trois contraintes posées ensemble, comme elles se présentent sur site.",
          tip: "En cas de conflit, la sûreté tranche : ce n’est pas négociable, et c’est un bon point de départ." },
        { url: "/analyse-de-risque", label: "Analyse de risque · 3-2",
          action: "Traitez les systèmes instrumentés de sécurité comme une zone à part entière.",
          gain: "Une frontière nette entre ce qui protège les personnes et ce qui pilote le procédé.",
          tip: "Un SIS partagé avec le contrôle-commande n’est plus un SIS : la séparation se vérifie physiquement." },
        { url: "/exigences-systeme", label: "Exigences système · 3-3",
          action: "Déclinez le niveau cible en tenant compte des contraintes de qualification.",
          gain: "Des exigences compatibles avec un environnement réglementé.",
          tip: "Anticipez le coût de requalification dès l’écriture de l’exigence, pas au moment du déploiement." },
        { url: "/programme-securite", label: "Programme de sécurité · 2-1",
          action: "Adossez le CSMS au système qualité déjà en place.",
          gain: "Un seul système de management, donc un seul jeu de preuves à tenir.",
          tip: "Vos procédures de gestion du changement existent déjà : étendez-les plutôt que d’en créer." },
        { url: "/gestion-correctifs", label: "Gestion des correctifs · 2-3",
          action: "Intégrez la requalification au processus de correctifs.",
          gain: "Une politique qui tient compte du coût réel d’un patch dans votre environnement.",
          tip: "Groupez les correctifs par campagne de requalification : un patch isolé coûte autant que dix." }
      ]
    },
    {
      id: "transport", icone: "🚚", nom: "Transport & logistique",
      enjeu: "Cloisonner les prestataires et superviser des flux machine-à-machine nombreux, " +
             "sur des automatismes en télémaintenance permanente.",
      textes: "NIS 2 (transport terrestre, aérien, maritime, ferroviaire selon le cas), " +
              "IEC 62443, et les exigences sectorielles d’homologation pour le ferroviaire.",
      piege: "Un accès prestataire par équipement, chacun ouvert en permanence, aucun tracé. " +
             "La télémaintenance est ici la norme d’exploitation, pas l’exception.",
      notes: {
        "/exigences-prestataires": "Le cœur du sujet dans ce secteur : cadrez l’accès distant " +
                                   "explicitement, équipement par équipement, avec traçabilité et révocation.",
        "/analyse-de-risque": "Chaque accès de télémaintenance est un conduit : recensez-les tous, " +
                              "y compris ceux qu’aucun schéma ne montre.",
        "/demo": "Les flux machine-à-machine sont nombreux et réguliers : leur régularité rend " +
                 "la détection d’anomalie particulièrement efficace ici.",
        "/diagnostic": "Comptez vos accès prestataires avant toute chose : dans ce secteur, le chiffre réel dépasse presque toujours l’estimation.",
        "/etudes-de-cas": "Deux missions de votre secteur sont publiées : ATOS — Société du Grand Paris et ALSTOM — Projet REM (Montréal). Lisez-les en premier.",
        "/feuille-de-route": "Commencez par les prestataires les plus NOMBREUX, pas les plus critiques : ici, c’est le volume d’accès qui fait le risque.",
        "/referentiel": "Entrez par la 2-4 (prestataires) : dans ce secteur, l’essentiel du risque passe par les tiers.",
        "/audit-conformite": "Le point le plus souvent en écart : des accès de télémaintenance permanents, non tracés, souvent ouverts depuis la mise en service.",
        "/nis2": "Le transport figure à l’annexe I, mode par mode (aérien, ferroviaire, routier, maritime) : vérifiez chaque activité séparément."
      },
      etapes: [
        { url: "/secteurs", label: "Secteurs · Transport & logistique",
          action: "Repérez les contraintes des automatismes et de la télémaintenance.",
          gain: "Le cadre métier, notamment la dépendance aux prestataires.",
          tip: "Comptez vos accès prestataires avant de lire la suite : le chiffre surprend souvent." },
        { url: "/exigences-prestataires", label: "Exigences prestataires · 2-4",
          action: "Cadrez les obligations et surtout les modalités d’accès distant.",
          gain: "Une reprise de contrôle sur ce qui est aujourd’hui souvent permanent et non tracé.",
          tip: "Passez d’un accès permanent à un accès sur demande, tracé et borné dans le temps." },
        { url: "/analyse-de-risque", label: "Analyse de risque · 3-2",
          action: "Recensez tous les conduits, accès de télémaintenance compris.",
          gain: "La carte réelle des points d’entrée, au-delà du schéma officiel.",
          tip: "Interrogez les équipes de maintenance, pas la documentation : ils savent par où ils passent." },
        { url: "/demo", label: "Cockpit de supervision",
          action: "Évaluez la détection sur des flux machine-à-machine réguliers.",
          gain: "Une détection d’autant plus efficace que les flux sont prévisibles.",
          tip: "La régularité des flux logistiques rend l’anomalie visible : c’est un avantage, exploitez-le." },
        { url: "/feuille-de-route", label: "Feuille de route",
          action: "Priorisez la reprise en main des accès distants.",
          gain: "Le chantier au meilleur rapport effet/effort dans ce secteur.",
          tip: "Commencez par les prestataires les plus nombreux, pas les plus critiques : le volume fait le risque ici." }
      ]
    },
    {
      id: "finance", icone: "🏦", nom: "Assurance & services financiers",
      enjeu: "Absorber l’accélération des vulnérabilités découvertes par l’IA — exposition, " +
             "remédiation à l’échelle, SOC augmenté et gestion de crise.",
      textes: "DORA (résilience opérationnelle numérique, applicable depuis janvier 2025), " +
              "NIS 2, RGPD, et les exigences de l’ACPR sur les tiers critiques TIC.",
      piege: "Le registre des prestataires TIC exigé par DORA, tenu au niveau groupe et jamais " +
             "réconcilié avec la réalité des filiales. Le contrôle porte sur l’écart.",
      notes: {
        "/nis2": "DORA prime sur NIS 2 pour le secteur financier au titre de la lex specialis : " +
                 "vérifiez lequel des deux régimes s’applique à chaque entité du groupe.",
        "/exigences-prestataires": "DORA impose un registre des prestataires TIC et des stratégies " +
                                   "de sortie approuvées par l’organe de direction (art. 28.8).",
        "/juridique": "Le clausier couvre les clauses contractuelles obligatoires de DORA — " +
                      "leur absence est un manquement en soi, indépendamment de tout incident.",
        "/relecture-contrat": "Passez d’abord les contrats de vos prestataires TIC CRITIQUES : " +
                              "ce sont eux que le régulateur ouvrira, et l’article 30 y attend des " +
                              "clauses nommées, pas un équivalent de bonne foi.",
        "/gouvernance-ia": "L’IA qui augmente votre SOC est elle-même un système à gouverner : " +
                           "elle décide de ce qui est remonté, donc de ce qui ne l’est pas.",
        "/demo": "Le SOC augmenté par l’IA répond ici à un enjeu de volume : la remédiation à " +
                 "l’échelle prime sur la détection unitaire.",
        "/diagnostic": "Le sujet n’est pas la sophistication mais l’échelle : mesurez votre capacité de remédiation, pas seulement votre exposition.",
        "/etudes-de-cas": "La mission menée pour un groupe d’assurance international est directement transposable : cartographie de l’exposition, chaînes de patching, SOC augmenté par l’IA, gestion de crise.",
        "/feuille-de-route": "Traitez d’abord les entités portant les fonctions critiques : c’est par elles que le régulateur commencera.",
        "/referentiel": "La 62443 vous concerne peu directement, sauf pour vos infrastructures techniques : votre cadre est DORA.",
        "/audit-conformite": "Le point le plus souvent en écart : le registre des prestataires TIC, tenu au niveau groupe et non réconcilié avec les filiales."
      },
      etapes: [
        { url: "/secteurs", label: "Secteurs · Assurance & finance",
          action: "Repérez les enjeux d’exposition et de remédiation à l’échelle groupe.",
          gain: "Le cadre : ici le volume et la vitesse priment sur la sophistication.",
          tip: "L’accélération des vulnérabilités découvertes par l’IA change l’échelle, pas la nature du problème." },
        { url: "/nis2", label: "NIS 2 · articulation avec DORA",
          action: "Déterminez, entité par entité, lequel des deux régimes s’applique.",
          gain: "La clarté sur le texte applicable, première condition d’un dispositif défendable.",
          tip: "DORA prime pour les entités financières ; les filiales non financières du groupe peuvent relever de NIS 2." },
        { url: "/exigences-prestataires", label: "Exigences prestataires · 2-4",
          action: "Structurez le registre des prestataires TIC et les stratégies de sortie.",
          gain: "Deux exigences DORA explicitement contrôlées, souvent les plus mal tenues.",
          tip: "Les stratégies de sortie doivent être approuvées par l’organe de direction : ce n’est pas un document technique." },
        { url: "/juridique", label: "Conseil juridique assisté",
          action: "Passez vos contrats fournisseurs au clausier et à la revue clause par clause.",
          gain: "Les clauses obligatoires de DORA vérifiées avant le prochain contrôle.",
          tip: "Réservé aux comptes connectés. Le contrat est analysé en mémoire, jamais conservé." },
        { url: "/feuille-de-route", label: "Feuille de route",
          action: "Séquencez la mise en conformité DORA sur les entités du groupe.",
          gain: "Une trajectoire par entité plutôt qu’un plan groupe inapplicable localement.",
          tip: "Traitez d’abord les entités portant les fonctions critiques : le régulateur commencera par là." }
      ]
    },
    {
      id: "nucleaire", icone: "☢️", nom: "Nucléaire",
      enjeu: "Concilier cybersécurité, exigences de sûreté et gestion rigoureuse des accès " +
             "et des interventions, en défense en profondeur.",
      textes: "Régime des installations nucléaires de base et prescriptions de l’ASN, " +
              "IEC 62645 (systèmes d’instrumentation et de contrôle des centrales), " +
              "IEC 62443 pour les systèmes non classés, NIS 2, régime OIV.",
      piege: "Appliquer à un système classé de sûreté une mesure conçue pour l’informatique " +
             "industrielle courante. Le classement de sûreté commande, et il ne se discute pas.",
      notes: {
        "/analyse-de-risque": "Le classement de sûreté PRÉCÈDE l’analyse de risque cyber et la " +
                              "contraint : on ne redéfinit pas des zones qui sont déjà prescrites.",
        "/exigences-systeme": "Pour les systèmes classés, l’IEC 62645 prime sur la 62443 : " +
                              "la seconde s’applique au périmètre non classé.",
        "/gestion-correctifs": "Toute modification sur un système classé relève d’un processus " +
                               "d’autorisation dédié : le délai n’est pas technique, il est réglementaire.",
        "/gestion-des-changements": "Le MOC ne se substitue pas au régime d’autorisation de " +
                                    "l’installation : il l’alimente. Le classement de sûreté décide " +
                                    "de ce qui peut être modifié, le MOC de comment on l’instruit.",
        "/architecture-cible": "Le zonage de sûreté PRÉCÈDE l’architecture cyber et la contraint : " +
                               "aucun conduit ne doit traverser une frontière de classement, " +
                               "fût-ce par une diode.",
        "/exigences-prestataires": "La gestion des intervenants est ici un sujet en soi : " +
                                   "habilitation, accompagnement, traçabilité des actes.",
        "/diagnostic": "Un diagnostic générique ne remplace pas le cadre réglementaire de l’installation : lisez-le comme un point d’entrée, jamais comme une évaluation de conformité.",
        "/etudes-de-cas": "Aucune mission nucléaire publiée. Le FPSO Karish & Tanin en est le plus proche pour le raisonnement sûreté / cybersécurité en environnement hautement contraint.",
        "/feuille-de-route": "Chaque modification sur un système classé porte un délai d’autorisation, pas seulement un délai technique : le calendrier doit l’intégrer dès la conception.",
        "/referentiel": "La 62443 s’applique au périmètre NON classé. Pour les systèmes classés de sûreté, l’IEC 62645 et les prescriptions de l’autorité priment.",
        "/audit-conformite": "Le point le plus souvent en écart : la traçabilité des interventions et des habilitations, contrôlée avec une exigence particulière ici.",
        "/nis2": "Le nucléaire relève de l’annexe I (énergie) et, en France, du régime des opérateurs d’importance vitale : les régimes se cumulent avec les prescriptions de l’autorité de sûreté."
      },
      etapes: [
        { url: "/secteurs", label: "Secteurs · Nucléaire",
          action: "Repérez l’articulation entre sûreté classée, défense en profondeur et cyber.",
          gain: "L’ordre de préséance des exigences, qui structure tout le reste.",
          tip: "En cas de doute, la sûreté prime — et se démontre auprès de l’autorité, pas en interne." },
        { url: "/referentiel", label: "Référentiel IEC 62443",
          action: "Situez ce qui relève de la 62443 et ce qui relève des référentiels de sûreté.",
          gain: "Une frontière nette entre deux corpus qu’on confond souvent.",
          tip: "La 62443 s’applique pleinement au périmètre non classé : c’est déjà un large domaine." },
        { url: "/analyse-de-risque", label: "Analyse de risque · 3-2",
          action: "Conduisez l’analyse dans le cadre du classement de sûreté existant.",
          gain: "Une analyse qui s’insère dans le dispositif réglementaire au lieu de le heurter.",
          tip: "Ne proposez jamais un redécoupage qui traverserait une frontière de classement." },
        { url: "/exigences-prestataires", label: "Exigences prestataires · 2-4",
          action: "Cadrez habilitation, accompagnement et traçabilité des intervenants.",
          gain: "La maîtrise des interventions, point de contrôle central dans ce secteur.",
          tip: "La traçabilité des actes vaut ici autant que la prévention : elle est exigée en cas d’écart." },
        { url: "/programme-securite", label: "Programme de sécurité · 2-1",
          action: "Articulez le CSMS avec le système de management de la sûreté.",
          gain: "Un dispositif présentable à l’autorité, cohérent avec l’existant.",
          tip: "Un dispositif cyber parallèle au dispositif sûreté ne passera pas l’inspection." }
      ]
    },
    {
      id: "aero", icone: "✈️", nom: "Aerospace & défense",
      enjeu: "Protéger la propriété industrielle et répondre aux exigences de souveraineté " +
             "sans ralentir la production, sur des sites multiples.",
      textes: "NIS 2, régime de la protection du secret de la défense nationale, " +
              "loi de programmation militaire, régime OIV, IEC 62443, " +
              "et les exigences de sécurité imposées par les donneurs d’ordre.",
      piege: "La cascade des exigences des donneurs d’ordre, différentes d’un client à l’autre, " +
             "empilées sans cadre commun. On finit par tenir dix référentiels au lieu d’un.",
      notes: {
        "/exigences-prestataires": "La cascade fonctionne dans les deux sens : vous la subissez de " +
                                   "vos donneurs d’ordre et la transmettez à vos fournisseurs.",
        "/relecture-contrat": "Relisez d’abord les contrats REÇUS de vos donneurs d’ordre : c’est " +
                              "là que s’écrivent les exigences que vous devrez ensuite répercuter, " +
                              "souvent sans marge de négociation en aval.",
        "/programme-securite": "Construisez UN référentiel interne qui couvre le plus exigeant de " +
                               "vos clients, plutôt que d’en tenir un par contrat.",
        "/analyse-de-risque": "La propriété industrielle est ici un actif au même titre que la " +
                              "disponibilité : l’exfiltration compte autant que l’arrêt.",
        "/developpement-securise": "Les exigences des donneurs d’ordre portent de plus en plus sur " +
                                   "le processus de développement lui-même, pas seulement sur le produit.",
        "/diagnostic": "Évaluez aussi l’exposition de votre propriété industrielle : dans ce secteur, l’exfiltration silencieuse pèse autant que l’arrêt de production.",
        "/etudes-de-cas": "Aucune mission aerospace publiée. La sous-station offshore illustre le sujet central de votre secteur : la cascade d’exigences vers les fournisseurs.",
        "/feuille-de-route": "Traitez un site pilote de bout en bout avant d’élargir : sur plusieurs sites, le déploiement parallèle multiplie les erreurs au lieu de gagner du temps.",
        "/referentiel": "Entrez par la 2-4 et la 4-1 : votre sujet est la cascade d’exigences, subie et transmise.",
        "/audit-conformite": "Le point le plus souvent en écart : des référentiels multiples empilés par client, sans socle interne commun ni preuves consolidées.",
        "/nis2": "La fabrication aéronautique relève de l’annexe II, mais les activités de défense peuvent relever d’un régime spécifique qui prime : vérifiez activité par activité."
      },
      etapes: [
        { url: "/secteurs", label: "Secteurs · Aerospace & défense",
          action: "Repérez les enjeux de souveraineté, de confidentialité et de multi-sites.",
          gain: "Le cadre, où la confidentialité pèse autant que la disponibilité.",
          tip: "Ici, l’exfiltration silencieuse est un scénario au moins aussi probable que l’arrêt de production." },
        { url: "/exigences-prestataires", label: "Exigences prestataires · 2-4",
          action: "Cadrez la cascade fournisseurs, dans les deux sens.",
          gain: "Un cadre unique là où s’empilent aujourd’hui les exigences de chaque client.",
          tip: "Cartographiez d’abord ce que vos donneurs d’ordre exigent : la convergence est souvent plus forte qu’il n’y paraît." },
        { url: "/programme-securite", label: "Programme de sécurité · 2-1",
          action: "Construisez un référentiel interne couvrant le plus exigeant de vos clients.",
          gain: "Un seul dispositif à tenir, au lieu d’un par contrat.",
          tip: "Le surcoût du plus exigeant est presque toujours inférieur au coût de dix référentiels parallèles." },
        { url: "/developpement-securise", label: "Développement sécurisé · 4-1",
          action: "Structurez le processus de développement de vos propres produits.",
          gain: "La réponse à une exigence de plus en plus systématique des donneurs d’ordre.",
          tip: "Les preuves de processus se constituent en continu : les reconstituer a posteriori est très coûteux." },
        { url: "/feuille-de-route", label: "Feuille de route",
          action: "Séquencez le déploiement sur vos différents sites.",
          gain: "Un plan multi-sites, où le premier site sert de modèle aux suivants.",
          tip: "Traitez un site pilote de bout en bout avant d’élargir : le déploiement parallèle multiplie les erreurs." }
      ]
    }
  ];

  /* Le moteur et ses données sont désormais définis. Sous Node (recette), on
     les expose et on s'arrête AVANT tout code de page : rien ci-dessous ne
     tourne sans navigateur, et le moteur s'éprouve avec les VRAIES données,
     sans les recopier — donc sans risque de divergence entre test et site. */
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      AXES_URL: AXES_URL, POIDS: POIDS, AXE_LABEL: AXE_LABEL, AXE_COURT: AXE_COURT,
      personnaliser: personnaliser, PARCOURS: PARCOURS, SECTEURS: SECTEURS
    };
  }
  /* Le moteur est aussi offert au navigateur pour un éventuel usage tiers ;
     le rendu ci-dessous l'appelle directement, il n'en dépend pas. */
  if (typeof window !== "undefined") {
    window.PCMoteur = {
      personnaliser: personnaliser, AXES_URL: AXES_URL, POIDS: POIDS,
      AXE_LABEL: AXE_LABEL, AXE_COURT: AXE_COURT
    };
  }
  if (typeof document === "undefined") return;

  function trouverSecteur(id) {
    for (var k = 0; k < SECTEURS.length; k++) if (SECTEURS[k].id === id) return SECTEURS[k];
    return null;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     État — conservé entre les pages
     ═══════════════════════════════════════════════════════════════════════ */
  function lire() {
    try {
      var v = JSON.parse(sessionStorage.getItem(CLE) || "null");
      if (!v || !trouver(v.id) || typeof v.i !== "number") return null;
      var p = trouver(v.id);
      if (v.i < 0 || v.i >= p.etapes.length) return null;
      /* `vus` : les pages du parcours REELLEMENT ATTEINTES pendant cette
         session. C'est ce qui distingue « fait » de « dépassé » — la
         progression par position peignait en vert les étapes SAUTEES. */
      if (!Array.isArray(v.vus)) v.vus = [];
      v.vus = v.vus.filter(function (u) { return typeof u === "string"; });
      if (typeof v.bloque !== "string") v.bloque = null;
      return v;
    } catch (e) { return null; }
  }

  /* Une visite CONSTATEE : l'URL n'entre dans `vus` que si elle est une étape
     du parcours actif, et jamais deux fois. Le module constate qu'une page a
     été atteinte — il ne prétend pas mesurer le travail qu'on y a fait, et le
     libellé à l'écran dit exactement cela. */
  function marquerVisite(g, url) {
    var p = trouver(g.id);
    if (!p) return g;
    var estEtape = p.etapes.some(function (e) { return e.url === url; });
    if (estEtape && g.vus.indexOf(url) < 0) g.vus.push(url);
    return g;
  }
  function ecrire(v) {
    try {
      if (v) sessionStorage.setItem(CLE, JSON.stringify(v));
      else sessionStorage.removeItem(CLE);
    } catch (e) { /* navigation privée : le parcours reste utilisable, sans mémoire */ }
  }
  /* Résout un identifiant de parcours, qu'il désigne un RÔLE (« rssi ») ou un
     SECTEUR (« sec:energie »). Le bandeau, l'état conservé et le recalage
     n'ont ainsi qu'une seule notion de parcours à manipuler — sans quoi chaque
     fonction devrait redemander « rôle ou secteur ? » et finirait par diverger. */
  function trouver(id) {
    if (!id) return null;
    if (id.indexOf("sec:") === 0) {
      var x = trouverSecteur(id.slice(4));
      return x ? { id: id, icone: x.icone, role: x.nom, etapes: x.etapes, secteur: true } : null;
    }
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
    /* Deux listes côte à côte, empilées quand la place manque. Elles sont
       INDÉPENDANTES : chacune se choisit seule, et l'ensemble se lit comme un
       filtre, pas comme un formulaire à remplir dans l'ordre. */
    ".pc-selects{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(260px,100%),1fr));gap:12px}",
    ".pc-lab{display:block;min-width:0;font-family:var(--mono);font-size:10px;letter-spacing:.08em;",
    "text-transform:uppercase;color:var(--muted2)}",
    ".pc-lab .pc-select{margin-top:6px}",
    ".pc-croix{color:var(--teal);font-weight:400;margin:0 2px}",
    /* Bloc « ce que le secteur change » */
    ".pc-sect{border:1px solid var(--line);border-left:3px solid var(--teal);border-radius:0 10px 10px 0;",
    "background:var(--bg2);padding:12px 15px;margin:12px 0 16px;min-width:0}",
    ".pc-sect-t{font-size:13.5px;font-weight:700;color:var(--ink);margin-bottom:7px}",
    ".pc-sect-l{font-size:12.3px;color:var(--muted);line-height:1.6;margin-bottom:6px;overflow-wrap:anywhere}",
    ".pc-sect-l:last-child{margin-bottom:0}",
    ".pc-sect-l b{color:var(--ink)}",
    ".pc-sect-p b{color:var(--amber)}",
    /* Note sectorielle attachée à une étape */
    ".pc-e-sec{font-size:12px;color:var(--muted);line-height:1.55;margin-top:8px;padding:8px 11px;",
    "background:rgba(45,212,191,.07);border:1px solid rgba(45,212,191,.28);border-radius:8px;overflow-wrap:anywhere}",
    ".pc-e-sec b{color:var(--teal);font-weight:600}",
    /* Secteur rappelé dans le bandeau */
    ".pc-b-sec{font-family:var(--mono);font-size:10px;letter-spacing:.05em;color:var(--teal);",
    "border:1px solid var(--teal);border-radius:20px;padding:4px 10px;white-space:nowrap;",
    "overflow:hidden;text-overflow:ellipsis;max-width:200px}",
    /* Fiche du parcours */
    ".pc-fiche{margin-top:18px}",
    ".pc-fiche-head{display:flex;gap:12px;align-items:flex-start;margin-bottom:8px}",
    ".pc-fiche-ic{font-size:24px;line-height:1;flex-shrink:0}",
    ".pc-fiche-role{font-size:15px;font-weight:700;color:var(--ink)}",
    ".pc-fiche-pitch{font-size:12.5px;color:var(--muted);line-height:1.6;margin-top:4px}",
    ".pc-cas{font-size:11.5px;color:var(--muted2);border-left:2px solid var(--teal);padding-left:10px;",
    "margin:12px 0 16px;line-height:1.55}",
    /* Bloc « Priorités calculées » : la sortie du moteur de pertinence. Teinté
       ambre pour se distinguer du bloc sectoriel (teal) : l'un dit « ce que le
       secteur change », l'autre « par où commencer pour CE croisement ». */
    ".pc-prio{border:1px solid var(--amber);border-left:3px solid var(--amber);border-radius:0 10px 10px 0;",
    "background:rgba(245,158,11,.07);padding:12px 15px;margin:12px 0 16px;min-width:0}",
    ".pc-prio-t{font-size:13.5px;font-weight:700;color:var(--ink);margin-bottom:7px}",
    ".pc-prio-syn{font-size:12.5px;color:var(--muted);line-height:1.6;margin-bottom:8px;overflow-wrap:anywhere}",
    ".pc-prio-syn b{color:var(--ink)}",
    ".pc-prio-l{margin:0;padding-left:20px}",
    ".pc-prio-l li{font-size:12.3px;color:var(--muted);line-height:1.6;margin-bottom:5px;overflow-wrap:anywhere}",
    ".pc-prio-l li b{color:var(--ink)}",
    ".pc-prio-det{font-size:12.3px;color:var(--muted);line-height:1.6;margin-top:8px;padding-top:8px;",
    "border-top:1px dashed var(--line);overflow-wrap:anywhere}",
    ".pc-prio-det b{color:var(--amber)}",
    ".pc-prio-badge{flex-shrink:0;font-family:var(--mono);font-size:9.5px;letter-spacing:.06em;",
    "text-transform:uppercase;color:#0d2b28;background:var(--amber);border-radius:999px;",
    "padding:3px 8px;white-space:nowrap;font-weight:700}",
    ".pc-etape{border:1px solid var(--line);border-radius:10px;padding:13px 15px;background:var(--bg2);min-width:0}",
    /* CE QUI RESTE A FAIRE bat doucement en ambre ; CE QUI EST VISITE tient
       en vert, immobile. Cadence 1,8 s — la meme que les guidages de
       Sentinel, tres en dessous du seuil de photosensibilite (3 eclats/s).
       Seule la BORDURE anime : aucun texte ne change de fond, les contrastes
       du contenu sont constants a chaque phase. */
    "@keyframes pcAFaire{0%,100%{border-color:rgba(240,180,41,.55);box-shadow:0 0 0 0 rgba(240,180,41,0)}",
    "50%{border-color:var(--amber);box-shadow:0 0 12px 0 rgba(240,180,41,.35)}}",
    ".pc-etape.pc-e-reste{border:2px solid rgba(240,180,41,.55);animation:pcAFaire 1.8s ease-in-out infinite}",
    ".pc-etape.pc-e-fait{border:2px solid var(--green)}",
    "@media(prefers-reduced-motion:reduce){.pc-etape.pc-e-reste{animation:none;border-color:var(--amber)}}",
    ".pc-e-etat{flex-shrink:0;font-family:var(--mono);font-size:10px;letter-spacing:.05em;",
    "padding:2px 8px;border-radius:10px;white-space:nowrap}",
    ".pc-e-etat.fait{color:#0d2b1e;background:var(--green);font-weight:700}",
    ".pc-e-etat.reste{color:var(--amber);border:1px solid var(--amber)}",
    ".pc-compte{font-size:12.5px;color:var(--muted2);margin:2px 0 10px}",
    ".pc-compte-fait{color:var(--green);font-weight:700}",
    ".pc-compte-reste{color:var(--amber);font-weight:700}",
    ".pc-etape.pc-ici{border-color:var(--teal);background:rgba(45,212,191,.07)}",
    /* La visite prime la position : une etape courante ET visitee garde le
       fond teal du « vous y etes », mais son cadre dit la visite. */
    ".pc-etape.pc-ici.pc-e-fait{border-color:var(--green)}",
    ".pc-etape.pc-prio-etape{border-left:3px solid var(--amber)}",
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
    ".pc-dot.reste{background:none;border:1px solid var(--amber)}",
    ".pc-dot.ici{background:var(--teal);box-shadow:0 0 0 2px rgba(45,212,191,.28)}",
    ".pc-b-step.att{color:var(--amber)}",
    ".pc-b-mur a{color:var(--teal);font-weight:600}",
    ".pc-mur{font-family:var(--mono);font-size:10px;letter-spacing:.05em;color:var(--amber);",
    "border:1px solid var(--amber);border-radius:10px;padding:2px 9px;white-space:nowrap}",
    ".pc-b-mur{flex-basis:100%;font-size:11.5px;line-height:1.55;color:var(--muted);",
    "margin-top:8px;padding:8px 11px;border-left:3px solid var(--amber);",
    "background:rgba(240,180,41,.07);border-radius:0 6px 6px 0}",
    ".pc-b-mur b{color:var(--ink)}",
    ".pc-b-reste{font-family:var(--mono);font-size:10px;color:var(--amber);white-space:nowrap;",
    "animation:pcAFaireTxt 1.8s ease-in-out infinite}",
    /* Le texte ne bat que par sa LUEUR, jamais par sa couleur : l'ambre sur
       fond sombre tient le seuil AA a chaque phase. */
    "@keyframes pcAFaireTxt{0%,100%{text-shadow:none}50%{text-shadow:0 0 8px rgba(240,180,41,.55)}}",
    "@media(prefers-reduced-motion:reduce){.pc-b-reste{animation:none}}",
    ".pc-b-d{display:flex;align-items:center;gap:8px;flex-wrap:wrap}",
    ".pc-b-btn{font:inherit;font-size:12px;font-weight:600;padding:7px 12px;border-radius:8px;cursor:pointer;",
    "border:1px solid var(--line);background:var(--panel2);color:var(--ink);text-decoration:none;",
    "max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    ".pc-b-btn:hover{border-color:var(--teal);color:var(--teal)}",
    ".pc-b-suiv{border-color:var(--teal);background:rgba(45,212,191,.14);color:var(--teal)}",
    ".pc-b-x{background:none;border:none;color:var(--muted2);font-size:22px;line-height:1;cursor:pointer;padding:0 5px}",
    ".pc-b-x:hover{color:var(--ink)}",
    "@media(max-width:640px){.pc-b-btn{max-width:130px}.pc-live span{display:none}.pc-b-role{max-width:140px}",
    ".pc-card{padding:18px 16px}.pc-b-sec{display:none}}",
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
    var optsRole = '<option value="">— Choisir un rôle —</option>'
      + PARCOURS.map(function (p) {
          return '<option value="' + esc(p.id) + '">' + esc(p.icone + "  " + p.role) + "</option>";
        }).join("");
    var optsSect = '<option value="">— Choisir un secteur —</option>'
      + SECTEURS.map(function (x) {
          return '<option value="' + esc(x.id) + '">' + esc(x.icone + "  " + x.nom) + "</option>";
        }).join("");
    m.innerHTML = '<div class="pc-card" role="dialog" aria-modal="true" aria-label="Parcours guidés">'
      + '<div class="pc-head"><div><div class="pc-eyebrow">Par où commencer</div>'
      + '<div class="pc-title">Parcours guidés</div></div>'
      + '<button class="pc-x" type="button" aria-label="Fermer">×</button></div>'
      + '<p class="pc-intro">Une trentaine de pages, et aucune évidente au premier abord. '
      + 'Deux entrées, indépendantes : le <b>rôle</b> décide de l’itinéraire — quelles pages, dans quel '
      + 'ordre ; le <b>secteur</b> décide de ce qui change en route — le texte qui s’impose ici et pas '
      + 'ailleurs, la contrainte qui prime, le piège du métier. Choisissez l’un, l’autre, ou les deux. '
      + 'Les étapes marquées <b>🔒 Compte requis</b> demandent un compte client validé — '
      + '<a href="/inscription">en créer un</a> : votre adresse est confirmée par courriel, puis '
      + 'l’accès est validé par notre équipe, qui vous prévient. Vous le savez avant de cliquer.</p>'
      + '<div class="pc-selects">'
      + '<label class="pc-lab">Votre rôle'
      + '<select class="pc-select" id="pc-select">' + optsRole + '</select></label>'
      + '<label class="pc-lab">Votre secteur industriel'
      + '<select class="pc-select" id="pc-select-sec">' + optsSect + '</select></label>'
      + '</div><div id="pc-fiche"></div></div>';
    m.querySelector(".pc-x").addEventListener("click", fermer);
    var sel = m.querySelector("#pc-select");
    var selSec = m.querySelector("#pc-select-sec");
    function maj() { fiche(sel.value, selSec.value); }
    sel.addEventListener("change", maj);
    selSec.addEventListener("change", maj);
    m.classList.add("on");
    var g = lire();
    if (idPre || (g && g.sec)) {
      if (idPre) sel.value = idPre;
      if (g && g.sec) selSec.value = g.sec;
      maj();
    } else sel.focus();
    document.addEventListener("keydown", echap);
  }
  function echap(e) { if (e.key === "Escape") fermer(); }
  function fermer() {
    var m = document.getElementById("pc-modal");
    if (m) m.classList.remove("on");
    document.removeEventListener("keydown", echap);
  }

  /* Une étape, rendue avec la note du secteur s'il y en a une pour cette page.
     `sec` peut être null : le rendu est alors celui d'avant, à l'identique. */
  function etapeHtml(idParcours, e, i, ici, sec, perso, vus) {
    var courante = e.url === ici;
    var note = sec && sec.notes ? sec.notes[e.url] : null;
    var prioAxe = perso && perso.prioIdx.hasOwnProperty(i) ? perso.prioIdx[i] : null;
    /* FAIT n'est pas DEPASSE : vert seulement si la page a ETE ATTEINTE
       pendant ce parcours. Le reste est A FAIRE — encadré d'ambre et battant
       doucement, pour que l'œil trouve d'un regard ce qui l'attend. Le badge
       dit ce que le vert MESURE : la visite, pas le travail accompli. */
    var faite = (vus || []).indexOf(e.url) >= 0;
    return '<div class="pc-etape' + (courante ? " pc-ici" : "")
      + (faite ? " pc-e-fait" : " pc-e-reste")
      + (prioAxe ? " pc-prio-etape" : "") + '">'
      + '<div class="pc-e-top"><span class="pc-num">' + (i + 1) + "</span>"
      + '<span class="pc-e-label">' + esc(e.label) + (courante ? " · vous y êtes" : "") + "</span>"
      + (faite
          ? '<span class="pc-e-etat fait" title="Page atteinte pendant ce parcours — le module constate la visite, pas le travail accompli">✓ Visitée</span>'
          : '<span class="pc-e-etat reste" title="Cette page n’a pas encore été ouverte pendant ce parcours">À faire</span>')
      + (prioAxe ? '<span class="pc-prio-badge" title="Étape à fort enjeu pour ce secteur">★ Prioritaire</span>' : "")
      + (reserve(e.url) ? '<span class="pc-cle" title="Cette page demande un compte">🔒 Compte requis</span>' : "")
      + '<a class="pc-go" href="' + esc(e.url) + '" data-pc-go="' + esc(idParcours) + "|" + i + '">'
      + (courante ? "Rester ici" : "Aller à cette page") + " →</a></div>"
      + '<div class="pc-e-d"><b>À faire :</b> ' + esc(e.action) + "</div>"
      + '<div class="pc-e-d"><b>Ce que vous y gagnez :</b> ' + esc(e.gain) + "</div>"
      + (e.tip ? '<div class="pc-e-tip">' + esc(e.tip) + "</div>" : "")
      + (note ? '<div class="pc-e-sec"><b>' + esc(sec.icone + " " + sec.nom) + " — </b>"
                + esc(note) + "</div>" : "")
      + "</div>";
  }

  /* Nom court du rôle (avant le « · ») pour les titres croisés. */
  function courtRole(role) {
    var s = String(role || "");
    var j = s.indexOf(" · ");
    return j > 0 ? s.slice(0, j) : s;
  }

  /* Le bloc « Priorités calculées » : la sortie visible du moteur de pertinence,
     affiché seulement quand un rôle ET un secteur sont choisis — c'est là que le
     croisement a un sens à régler finement. */
  function blocPrio(p, sec, perso) {
    if (!perso || (!perso.prio.length && !perso.detour)) return "";
    var syn = "Pour <b>" + esc(courtRole(p.role)) + "</b> en <b>" + esc(sec.nom)
      + "</b>, l’itinéraire de votre fonction et les priorités du secteur convergent surtout sur <b>"
      + esc(AXE_LABEL[perso.domAxe] || perso.domAxe) + "</b>.";
    var items = perso.prio.map(function (x) {
      return '<li><b>Étape ' + (x.i + 1) + " · " + esc(x.label) + "</b> — "
        + "porte " + esc(AXE_LABEL[x.axe] || x.axe) + " pour ce secteur.</li>";
    }).join("");
    var liste = items ? '<ol class="pc-prio-l">' + items + "</ol>" : "";
    var det = perso.detour
      ? '<div class="pc-prio-det">↳ <b>Détour conseillé :</b> ' + esc(perso.detour.label)
        + " — étape propre à ce secteur, hors de l’itinéraire type de votre rôle, mais décisive ici ("
        + esc(AXE_COURT[perso.detour.axe] || perso.detour.axe) + ")."
        + '</div>'
      : "";
    return '<div class="pc-prio">'
      + '<div class="pc-prio-t">🎯 Priorités calculées · ' + esc(courtRole(p.role))
      + ' <span class="pc-croix">×</span> ' + esc(sec.nom) + "</div>"
      + '<div class="pc-prio-syn">' + syn + "</div>"
      + liste + det + "</div>";
  }

  /* Le bloc sectoriel : ce que le secteur change, indépendamment du rôle. */
  function blocSecteur(sec, avecTitre) {
    return '<div class="pc-sect">'
      + (avecTitre ? '<div class="pc-sect-t">' + esc(sec.icone + " " + sec.nom) + "</div>" : "")
      + '<div class="pc-sect-l"><b>L’enjeu :</b> ' + esc(sec.enjeu) + "</div>"
      + '<div class="pc-sect-l"><b>Textes qui s’imposent :</b> ' + esc(sec.textes) + "</div>"
      + '<div class="pc-sect-l pc-sect-p"><b>Le piège :</b> ' + esc(sec.piege) + "</div>"
      + "</div>";
  }

  function fiche(id, idSec) {
    var h = document.getElementById("pc-fiche");
    if (!h) return;
    var p = id ? trouver(id) : null;
    var sec = idSec ? trouverSecteur(idSec) : null;
    if (!p && !sec) { h.innerHTML = ""; return; }
    var ici = chemin();

    /* Trois cas. Le rôle commande l'itinéraire dès qu'il est choisi ; le
       secteur seul mène son propre parcours court plutôt qu'une fiche de
       lecture sans issue. */
    var source = p || sec;
    var idParcours = p ? p.id : "sec:" + sec.id;
    /* Le moteur ne s'applique qu'au croisement d'un rôle ET d'un secteur : c'est
       le seul cas où « régler finement » veut dire quelque chose. Un rôle seul
       garde sa séquence éprouvée ; un secteur seul mène son parcours court. */
    var perso = (p && sec) ? personnaliser(p.etapes, sec.id, sec.etapes) : null;
    /* La progression appartient au parcours ACTIF : afficher la fiche d'un
       autre parcours montre son chemin, pas une progression qui n'est pas la
       sienne. */
    var etatActif = lire();
    var vus = (etatActif && etatActif.id === idParcours) ? etatActif.vus : [];
    var faites = source.etapes.filter(function (e) { return vus.indexOf(e.url) >= 0; }).length;
    var restantes = source.etapes.length - faites;
    var compteur = '<div class="pc-compte">'
      + '<span class="pc-compte-fait">' + faites + " visitée" + (faites > 1 ? "s" : "") + "</span>"
      + ' · <span class="pc-compte-reste">' + restantes + " à faire</span>"
      + " sur " + source.etapes.length + " étape" + (source.etapes.length > 1 ? "s" : "") + "</div>";
    var etapes = compteur + source.etapes.map(function (e, i) {
      return etapeHtml(idParcours, e, i, ici, sec, perso, vus);
    }).join('<div class="pc-fleche">↓</div>');

    var tete;
    if (p) {
      tete = '<div class="pc-fiche-head"><span class="pc-fiche-ic">' + esc(p.icone) + "</span>"
        + '<div><div class="pc-fiche-role">' + esc(p.role)
        + (sec ? ' <span class="pc-croix">×</span> ' + esc(sec.icone + " " + sec.nom) : "")
        + "</div>"
        + '<div class="pc-fiche-pitch">' + esc(p.pitch) + "</div></div></div>"
        + '<div class="pc-cas">' + esc(p.cas) + "</div>"
        + (sec ? blocSecteur(sec, false) : "")
        + (perso ? blocPrio(p, sec, perso) : "");
    } else {
      tete = '<div class="pc-fiche-head"><span class="pc-fiche-ic">' + esc(sec.icone) + "</span>"
        + '<div><div class="pc-fiche-role">' + esc(sec.nom) + "</div>"
        + '<div class="pc-fiche-pitch">Parcours propre au secteur. Choisissez aussi un rôle '
        + 'ci-dessus pour obtenir l’itinéraire de votre fonction, annoté des contraintes de ce '
        + 'secteur.</div></div></div>'
        + blocSecteur(sec, false);
    }

    h.innerHTML = '<div class="pc-fiche">' + tete + etapes + "</div>";

    h.querySelectorAll("[data-pc-go]").forEach(function (a) {
      a.addEventListener("click", function (ev) {
        var d = this.getAttribute("data-pc-go").split("|");
        /* Reprendre un parcours ne remet PAS sa progression à zéro : les
           pages déjà visitées le restent. Changer de parcours, si. */
        var avant = lire();
        /* MÊME RÈGLE QU'AU BANDEAU : le rang est une CONSTATATION. On garde
           l'étape visée à part — elle deviendra le rang si la page s'ouvre,
           et restera une intention si un mur de connexion la retient. */
        var g = { id: d[0], i: parseInt(d[1], 10), sec: idSec || null,
                  vus: (avant && avant.id === d[0]) ? avant.vus : [], bloque: null };
        if (this.getAttribute("href") === ici) {   // déjà sur la page : pas de rechargement
          marquerVisite(g, ici);                   // on y est : la visite est un fait
          ecrire(g);
          ev.preventDefault();
          fermer();
          bandeau();
          return;
        }
        ecrire(g);
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
    var secActif = g.sec ? trouverSecteur(g.sec) : null;

    /* LES POINTS DISAIENT FAUX : « fait » pour tout point AVANT la position
       courante — sauter à l'étape 4 peignait en vert deux pages jamais
       ouvertes. Chaque point dit désormais sa VISITE ; ce qui reste est
       ambre, comme dans la fiche. */
    var dots = "", nVus = 0;
    for (var k = 0; k < n; k++) {
      var vu = g.vus.indexOf(p.etapes[k].url) >= 0;
      if (vu) nVus++;
      dots += '<span class="pc-dot' + (k === i ? " ici" : (vu ? " fait" : " reste")) + '"></span>';
    }
    /* CE QUE LE LECTEUR VOIT QUAND LE MUR EST LÀ. Le bandeau annonçait
       l'étape visée comme atteinte ; il annonce désormais qu'elle est
       DEMANDÉE et pourquoi elle n'est pas là. Le rang affiché reste celui de
       la dernière page réellement vue — c'est le seul qui soit vrai. */
    var bloque = null;
    if (g.bloque) {
      for (var z = 0; z < n; z++) if (p.etapes[z].url === g.bloque) bloque = { i: z, e: p.etapes[z] };
    }

    /* LE RANG N'EST AFFICHÉ QUE SI ON EST SUR L'ÉTAPE. Hors d'elle — mur de
       connexion, page du menu, retour arrière — annoncer « Étape 5 / 7 »
       décrit une position que le lecteur n'occupe pas. On dit alors ce qui
       est vrai : le parcours est en attente, et voici où il reprend. */
    var surEtape = p.etapes[i] && p.etapes[i].url === chemin();

    var h = '<div class="pc-b-g">'
      + (bloque
          ? '<span class="pc-mur" title="Cette étape demande un compte client validé">🔒 Étape '
            + (bloque.i + 1) + " — compte requis</span>"
          : '<span class="pc-live" title="Parcours en cours"><i></i><span>Parcours en cours</span></span>')
      + '<button class="pc-b-role" type="button" data-pc-rouvrir="' + esc(p.id) + '" '
      + 'title="Revoir le parcours complet">' + esc(p.icone + " " + p.role) + "</button>"
      + (secActif ? '<span class="pc-b-sec" title="Secteur retenu">'
                    + esc(secActif.icone + " " + secActif.nom) + "</span>" : "")
      + '<div class="pc-b-prog"><span class="pc-b-step' + (surEtape ? "" : " att") + '">'
      + (surEtape
          ? "Étape " + (i + 1) + " / " + n + " · " + esc(e.label)
          : "En attente · reprise à l’étape " + (i + 1) + " / " + n + " · " + esc(e.label))
      + '</span><span class="pc-b-dots">' + dots + "</span>"
      + '<span class="pc-b-reste">' + (n - nVus > 0
          ? (n - nVus) + " à faire"
          : "toutes visitées ✓") + "</span></div>"
      + (bloque
          ? '<div class="pc-b-mur">L’étape ' + (bloque.i + 1) + ' — <b>'
            + esc(bloque.e.label) + '</b> — demande un compte client validé. '
            + '<a href="/connexion?next=' + encodeURIComponent(bloque.e.url) + '">Se '
            + 'connecter</a> ou <a href="/inscription">demander un compte</a> : vous '
            + 'serez ramené à cette page et le parcours reprendra là. '
            + (nVus ? 'Tant qu’elle n’est pas ouverte, elle reste comptée « à faire ».'
                    : 'Aucune étape de ce parcours n’a encore été ouverte.')
            + '</div>'
          : "")
      + "</div>"
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

    /* LE RANG NE S'AVANCE PLUS AU CLIC — IL SE CONSTATE À L'ARRIVÉE.
       C'était le défaut le plus grave du dispositif : cliquer « Suivant »
       écrivait l'étape suivante, PUIS le navigateur partait. Quand la page
       visée demandait un compte, le serveur renvoyait vers /connexion — et le
       bandeau annonçait « Étape 5 / 7 · Feuille de route » à un lecteur assis
       devant un formulaire de connexion. Mesuré sur les sept étapes du
       parcours RSSI : les sept mentaient. Le rang est désormais posé par
       `recaler()`, au chargement de la page réellement atteinte. */
    b.querySelectorAll("[data-pc-aller]").forEach(function (a) {
      a.addEventListener("click", function () { ecrire(g); });
    });
    b.querySelectorAll("[data-pc-fin]").forEach(function (x) {
      x.addEventListener("click", function () { ecrire(null); bandeau(); });
    });
    var r = b.querySelector("[data-pc-rouvrir]");
    if (r) {
      r.addEventListener("click", function () {
        var id = this.getAttribute("data-pc-rouvrir");
        // Un parcours sectoriel se rouvre par sa liste secteur, pas par la
        // liste rôle : on rouvre la modale et on laisse `ouvrir` recharger
        // l'état, qui porte déjà le couple retenu.
        ouvrir(id.indexOf("sec:") === 0 ? null : id);
      });
    }
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
      if (p.etapes[k].url === ici) {
        /* LA VISITE ET LE RANG SE CONSTATENT ICI, au chargement de la page
           réellement atteinte — pas au clic qui y mène. Un clic peut échouer
           (page fermée, réseau) : créditer l'intention peindrait en vert une
           page jamais vue, et placerait le lecteur là où il n'est pas. */
        marquerVisite(g, ici);
        g.i = k;
        g.bloque = null;                 /* on y est : le mur est franchi */
        ecrire(g);
        return;
      }
    }
    /* LE MUR DE CONNEXION EST UN ÉTAT DU PARCOURS, PAS UNE SORTIE.
       Une étape réservée renvoie vers /connexion?next=… . Sans ce cas, le
       bandeau restait muet sur la seule chose qui comptait : pourquoi la page
       demandée n'est pas là, et comment y revenir. On retient l'étape visée —
       elle sera franchie, ou elle restera annoncée. */
    var m = /[?&]next=([^&]+)/.exec(location.search || "");
    var vise = m ? decodeURIComponent(m[1]).replace(/\/+$/, "") : null;
    if (vise) {
      for (var j = 0; j < p.etapes.length; j++) {
        if (p.etapes[j].url === vise) {
          if (g.bloque !== vise) { g.bloque = vise; ecrire(g); }
          return;
        }
      }
    }
    if (g.bloque) { g.bloque = null; ecrire(g); }
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

  /* Le cadenas dit-il vrai ? On le demande au serveur plutôt qu'à nous-mêmes.
     nav.js pose déjà les deux questions — quelles pages sont fermées, et
     sommes-nous connecté — une seule fois par page ; on partage sa réponse au
     lieu d'en relancer une (celle de /api/auth/me est en no-store : la reposer
     coûterait une lecture de compte de plus à chaque chargement).

     Les 56 pages qui portent ce module portent aussi nav.js, et la recette le
     vérifie ; si malgré tout la réponse manque, la liste écrite plus haut
     reste, et le bandeau reste juste. */
  function synchroniserAcces() {
    if (typeof window.navAcces !== "function") return;
    window.navAcces().then(function (a) {
      if (!a) return;
      var avant = JSON.stringify([CONNECTE, Object.keys(RESERVE).sort()]);
      CONNECTE = a.connecte;
      if (a.client && a.client.length) {
        RESERVE = {};
        a.client.forEach(function (u) { RESERVE[u] = 1; });
      }
      if (JSON.stringify([CONNECTE, Object.keys(RESERVE).sort()]) === avant) return;
      /* Redessiner seulement ce qui est à l'écran. Le bandeau porte le cadenas
         du « Suivant », la fiche le porte sur chaque étape. */
      bandeau();
      var m = document.getElementById("pc-modal");
      if (m && m.classList.contains("on")) {
        var r = m.querySelector("#pc-select"), s = m.querySelector("#pc-select-sec");
        if (r || s) fiche(r ? r.value : "", s ? s.value : "");
      }
    }).catch(function () { /* la liste écrite reste : le parcours ne ment pas */ });
  }

  function init() {
    poserStyle();
    window.parcoursPret();
    recaler();
    bandeau();
    synchroniserAcces();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
