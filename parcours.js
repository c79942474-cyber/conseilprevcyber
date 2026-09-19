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
    "/parcours-mission": ["gouvernance"],
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
    "/securite-ia": ["analyse", "exigences", "gouvernance"],
    "/demo": ["technique", "continuite"],
    "/veille": ["preuve"],
    "/audit-conformite": ["preuve", "juridique"],
    "/conformite": ["juridique", "preuve"],
    "/juridique": ["juridique", "tiers"],
    "/relecture-contrat": ["juridique", "tiers"],
    "/nis2": ["juridique"],
    "/etudes-de-cas": ["analyse"],
    /* LE REGISTRE DES MISSIONS N'EST PAS UNE ANALYSE : c'est ce qu'on oppose
       à un acheteur qui demande « pour qui avez-vous travaillé, et qui peut
       le confirmer ». Son axe est donc la preuve, et la gouvernance de la
       relation — pas la technique, qui est l'axe des études de cas. */
    "/references": ["preuve", "gouvernance"],
    /* Les trois pages « centres de données ». Elles ne relèvent pas de la
       cybersécurité : leur axe est l'analyse (ce qu'on mesure), la preuve (ce
       qu'on peut opposer) et la gouvernance (ce qu'on décide). Sans ces
       entrées, un parcours qui les traverse ne pondérait rien. */
    "/strategie-durable-datacenter": ["analyse", "gouvernance"],
    "/datacenter": ["analyse", "preuve"],
    "/ingenierie-datacenter": ["exigences", "preuve"],
    "/ingenierie-ia-factory": ["gouvernance", "analyse"],
    /* LES PAGES ENTRÉES DANS LES PARCOURS LE 4 SEPTEMBRE 2026. La recette
       exige une entrée pour toute URL de parcours : sans elle, une étape
       traversée ne pondérerait rien et le croisement rôle × secteur
       l'ignorerait en silence. Un tableau vide reste un choix explicite. */
    "/checklist-62443": ["preuve", "exigences"],
    "/tendances": ["preuve", "continuite"],
    "/guide-integration": ["technique", "preuve"],
    "/services": [],
    "/ressources": [],
    "/assistant": [],
    /* LA CONCLUSION N'EST PAS PONDÉRÉE, ET C'EST DÉLIBÉRÉ. Elle figure dans
       TOUS les parcours : lui donner un axe le renforcerait partout de la même
       quantité, donc ne distinguerait rien — une pondération constante est un
       décalage, pas une information. */
    "/vos-projets": [],
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
    /* trois textes à articuler + le dossier technique d'un système à haut
       risque, qui ne se reconstitue pas après coup */
    banque:        { gouvernance:2, analyse:1, technique:1, exigences:2, tiers:2, juridique:3, continuite:2, preuve:3 },
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
     LE CONSEILLER — quel itinéraire, pour qui, et POURQUOI PAS L'AUTRE

     LE PROBLÈME QU'IL RÉSOUT. La modale ouvre sur treize rôles. Un visiteur
     qui sait qu'il est RSSI trouve en deux secondes ; un directeur de projet
     de centre de données voit CINQ entrées « centre de données » dont les
     pages se recouvrent largement, et rien à l'écran ne lui dit laquelle est
     la sienne avant qu'il l'ait ouverte. Choisir suppose de connaître notre
     découpage — c'est-à-dire exactement ce qu'un premier visiteur ignore.

     POURQUOI UN MOTEUR ET PAS UN APPEL À UN MODÈLE DE LANGAGE. Une
     recommandation qu'on ne peut pas rejouer ne se défend pas en réunion :
     « pourquoi ce parcours ? — le modèle l'a dit » n'est pas une réponse.
     Ici, trois réponses entrent, un classement sort, et les deux mêmes
     réponses donnent toujours le même classement. Le conseil porte ses
     raisons, et surtout CE QU'IL ÉCARTE et sur quel motif — c'est la moitié
     qu'on ne montre jamais, et c'est celle qui permet de contredire.

     CE QU'IL NE FAIT PAS. Il ne conseille pas de SECTEUR : le secteur est un
     fait que le visiteur connaît, pas une question à lui poser. Et il ne
     tranche pas quand il n'a pas de quoi : deux itinéraires à un point d'écart
     sont présentés tous les deux, ce qui est une réponse plus utile qu'un
     gagnant tiré au sort.
     ═══════════════════════════════════════════════════════════════════════ */

  /* Les trois questions. Chacune porte sur la SITUATION du visiteur, jamais
     sur notre vocabulaire : « ce que vous devez sécuriser », pas « quel rôle
     du référentiel ». La dernière valeur de chaque liste est neutre — elle
     ne désigne rien, et le conseiller le dit au lieu de faire semblant. */
  var QUESTIONS = [
    { cle: "objet", titre: "Ce que vous devez sécuriser ou construire",
      choix: [
        { v: "industriel",  l: "Une installation industrielle, un site, un réseau OT" },
        { v: "datacenter",  l: "Un centre de données — en projet ou en exploitation" },
        { v: "ia",          l: "Un système d’intelligence artificielle" },
        { v: "organisation", l: "L’organisation elle-même, pas un actif en particulier" },
        { v: "",            l: "Je ne sais pas encore", neutre: true }
      ] },
    { cle: "declencheur", titre: "Ce qui vous amène aujourd’hui",
      choix: [
        { v: "texte",   l: "Un texte réglementaire qui nous vise" },
        { v: "projet",  l: "Un projet à cadrer, à concevoir ou à lancer" },
        { v: "chiffre", l: "On nous réclame des chiffres ou des preuves" },
        { v: "marche",  l: "Un marché, un contrat, un prestataire à qualifier" },
        { v: "",        l: "Rien de précis — je regarde", neutre: true }
      ] },
    { cle: "levier", titre: "Ce dont vous répondez",
      choix: [
        { v: "technique",  l: "La technique et l’architecture" },
        { v: "budget",     l: "L’argent et les délais" },
        { v: "conformite", l: "La conformité et le juridique" },
        { v: "direction",  l: "La décision — j’ai un comité à convaincre" },
        { v: "",           l: "Je ne décide pas encore", neutre: true }
      ] }
  ];

  /* Ce que chaque réponse veut dire, en clair, pour ÉCRIRE le motif d'un
     écart. Sans ce dictionnaire le conseiller ne pourrait dire que « score
     inférieur », qui n'explique rien à personne. */
  var EN_CLAIR = {
    objet: { industriel: "une installation industrielle", datacenter: "un centre de données",
             ia: "un système d’IA", organisation: "l’organisation elle-même" },
    declencheur: { texte: "un texte réglementaire", projet: "un projet à lancer",
                   chiffre: "une demande de chiffres", marche: "un marché à passer" },
    levier: { technique: "la technique", budget: "l’argent et les délais",
              conformite: "la conformité", direction: "la décision en comité" }
  };

  /* Le poids de chaque question, et l'ordre compte. L'OBJET est la contrainte
     dure : envoyer un exploitant de centre de données sur l'analyse de risque
     d'un réseau OT est faux, pas seulement mal réglé. Le DÉCLENCHEUR décide de
     l'ordre de lecture. Le LEVIER n'est qu'un départage : deux itinéraires qui
     servent le même objet et le même déclencheur se distinguent par ce dont on
     répond, et ce n'est pas une raison de changer d'itinéraire à soi seul. */
  var POIDS_Q = { objet: 3, declencheur: 2, levier: 1 };

  /* L'ÉCART EN DEÇÀ DUQUEL LE CONSEILLER REFUSE DE TRANCHER — et sa première
     valeur était fausse. Elle valait DEUX, au motif qu'un itinéraire que seul
     le levier sépare du suivant ne mérite pas d'être préféré. Mesuré sur onze
     situations réelles, ce seuil rendait « je ne tranche pas » HUIT FOIS : un
     conseiller qui s'abstient trois fois sur quatre ne conseille rien, il
     déplace la question. Et il s'abstenait à tort — l'économiste de la
     construction et le DSI qui décide la charge d'une salle recevaient la
     même réponse, alors que le levier les sépare exactement.

     Le vrai remède n'était pas le seuil mais les profils : chacun déclarait
     DEUX leviers, donc en matchait un sur deux. Un levier par itinéraire, et
     le seuil redevient ce qu'il doit être : on ne s'abstient que sur une
     ÉGALITÉ STRICTE, où il n'y a réellement rien à préférer. */
  var MARGE_MINIMALE = 1;

  /* Au-delà de ce nombre d'ex æquo, le problème n'est plus de départager :
     c'est qu'on n'a pas assez demandé. Le conseiller le dit alors, et nomme la
     question restée sans réponse, au lieu d'afficher une liste qui ressemble à
     un choix mais n'en est pas un. */
  var EX_AEQUO_MAX = 3;

  function libelleReponse(cle, v) {
    return (EN_CLAIR[cle] && EN_CLAIR[cle][v]) || v;
  }

  /* Le cœur. Pur : aucune lecture du DOM, aucun effet. Rend TOUJOURS un objet,
     y compris quand rien ne matche — le recours est alors nommé comme tel. */
  function conseiller(rep, parcours) {
    var liste = parcours || PARCOURS;
    rep = rep || {};
    var posees = [];
    for (var q = 0; q < QUESTIONS.length; q++) {
      var c = QUESTIONS[q].cle;
      if (rep[c]) posees.push(c);
    }

    var notes = liste.map(function (p) {
      var prof = p.profil || {};
      var score = 0, pour = [], contre = [];
      for (var k = 0; k < posees.length; k++) {
        var cle = posees[k], attendu = prof[cle] || [];
        if (attendu.indexOf(rep[cle]) >= 0) {
          score += POIDS_Q[cle];
          pour.push({ cle: cle, valeur: rep[cle], dit: libelleReponse(cle, rep[cle]) });
        } else if (attendu.length) {
          contre.push({ cle: cle, valeur: rep[cle],
                        dit: libelleReponse(cle, rep[cle]),
                        au_lieu_de: attendu.map(function (a) { return libelleReponse(cle, a); }) });
        }
      }
      return { id: p.id, role: p.role, icone: p.icone, entree: prof.entree || "",
               score: score, pour: pour, contre: contre,
               urls: p.etapes.map(function (e) { return e.url; }),
               recours: !prof.objet };
    });

    /* Le recours ne concourt pas : il est le filet, pas un candidat. Le
       classer avec les autres le ferait gagner dès qu'on ne répond à rien,
       ce qui est vrai, mais il le ferait aussi perdre de justesse dès qu'on
       répond à une seule chose — et le filet doit être franc. */
    var recours = null, candidats = [];
    notes.forEach(function (n) { if (n.recours) recours = n; else candidats.push(n); });
    candidats.sort(function (a, b) {
      return b.score - a.score || a.id.localeCompare(b.id);
    });

    var meilleur = candidats[0] || null;
    var suivant = candidats[1] || null;

    /* AUCUNE RÉPONSE N'A RIEN DÉSIGNÉ. On le dit, et on donne le recours. */
    if (!posees.length || !meilleur || meilleur.score === 0) {
      return { verdict: "recours", posees: posees, retenus: recours ? [recours] : [],
               ecartes: [], marge: 0, classement: candidats,
               motif: !posees.length
                 ? "Aucune réponse donnée : rien à départager."
                 : "Aucun itinéraire ne répond à ce que vous avez décrit." };
    }

    var marge = suivant ? meilleur.score - suivant.score : meilleur.score;

    /* DEUX EX ÆQUO, OU PRESQUE. On ne tranche pas — et on dit sur quoi ils se
       séparent, pour que le visiteur tranche sur un fait et non sur un titre. */
    if (suivant && marge < MARGE_MINIMALE) {
      var exaequo = candidats.filter(function (c) {
        return meilleur.score - c.score < MARGE_MINIMALE;
      });
      /* TROP D'EX ÆQUO N'EST PAS UNE ÉGALITÉ, C'EST UNE QUESTION SANS RÉPONSE.
         Répondre au seul objet laisse cinq itinéraires au même score : les
         afficher tous les cinq ressemble à un choix et n'en est pas un. On
         nomme alors la question qui manque — c'est elle qui trancherait. */
      if (exaequo.length > EX_AEQUO_MAX) {
        var restent = [];
        for (var z = 0; z < QUESTIONS.length; z++) {
          if (posees.indexOf(QUESTIONS[z].cle) < 0) restent.push(QUESTIONS[z]);
        }
        return { verdict: "trop_large", posees: posees,
                 retenus: exaequo.slice(0, EX_AEQUO_MAX),
                 manquantes: restent.map(function (q) { return q.cle; }),
                 ecartes: [], marge: marge, classement: candidats,
                 motif: exaequo.length + " itinéraires à égalité" +
                        (restent.length
                          ? " : il manque votre réponse à « " +
                            restent.map(function (q) { return q.titre.toLowerCase(); }).join(" » et « ") + " »."
                          : " — et rien ici ne les sépare.") };
      }
      return { verdict: "partage", posees: posees, retenus: exaequo,
               ecartes: ecarter(candidats, exaequo, rep), marge: marge,
               classement: candidats,
               motif: exaequo.length + " itinéraires à égalité stricte : le choix vous revient, " +
                      "et ce qui les sépare est écrit sous chacun." };
    }

    /* LE SECOND N'EST PAS UN ÉCARTÉ. Il était pourtant dans les deux listes :
       présenté en « voyez celui-ci plutôt », puis rejeté trois lignes plus bas
       avec son motif. Le lecteur y lisait deux avis contraires sur le même
       itinéraire — et c'est le genre de contradiction qui fait douter de tout
       le reste. On le montre une fois, à la place où il sert. */
    return { verdict: "retenu", posees: posees, retenus: [meilleur],
             second: suivant ? enPlus(suivant, meilleur) : null,
             ecartes: ecarter(candidats, suivant ? [meilleur, suivant] : [meilleur], rep),
             marge: marge,
             classement: candidats,
             motif: "Un itinéraire devance le suivant de " + marge + " point" +
                    (marge > 1 ? "s" : "") + "." };
  }

  /* CE QUE LE SECOND AURAIT DONNÉ EN PLUS. Non pas « il a moins de points »,
     mais les pages qu'il montre et que le retenu ne montre pas : c'est la
     seule information qui permette de contester le classement. */
  function enPlus(second, retenu) {
    var vues = {};
    retenu.urls.forEach(function (u) { vues[u] = 1; });
    var sup = second.urls.filter(function (u) { return !vues[u]; });
    /* AUCUNE PAGE DE PLUS N'EST UN FAIT, PAS UN VIDE. Plusieurs itinéraires de
       ce site visitent les mêmes pages en posant d'autres questions : le second
       peut n'ajouter aucune adresse et changer entièrement la lecture. Afficher
       « rien » laisserait croire qu'il n'apporte rien ; c'est faux, et c'est la
       chose qu'il faut dire à l'endroit exact où le lecteur hésite. */
    return { id: second.id, role: second.role, icone: second.icone,
             score: second.score, entree: second.entree,
             urls_en_plus: sup,
             apport: sup.length
               ? "il ajoute " + sup.length + " page" + (sup.length > 1 ? "s" : "") + " à l’itinéraire"
               : "il ne montre aucune page de plus : il pose d’autres questions sur les mêmes pages" };
  }

  /* LES ÉCARTÉS, AVEC LEUR MOTIF — et le motif est la PREMIÈRE question sur
     laquelle ils tombent, par ordre de poids : c'est celle qui décide. */
  function ecarter(candidats, gardes, rep) {
    var gardeIds = {};
    gardes.forEach(function (g) { gardeIds[g.id] = 1; });
    return candidats.filter(function (c) { return !gardeIds[c.id]; })
      .map(function (c) {
        var ordre = ["objet", "declencheur", "levier"], motif = null;
        for (var i = 0; i < ordre.length && !motif; i++) {
          for (var j = 0; j < c.contre.length; j++) {
            if (c.contre[j].cle !== ordre[i]) continue;
            var x = c.contre[j];
            /* « il part de une demande de chiffres » : l'élision manquait, et
               aucune valeur en clair ne peut la porter — « l'organisation »
               ne s'élide pas comme « une installation ». On change donc de
               verbe plutôt que de bricoler l'article : « viser » prend son
               complément direct, quel que soit le déterminant. */
            motif = "il vise " + x.au_lieu_de.join(" ou ") +
                    " ; vous avez répondu " + x.dit;
          }
        }
        return { id: c.id, role: c.role, icone: c.icone, score: c.score,
                 entree: c.entree,
                 motif: motif || "il répond à moins de ce que vous avez décrit" };
      });
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
      profil: { objet: ["industriel"], declencheur: ["texte", "projet"],
                levier: ["technique"],
                entree: "un programme de sécurité industrielle à construire de bout en bout, et à tenir devant un auditeur" },
      icone: "🛡️",
      role: "RSSI · Responsable cybersécurité industrielle",
      cas: "Inspiré de la mission GRDF — Projet Biométhane (PSSI industrielle, EBIOS, analyse d’écarts)",
      pitch: "Vous devez construire un programme de sécurité industrielle qui tienne devant un auditeur " +
             "comme devant un exploitant. Ce parcours suit l’ordre d’une mission réelle : constater, " +
             "mesurer, analyser, structurer, planifier, transmettre, prouver.",
      etapes: [
        /* LE PARCOURS DE MISSION OUVRE CELUI-CI, et ce n’est pas un doublon :
           le pitch ci-dessus annonce « l’ordre d’une mission réelle », et
           cette page EST cet ordre — huit phases, ce que chacune exige de la
           précédente, et le piège qu’elle porte. La lire en premier évite de
           faire les étapes suivantes dans le désordre, ce qui est la faute
           que tout ce parcours cherche à éviter. */
        { url: "/parcours-mission", label: "L’ordre d’une mission",
          action: "Parcourez les huit phases et cochez celles qui sont déjà acquises chez vous.",
          gain: "Vous savez par quoi commencer, et ce que chaque phase exige de la précédente.",
          tip: "Un modèle cible écrit avant le diagnostic organisationnel décrit une organisation qu’on n’a pas regardée : il sera juste sur le papier et inapplicable dans l’atelier." },
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
        /* LA SÉCURITÉ DE L'IA ENTRE DANS LE PARCOURS DU RSSI, et à cette
           place précise : après le programme et la feuille de route, avant
           les métriques. Un RSSI qui découvre les agents de son organisation
           AVANT d'avoir un programme n'a nulle part où ranger ce qu'il
           trouve ; après les métriques, il aurait choisi ses indicateurs
           sans savoir ce qu'il y a à mesurer. */
        { url: "/securite-ia", label: "Sécurité de l'IA — la chaîne d'autonomie",
          action: "Cotez les cinq maillons de vos systèmes d'IA : ce qui part sans validation, et ce qui l'en empêche.",
          gain: "Les maillons ouverts se constatent au lieu de s'imaginer — y compris ceux qu'aucun scénario n'avait prévus.",
          tip: "Commencez par le maillon « action » : c'est là que se trouvent les agents branchés un vendredi pour gagner du temps, et que personne n'a déclarés." },
        { url: "/metriques-62443", label: "Métriques · 1-3",
          action: "Choisissez le petit nombre d’indicateurs que vous saurez tenir dans la durée.",
          gain: "De quoi démontrer une progression, et non une intention renouvelée chaque année.",
          tip: "Cinq indicateurs suivis valent mieux que vingt déclarés — on ne pilote que ce qu’on mesure vraiment." }
      ]
    },
    {
      id: "ot",
      profil: { objet: ["industriel"], declencheur: ["projet", "chiffre"],
                levier: ["technique"],
                entree: "une installation déjà en exploitation, dont il faut tenir les correctifs, les changements et la continuité" },
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
        { url: "/checklist-62443", label: "Checklist de conformité · 27 points",
          action: "Passez les vingt-sept points des six sections — gouvernance, architecture, accès, " +
                  "protection, détection, fournisseurs — sur VOTRE installation.",
          gain: "Un état des lieux point par point, avec ce que chacun exige et comment le prouver : " +
                "la différence entre « on pense être conforme » et « voici où l’on ne l’est pas ».",
          tip: "Faites-la remplir par l’exploitant, pas par l’intégrateur : c’est celui qui vit " +
               "avec l’installation qui sait ce qui est réellement en place." },
        { url: "/tendances", label: "Tendances de la supervision",
          action: "Lisez le volume d’événements par jour et sa répartition par zone et par " +
                  "catégorie, sur l’historique conservé.",
          gain: "Ce qu’un tableau instantané ne montre jamais : une dérive lente, qui ne déclenche " +
                "aucune alerte et change pourtant le risque.",
          tip: "Une baisse du volume n’est pas une bonne nouvelle par défaut : vérifiez d’abord " +
               "qu’une sonde n’est pas devenue muette." },
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
      profil: { objet: ["industriel"], declencheur: ["projet", "marche"],
                levier: ["technique"],
                entree: "une installation à concevoir ou à intégrer, avec des pièces techniques à produire" },
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
        { url: "/guide-integration", label: "Brancher la supervision au cockpit",
          action: "Suivez le raccordement d’une plateforme OT — Nozomi, Claroty, Tenable, " +
                  "Defender for IoT — ou d’un simple flux syslog/CEF, jusqu’à l’export CSV.",
          gain: "L’étape que les architectures oublient : ce qui est conçu doit ensuite REMONTER " +
                "quelque part, et le format de remontée se décide en conception, pas à la mise en service.",
          tip: "Négociez l’accès aux journaux dans le marché d’équipement : réclamé après la " +
               "réception, il devient un avenant." },
        { url: "/etudes-de-cas", label: "Études de cas",
          action: "Lisez comment ces sujets ont été traités sur des projets d’infrastructure comparables.",
          gain: "Des points de comparaison concrets pour arbitrer, plutôt que des principes généraux.",
          tip: "Les projets de transport ferroviaire concentrent la plupart des difficultés : multi-lots, multi-fournisseurs, longue durée." }
      ]
    },
    {
      id: "achats",
      profil: { objet: ["industriel"], declencheur: ["marche"],
                levier: ["conformite"],
                entree: "un prestataire à qualifier et un contrat à écrire sur un sujet dont on n’est pas expert" },
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
      profil: { objet: ["industriel", "organisation"], declencheur: ["texte", "projet"],
                levier: ["direction"],
                entree: "une décision à porter en comité, avec un budget à défendre et une échéance à tenir" },
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
        { url: "/references", label: "Registre des missions",
          action: "Parcourez les dix missions : donneur d’ordre, objet, période, et à quelle direction l’interlocuteur appartenait.",
          gain: "De quoi vérifier une expérience plutôt que la croire — les attestations de bonne exécution se demandent, et se fournissent.",
          tip: "Demandez l’attestation AVANT de rédiger le cahier des charges : ce qu’un prestataire peut prouver borne ce qu’il est raisonnable d’exiger." },
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
      profil: { objet: ["organisation", "ia"], declencheur: ["texte"],
                levier: ["conformite"],
                entree: "un cadre réglementaire à tenir, et un dossier qu’un contrôleur ouvrira" },
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
      profil: { objet: ["datacenter"], declencheur: ["projet"],
                levier: ["direction"],
                entree: "un centre de données à programmer, du document d’ouverture d’étude aux phases d’ingénierie" },
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
          gain: "Le document d'ouverture d'étude : les enjeux retenus, ceux qu'on écarte, le programme " +
                "de travail qui en découle — et, en dernier chapitre, ce que les TRENTE PROPOSITIONS " +
                "pour des entreprises durables engagent sur les enjeux retenus, ce qu'elles demandent " +
                "et que la stratégie ne couvre pas encore, et ce que la stratégie porte et dont elles " +
                "ne disent rien.",
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
                "pièce contractuelle — et, en regard, ce que coûte l'ingénierie qui produira ces pièces. " +
                "Le dossier de candidature et le DOSSIER D'OFFRE se remplissent au même endroit : DPGF, " +
                "mémoire technique, acte d'engagement.",
          tip: "Le facteur eau amont porte ±40 % et le carbone incorporé ±50 % — deux valeurs qui " +
               "passent en APS et ne passent plus en DCE. Repérez-les avant, pas après." },
        { url: "/ingenierie-ia-factory", label: "Si le programme est une usine IA",
          action: "Renseignez le secteur et le dimensionnement, et lisez les postes, les phases et " +
                  "les jalons du modèle paramétrique.",
          gain: "Ce qui distingue une usine IA d'un centre de données ordinaire — densité, " +
                "refroidissement, cycle de renouvellement du matériel — et ce que cela déplace dans " +
                "le programme.",
          tip: "Ce module ne rend aucun prix : il rend une STRUCTURE de coût. Un chiffre au kilowatt " +
               "trouvé ailleurs et appliqué ici donnerait un total faux et rassurant." }
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
      profil: { objet: ["datacenter"], declencheur: ["projet", "marche"],
                levier: ["budget"],
                entree: "un coût d’opération à produire et à défendre poste par poste, sans ratio au kilowatt" },
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
               "n’en est pas un, et un zéro silencieux ferait croire la mission gratuite." },
        { url: "/ingenierie-ia-factory", label: "Quand le programme est une usine IA",
          action: "Comparez la structure de coût d’une usine IA à celle que vous venez de chiffrer : " +
                  "postes, phases, jalons — et ce qui pèse différemment.",
          gain: "De quoi refuser un ratio importé d’un centre de données classique : la densité et le " +
                "cycle de renouvellement du matériel déplacent l’équilibre entre bâti et équipement.",
          tip: "Le poste qui surprend le plus n’est pas le refroidissement, c’est le remplacement : " +
               "un cycle matériel court change la nature de la dépense, d’investissement en charge." }
      ]
    },
    {
      id: "dc-durabilite",
      profil: { objet: ["datacenter"], declencheur: ["texte", "chiffre"],
                levier: ["conformite"],
                entree: "une déclaration à publier qu’un tiers vérifiera, et une trajectoire à démontrer" },
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
                "regardé — un enjeu non instruit n'est pas un enjeu mineur. Le dernier chapitre " +
                "confronte vos enjeux retenus aux trente propositions pour des entreprises durables, " +
                "en distinguant ce que le projet DÉCIDE, ce qu'il ANTICIPE d'une politique publique, " +
                "et ce à quoi il CONTRIBUE sans en décider.",
          tip: "Un enjeu que les données donnent pour structurant et que personne ne soulève est le " +
               "cas le plus dangereux : il n'arrivera pas par une plainte, il arrivera par un fait." },
        { url: "/ingenierie-datacenter", label: "Prouver — les pièces, phase par phase",
          action: "Situez vos indicateurs dans la séquence projet et repérez le registre des pièces " +
                  "à remettre.",
          gain: "Le passage du tableau de bord au dossier : ce qu'on écrit, et ce qu'on REMET.",
          tip: "Les points de comptage se posent à la conception. Découvrir l'obligation de déclarer " +
               "après avoir figé le plan de comptage coûte une année de mesure." },
        { url: "/veille", label: "Suivre ce qui bouge sous la déclaration",
          action: "Relevez les textes et avis parus depuis votre dernière publication — CSRD, " +
                  "taxonomie, efficacité énergétique, déclaration européenne des centres de données.",
          gain: "L'écart entre ce que vous avez déclaré l'an dernier et ce qui sera exigé cette " +
                "année — c'est là que se logent les reprises de dossier.",
          tip: "Datez chaque obligation dans votre plan de collecte : une exigence nouvelle qui porte " +
               "sur l'exercice en cours suppose une donnée qu'on ne peut plus aller chercher." }
      ]
    },
    /* ══ LES DEUX RÔLES D'EXPLOITANT QUE CES QUATRE PAGES SERVENT ═══════
       CE QUI A DÉCIDÉ DE CES DEUX-LÀ, ET DE L'ABSENCE DES AUTRES. Un relevé
       des rôles qui décident dans un exploitant de centres de données en
       compte huit : exploitation de site, direction de l'exploitation,
       ingénierie et technique de site, direction générale, direction de
       programme, direction des systèmes d'information, direction commerciale,
       direction des ressources humaines. Les trois parcours ci-dessus en
       servaient déjà trois — programme, coût, durabilité — sans le dire.

       DEUX PARCOURS NEUFS, PAS SIX. Ce site porte QUATRE pages de centre de
       données, et un parcours ne peut viser deux fois la même. Six lectures
       tirées de quatre pages auraient produit six listes presque identiques,
       distinguées par leur seul titre — ce que la maison appelle un sommaire
       dans l'ordre. Les deux qui suivent se distinguent par leur PREMIÈRE
       page, celle sur laquelle un lecteur choisit : la veille pour celui à qui
       l'on réclame des chiffres, l'usine IA pour celui dont la charge
       informatique commande tout le reste. Aucun autre parcours ne commence
       par l'une ou par l'autre.

       ET CE QUE CE SITE NE SERT PAS, écrit plutôt que laissé vide. La
       direction commerciale d'un exploitant cherche un état de marché — où
       sont les capacités, ce que valent les juridictions ; ce site n'en porte
       aucun, Sentinel oui. L'ingénieur ou le technicien d'exploitation vit
       dans la GTB et le DCIM : rien ici ne s'adresse à lui. La direction des
       ressources humaines trouverait `/formation`, qui est de la formation
       CYBER INDUSTRIELLE — un autre métier, un autre vocabulaire, et l'y
       envoyer serait un renvoi trompeur. Voir ROLES_EXPLOITANT_DC plus bas. */
    {
      id: "dc-exploitation",
      profil: { objet: ["datacenter"], declencheur: ["chiffre"],
                levier: ["technique"],
                entree: "un site qui tourne déjà, et une demande extérieure de chiffres arrivée avant le dispositif de mesure" },
      icone: "🏭",
      role: "Exploitation d’un centre de données · on vous réclame des chiffres",
      cas: "Le cas le plus fréquent : une demande extérieure — bailleur, client, autorité, banque — arrive avant que le dispositif de mesure existe",
      pitch: "Vous n’avez pas de projet neuf : vous avez un site qui tourne, et quelqu’un vous demande " +
             "ce qu’il consomme. Ce parcours part de la demande, pas de la stratégie : quels chiffres " +
             "vous seront réclamés, comment on les établit, ce qu’on en fait ensuite.",
      etapes: [
        { url: "/veille", label: "Ce qu’on va vous demander, et quand",
          action: "Repérez les textes qui fixent ce qu’un exploitant déclare — périmètre, indicateurs, échéance — et lesquels bougent cette année.",
          gain: "La liste des obligations réelles avant de construire un tableau de bord, plutôt qu’après l’avoir construit pour autre chose.",
          tip: "Surveillez ce qui change le PÉRIMÈTRE plus que ce qui ajoute un indicateur : un seuil qui descend fait entrer des sites entiers, et c’est autrement plus coûteux qu’une colonne de plus." },
        { url: "/datacenter", label: "Établir les chiffres — énergie, eau, carbone",
          action: "Renseignez le profil de l’installation telle qu’elle tourne, puis lisez le bilan : électricité, eau du site ET de la source, CO₂e, fabrication amortie.",
          gain: "Des chiffres qui portent leur méthode, opposables à qui les demande — et non des valeurs reprises d’un tableur dont plus personne ne connaît les hypothèses.",
          tip: "L’eau du site et l’eau de la source ne sont pas la même grandeur. Un aéroréfrigérant sec affiche zéro sur site et consomme davantage à la source : déclarer la première seule est exact et trompeur." },
        { url: "/ingenierie-datacenter", label: "Les pièces, phase par phase",
          action: "Repérez, dans la séquence d’ingénierie, les pièces qui documentent ce que vous venez de mesurer — et celles qui manquent à votre dossier.",
          gain: "Le passage du chiffre à la pièce : ce qui se produit sur demande, et ce qui se reconstitue péniblement quand on ne l’a pas gardé.",
          tip: "Une pièce reconstituée après coup se voit : elle ne porte pas la date de la décision qu’elle documente. Gardez-la au moment où elle se fabrique, pas quand on la réclame." }
      ]
    },
    {
      id: "dc-charge-ia",
      profil: { objet: ["datacenter", "ia"], declencheur: ["projet"],
                levier: ["technique"],
                entree: "une charge de calcul décidée, dont le bâtiment doit suivre la densité" },
      icone: "🧮",
      role: "Direction des systèmes d’information · la charge commande le bâtiment",
      cas: "Inspiré des études d’usine IA : c’est la densité de la charge qui fixe le refroidissement, la puissance et l’emprise — jamais l’inverse",
      pitch: "Vous décidez ce qui tournera dans la salle, et cette décision commande tout le reste : la densité " +
             "fixe le refroidissement, le refroidissement fixe l’eau et l’électricité, l’électricité fixe " +
             "l’emprise et le raccordement. Ce parcours part donc de la charge, et descend vers le bâtiment.",
      etapes: [
        { url: "/ingenierie-ia-factory", label: "La charge d’abord — densité, refroidissement, puissance",
          action: "Partez de ce que vous comptez héberger : type d’accélérateurs, densité par baie, régime de fonctionnement — et lisez ce que cela impose au bâtiment.",
          gain: "La chaîne de conséquences dans le bon sens : c’est la charge qui contraint l’enveloppe, et une enveloppe dimensionnée avant la charge est dimensionnée pour la charge d’avant.",
          tip: "Une densité moyenne ne dimensionne rien : ce sont les baies les plus chaudes qui fixent le refroidissement, et elles décident du reste même si elles sont minoritaires." },
        { url: "/datacenter", label: "Ce que cette charge pèse, une fois installée",
          action: "Portez le profil obtenu dans le bilan énergie-eau-carbone, et regardez la part qui revient à la charge par rapport à celle du bâtiment.",
          gain: "La séparation qui décide des leviers : sur un site déjà efficace, le gain n’est plus dans le PUE mais dans ce qu’on fait tourner.",
          tip: "Un gain de PUE porte sur la fraction NON informatique. Sur un site à 1,2, elle représente un sixième du total : y concentrer l’effort revient à optimiser la petite moitié du problème." },
        { url: "/ingenierie-datacenter", label: "Ce que cela coûte à construire",
          action: "Chiffrez les travaux que cette charge impose — lots techniques, honoraires, séquence — avant de vous engager sur une date.",
          gain: "Le coût de la densité, lot par lot : c’est là qu’on voit ce qu’une baie à haute densité vaut réellement par rapport à trois baies ordinaires.",
          tip: "Le refroidissement liquide déplace le coût plutôt qu’il ne le supprime : moins d’air à traiter, mais une boucle, une distribution et une maintenance qui n’existaient pas." }
      ]
    },
    /* ── LE RÔLE QUI MANQUAIT : CELUI QUI CONTESTE UNE USINE IA ─────────────
       IL NE DOUBLE NI LE RSSI NI LA CONFORMITÉ, et la différence tient en une
       phrase : ceux-là construisent un dispositif, celui-ci conteste un
       programme qui est DÉJÀ PARTI. C'est un métier d'arrivée en cours de
       route — l'usine tourne, des cas d'usage sont en service, et la question
       n'est pas « que faudrait-il mettre en place » mais « qu'est-ce qui est
       parti sans son contrôle, et depuis combien de jours ».

       L'ORDRE DES ÉTAPES EST CELUI D'UNE RÉUNION QUI SE PASSE BIEN : le fait
       d'abord — la dette, qui ne se discute pas —, l'ordre imposé ensuite,
       et l'ambition en écart seulement après. Commencer par l'alerte met la
       salle en défense avant le premier chiffre, et on ne la récupère pas. */
    {
      id: "securite-ia",
      profil: { objet: ["ia"], declencheur: ["texte", "projet"],
                levier: ["conformite"],
                entree: "des systèmes d’IA déjà en production, dont personne ne tient la chaîne d’autonomie" },
      icone: "🧪",
      role: "Sécurité IA · contre-expertise d’une AI Factory en déploiement",
      cas: "Écrit pour le poste qui arrive quand l’usine tourne déjà : évaluer et challenger " +
           "une AI Factory en cours de déploiement, en secteur bancaire",
      pitch: "Vous héritez d’une usine IA lancée sans vous. Des cas d’usage sont en service, " +
             "d’autres sont promis pour une date, et on vous demande un avis de sécurité. " +
             "Ce parcours part du seul terrain où la discussion n’est pas une opinion contre " +
             "une autre : ce qui est parti sans son contrôle, et de combien de jours l’ambition " +
             "dépasse le temps que les contrôles demandent.",
      etapes: [
        { url: "/securite-ia", label: "La dette d’antériorité, puis la chaîne",
          action: "Deux instruments sur la même page, dans cet ordre. D’abord la " +
                  "contre-expertise : déclarez les cas d’usage en service et les contrôles " +
                  "réellement en place, et soustrayez. Ensuite la chaîne d’autonomie : " +
                  "cotez chaque système du parc sur les cinq maillons.",
          gain: "Un compte de cas et un nombre de jours — les deux seuls chiffres qui se " +
                "discutent avec un directeur — puis le maillon ouvert qui commande, sans " +
                "avoir eu à imaginer le scénario d’attaque.",
          tip: "Ne demandez pas de taux de couverture : il monte pendant que des cas d’usage partent sans contrôle, puisqu’il compte les contrôles et non les cas découverts. Et cotez chaque système séparément — coter un système « représentatif » revient à moyenner de tête ce que la méthode vous interdit de moyenner." },
        { url: "/gouvernance-ia", label: "La gouvernance, avec le Data Office",
          action: "Situez qui décide de quoi : inventaire des cas d’usage, politique d’usage " +
                  "des outils génératifs, encadrement du Shadow AI.",
          gain: "Les trois contrôles de gouvernance sans lesquels les contrôles techniques " +
                "portent sur un périmètre inconnu.",
          tip: "Publiez l’outil autorisé AVANT l’interdiction : une politique sans alternative qui fasse le travail crée le Shadow AI qu’elle prétend traiter." },
        { url: "/nis2", label: "Le cadre applicable, entité par entité",
          action: "Déterminez lequel de DORA, NIS 2 et du règlement IA s’applique à chaque " +
                  "entité et à chaque cas d’usage.",
          gain: "Le texte opposable, avant d’écrire une exigence au nom d’un texte qui ne " +
                "s’applique pas.",
          tip: "DORA prime sur NIS 2 pour les entités financières. Un cas d’usage de scoring de crédit relève en plus de l’annexe III du règlement IA — ce n’est pas le même régime, ni la même équipe." },
        { url: "/developpement-securise", label: "La chaîne de production",
          action: "Branchez les contrôles sur la chaîne : relecture du code produit par l’IA, " +
                  "scan des dépendances, secrets, signature et provenance des modèles.",
          gain: "Des contrôles qui bloquent la fusion, et non des consignes.",
          tip: "Une consigne sans blocage technique tient trois semaines. Le « vibe coding » n’est pas du code écrit par une IA : c’est du code accepté sans relecture, et c’est l’acceptation qu’on encadre." },
        { url: "/technologies-securite", label: "Les familles de solutions",
          action: "Confrontez filtrage IA, IAM des agents, MLOps/LLMOps, validation de modèles, " +
                  "serveurs d’outils et API à ce que chacune ne fait PAS.",
          gain: "De quoi refuser une solution présentée comme couvrant un risque qu’elle " +
                "ne couvre pas.",
          tip: "La description d’un outil raccordé entre dans l’invite du modèle : un serveur d’outils est une surface d’injection, pas seulement une surface d’exécution." },
        { url: "/formation", label: "Les ateliers, et les deux publics",
          action: "Séparez ce qui est dit aux métiers de ce qui est dit aux équipes cyber.",
          gain: "Deux contenus qui portent, au lieu d’un seul qui ne parle à personne.",
          tip: "Une sensibilisation employée à la place d’un garde-fou transfère la charge sur l’utilisateur — et c’est lui qui portera la faute le jour de l’incident." },
        { url: "/feuille-de-route", label: "La trajectoire, et ce qu’elle coûte",
          action: "Séquencez les contrôles manquants avec leurs prérequis, puis chiffrez.",
          gain: "Un ordre qui n’est pas une préférence : c’est ce que les prérequis autorisent.",
          tip: "Un lot ne dure pas la somme de ses contrôles mais la durée du plus long — et c’est celui-là qu’il faut nommer en comité, pas la moyenne." },
        { url: "/veille", label: "Les menaces armées par l’IA",
          action: "Suivez ce qui ne dépend d’aucun de vos systèmes : hypertrucages, ingénierie " +
                  "sociale assistée, fraude générative.",
          gain: "La direction qui tombe entre les chaises — elle n’attaque pas votre usine, " +
                "donc durcir l’usine n’y change rien.",
          tip: "Ce n’est pas un sujet d’usine IA : c’est un sujet de processus métier. Le rappel de vérification d’un virement se traite au métier, pas au modèle." }
      ]
    },
    {
      id: "decouverte",
      /* PAS D'`objet` DANS LE PROFIL, ET C'EST CE QUI LE DÉFINIT. Le conseiller
         reconnaît le recours à cette absence : celui qu'on propose quand aucune
         réponse ne désigne rien. Lui donner un objet le ferait concourir, et un
         filet qui concourt gagne au mauvais moment — ou perd de justesse quand
         on aurait eu besoin de lui. Il garde en revanche son `entree`, parce
         qu'un recours proposé sans dire ce qu'il est n'est qu'un lot de
         consolation. */
      profil: { entree: "aucune réponse ne désigne d’itinéraire — celui-ci fait le tour " +
                        "de ce que le site sait faire, et le diagnostic express est au bout" },
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
        { url: "/services", label: "Ce que fait CONSEILPREV",
          action: "Lisez la chaîne complète — état des lieux, architecture et segmentation, " +
                  "analyse de risque, supervision, maintien en condition de sécurité.",
          gain: "De quoi situer ce que vous lirez ensuite : un référentiel se comprend mieux " +
                "quand on sait quel travail il commande.",
          tip: "Repérez d’abord l’étape où VOUS en êtes : lire la méthode d’une phase déjà passée " +
               "fait perdre le fil, et lire celle d’une phase lointaine décourage." },
        { url: "/glossaire-62443", label: "Glossaire · 1-2",
          action: "Fixez le vocabulaire : zone, conduit, SL-T, SL-A, IACS, CSMS.",
          gain: "De quoi suivre une réunion technique sans perdre le fil au troisième sigle.",
          tip: "La confusion SL-T (cible) / SL-A (atteint) est la plus fréquente, et la plus lourde de conséquences." },
        { url: "/assistant", label: "Poser la question directement",
          action: "Interrogez l’assistant sur votre situation plutôt que de chercher la page qui " +
                  "en parle : « des automates hors support, et un audit dans six mois ».",
          gain: "La réponse au cas précis, sans passer par le sommaire — c’est la voie la plus " +
                "courte quand on ne sait pas encore quel mot chercher.",
          tip: "N’y saisissez ni nom de personne ni schéma d’installation : la conversation n’est " +
               "pas conservée, mais elle transite par un fournisseur tiers." },
        { url: "/ressources", label: "Les sources, pour vérifier par vous-même",
          action: "Ouvrez les références de première main — ANSSI, CERT-FR, ENISA, CISA, IEC, " +
                  "ISO, NIST SP 800-82.",
          gain: "De quoi contrôler à la source ce que vous venez de lire, et continuer sans nous.",
          tip: "Ne partez jamais d’une synthèse pour une décision opposable : les synthèses " +
               "vieillissent sans le dire, les textes portent leur date." },
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
    /* ── LA BANQUE SE SÉPARE DE L'ASSURANCE, ET CE N'EST PAS UN DÉTAIL ─────
       LE SITE NE CONNAISSAIT QU'UN SEUL SEAU — « Assurance & services
       financiers » — alors que son propre moteur d'usine IA distingue déjà
       banque et assurance, et que le règlement sur l'IA les sépare lui aussi :
       l'évaluation de solvabilité et la notation de crédit des personnes
       physiques relèvent de l'annexe III, point 5 b, et c'est un cas d'usage
       BANCAIRE. Un directeur de banque qui lisait « assurance » en tête de son
       parcours en concluait, raisonnablement, que la page ne parlait pas de
       lui.

       CE QUE CE SECTEUR APPORTE QUE L'AUTRE N'A PAS : la banque possède déjà
       la fonction qui manque partout ailleurs — une validation indépendante
       des modèles, tenue depuis le risque de crédit, capable de REFUSER une
       mise en service. Presque aucune ne l'a étendue aux modèles de langage.
       C'est le seul secteur où la réponse au « qui peut dire non » existe
       avant qu'on pose la question, et où il suffit d'élargir un mandat
       plutôt que de créer une fonction. */
    {
      id: "banque", icone: "🏛️", nom: "Banque de détail et de financement",
      enjeu: "Faire tenir ensemble trois textes sur une même usine IA — et étendre aux modèles " +
             "de langage la validation indépendante qui existe déjà pour le risque de crédit.",
      textes: "DORA (résilience opérationnelle numérique, applicable depuis janvier 2025), " +
              "le règlement (UE) 2024/1689 sur l’IA — dont l’annexe III, point 5 b, pour " +
              "l’évaluation de solvabilité et la notation de crédit des personnes physiques — " +
              "et NIS 2, qui s’efface là où DORA couvre la matière.",
      piege: "Le modèle de scoring construit par l’équipe data, jamais qualifié au titre de " +
             "l’annexe III parce que le sujet est arrivé par la conformité et non par la chaîne " +
             "de production. Il tourne, il décide, et il n’a pas de dossier technique.",
      notes: {
        "/gouvernance-ia": "Qualifiez d’abord, gouvernez ensuite : l’évaluation de solvabilité " +
                           "et la notation de crédit des personnes physiques relèvent de " +
                           "l’annexe III, point 5 b. La détection de fraude financière en est " +
                           "exclue — mais l’exclusion porte sur la FINALITÉ, et elle se vérifie " +
                           "cas par cas, pas par famille d’outils.",
        "/securite-ia": "Votre validation indépendante des modèles existe déjà, pour le risque " +
                        "de crédit. La question n’est pas de la créer : c’est de savoir si son " +
                        "mandat couvre un modèle de langage que le fournisseur met à jour sans " +
                        "préavis derrière la même adresse.",
        "/nis2": "DORA écarte les dispositions correspondantes de NIS 2 au titre de l’article 4, " +
                 "supervision comprise. La réserve vaut d’être lue : un groupe bancaire porte " +
                 "souvent les deux régimes selon l’entité, parce que DORA ne couvre pas toutes " +
                 "les filiales.",
        "/juridique": "Deux jeux de clauses, pas un : celles que DORA impose aux prestataires " +
                      "TIC, et celles qu’il faut à un fournisseur de modèle — notamment le " +
                      "préavis de changement de version, qu’aucun contrat de service standard " +
                      "ne prévoit.",
        "/audit-conformite": "Le dossier technique d’un système à haut risque et les journaux " +
                             "associés ne se reconstituent pas après coup : ce qui n’a pas été " +
                             "conservé pendant l’exploitation ne s’invente pas au contrôle.",
        "/feuille-de-route": "Deux calendriers distincts courent en parallèle — celui de DORA, " +
                             "déjà applicable, et celui du régime haut risque. Les fondre en un " +
                             "seul plan fait glisser le plus proche.",
        "/exigences-prestataires": "Un fournisseur de modèle est un prestataire TIC comme un " +
                                   "autre — sauf qu’il change de version sans préavis derrière " +
                                   "la même adresse, ce qu’aucune stratégie de sortie ne prévoit.",
        "/referentiel": "La 62443 ne vous concerne guère, sauf pour vos infrastructures " +
                        "techniques : votre cadre est DORA et le règlement sur l’IA."
      },
      etapes: [
        { url: "/secteurs", label: "Secteurs · Banque",
          action: "Repérez ce qui sépare votre cadre de celui de l’assurance : ce n’est pas le " +
                  "même point de l’annexe III, ni le même cas d’usage.",
          gain: "Le cadre : ici la qualification du cas d’usage commande le régime, et le " +
                "régime commande le dossier à tenir.",
          tip: "Assurance et banque ont longtemps partagé une seule page sur ce site. Elles ne partagent ni le point de l’annexe III qui les vise, ni le calendrier qui en découle." },
        { url: "/gouvernance-ia", label: "Qualifier chaque cas d’usage",
          action: "Passez vos cas d’usage un par un : scoring, octroi, fraude, LCB-FT, " +
                  "assistant conseiller — et dites lequel relève du haut risque.",
          gain: "La liste de ceux qui portent un dossier technique à tenir, et de ceux qui n’en " +
                "portent pas. Les deux réponses sont utiles ; l’absence de réponse ne l’est pas.",
          tip: "La détection de fraude financière est exclue de l’annexe III, mais l’exclusion porte sur la finalité. Un même moteur servant au scoring et à la fraude ne se qualifie pas en bloc." },
        { url: "/securite-ia", label: "La dette d’antériorité, et la chaîne",
          action: "Déclarez les cas d’usage en service et les contrôles réellement en place, " +
                  "puis soustrayez. Cotez ensuite chaque système sur les cinq maillons.",
          gain: "Un compte de cas et un nombre de jours, avant que le superviseur ne pose la " +
                "même question — et le maillon ouvert qui commande.",
          tip: "Inscrivez la validation indépendante des modèles parmi les contrôles en place seulement si son mandat couvre l’IA générative. Sinon elle compte pour le risque de crédit, pas pour l’usine." },
        { url: "/nis2", label: "DORA, NIS 2, et l’article 4",
          action: "Déterminez, entité par entité, lequel des deux régimes s’applique.",
          gain: "Le texte opposable, avant d’écrire une exigence au nom d’un texte qui ne " +
                "s’applique pas à cette entité-là.",
          tip: "L’article 4 n’efface NIS 2 que pour les matières couvertes, et que pour les entités couvertes. Les filiales non financières du groupe peuvent rester sous NIS 2." },
        { url: "/juridique", label: "Les clauses du fournisseur de modèle",
          action: "Passez vos contrats au clausier : clauses DORA obligatoires, puis ce qui " +
                  "manque en propre à un contrat de modèle.",
          gain: "Le préavis de changement de version, obtenu avant la mise à jour qui invalide " +
                "l’évaluation — pas après.",
          tip: "Réservé aux comptes connectés. Le contrat est analysé en mémoire, jamais conservé." },
        { url: "/audit-conformite", label: "Le dossier, et les journaux",
          action: "Vérifiez ce qui est conservé pour chaque système à haut risque, et pendant " +
                  "combien de temps.",
          gain: "L’écart entre ce qu’on croit tracer et ce qu’on pourrait produire.",
          tip: "Tranchez la durée de conservation avec le délégué à la protection des données AVANT d’ouvrir le robinet : un journal d’invites contient des données personnelles en volume." },
        { url: "/feuille-de-route", label: "Deux calendriers, un plan",
          action: "Séquencez séparément ce que DORA exige déjà et ce que le régime haut risque " +
                  "exigera, puis arbitrez.",
          gain: "Une trajectoire où l’échéance la plus proche ne disparaît pas derrière la plus " +
                "lointaine.",
          tip: "Traitez d’abord les entités portant les fonctions critiques : c’est par elles que le superviseur commencera." }
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
        "/securite-ia": "Le SOC augmenté et l’usine IA sont deux sujets, pas un : l’un emploie " +
                        "l’IA dans la défense, l’autre la déploie pour les métiers. Le premier " +
                        "échappe presque toujours à l’inventaire des cas d’usage, parce qu’il " +
                        "est porté par la cyber elle-même — et un inventaire qui oublie l’IA " +
                        "de la cyber n’est pas un inventaire.",
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
        /* LA SÉCURITÉ DE L'IA ENTRE ICI, ENTRE LE CADRE ET LES PRESTATAIRES,
           et cette place dit quelque chose. Un fournisseur de modèle est un
           prestataire TIC comme un autre au sens de DORA — mais il change de
           version sans préavis derrière la même adresse, ce qu'aucune
           stratégie de sortie ne prévoit. Lire la dette d'antériorité AVANT
           de remplir le registre évite d'y inscrire un service en croyant y
           inscrire une version. */
        { url: "/securite-ia", label: "L’usine IA, et ce qui est déjà parti sans contrôle",
          action: "Déclarez les cas d’usage d’IA en service dans le groupe et les contrôles " +
                  "réellement en place, puis soustrayez.",
          gain: "Le nombre de cas d’usage en service sans contrôle requis, et depuis combien " +
                "de jours — avant que le régulateur ne pose la même question.",
          tip: "Le scoring de crédit relève de l’annexe III du règlement IA en plus de DORA : ce n’est ni le même régime, ni la même équipe, ni le même calendrier." },
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

  /* ═══════════════════════════════════════════════════════════════════════
     CE QU'ON FAIT À LA FIN — l'étape que dix-huit parcours sur dix-neuf
     n'avaient pas.

     LE RELEVÉ DU 4 SEPTEMBRE 2026. Un seul parcours se terminait par un
     geste : « achats », qui finit sur /contact. Les dix-huit autres
     s'arrêtaient sur une page de contenu — le lecteur suivait sept étapes,
     arrivait au bout, et le bandeau s'éteignait sans rien lui proposer. Un
     chemin de lecture qui ne mène nulle part n'est pas un parcours, c'est un
     sommaire dans l'ordre.

     ELLE EST ÉCRITE UNE FOIS ET AJOUTÉE PAR ÉNUMÉRATION, pas recopiée
     dix-huit fois. Une conclusion recopiée dix-huit fois diverge à la
     première retouche, et c'est celle qu'on oublie qui reste fausse. Surtout :
     le parcours écrit dans six mois la recevra sans qu'on y pense — c'est la
     seule façon qu'elle ne manque pas de nouveau.

     ELLE NE S'AJOUTE PAS À CEUX QUI CONCLUENT DÉJÀ. Un parcours qui finit sur
     /contact ou /vos-projets a sa conclusion ; lui en coller une seconde
     ferait deux fois le même geste, et la deuxième serait de trop. */
  /* ══ LES HUIT RÔLES D'UN EXPLOITANT, ET CE QUE CE SITE-CI LEUR OFFRE ═══
     POURQUOI CETTE TABLE. Cinq parcours de centre de données servent
     maintenant cinq rôles, et trois autres n'en ont pas. Sans cette table, ces
     trois absences se lisent toutes comme un oubli : on rouvre le sujet dans
     six mois, on écrit un sixième parcours tiré des quatre mêmes pages, et
     l'on envoie la direction des ressources humaines sur `/formation`, qui est
     de la formation cyber industrielle et non de l'exploitation de centre de
     données. Une absence motivée vaut mieux qu'une absence muette.

     `porte: null` DIT AUSSI OÙ ALLER QUAND CE N'EST PAS ICI. Deux de ces rôles
     sont servis par l'autre plateforme du cabinet — c'est écrit dans le motif.
     Le troisième n'est servi nulle part, et c'est le constat, pas un projet.

     Une recette compare cette table au catalogue : une porte qui nomme un
     parcours disparu, ou un parcours de centre de données qu'aucune ligne ne
     revendique, fait tomber la règle. */
  var ROLES_EXPLOITANT_DC = [
    { role: "Direction de programme / de projet", porte: "dc-projet",
      motif: "la séquence du projet, de la stratégie à l'usine IA" },
    { role: "Direction générale · arbitrage d'investissement", porte: "dc-couts",
      motif: "ce que l'opération coûte, lot par lot, avant l'engagement" },
    { role: "Direction durabilité · RSE", porte: "dc-durabilite",
      motif: "compter, arbitrer la matérialité, prouver, suivre" },
    { role: "Exploitation d'un site en service", porte: "dc-exploitation",
      motif: "part de la demande extérieure, pas de la stratégie" },
    { role: "Direction des systèmes d'information et de la technologie",
      porte: "dc-charge-ia",
      motif: "part de la charge informatique, qui commande le bâtiment" },
    { role: "Direction commerciale & développement", porte: null,
      motif: "PAS ICI : ce rôle cherche un état de marché — où sont les " +
             "capacités, ce que valent les juridictions, ce qu'une " +
             "implantation rapporte. Ce site ne porte aucun de ces trois. " +
             "La plateforme Sentinel les porte, et lui ouvre un parcours." },
    { role: "Ressources humaines, formation & développement des compétences",
      porte: null,
      motif: "PAS ICI : `/formation` existe, mais c'est de la formation CYBER " +
             "INDUSTRIELLE — sensibilisation exploitation, essentiels 62443, " +
             "exercices de crise. L'y envoyer pour former des équipes de " +
             "centre de données serait un renvoi trompeur. Sentinel porte le " +
             "volet montée en compétence sur les outils d'IA." },
    { role: "Ingénieur ou technicien d'exploitation de site", porte: null,
      motif: "PAS ICI, ET NULLE PART : ce rôle vit dans la gestion technique " +
             "du bâtiment et le DCIM. Aucune des deux plateformes du cabinet " +
             "ne s'y adresse, et lui composer un chemin à partir de pages " +
             "d'ingénierie et de bilan carbone serait le promener." }
  ];

  var ETAPE_FINALE = {
    url: "/vos-projets", label: "Soumettre votre projet",
    action: "Décrivez le périmètre que vous venez de parcourir — installations, " +
            "enjeu principal, échéance — et ce que vous attendez d'un tiers.",
    gain: "Le passage de la lecture à l'engagement : un interlocuteur qui a déjà " +
          "le contexte, au lieu d'un premier rendez-vous consacré à le reconstituer.",
    tip: "Dites où vous en êtes VRAIMENT, y compris si c'est « nulle part » : " +
         "un état des lieux honnête raccourcit le cadrage de plusieurs semaines, " +
         "un état des lieux flatteur le rallonge d'autant."
  };

  /* ── CE QUE VOUS EMPORTEZ ───────────────────────────────────────────────
     CETTE ÉTAPE ÉTAIT LA MÊME VINGT-DEUX FOIS. Elle est ajoutée à tous les
     itinéraires par `conclure` ci-dessous, et elle disait à tout le monde la
     même chose : « décrivez le périmètre que vous venez de parcourir ». Un
     visiteur qui a passé dix étapes sur l'analyse de risque et un autre qui
     vient de chiffrer un centre de données lisaient, en dernier, la phrase
     identique. C'est la seule étape où le site demande quelque chose au
     lecteur, et c'était la seule qui ne savait pas ce qu'il venait de faire.

     L'ACTE, LUI, EST BIEN LE MÊME : on remplit le même formulaire. Ce n'est
     donc pas `action` qu'il fallait réécrire vingt-deux fois — une reformulation
     n'aurait rien rendu de plus vrai. Ce qui manquait, c'est CE QU'ON EMPORTE :
     les pièces que CET itinéraire a produites, et qu'on pose sur la table au
     premier rendez-vous. Chacune est nommée ici, à côté des autres, parce que
     c'est côte à côte qu'on voit si deux itinéraires produisent la même chose
     — et si c'était le cas, ce sont les itinéraires qu'il faudrait revoir,
     pas leur conclusion.

     La règle qui garde ce bloc est dans la recette, pas ici : un garde-fou
     qui lèverait dans le navigateur tuerait le bandeau sur TOUTES les pages
     pour une faute d'inventaire. Le site dégrade, la recette refuse. */
  var EMPORTER = {
    /* — les rôles — */
    rssi: "un diagnostic chiffré, un score de maturité OT, un découpage en zones " +
          "avec ses niveaux cibles et une feuille de route jalonnée",
    ot: "un découpage en zones, les exigences système retenues, votre position sur " +
        "les vingt-sept points de la checklist et un plan de continuité OT",
    projet: "une architecture cible, les exigences système et composants à verser au " +
            "CCTP, et la grille de qualification 2-4 de vos prestataires",
    direction: "votre qualification NIS 2, un diagnostic chiffré, un operating model " +
               "et une feuille de route dont chaque euro porte une échéance",
    conformite: "votre qualification NIS 2, le dossier de conformité, la grille " +
                "Governance by Design de vos systèmes d'IA et les écarts relevés à l'audit",
    "dc-projet": "un document d'ouverture d'étude, le bilan énergie-eau-carbone du " +
                 "programme et la séquence d'ingénierie phase par phase",
    "dc-couts": "un coût d'opération complet — les travaux poste par poste, puis les " +
                "honoraires qu'ils portent — et ce qui n'est PAS chiffré, compté comme tel",
    "dc-durabilite": "un bilan opposable, la matérialité arbitrée enjeu par enjeu et le " +
                     "registre des pièces à remettre, phase par phase",
    "dc-exploitation": "les chiffres — énergie, eau, carbone — de l'installation telle " +
                       "qu'elle tourne, la méthode qui les porte, et les pièces, phase par " +
                       "phase, qui manquent à votre dossier",
    "dc-charge-ia": "le profil de la charge — densité, refroidissement, puissance —, ce " +
                    "qu'elle pèse une fois installée et ce qu'elle coûte à construire",
    "securite-ia": "l'inventaire de votre dette d'antériorité, la cotation de la chaîne " +
                   "d'autonomie, le cadre applicable entité par entité, et la trajectoire " +
                   "avec ce qu'elle coûte",
    decouverte: "une lecture des secteurs et des études de cas, le vocabulaire du " +
                "référentiel 62443 et un diagnostic express déjà passé",
    /* — les secteurs — */
    energie: "votre qualification NIS 2, un découpage en zones qui traite les postes " +
             "distants à part, et une feuille de route adossée aux arrêts réseau",
    eau: "l'état réel de votre inventaire, un diagnostic express déjà passé, un score de " +
         "maturité et une feuille de route priorisée par criticité pour le service public",
    manufacturing: "un découpage en zones compatible avec les lignes, et les exigences " +
                   "système et composants à opposer à vos intégrateurs",
    agro: "un découpage en zones de vos procédés continus, les technologies de sécurité " +
          "retenues en compensation et un calendrier de correctifs adossé aux arrêts",
    chimie: "un découpage en zones qui isole les systèmes instrumentés de sécurité, les " +
            "exigences système retenues et un programme qui ne réinvalide pas vos qualifications",
    transport: "les exigences prestataires opposables à vos sous-traitants, un découpage " +
               "en zones de vos flux M2M et ce que la supervision apporte sur un parc mobile",
    banque: "vos cas d'usage qualifiés un par un, l'articulation de DORA et de NIS 2, les " +
            "clauses à obtenir du fournisseur de modèle et deux calendriers tenus ensemble",
    finance: "l'articulation de NIS 2 et de DORA, l'inventaire de ce qui est déjà parti " +
             "sans contrôle, et les exigences prestataires de vos fournisseurs TIC",
    nucleaire: "la partie du référentiel qui vous concerne, un découpage en zones " +
               "compatible avec la sûreté classée et un programme de sécurité adossé à votre organisation",
    aero: "les exigences prestataires pour la cascade de vos donneurs d'ordre, un " +
          "programme de sécurité et les exigences de développement sécurisé à imposer"
  };

  var CONCLUSIONS = ["/vos-projets", "/contact"];
  /* `emporter` n'est pas facultatif : un itinéraire dont on ne sait pas dire
     ce qu'il produit n'a pas de conclusion à offrir. Absent, on retombe sur la
     phrase commune plutôt que d'afficher un trou — et la recette, elle, refuse
     l'absence. Le site dégrade proprement ; la faute, on la voit en recette. */
  function conclure(etapes, id) {
    var derniere = etapes[etapes.length - 1];
    if (derniere && CONCLUSIONS.indexOf(derniere.url) >= 0) return etapes;
    var emporte = EMPORTER[id];
    var fin = {
      url: ETAPE_FINALE.url, label: ETAPE_FINALE.label,
      action: ETAPE_FINALE.action, tip: ETAPE_FINALE.tip,
      gain: emporte
        ? "Vous arrivez avec " + emporte + ". " + ETAPE_FINALE.gain
        : ETAPE_FINALE.gain
    };
    return etapes.concat([fin]);
  }
  for (var iP = 0; iP < PARCOURS.length; iP++) {
    PARCOURS[iP].etapes = conclure(PARCOURS[iP].etapes, PARCOURS[iP].id);
  }
  for (var iS = 0; iS < SECTEURS.length; iS++) {
    SECTEURS[iS].etapes = conclure(SECTEURS[iS].etapes, SECTEURS[iS].id);
  }

  /* Le moteur et ses données sont désormais définis. Sous Node (recette), on
     les expose et on s'arrête AVANT tout code de page : rien ci-dessous ne
     tourne sans navigateur, et le moteur s'éprouve avec les VRAIES données,
     sans les recopier — donc sans risque de divergence entre test et site. */
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      AXES_URL: AXES_URL, POIDS: POIDS, AXE_LABEL: AXE_LABEL, AXE_COURT: AXE_COURT,
      personnaliser: personnaliser, PARCOURS: PARCOURS, SECTEURS: SECTEURS,
      ROLES_EXPLOITANT_DC: ROLES_EXPLOITANT_DC, EMPORTER: EMPORTER,
      QUESTIONS: QUESTIONS, EN_CLAIR: EN_CLAIR, POIDS_Q: POIDS_Q,
      MARGE_MINIMALE: MARGE_MINIMALE, conseiller: conseiller
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
    "border-radius:14px;padding:22px 24px;margin:auto;min-width:0;",
    "transition:max-width .22s ease}",
    /* ── LE MODE LECTURE ──────────────────────────────────────────────────
       LA MODALE FAIT DEUX MÉTIERS, ET ELLE LES FAISAIT À LA MÊME TAILLE.
       Tant qu'on CHOISIT, elle porte deux listes déroulantes et doit rester
       compacte : une boîte de dialogue large pour deux menus paraît vide.
       Dès qu'un parcours est choisi, elle porte de six à onze étapes, chacune
       avec son action, son gain et son piège — et 780 px les empilait en
       colonnes étroites qu'on lit mal, dans une modale qu'il faut faire
       défiler longuement.

       CE QUI S'AGRANDIT N'EST DONC PAS « LA MODALE » : c'est la LECTURE.
       Le choix reste compact, la fiche s'ouvre en grand. Et la transition
       porte sur `max-width` seule — animer la hauteur ferait sauter le
       contenu pendant qu'on commence à le lire. */
    ".pc-card.pc-lecture{max-width:1060px;padding:26px 30px}",
    ".pc-lecture .pc-title{font-size:22px}",
    ".pc-lecture .pc-intro{font-size:14px;line-height:1.7}",
    ".pc-lecture .pc-fiche-ic{font-size:30px}",
    ".pc-lecture .pc-fiche-role{font-size:18.5px}",
    ".pc-lecture .pc-fiche-pitch{font-size:14.5px;line-height:1.7;max-width:86ch}",
    ".pc-lecture .pc-cas{font-size:13px;line-height:1.65}",
    ".pc-lecture .pc-etape{padding:17px 20px;border-radius:12px}",
    ".pc-lecture .pc-e-label{font-size:15.5px}",
    ".pc-lecture .pc-num{width:28px;height:28px;font-size:12.5px}",
    ".pc-lecture .pc-e-d{font-size:14px;line-height:1.7}",
    ".pc-lecture .pc-e-tip{font-size:13.5px;line-height:1.65;padding-left:13px}",
    ".pc-lecture .pc-go{font-size:13px;padding:8px 14px}",
    ".pc-lecture .pc-prio-t{font-size:15px}",
    ".pc-lecture .pc-prio-syn,.pc-lecture .pc-prio-l li,.pc-lecture .pc-prio-det{",
    "font-size:13.5px;line-height:1.7}",
    ".pc-lecture .pc-compte{font-size:13px}",
    /* SOUS 1100 px L'ÉCRAN NE DONNE PAS CES 1060 px : la règle ci-dessus ne
       fait alors rien de mal, mais les tailles de texte, elles, s'appliquent
       quand même et serrent le texte. On les rend donc à leur valeur de
       choix tant que la place manque. */
    "@media(max-width:1100px){.pc-card.pc-lecture{padding:22px 24px}",
    ".pc-lecture .pc-e-d{font-size:13px}.pc-lecture .pc-e-label{font-size:14px}",
    ".pc-lecture .pc-fiche-pitch{font-size:13px}}",
    "@media(prefers-reduced-motion:reduce){.pc-card{transition:none}}",
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
    /* ── LA PORTE DE CEUX QUI NE CONNAISSENT PAS NOTRE DÉCOUPAGE ──────────
       Repliée par défaut : celui qui sait qu'il est RSSI ne doit pas la
       traverser pour arriver à sa liste. Elle s'ouvre en un clic, et le
       verdict qu'elle rend REMPLIT la liste déroulante au lieu de la
       remplacer — on ne retire jamais au visiteur la main sur son choix. */
    ".pc-conseil{margin-top:14px;border:1px solid var(--line);border-radius:12px;overflow:hidden}",
    ".pc-conseil>summary{cursor:pointer;list-style:none;padding:11px 14px;font-size:13px;",
    "font-weight:600;color:var(--ink);background:rgba(255,255,255,.02);display:flex;",
    "align-items:center;gap:9px}",
    ".pc-conseil>summary::-webkit-details-marker{display:none}",
    ".pc-conseil>summary::after{content:'▸';margin-left:auto;color:var(--muted2);font-size:12px;",
    "transition:transform .18s ease}",
    ".pc-conseil[open]>summary::after{transform:rotate(90deg)}",
    ".pc-conseil>summary:hover{background:rgba(255,255,255,.05)}",
    ".pc-conseil>summary:focus-visible{outline:2px solid var(--teal);outline-offset:-2px}",
    ".pc-cq{padding:14px;display:grid;gap:14px}",
    ".pc-cq fieldset{border:0;margin:0;padding:0;min-width:0}",
    ".pc-cq legend{font-family:var(--mono);font-size:10px;letter-spacing:.09em;",
    "text-transform:uppercase;color:var(--muted2);padding:0;margin-bottom:7px}",
    ".pc-cq-opts{display:grid;gap:5px}",
    ".pc-cq-opt{display:flex;align-items:flex-start;gap:8px;font-size:12.5px;color:var(--muted);",
    "line-height:1.5;cursor:pointer;padding:5px 7px;border-radius:7px}",
    ".pc-cq-opt:hover{background:rgba(255,255,255,.04);color:var(--ink)}",
    ".pc-cq-opt input{margin:2px 0 0;flex-shrink:0;accent-color:var(--teal)}",
    ".pc-cq-opt input:focus-visible{outline:2px solid var(--teal);outline-offset:2px}",
    ".pc-cq-opt:has(input:checked){background:rgba(45,212,191,.10);color:var(--ink)}",
    /* ── LE VERDICT ────────────────────────────────────────────────────── */
    ".pc-verdict{border-top:1px solid var(--line);padding:14px;background:rgba(255,255,255,.015)}",
    ".pc-v-motif{font-size:12.5px;color:var(--muted);line-height:1.6;margin-bottom:10px}",
    ".pc-v-motif b{color:var(--ink)}",
    ".pc-v-card{border:1px solid var(--teal);border-left:3px solid var(--teal);border-radius:0 10px 10px 0;",
    "padding:11px 13px;margin-bottom:8px}",
    ".pc-v-card.pc-v-second{border-color:var(--line);border-left-color:var(--muted2)}",
    ".pc-v-role{font-size:13.5px;font-weight:700;color:var(--ink);display:flex;gap:8px;align-items:baseline}",
    ".pc-v-pts{font-family:var(--mono);font-size:10px;color:var(--muted2);margin-left:auto;flex-shrink:0}",
    ".pc-v-entree{font-size:12.3px;color:var(--muted);line-height:1.6;margin-top:4px}",
    ".pc-v-apport{font-size:12px;color:var(--muted2);line-height:1.55;margin-top:5px;font-style:italic}",
    ".pc-v-go{margin-top:9px;font:inherit;font-size:12px;font-weight:600;color:var(--bg);",
    "background:var(--teal);border:0;border-radius:7px;padding:7px 13px;cursor:pointer}",
    ".pc-v-go:hover{filter:brightness(1.1)}",
    ".pc-v-go:focus-visible{outline:2px solid var(--ink);outline-offset:2px}",
    /* LES ÉCARTÉS SONT REPLIÉS, MAIS ILS SONT LÀ. Un conseil dont on ne peut
       pas voir ce qu'il a refusé ne se conteste pas — et un conseil qu'on ne
       peut pas contester ne vaut rien en réunion. */
    ".pc-v-ec{margin-top:6px;border-top:1px dashed var(--line);padding-top:8px}",
    ".pc-v-ec>summary{cursor:pointer;list-style:none;font-size:11.5px;color:var(--muted2);",
    "font-family:var(--mono);letter-spacing:.04em}",
    ".pc-v-ec>summary::-webkit-details-marker{display:none}",
    ".pc-v-ec>summary:hover{color:var(--ink)}",
    ".pc-v-ec>summary:focus-visible{outline:2px solid var(--teal);outline-offset:2px}",
    ".pc-v-ec ul{margin:8px 0 0;padding-left:17px}",
    ".pc-v-ec li{font-size:11.8px;color:var(--muted);line-height:1.6;margin-bottom:5px}",
    ".pc-v-ec li b{color:var(--muted2);font-weight:600}",
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
    /* CE QUI RESTE A FAIRE TIENT EN BLEU, IMMOBILE ; CE QUI EST VALIDE BAT EN
       VERT. Les images-cles `cpValide` et la cadence `--cp-battement` vivent
       dans styles.css : ce module les EMPLOIE, il ne les redefinit pas.
       Trois modules partagent cette grammaire ; trois copies de la meme
       seconde et demie auraient diverge au premier reglage.

       POURQUOI LE BLEU NE BAT PAS. Si tout bat, plus rien ne signale. Le
       battement est le langage de l'ACQUIS — il recompense, il n'aiguillonne
       pas. Ce qui reste a faire se lit a la fleche qui y mene, pas a un
       clignotement de plus. */
    ".pc-etape.pc-e-reste{border:2px solid var(--blue)}",
    ".pc-etape.pc-e-fait{border:2px solid var(--green);",
    "animation:cpValide var(--cp-battement) ease-in-out infinite}",
    "@media(prefers-reduced-motion:reduce){.pc-etape.pc-e-fait{animation:none;border-color:var(--green)}}",
    ".pc-e-etat{flex-shrink:0;font-family:var(--mono);font-size:10px;letter-spacing:.05em;",
    "padding:2px 8px;border-radius:10px;white-space:nowrap}",
    ".pc-e-etat.fait{color:#0d2b1e;background:var(--green);font-weight:700}",
    ".pc-e-etat.reste{color:var(--blue);border:1px solid var(--blue)}",
    ".pc-compte{font-size:12.5px;color:var(--muted2);margin:2px 0 10px}",
    ".pc-compte-fait{color:var(--green);font-weight:700}",
    ".pc-compte-reste{color:var(--blue);font-weight:700}",
    /* « VOUS Y ETES » EST UNE POSITION, PAS UN ETAT. Elle se dit par le fond
       et par le texte, jamais par une troisieme couleur : deux couleurs
       suffisent a dire l'avancement, une troisieme le brouillerait. */
    ".pc-etape.pc-ici{background:rgba(156,196,245,.10);border-width:2px}",
    ".pc-etape.pc-ici.pc-e-reste{border-color:var(--blue);box-shadow:0 0 0 1px rgba(156,196,245,.35)}",
    /* La visite prime la position : une etape courante ET visitee garde le
       fond du « vous y etes », et son cadre vert bat comme les autres. */
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
    /* LA FLECHE NE DECORE PLUS, ELLE MENE. Trois etats : verte entre deux
       etapes faites (le chemin parcouru), BLEUE ET DESCENDANTE devant la
       prochaine a faire (le chemin a prendre), sourde ailleurs. Elle porte un
       LIBELLE : « a faire ensuite » se lit sans distinguer les couleurs. */
    ".pc-fleche{text-align:center;color:var(--muted2);font-size:15px;line-height:1;margin:7px 0}",
    ".pc-fleche.pc-fl-fait{color:var(--green)}",
    ".pc-fleche.pc-fl-suite{color:var(--blue);font-family:var(--mono);font-size:10.5px;",
    "letter-spacing:.07em;text-transform:uppercase;font-weight:700;margin:9px 0;",
    "animation:cpVersSuite var(--cp-battement) ease-in-out infinite}",
    "@media(prefers-reduced-motion:reduce){.pc-fleche.pc-fl-suite{animation:none}}",
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
    ".pc-dot.fait{background:var(--green);animation:cpPastille var(--cp-battement) ease-in-out infinite}",
    ".pc-dot.reste{background:none;border:1px solid var(--blue)}",
    ".pc-dot.ici{background:var(--blue);box-shadow:0 0 0 2px rgba(156,196,245,.32)}",
    /* La pastille n'a pas de bordure a faire battre : c'est sa LUEUR qui bat,
       et sa couleur pleine ne change jamais — le contraste tient a chaque
       phase. Cadence lue dans la meme variable que tout le reste. */
    "@keyframes cpPastille{0%,100%{box-shadow:0 0 0 0 rgba(52,211,153,0)}",
    "50%{box-shadow:0 0 0 3px rgba(52,211,153,.40)}}",
    "@media(prefers-reduced-motion:reduce){.pc-dot.fait{animation:none}}",
    ".pc-b-step.att{color:var(--blue)}",
    ".pc-b-mur a{color:var(--teal);font-weight:600}",
    ".pc-mur{font-family:var(--mono);font-size:10px;letter-spacing:.05em;color:var(--amber);",
    "border:1px solid var(--amber);border-radius:10px;padding:2px 9px;white-space:nowrap}",
    ".pc-b-mur{flex-basis:100%;font-size:11.5px;line-height:1.55;color:var(--muted);",
    "margin-top:8px;padding:8px 11px;border-left:3px solid var(--amber);",
    "background:rgba(240,180,41,.07);border-radius:0 6px 6px 0}",
    ".pc-b-mur b{color:var(--ink)}",
    ".pc-b-reste{font-family:var(--mono);font-size:10px;color:var(--blue);white-space:nowrap}",
    /* CE QUI BAT EST CE QUI EST ACQUIS. « 3 a faire » se tient tranquille en
       bleu ; « toutes visitees ✓ » bat en vert — c'est l'arrivee qu'on
       celebre, pas le reste du chemin. Le texte ne bat que par sa LUEUR,
       jamais par sa couleur : le vert tient le seuil AA a chaque phase. */
    ".pc-b-reste.fini{color:var(--green);animation:cpTexteValide var(--cp-battement) ease-in-out infinite}",
    "@media(prefers-reduced-motion:reduce){.pc-b-reste.fini{animation:none}}",
    ".pc-b-d{display:flex;align-items:center;gap:8px;flex-wrap:wrap}",
    ".pc-b-btn{font:inherit;font-size:12px;font-weight:600;padding:7px 12px;border-radius:8px;cursor:pointer;",
    "border:1px solid var(--line);background:var(--panel2);color:var(--ink);text-decoration:none;",
    "max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    ".pc-b-btn:hover{border-color:var(--teal);color:var(--teal)}",
    ".pc-b-suiv{border-color:var(--blue);background:rgba(156,196,245,.14);color:var(--blue)}",
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
      + '</div>'
      + '<details class="pc-conseil"><summary>🧭 Je ne sais pas quel rôle choisir — trois questions</summary>'
      + '<div class="pc-cq">' + questionsHTML() + '</div>'
      + '<div class="pc-verdict" id="pc-verdict"></div></details>'
      + '<div id="pc-fiche"></div></div>';
    m.querySelector(".pc-x").addEventListener("click", fermer);
    var sel = m.querySelector("#pc-select");
    var selSec = m.querySelector("#pc-select-sec");
    function maj() { fiche(sel.value, selSec.value); }
    sel.addEventListener("change", maj);
    selSec.addEventListener("change", maj);
    brancherConseil(m, sel, maj);
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
       pendant ce parcours. Le reste tient en BLEU, immobile — c'est la flèche
       qui désigne la prochaine, pas un clignotement de plus. Le badge dit ce
       que le vert MESURE : la visite, pas le travail accompli. */
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

  /* LE LIBELLE FAIT PARTIE DE LA FLECHE, il n'est pas un ornement. Un lecteur
     qui ne distingue pas le bleu du vert lit « À FAIRE ENSUITE » et sait où
     aller ; la couleur et le mouvement ne font qu'accélérer la même lecture.
     Les flèches muettes restent `aria-hidden` : elles n'apprennent rien à qui
     écoute la page, et trois « flèche vers le bas » de suite la encombrent. */
  function fleche(etat, texte) {
    return '<div class="pc-fleche pc-fl-' + etat + '"'
      + (texte ? "" : ' aria-hidden="true"') + ">"
      + (texte ? "↓ " + esc(texte) + " ↓" : "↓") + "</div>";
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

  /* ═══════════════════════════════════════════════════════════════════════
     LE RENDU DU CONSEILLER
     Le moteur au-dessus est pur ; ici on ne fait que l'afficher. La règle
     tenue partout : ce qui est RETENU et ce qui est ÉCARTÉ arrivent par le
     même chemin, et l'écarté porte son motif. Un conseil qui ne montrerait
     que son gagnant serait un oracle ; celui-ci se conteste.
     ═══════════════════════════════════════════════════════════════════════ */
  function questionsHTML() {
    return QUESTIONS.map(function (q) {
      var opts = q.choix.map(function (c, i) {
        var id = "pc-q-" + q.cle + "-" + i;
        return '<label class="pc-cq-opt" for="' + id + '">'
          + '<input type="radio" id="' + id + '" name="pc-q-' + esc(q.cle) + '" value="'
          + esc(c.v) + '"' + (c.neutre ? " checked" : "") + ">"
          + "<span>" + esc(c.l) + "</span></label>";
      }).join("");
      return '<fieldset><legend>' + esc(q.titre) + "</legend>"
        + '<div class="pc-cq-opts">' + opts + "</div></fieldset>";
    }).join("");
  }

  function carteVerdict(x, second) {
    return '<div class="pc-v-card' + (second ? " pc-v-second" : "") + '">'
      + '<div class="pc-v-role">' + esc(x.icone || "") + "<span>" + esc(x.role || x.id) + "</span>"
      + '<span class="pc-v-pts">' + x.score + " / 6</span></div>"
      + (x.entree ? '<div class="pc-v-entree">' + esc(x.entree) + "</div>" : "")
      + (second && x.apport ? '<div class="pc-v-apport">' + esc(x.apport) + "</div>" : "")
      + '<button class="pc-v-go" type="button" data-pc-aller="' + esc(x.id) + '">'
      + (second ? "Voir celui-ci plutôt" : "Suivre ce parcours") + "</button></div>";
  }

  function verdictHTML(r) {
    var h = '<div class="pc-v-motif">' + esc(r.motif) + "</div>";
    h += r.retenus.map(function (x) { return carteVerdict(x, false); }).join("");
    if (r.second) h += carteVerdict(r.second, true);
    if (r.ecartes && r.ecartes.length) {
      h += '<details class="pc-v-ec"><summary>Ce qui a été écarté, et sur quel motif ('
        + r.ecartes.length + ")</summary><ul>"
        + r.ecartes.map(function (e) {
            return "<li><b>" + esc(e.role || e.id) + "</b> — " + esc(e.motif) + "</li>";
          }).join("")
        + "</ul></details>";
    }
    return h;
  }

  /* Brancher la porte sur la modale. Le verdict se recalcule à CHAQUE réponse :
     le visiteur voit le classement bouger pendant qu'il répond, ce qui lui
     apprend quelle question compte — et c'est gratuit, le moteur étant pur. */
  function brancherConseil(m, sel, maj) {
    var d = m.querySelector(".pc-conseil");
    if (!d) return;
    var zone = d.querySelector("#pc-verdict");
    function calculer() {
      var rep = {};
      QUESTIONS.forEach(function (q) {
        var c = d.querySelector('input[name="pc-q-' + q.cle + '"]:checked');
        if (c && c.value) rep[q.cle] = c.value;
      });
      var r = conseiller(rep);
      zone.innerHTML = verdictHTML(r);
      zone.querySelectorAll("[data-pc-aller]").forEach(function (b) {
        b.addEventListener("click", function () {
          /* LE VERDICT REMPLIT LE MENU, IL NE SE SUBSTITUE PAS À LUI. Le
             visiteur garde la main : il voit son rôle sélectionné, et peut en
             changer aussitôt. Un conseil qui déciderait à sa place serait plus
             court à écrire et plus difficile à démentir. */
          sel.value = b.getAttribute("data-pc-aller");
          maj();
          var f = document.getElementById("pc-fiche");
          if (f && f.scrollIntoView) f.scrollIntoView({ block: "nearest" });
        });
      });
    }
    d.addEventListener("change", calculer);
    calculer();
  }

  function fiche(id, idSec) {
    var h = document.getElementById("pc-fiche");
    if (!h) return;
    var p = id ? trouver(id) : null;
    var sec = idSec ? trouverSecteur(idSec) : null;
    /* LA TAILLE SUIT CE QU'IL Y A À LIRE, et rien d'autre. Tant qu'aucun
       parcours n'est choisi, la carte reste celle du choix ; dès qu'une
       fiche s'affiche, elle passe en lecture. Piloter la classe depuis les
       écouteurs des deux menus aurait donné deux endroits à tenir d'accord,
       et c'est ici qu'on sait s'il y a une fiche. */
    var carte = h.closest ? h.closest(".pc-card") : null;
    if (carte) { carte.classList.toggle("pc-lecture", !!(p || sec)); }
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
    /* LES FLECHES SAVENT CE QU'ELLES RELIENT. Toutes identiques, elles ne
       disaient rien — un ↓ entre deux etapes est une ponctuation, pas un
       guide. Chacune lit desormais l'etat de ses DEUX extremites :

         · entre deux etapes faites  → verte : le chemin parcouru
         · devant la prochaine a faire → BLEUE, descendante, et LIBELLEE
         · ailleurs                   → sourde

       UNE SEULE est mise en avant, et c'est tout l'effet : un guide qui
       souligne tout ne guide rien. Si la premiere etape est aussi la
       prochaine a faire, la fleche se place AVANT elle — « commencez ici ». */
    var faitesTab = source.etapes.map(function (e) { return vus.indexOf(e.url) >= 0; });
    var prochaine = faitesTab.indexOf(false);
    var blocs = source.etapes.map(function (e, i) {
      return etapeHtml(idParcours, e, i, ici, sec, perso, vus);
    });
    var etapes = compteur;
    if (prochaine === 0) etapes += fleche("suite", "Commencez ici");
    for (var bi = 0; bi < blocs.length; bi++) {
      etapes += blocs[bi];
      if (bi === blocs.length - 1) break;
      etapes += (faitesTab[bi] && faitesTab[bi + 1]) ? fleche("fait", "")
        : (bi + 1 === prochaine) ? fleche("suite", "À faire ensuite")
        : fleche("calme", "");
    }

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
       bleu, comme dans la fiche. */
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
      + '<span class="pc-b-reste' + (n - nVus > 0 ? "" : " fini") + '">'
      + (n - nVus > 0 ? (n - nVus) + " à faire" : "toutes visitées ✓") + "</span></div>"
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
        + '">Suivant : ' + (reserve(suiv.url) ? "🔒 " : "") + esc(suiv.label)
        + ' <span class="cp-av" aria-hidden="true">→</span></a>';
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
