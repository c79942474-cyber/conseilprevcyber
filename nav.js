/* CONSEILPREV Cyber — script partagé de toutes les pages.
   1. En-tête responsive (menu « burger » sur écran étroit).
   2. Flèches de navigation (précédent / suivant / haut / bas).
   3. Guide utilisateur contextuel : bouton « ? » flottant + panneau d'aide
      propre à chaque page (objectif, mode d'emploi, notions clés, liens).
   4. Infobulles de jargon : les termes techniques des puces (.taglist, .tags)
      reçoivent automatiquement une définition au survol / focus.
   Aucune balise à ajouter aux pages : tout est construit ici. */
(function () {
  document.documentElement.classList.add("js-nav");

  /* ── 1. Menu burger ─────────────────────────────────────────────────────── */
  function initBurger() {
    var nav = document.querySelector("header .nav");
    if (!nav) return;
    var links = nav.querySelector(".links");
    if (!links || nav.querySelector(".nav-toggle")) return;
    if (!links.id) links.id = "nav-links";

    var btn = document.createElement("button");
    btn.className = "nav-toggle";
    btn.type = "button";
    btn.setAttribute("aria-label", "Ouvrir le menu");
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-controls", links.id);
    btn.innerHTML =
      '<span class="nav-toggle-bar"></span>' +
      '<span class="nav-toggle-bar"></span>' +
      '<span class="nav-toggle-bar"></span>';
    nav.appendChild(btn);

    function setOpen(open) {
      nav.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.setAttribute("aria-label", open ? "Fermer le menu" : "Ouvrir le menu");
    }
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      setOpen(!nav.classList.contains("open"));
    });
    links.addEventListener("click", function (e) {
      if (e.target.closest("a")) setOpen(false);
    });
    document.addEventListener("click", function (e) {
      if (nav.classList.contains("open") && !nav.contains(e.target)) setOpen(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" || e.key === "Esc") setOpen(false);
    });
    var mq = window.matchMedia("(min-width: 861px)");
    var onChange = function () { if (mq.matches) setOpen(false); };
    if (mq.addEventListener) mq.addEventListener("change", onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }

  /* ── 2. Flèches de navigation ───────────────────────────────────────────── */
  function initPageNav() {
    if (document.querySelector(".pagenav")) return;
    var box = document.createElement("div");
    box.className = "pagenav";
    box.setAttribute("role", "group");
    box.setAttribute("aria-label", "Navigation de page");
    var defs = [
      ["back", "←", "Page précédente", "Précédent"],
      ["forward", "→", "Page suivante", "Suivant"],
      ["top", "↑", "Haut de la page", "Haut"],
      ["bottom", "↓", "Bas de la page", "Bas"],
    ];
    defs.forEach(function (d) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "pagenav-btn";
      b.setAttribute("data-nav", d[0]);
      b.setAttribute("aria-label", d[2]);
      b.title = d[3];
      b.textContent = d[1];
      box.appendChild(b);
    });
    document.body.appendChild(box);

    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var behavior = reduce ? "auto" : "smooth";
    box.addEventListener("click", function (e) {
      var b = e.target.closest(".pagenav-btn");
      if (!b) return;
      switch (b.getAttribute("data-nav")) {
        case "back": history.back(); break;
        case "forward": history.forward(); break;
        case "top": window.scrollTo({ top: 0, behavior: behavior }); break;
        case "bottom":
          window.scrollTo({ top: document.documentElement.scrollHeight, behavior: behavior });
          break;
      }
    });
  }

  /* ── 3. Guide utilisateur par page ──────────────────────────────────────── */
  var REF_LINKS = [["Référentiel 62443", "/referentiel"], ["Lancer l'audit 62443", "/audit-conformite"]];
  var GUIDES = {
    "/": { t: "Accueil", p: "Vue d'ensemble de CONSEILPREV Cyber : nos domaines d'intervention en cybersécurité industrielle et les points d'entrée du site.",
      s: ["Parcourez les quatre domaines d'intervention.", "Ouvrez la démo temps réel pour voir le cockpit en action.", "Demandez un état des lieux via le formulaire de contact."],
      k: [["IT / OT / IIoT", "Informatique de gestion / systèmes industriels (automates, SCADA) / objets connectés industriels."], ["IEC 62443", "La série de normes de référence pour la cybersécurité des systèmes d'automatisation industriels."]],
      l: [["Nos services", "/services"], ["Démo temps réel", "/demo"], ["Nous contacter", "/contact"]] },
    "/services": { t: "Services", p: "Le détail de nos offres — de l'état des lieux à la supervision — et de nos compétences techniques.",
      s: ["Survolez les puces techniques : chaque terme est expliqué.", "Consultez les objectifs de mission et les livrables.", "Passez à l'action : état des lieux ou démo."],
      k: [["NAC", "Contrôle d'accès réseau : n'admettre que les équipements autorisés."], ["EDR", "Détection et réponse sur les postes et serveurs."], ["MCO / MCS", "Maintien en condition opérationnelle / de sécurité dans la durée."]],
      l: [["Études de cas", "/etudes-de-cas"], ["Méthodologie", "/methodologie"], ["Contact", "/contact"]] },
    "/etudes-de-cas": { t: "Études de cas", p: "Nos références : missions menées pour de grands comptes de l'énergie, de la mobilité et de l'oil & gas.",
      s: ["Chaque carte résume le contexte, le rôle tenu et les résultats.", "Survolez les étiquettes techniques pour leur définition.", "Un enjeu similaire ? Contactez-nous."],
      k: [["EBIOS RM", "La méthode française d'analyse de risque (ANSSI)."], ["SIEM", "Plateforme qui centralise et corrèle les journaux de sécurité."], ["CSMS", "Système de management de la cybersécurité (volet organisationnel)."]],
      l: [["Nos services", "/services"], ["Contact", "/contact"]] },
    "/referentiel": { t: "Référentiel IEC 62443", p: "La carte de la série IEC 62443 : chaque carte ouvre notre lecture d'une partie de la norme.",
      s: ["Survolez le « i » d'une carte pour situer la partie.", "Ouvrez une partie pour le détail.", "Lancez l'étude de conformité pour l'appliquer à votre installation."],
      k: [["FR", "Les 7 familles d'exigences fondamentales de la série."], ["SL", "Niveaux de sécurité gradués (1 à 4) selon la menace visée."], ["Zones & conduits", "Découpage de l'installation en îlots reliés par des liaisons maîtrisées."]],
      l: [["Lancer l'audit 62443", "/audit-conformite"], ["Démo temps réel", "/demo"]] },
    "/methodologie": { t: "Concepts & méthodologie (1-1)", p: "Les fondations de la série : terminologie, exigences fondamentales, niveaux de sécurité et notre démarche en six phases.",
      s: ["Lisez les concepts dans l'ordre : FR, SL, défense en profondeur.", "Reliez chaque concept à votre contexte via l'audit."],
      k: [["Défense en profondeur", "Multiplier des barrières indépendantes plutôt qu'une seule protection."], ["SL-T", "Niveau de sécurité cible fixé par l'analyse de risque."]], l: REF_LINKS },
    "/analyse-de-risque": { t: "Analyse de risque (3-2)", p: "Découper le système en zones et conduits, fixer les niveaux de sécurité cibles et produire la spécification des exigences.",
      s: ["Comprenez le découpage zones & conduits.", "Suivez la démarche SL-T par zone.", "Appliquez-la via l'étude de conformité."],
      k: [["ZCR", "Le découpage zones / conduits documenté du système."], ["CRS", "La spécification des exigences de cybersécurité qui en découle."]], l: REF_LINKS },
    "/programme-securite": { t: "Programme de sécurité (2-1)", p: "Le volet organisationnel : établir et maintenir un système de management de la cybersécurité industrielle.",
      s: ["Parcourez les catégories et éléments du CSMS.", "Identifiez vos écarts organisationnels."],
      k: [["CSMS", "Le programme qui organise la cybersécurité : rôles, processus, amélioration continue."]], l: REF_LINKS },
    "/exigences-systeme": { t: "Exigences système (3-3)", p: "Les 7 exigences fondamentales déclinées en exigences système, associées aux niveaux SL 1-4.",
      s: ["Repérez les FR qui concernent vos zones.", "Comparez au niveau SL visé."],
      k: [["SR", "Exigence de sécurité au niveau du système."], ["SL-A", "Niveau de sécurité effectivement atteint."]], l: REF_LINKS },
    "/exigences-composants": { t: "Exigences composants (4-2)", p: "Les exigences au niveau du composant — applications, embarqués, hôtes, réseau.",
      s: ["Identifiez le type de chaque composant.", "Exigez ces capacités auprès des fournisseurs."],
      k: [["CR", "Exigence de sécurité au niveau du composant."]], l: REF_LINKS },
    "/gestion-correctifs": { t: "Gestion des correctifs (2-3)", p: "Le patch management en environnement industriel : rôles, états des correctifs, mesures compensatoires.",
      s: ["Suivez le cycle de qualification des correctifs.", "Prévoyez des mesures compensatoires quand on ne peut pas patcher."],
      k: [["Mesure compensatoire", "Protection alternative quand le correctif est impossible (cloisonnement, surveillance renforcée…)."]], l: REF_LINKS },
    "/exigences-prestataires": { t: "Exigences prestataires (2-4)", p: "La sécurité attendue des intégrateurs et mainteneurs : capacités et maturité.",
      s: ["Évaluez vos prestataires sur ces capacités.", "Intégrez-les à vos contrats."],
      k: [["Profil", "Ensemble d'exigences applicable selon le rôle du prestataire."]], l: REF_LINKS },
    "/developpement-securise": { t: "Développement sécurisé (4-1)", p: "Le cycle de développement sécurisé des produits : pratiques, threat modelling, maturité.",
      s: ["Parcourez les 8 pratiques.", "Demandez les preuves à vos fournisseurs."],
      k: [["SDL", "Cycle de développement qui intègre la sécurité de la conception aux tests."]], l: REF_LINKS },
    "/technologies-securite": { t: "Technologies de sécurité (TR 3-1)", p: "Le panorama des familles de technologies applicables en environnement OT.",
      s: ["Situez chaque famille par rapport à vos besoins.", "Croisez avec les exigences système."],
      k: [["IDS OT", "Sonde de détection qui comprend les protocoles industriels."]], l: REF_LINKS },
    "/glossaire-62443": { t: "Glossaire (1-2)", p: "Le vocabulaire de la série, reformulé pour être compris de tous.",
      s: ["Utilisez la recherche du navigateur (Ctrl+F) pour trouver un terme."], k: [], l: REF_LINKS },
    "/metriques-62443": { t: "Métriques (1-3)", p: "Construire des indicateurs mesurables : écart au niveau cible, tendance, tableau de bord.",
      s: ["Choisissez peu d'indicateurs, mais suivis dans la durée.", "Reliez-les aux tendances du cockpit."],
      k: [["Écart SL", "Différence entre niveau cible (SL-T) et niveau atteint (SL-A)."]], l: [["Tendances", "/tendances"], ["Audit 62443", "/audit-conformite"]] },
    "/demo": { t: "Cockpit de supervision", p: "La supervision temps réel : découverte d'actifs, zones IEC 62443, alertes et score de risque.",
      s: ["Mode Démo : données simulées pour explorer librement.", "Mode Temps réel : branchez votre plateforme via « Connecter ».", "Exportez le rapport PDF ou ouvrez l'audit 62443."],
      k: [["Score de risque", "Indice global 0-100 : plus il monte, plus l'exposition est forte."], ["Zone", "Îlot de l'installation au sens IEC 62443 ; chaque actif y est rattaché."], ["SSE", "Flux serveur → navigateur qui pousse les événements en direct."]],
      l: [["Connecter une plateforme", "/connecter"], ["Tendances", "/tendances"], ["Audit 62443", "/audit-conformite"]] },
    "/audit-conformite": { t: "Étude & audit 62443", p: "L'étude guidée en 6 étapes : inventaire audité, schéma par couches, risques, panorama de conformité, remédiations et cycle de vie.",
      s: ["Explorez d'abord le site démo (mode Démo).", "Basculez en Temps réel pour analyser vos données du cockpit (connexion requise).", "Exportez l'étude en PDF pour la partager."],
      k: [["Criticité", "Impact métier/sûreté si l'actif est compromis (1 à 5)."], ["Exposition", "Surface d'attaque de l'actif (1 à 5)."], ["SL-T / SL-A", "Niveau de sécurité cible / atteint — l'écart guide les priorités."]],
      l: [["Cockpit", "/demo"], ["Connecter une plateforme", "/connecter"], ["Référentiel", "/referentiel"]] },
    "/assistant": { t: "Assistant IA", p: "Un chat sécurisé (Claude & Mistral) dédié à la cybersécurité industrielle et à la conformité, transparent (AI Act) et respectueux du RGPD.",
      s: ["Posez votre question ou cliquez une suggestion.", "Choisissez le modèle : Claude ou Mistral.", "N'indiquez pas de données personnelles ou confidentielles — les échanges ne sont pas conservés."],
      k: [["Transparence (AI Act)", "Vous êtes clairement informé que vous parlez à une IA ; ses réponses ne remplacent pas un audit."], ["Sans conservation (RGPD)", "Aucune conversation stockée, aucune donnée utilisée pour l'entraînement des modèles."]],
      l: [["Audit 62443", "/audit-conformite"], ["Contact humain", "/contact"]] },
    "/tendances": { t: "Tendances", p: "L'historique agrégé du cockpit : volumes par jour, par zone et par catégorie d'événement.",
      s: ["Choisissez la période d'analyse.", "Repérez les zones les plus actives.", "Croisez avec l'audit pour prioriser."],
      k: [["Catégorie", "Classement automatique des événements : découverte, critique, avertissement, correctif, info."]],
      l: [["Cockpit", "/demo"], ["Audit 62443", "/audit-conformite"]] },
    "/connecter": { t: "Connecter votre plateforme", p: "Brancher votre plateforme OT (Nozomi, Claroty, Tenable, Defender…) au cockpit en 4 étapes.",
      s: ["Téléchargez le connecteur (zip).", "Configurez l'URL du site et le jeton d'ingestion.", "Lancez le connecteur avec le préréglage de votre éditeur.", "Vérifiez l'arrivée des événements dans le cockpit."],
      k: [["INGEST_TOKEN", "Le secret qui autorise l'envoi de données — à garder hors de tout dépôt de code."], ["Préréglage", "Mapping prêt à l'emploi pour votre éditeur OT."]],
      l: [["Guide d'intégration détaillé", "/guide-integration"], ["Cockpit", "/demo"]] },
    "/guide-integration": { t: "Guide d'intégration", p: "Le pas-à-pas professionnel complet du branchement : prérequis, sécurité, déploiement, supervision.",
      s: ["Naviguez par le sommaire à gauche.", "Copiez les commandes : votre domaine y est déjà injecté.", "Imprimez en PDF pour vos équipes."], k: [],
      l: [["Connecter votre plateforme", "/connecter"], ["Cockpit", "/demo"]] },
    "/ressources": { t: "Ressources", p: "Les sources officielles utiles : ANSSI, CERT-FR, ENISA, CISA, IEC, NIST…",
      s: ["Chaque lien ouvre la source officielle dans un nouvel onglet."], k: [],
      l: [["Référentiel 62443", "/referentiel"], ["FAQ", "/faq"]] },
    "/faq": { t: "FAQ", p: "Les réponses aux questions les plus fréquentes sur nos interventions et la norme.",
      s: ["Parcourez par thème.", "Pas de réponse ? Écrivez-nous."], k: [], l: [["Contact", "/contact"]] },
    "/about": { t: "À propos", p: "Qui nous sommes : parcours, expertises et convictions.",
      s: [], k: [], l: [["Études de cas", "/etudes-de-cas"], ["Contact", "/contact"]] },
    "/secteurs": { t: "Secteurs", p: "Les secteurs industriels où nous intervenons et leurs enjeux propres.",
      s: [], k: [], l: [["Études de cas", "/etudes-de-cas"], ["Services", "/services"]] },
    "/contact": { t: "Contact", p: "Le formulaire sécurisé pour demander une démonstration, un état des lieux ou tout renseignement.",
      s: ["Choisissez le sujet le plus proche (démo, conformité, audit…).", "Décrivez votre contexte : nous répondons sous 48 h ouvrées."],
      k: [["Formulaire sécurisé", "Transmission chiffrée, anti-spam et limitation de débit — vos données ne servent qu'à vous répondre."]],
      l: [["Démo temps réel", "/demo"], ["Services", "/services"]] },
    "/mentions-legales": { t: "Mentions légales", p: "Les informations légales de l'éditeur du site et de l'hébergement.", s: [], k: [], l: [["Accueil", "/"], ["Politique de confidentialité", "/politique-confidentialite"]] },
    "/politique-confidentialite": { t: "Politique de confidentialité", p: "Comment vos données sont traitées : finalités, bases légales, durées, droits RGPD et transparence de l'assistant IA.",
      s: ["Le tableau reprend notre registre des traitements (art. 30).", "Vos droits s'exercent par email — réponse sous un mois."],
      k: [["Portabilité", "Recevoir vos données dans un format lisible par machine (art. 20)."], ["Cookie de session", "Le seul cookie du site : strictement nécessaire à l'espace client."]],
      l: [["Mentions légales", "/mentions-legales"], ["Contact", "/contact"]] },
    "/nis2": { t: "NIS2", p: "La directive européenne expliquée : qui est concerné, les obligations, la notification d'incidents et la correspondance avec l'IEC 62443.",
      s: ["Vérifiez votre régime : entité essentielle ou importante.", "Parcourez les obligations et les échéances 24 h / 72 h.", "Suivez la table NIS2 ↔ IEC 62443 pour le volet industriel."],
      k: [["EE / EI", "Entités essentielles (contrôles renforcés) / importantes (contrôles a posteriori)."], ["24 h / 72 h", "Alerte précoce puis notification d'incident aux autorités."], ["MonEspaceNIS2", "Le portail ANSSI pour vérifier son assujettissement et s'enregistrer."]],
      l: [["Audit 62443", "/audit-conformite"], ["Référentiel", "/referentiel"], ["Contact", "/contact"]] },
    "/vos-projets": { t: "Vos projets", p: "Décrivez votre besoin (état des lieux, segmentation, supervision, conformité NIS2/DORA) : nous répondons sous 48 h ouvrées.",
      s: ["Choisissez le type de projet le plus proche.", "Décrivez le contexte en quelques lignes."], k: [],
      l: [["Nos services", "/services"], ["Contact", "/contact"]] },
    "/veille": { t: "Veille cyber", p: "Les alertes et avis CERT-FR, collectés et résumés automatiquement — la même veille qui alimente l'assistant IA.",
      s: ["Les éléments les plus récents sont en haut.", "Cliquez un titre pour ouvrir le bulletin officiel CERT-FR.", "Résumés générés par IA : référez-vous toujours à la source."],
      k: [["Alerte", "Menace active ou vulnérabilité critique exploitée — à traiter en priorité."], ["Avis", "Vulnérabilités publiées avec correctifs — à intégrer au patch management."]],
      l: [["Gestion des correctifs", "/gestion-correctifs"], ["Assistant IA", "/assistant"], ["Ressources officielles", "/ressources"]] },
    "/diagnostic": { t: "Diagnostic express", p: "4 questions pour situer votre organisation : cadre réglementaire applicable, lectures utiles et démarche recommandée — puis un contact déjà contextualisé.",
      s: ["Répondez aux 4 questions (secteur, taille, situation, priorité) — les « i » expliquent l'enjeu de chacune.", "Lisez votre parcours recommandé (et « Comment lire ce résultat »).", "Imprimez votre parcours (🖨) pour le partager en interne.", "Le bouton contact pré-remplit le sujet et votre contexte — modifiables avant envoi."],
      k: [["Aucune donnée enregistrée", "Vos réponses restent dans votre navigateur tant que vous n'envoyez pas le formulaire de contact."]],
      l: [["NIS2", "/nis2"], ["Audit 62443", "/audit-conformite"], ["Contact", "/contact"]] },
    "/connexion": { t: "Connexion", p: "Accès à l'espace client : cockpit, tendances, connexion de plateforme et étude 62443.",
      s: ["Saisissez l'email et le mot de passe de votre compte.", "Pas de compte ? Créez une demande d'accès.", "Mot de passe oublié ? Utilisez le lien dédié."],
      k: [["Validation admin", "Après confirmation de votre email, un administrateur approuve l'accès — vous êtes prévenu par email."]],
      l: [["Créer un compte", "/inscription"], ["Mot de passe oublié", "/mot-de-passe-oublie"]] },
    "/inscription": { t: "Créer un compte", p: "La demande d'accès à l'espace client en trois temps : inscription, confirmation d'email, validation par notre équipe.",
      s: ["Remplissez le formulaire (mot de passe : 10 caractères min., lettres + chiffres).", "Cliquez le lien reçu par email pour confirmer.", "Attendez l'email « accès activé » puis connectez-vous."],
      k: [["Vérification anti-robot", "Le petit calcul bloque les inscriptions automatisées."]],
      l: [["Se connecter", "/connexion"]] },
    "/mot-de-passe-oublie": { t: "Mot de passe oublié", p: "Recevez un lien sécurisé pour choisir un nouveau mot de passe.",
      s: ["Saisissez l'email du compte.", "Ouvrez le lien reçu (valable 2 h).", "Choisissez le nouveau mot de passe."],
      k: [["Réponse générique", "Le message est identique qu'un compte existe ou non : personne ne peut deviner qui est inscrit."]],
      l: [["Retour à la connexion", "/connexion"]] },
    "/admin/comptes": { t: "Administration des comptes", p: "Approuver les demandes d'accès, suspendre, promouvoir ou supprimer des comptes.",
      s: ["« Approuver » active un compte dont l'email est confirmé.", "« Suspendre » coupe l'accès immédiatement (session invalidée).", "« Promouvoir admin » donne accès à cette page et au jeton d'ingestion."],
      k: [["En attente", "Email confirmé, mais accès pas encore approuvé."], ["Suspendu", "Compte désactivé : la connexion est refusée."]],
      l: [["Cockpit", "/demo"], ["Connecter une plateforme", "/connecter"]] }
  };
  var GUIDE_DEFAULT = { t: "Aide", p: "Cette page fait partie du site CONSEILPREV Cyber — cybersécurité industrielle IT / OT / IIoT.",
    s: ["Utilisez le menu pour naviguer.", "Les icônes « i » expliquent les notions techniques au survol."], k: [],
    l: [["Accueil", "/"], ["Contact", "/contact"]] };

  function initGuide() {
    if (document.querySelector(".guide-btn")) return;
    var path = location.pathname.replace(/\/+$/, "") || "/";
    if (/^\/reinitialiser\//.test(path)) path = "/mot-de-passe-oublie";
    var g = GUIDES[path] || GUIDE_DEFAULT;

    // Bouton « Guide de la page » placé en début de page (juste sous l'en-tête),
    // légèrement clignotant pour être repéré.
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "guide-btn";
    btn.innerHTML = '<span class="gi" aria-hidden="true">?</span><span class="gt">Guide de la page</span>';
    btn.title = "Ouvrir le guide de cette page";
    btn.setAttribute("aria-label", "Ouvrir le guide de cette page");
    btn.setAttribute("aria-haspopup", "dialog");
    var bar = document.createElement("div");
    bar.className = "guide-bar";
    var inner = document.createElement("div");
    inner.className = "wrap guide-bar-in";
    inner.appendChild(btn);
    bar.appendChild(inner);
    var hdr = document.querySelector("header");
    if (hdr && hdr.parentNode) hdr.parentNode.insertBefore(bar, hdr.nextSibling);
    else document.body.insertBefore(bar, document.body.firstChild);

    var ov = document.createElement("div");
    ov.className = "guide-overlay";
    var esc = function (s) { return ("" + (s == null ? "" : s)).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
    var html = '<div class="guide-panel" role="dialog" aria-modal="true" aria-label="Guide de la page">'
      + '<button type="button" class="guide-close" aria-label="Fermer le guide">✕</button>'
      + '<div class="guide-kicker">Guide de la page</div><h2>' + esc(g.t) + "</h2>"
      + "<p>" + esc(g.p) + "</p>";
    if (g.s && g.s.length) {
      html += "<h3>Comment l'utiliser</h3><ol>";
      g.s.forEach(function (x) { html += "<li>" + esc(x) + "</li>"; });
      html += "</ol>";
    }
    if (g.k && g.k.length) {
      html += "<h3>Notions clés</h3><ul class=\"guide-terms\">";
      g.k.forEach(function (x) { html += "<li><b>" + esc(x[0]) + "</b> — " + esc(x[1]) + "</li>"; });
      html += "</ul>";
    }
    if (g.l && g.l.length) {
      html += "<h3>Aller plus loin</h3><div class=\"guide-links\">";
      g.l.forEach(function (x) { html += '<a href="' + esc(x[1]) + '">' + esc(x[0]) + "</a>"; });
      html += "</div>";
    }
    html += '<p class="guide-foot">Besoin d\'aide humaine ? <a href="/contact">Contactez-nous</a> — réponse sous 48 h ouvrées.</p></div>';
    ov.innerHTML = html;
    document.body.appendChild(ov);

    var closeBtn = ov.querySelector(".guide-close");
    function setOpen(open) {
      ov.classList.toggle("open", open);
      if (open) { closeBtn.focus(); } else { btn.focus(); }
    }
    btn.addEventListener("click", function () { setOpen(true); });
    closeBtn.addEventListener("click", function () { setOpen(false); });
    ov.addEventListener("click", function (e) { if (e.target === ov) setOpen(false); });
    document.addEventListener("keydown", function (e) {
      if ((e.key === "Escape" || e.key === "Esc") && ov.classList.contains("open")) setOpen(false);
    });
  }

  /* ── 4. Infobulles de jargon sur les puces techniques ───────────────────── */
  var JARGON = {
    "discovery": "Découverte passive des équipements présents sur le réseau, sans agent ni perturbation de la production.",
    "discovery réseau": "Découverte passive des équipements présents sur le réseau, sans agent ni perturbation de la production.",
    "inventaire d'actifs": "Liste tenue à jour de tous les équipements IT/OT/IIoT : la base de toute démarche de sécurité.",
    "cartographie des flux": "Qui parle à qui : la carte des échanges réseau entre équipements et zones.",
    "cartographie it/ot": "La carte des équipements et des échanges entre informatique de gestion et systèmes industriels.",
    "flux industriels": "Les échanges réseau entre équipements de production (protocoles industriels).",
    "matrices de flux": "Tableau de référence des échanges autorisés entre zones — base du filtrage.",
    "iec 62443": "La série de normes de référence pour la cybersécurité des systèmes d'automatisation industriels.",
    "segmentation": "Cloisonner le réseau en zones étanches reliées par des conduits maîtrisés, pour limiter la propagation.",
    "nac": "Contrôle d'accès réseau : seuls les équipements identifiés et autorisés peuvent se connecter.",
    "nac · ngfw": "Contrôle d'accès réseau + pare-feu nouvelle génération (filtrage applicatif des protocoles).",
    "firewall nextgen": "Pare-feu nouvelle génération : filtre les flux jusqu'au protocole applicatif industriel.",
    "analyse de risques": "Identifier ce qui peut arriver, avec quelle vraisemblance et quel impact, pour prioriser les mesures.",
    "priorisation": "Traiter d'abord ce qui réduit le plus le risque, à effort donné.",
    "remédiation": "Les actions correctives qui referment les écarts constatés.",
    "mesures d'atténuation": "Les protections qui réduisent la vraisemblance ou l'impact d'un scénario redouté.",
    "plan de remédiation": "La feuille de route priorisée des actions correctives.",
    "ids / ips ot": "Détection (et blocage) d'intrusion adaptée aux protocoles industriels — en OT on privilégie la détection passive.",
    "edr": "Détection & réponse sur les postes et serveurs : repère les comportements malveillants au-delà de l'antivirus.",
    "mco": "Maintien en condition opérationnelle : garder le dispositif efficace dans la durée.",
    "maintien en condition": "Garder le niveau de sécurité dans la durée : correctifs, règles, surveillance, revues.",
    "hardening": "Durcissement : réduire la surface d'attaque d'un équipement (services inutiles, comptes, configuration).",
    "mise en conformité": "Aligner votre installation sur les exigences applicables (IEC 62443, NIS2…) avec preuves à l'appui.",
    "mise en sécurité — actifs & processus": "Sécuriser concrètement équipements et procédés : segmentation, durcissement, surveillance.",
    "veille réglementaire ics/ot": "Suivi continu des normes et réglementations cyber applicables aux systèmes industriels.",
    "ebios rm": "La méthode française d'analyse de risque (ANSSI), par scénarios de menace.",
    "ebios": "La méthode française d'analyse de risque (ANSSI).",
    "siem": "Plateforme qui centralise et corrèle les journaux pour détecter les incidents.",
    "csms · sums": "Systèmes de management de la cybersécurité et des mises à jour du véhicule connecté (UNECE).",
    "wp.29": "Réglementation UNECE imposant la cybersécurité du véhicule connecté (R155/R156).",
    "iso/sae 21434": "La norme de cybersécurité du cycle de vie du véhicule routier.",
    "r155/r156": "Règlements UNECE : management de la cybersécurité (R155) et des mises à jour logicielles (R156).",
    "rgpd": "Règlement européen sur la protection des données personnelles.",
    "pssi industrielle": "La politique de sécurité dédiée aux systèmes industriels.",
    "lpm · nis": "Lois et directives imposant des exigences cyber aux opérateurs critiques (France / Europe).",
    "scada · dcs": "Supervision centralisée (SCADA) et contrôle-commande distribué (DCS) des procédés.",
    "plc · hmi": "Automates programmables (PLC) et interfaces homme-machine (HMI).",
    "sûreté de fonctionnement": "Fiabilité, disponibilité, maintenabilité et sécurité des systèmes.",
    "ia risk management": "Gestion des risques appliquée aux systèmes d'information et à l'IA.",
    "vidéosurveillance": "Systèmes de surveillance des espaces — ici intégrés au réseau multi-services.",
    "réseau multi-services": "Réseau mutualisé transportant plusieurs usages (vidéo, données, téléphonie…).",
    "dat": "Dossier d'architecture technique : la référence documentaire de l'architecture.",
    "intégration": "Assemblage et mise en service des composants dans l'environnement cible.",
    "supervision": "Surveillance continue de l'état de sécurité et des événements.",
    "architecture": "La structure d'ensemble : zones, conduits, équipements et flux.",
    "oil & gas": "Secteur pétrole et gaz : exploration, production, transport, raffinage.",
    "biométhane": "Filière gaz renouvelable — ici, sécurisation du SI industriel des sites d'injection.",
    "grand paris express": "Le nouveau métro du Grand Paris (lignes 15, 16, 17…).",
    "nis2": "Directive européenne (2022/2555) imposant gestion des risques et notification d'incidents aux entités essentielles et importantes.",
    "dora": "Règlement européen de résilience opérationnelle numérique du secteur financier (banques, assurances).",
    "amoa · ia": "Assistance à maîtrise d'ouvrage d'un programme d'intégration de l'IA dans la cyberdéfense.",
    "soc augmenté ia": "Centre opérationnel de sécurité dont la détection et la réponse sont assistées par l'IA, sous supervision humaine.",
    "gestion de crise": "Dispositif d'organisation, de décision et de communication face à un incident majeur.",
    "ttd · mttr · mttp": "Délais moyens de détection (TTD), de réponse/remédiation (MTTR) et de déploiement des correctifs (MTTP).",
    "cartographie d'exposition": "Recensement des applications et services exposés sur internet, pour prioriser les remédiations.",
    "remédiation à l'échelle": "Capacité à traiter une vague de vulnérabilités critiques sur tout le périmètre, filiales comprises.",
    "multi-filiales": "Coordination d'un programme sur plusieurs entités juridiques et leurs SI respectifs.",
    "résilience": "Capacité à maintenir ou rétablir le service malgré un incident — au cœur de DORA et NIS2."
  };

  function initJargon() {
    var nodes = document.querySelectorAll(".taglist li, .case .tags span");
    nodes.forEach(function (el) {
      if (el.classList.contains("tipterm")) return;
      var key = el.textContent.replace(/\s+/g, " ").trim().toLowerCase();
      var def = JARGON[key];
      if (!def) return;
      el.classList.add("tipterm");
      el.setAttribute("data-tip", def);
      el.setAttribute("tabindex", "0");
      el.setAttribute("role", "note");
      el.setAttribute("aria-label", el.textContent.trim() + " : " + def);
    });
  }

  /* ── 5. Lanceur flottant de l'assistant IA (toutes pages sauf /assistant) ── */
  function initChatLauncher() {
    var path = location.pathname.replace(/\/+$/, "") || "/";
    if (path === "/assistant") return;
    if (document.querySelector(".chat-launch")) return;
    var a = document.createElement("a");
    a.className = "chat-launch";
    a.href = "/assistant";
    a.setAttribute("aria-label", "Ouvrir l'assistant IA");
    a.innerHTML = '<span class="cl-i" aria-hidden="true">💬</span><span class="cl-t">Assistant IA</span>';
    document.body.appendChild(a);
  }

  /* ── 6. Accessibilité : lien d'évitement + repères de navigation ─────────── */
  function initA11y() {
    var main = document.querySelector("main");
    if (main) {
      if (!main.id) main.id = "contenu";
      if (!main.hasAttribute("tabindex")) main.setAttribute("tabindex", "-1");
      if (!document.querySelector(".skip")) {
        var skip = document.createElement("a");
        skip.className = "skip";
        skip.href = "#" + main.id;
        skip.textContent = "Aller au contenu";
        document.body.insertBefore(skip, document.body.firstChild);
      }
    }
    var top = document.querySelector("header .nav .links");
    if (top && !top.hasAttribute("aria-label")) top.setAttribute("aria-label", "Navigation principale");
    var foot = document.querySelector("footer .fnav");
    if (foot && !foot.hasAttribute("aria-label")) {
      foot.setAttribute("role", "navigation");
      foot.setAttribute("aria-label", "Liens de pied de page");
    }
  }

  /* ── 7. Barre de progression de lecture ─────────────────────────────────── */
  function initReadBar() {
    if (document.querySelector(".readbar")) return;
    var bar = document.createElement("div");
    bar.className = "readbar";
    bar.setAttribute("aria-hidden", "true");
    document.body.appendChild(bar);
    var ticking = false;
    function update() {
      ticking = false;
      var doc = document.documentElement;
      var max = doc.scrollHeight - window.innerHeight;
      bar.style.width = max > 40 ? (Math.min(1, (window.scrollY || 0) / max) * 100) + "%" : "0";
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  /* ── 8. Lien actif dans l'en-tête (aria-current automatique) ────────────── */
  function initActiveLink() {
    var path = location.pathname.replace(/\/+$/, "") || "/";
    document.querySelectorAll("header .links a[href]").forEach(function (a) {
      var href = a.getAttribute("href");
      if (href === path) { a.classList.add("active"); a.setAttribute("aria-current", "page"); }
    });
  }

  /* ── 9. Sous-menu « Référentiel 62443 » dans l'en-tête ──────────────────── */
  var REF_MENU = [
    ["/methodologie", "1-1", "Concepts & méthodologie"],
    ["/glossaire-62443", "1-2", "Glossaire"],
    ["/metriques-62443", "1-3", "Métriques"],
    ["/programme-securite", "2-1", "Programme de sécurité (CSMS)"],
    ["/gestion-correctifs", "2-3", "Gestion des correctifs"],
    ["/exigences-prestataires", "2-4", "Exigences prestataires"],
    ["/technologies-securite", "3-1", "Technologies de sécurité"],
    ["/analyse-de-risque", "3-2", "Analyse de risque"],
    ["/exigences-systeme", "3-3", "Exigences système"],
    ["/developpement-securise", "4-1", "Développement sécurisé"],
    ["/exigences-composants", "4-2", "Exigences composants"],
    null,
    ["/audit-conformite", "▶", "Lancer l'audit 62443"],
    ["/nis2", "NIS2", "Correspondance NIS2 ↔ 62443"],
  ];

  function initRefMenu() {
    var link = document.querySelector('header .links a[href="/referentiel"]');
    if (!link || link.closest(".subnav-wrap")) return;
    var wrap = document.createElement("span");
    wrap.className = "subnav-wrap";
    link.parentNode.insertBefore(wrap, link);
    wrap.appendChild(link);

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "subnav-toggle";
    btn.setAttribute("aria-label", "Ouvrir le sommaire du référentiel 62443");
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-haspopup", "true");
    btn.textContent = "▼";
    wrap.appendChild(btn);

    var menu = document.createElement("div");
    menu.className = "subnav";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", "Pages du référentiel IEC 62443");
    REF_MENU.forEach(function (it) {
      if (!it) {
        var sep = document.createElement("div");
        sep.className = "subnav-sep";
        menu.appendChild(sep);
        return;
      }
      var a = document.createElement("a");
      a.href = it[0];
      a.setAttribute("role", "menuitem");
      var pn = document.createElement("span"); pn.className = "pn"; pn.textContent = it[1];
      a.appendChild(pn);
      a.appendChild(document.createTextNode(it[2]));
      menu.appendChild(a);
    });
    wrap.appendChild(menu);

    function setOpen(open) {
      wrap.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    }
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      setOpen(!wrap.classList.contains("open"));
    });
    document.addEventListener("click", function (e) {
      if (wrap.classList.contains("open") && !wrap.contains(e.target)) setOpen(false);
    });
    document.addEventListener("keydown", function (e) {
      if ((e.key === "Escape" || e.key === "Esc") && wrap.classList.contains("open")) { setOpen(false); btn.focus(); }
    });
  }

  /* ── 10. Recherche instantanée (Ctrl+K / bouton 🔍) ─────────────────────── */
  var SEARCH = [
    ["/", "Accueil", "Vue d'ensemble de CONSEILPREV Cyber.", "Découvrir", "home index"],
    ["/services", "Services", "Nos offres : état des lieux, segmentation, supervision, AMOA, sensibilisation.", "Découvrir", "offres prestations amoa ia"],
    ["/etudes-de-cas", "Études de cas", "Nos références : énergie, automobile, ferroviaire, oil & gas, assurance.", "Découvrir", "références missions clients"],
    ["/secteurs", "Secteurs", "Énergie, eau, manufacturing, agro, chimie, transport, assurance.", "Découvrir", "industries marchés"],
    ["/about", "À propos", "Qui nous sommes : parcours, expertises, convictions.", "Découvrir", "equipe société"],
    ["/vos-projets", "Vos projets", "Décrivez votre besoin — réponse sous 48 h ouvrées.", "Découvrir", "devis demande brief"],
    ["/diagnostic", "Diagnostic express (2 min)", "4 questions : cadre réglementaire, lectures utiles et démarche recommandée.", "Découvrir", "par où commencer parcours orientation nis2 evaluation"],
    ["/veille", "Veille cyber (CERT-FR)", "Alertes et avis officiels, résumés automatiquement et actualisés en continu.", "Découvrir", "certfr anssi alertes avis vulnérabilités actualité menaces"],
    ["/referentiel", "Référentiel IEC 62443", "La carte de la série 62443, partie par partie.", "Référentiel 62443", "norme standard"],
    ["/methodologie", "Concepts & méthodologie (1-1)", "FR, SL, zones & conduits, défense en profondeur.", "Référentiel 62443", "fondations principes"],
    ["/glossaire-62443", "Glossaire (1-2)", "Le vocabulaire de la série, reformulé.", "Référentiel 62443", "définitions termes lexique"],
    ["/metriques-62443", "Métriques (1-3)", "Indicateurs mesurables : écart SL, tendances, tableau de bord.", "Référentiel 62443", "kpi indicateurs mesure"],
    ["/programme-securite", "Programme de sécurité (2-1)", "Le CSMS : rôles, processus, amélioration continue.", "Référentiel 62443", "csms organisation management"],
    ["/gestion-correctifs", "Gestion des correctifs (2-3)", "Patch management OT et mesures compensatoires.", "Référentiel 62443", "patch mise à jour vulnérabilités"],
    ["/exigences-prestataires", "Exigences prestataires (2-4)", "La sécurité attendue des intégrateurs et mainteneurs.", "Référentiel 62443", "fournisseurs sous-traitants"],
    ["/technologies-securite", "Technologies de sécurité (3-1)", "Le panorama des technologies applicables en OT.", "Référentiel 62443", "outils solutions ids pare-feu"],
    ["/analyse-de-risque", "Analyse de risque (3-2)", "Zones & conduits, SL-T, spécification des exigences.", "Référentiel 62443", "ebios zcr crs"],
    ["/exigences-systeme", "Exigences système (3-3)", "Les 7 FR déclinées en exigences système SL 1-4.", "Référentiel 62443", "sr niveaux"],
    ["/developpement-securise", "Développement sécurisé (4-1)", "Le cycle de développement sécurisé des produits.", "Référentiel 62443", "sdl threat modelling"],
    ["/exigences-composants", "Exigences composants (4-2)", "Applications, embarqués, hôtes, équipements réseau.", "Référentiel 62443", "cr produits certification"],
    ["/audit-conformite", "Étude & audit 62443", "L'étude guidée en 6 étapes, exportable en PDF.", "Référentiel 62443", "conformité évaluation sl-a sl-t"],
    ["/nis2", "NIS2 — êtes-vous concerné ?", "Entités essentielles/importantes, obligations, notification 24 h/72 h, sanctions, pont IEC 62443.", "Conformité", "directive 2022/2555 dora anssi monespacenis2"],
    ["/demo", "Cockpit de supervision", "Démo temps réel : actifs, zones, alertes, score de risque.", "Outils temps réel", "dashboard scada surveillance"],
    ["/tendances", "Tendances", "Historique agrégé des événements du cockpit.", "Outils temps réel", "historique graphiques statistiques"],
    ["/connecter", "Connecter une plateforme", "Brancher Nozomi, Claroty, Tenable… au cockpit.", "Outils temps réel", "intégration jeton ingestion"],
    ["/guide-integration", "Guide d'intégration", "Le pas-à-pas complet du branchement de vos données.", "Outils temps réel", "documentation connecteur"],
    ["/assistant", "Assistant IA", "Le chat sécurisé (Claude & Mistral) — transparent, sans conservation.", "Outils temps réel", "chatbot question ia"],
    ["/faq", "FAQ", "Les réponses aux questions fréquentes.", "Aide & contact", "questions réponses"],
    ["/ressources", "Ressources", "Les sources officielles : ANSSI, CERT-FR, ENISA, IEC, NIST…", "Aide & contact", "liens officiels veille"],
    ["/contact", "Contact", "Le formulaire sécurisé — réponse sous 48 h ouvrées.", "Aide & contact", "email téléphone rendez-vous"],
    ["/connexion", "Espace client — connexion", "Accéder au cockpit et aux outils réservés.", "Compte", "login se connecter"],
    ["/inscription", "Créer un compte", "Demander un accès à l'espace client.", "Compte", "register s'inscrire"],
    ["/mentions-legales", "Mentions légales", "Éditeur, hébergement, propriété intellectuelle.", "Légal", "kbis société"],
    ["/politique-confidentialite", "Politique de confidentialité", "Traitements, droits RGPD, transparence IA, cookies.", "Légal", "rgpd données personnelles vie privée"],
  ];

  function initSearch() {
    var nav = document.querySelector("header .nav");
    var links = nav && nav.querySelector(".links");
    if (!nav || !links || nav.querySelector(".nav-search")) return;

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "nav-search";
    btn.setAttribute("aria-label", "Rechercher dans le site (Ctrl+K)");
    btn.setAttribute("aria-haspopup", "dialog");
    btn.innerHTML = '<span aria-hidden="true">🔍</span><span class="t">Rechercher</span><span class="k">Ctrl K</span>';
    nav.insertBefore(btn, links);

    var ov = document.createElement("div");
    ov.className = "cmdk";
    ov.innerHTML =
      '<div class="cmdk-panel" role="dialog" aria-modal="true" aria-label="Recherche dans le site">'
      + '<div class="cmdk-in"><span aria-hidden="true">🔍</span>'
      + '<input type="text" placeholder="Rechercher une page, un sujet… (NIS2, audit, SOC, RGPD…)" aria-label="Rechercher dans le site">'
      + '<span class="k">Échap</span></div>'
      + '<div class="cmdk-list" role="listbox" aria-label="Résultats"></div>'
      + '<div class="cmdk-foot"><span>↑↓ naviguer</span><span>Entrée ouvrir</span><span>Échap fermer</span></div></div>';
    document.body.appendChild(ov);
    var input = ov.querySelector("input");
    var list = ov.querySelector(".cmdk-list");
    var lastFocus = null;
    var sel = 0, shown = [];

    // Recherche approfondie : les termes du glossaire intégré (définition affichée)
    // et les questions fréquentes participent aussi à la recherche — uniquement
    // lorsqu'une saisie existe (la liste vide reste le plan du site).
    var EXTRA = [];
    Object.keys(JARGON).forEach(function (k) {
      EXTRA.push(["/glossaire-62443", k.charAt(0).toUpperCase() + k.slice(1), JARGON[k], "Terme", k]);
    });
    [
      ["Qui est concerné par la directive NIS2 ?", "nis2 directive entités essentielles importantes"],
      ["Qu'est-ce que la cybersécurité OT/IACS ?", "ot iacs différence it industriel"],
      ["Qu'est-ce que la série IEC 62443, en bref ?", "norme 62443 résumé"],
      ["Par où commencer sans inventaire de son réseau industriel ?", "commencer inventaire cartographie début"],
      ["Peut-on auditer sans arrêter la production ?", "audit production arrêt passif"],
      ["Que sont les zones et les conduits ?", "zones conduits segmentation découpage"],
    ].forEach(function (q) {
      EXTRA.push(["/faq", q[0], "Réponse détaillée dans la FAQ.", "Question", q[1]]);
    });

    function norm(s) {
      return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }
    function esc(s) { return ("" + s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

    function render(q) {
      var nq = norm(q).trim();
      var toks = nq.split(/\s+/).filter(Boolean);
      var out = [];
      (toks.length ? SEARCH.concat(EXTRA) : SEARCH).forEach(function (e) {
        var hayT = norm(e[1]), hayD = norm(e[2]), hayK = norm(e[3] + " " + e[4]);
        if (!toks.length) { out.push([1, e]); return; }
        var score = 0;
        for (var i = 0; i < toks.length; i++) {
          var t = toks[i];
          if (hayT.indexOf(t) !== -1) score += hayT.indexOf(t) === 0 ? 5 : 3;
          else if (hayK.indexOf(t) !== -1) score += 2;
          else if (hayD.indexOf(t) !== -1) score += 1;
          else { score = 0; break; }
        }
        if (score > 0) out.push([score, e]);
      });
      out.sort(function (a, b) { return b[0] - a[0]; });
      if (toks.length) out = out.slice(0, 10);
      shown = out.map(function (x) { return x[1]; });
      sel = 0;
      if (!shown.length) {
        list.innerHTML = '<div class="cmdk-empty">Aucune page ne correspond. Essayez « audit », « NIS2 », « supervision »…<br>' +
          'Ou posez la question à l\'<a href="/assistant" style="color:var(--cyan)">assistant IA</a>.</div>';
        return;
      }
      var html = "", lastG = null;
      shown.forEach(function (e, i) {
        if (!toks.length && e[3] !== lastG) { html += '<div class="cmdk-g">' + esc(e[3]) + "</div>"; lastG = e[3]; }
        html += '<a class="cmdk-item' + (i === sel ? " sel" : "") + '" data-i="' + i + '" href="' + esc(e[0]) + '" role="option" aria-selected="' + (i === sel) + '">'
          + "<b>" + esc(e[1]) + "</b><span>" + esc(e[2]) + "</span></a>";
      });
      list.innerHTML = html;
    }
    function markSel() {
      list.querySelectorAll(".cmdk-item").forEach(function (el, idx) {
        var on = parseInt(el.getAttribute("data-i"), 10) === sel;
        el.classList.toggle("sel", on);
        el.setAttribute("aria-selected", on ? "true" : "false");
        if (on) el.scrollIntoView({ block: "nearest" });
      });
    }
    function setOpen(open) {
      ov.classList.toggle("open", open);
      if (open) {
        lastFocus = document.activeElement;
        input.value = "";
        render("");
        setTimeout(function () { input.focus(); }, 0);
      } else if (lastFocus && lastFocus.focus) { lastFocus.focus(); }
    }
    btn.addEventListener("click", function () { setOpen(true); });
    ov.addEventListener("click", function (e) { if (e.target === ov) setOpen(false); });
    input.addEventListener("input", function () { render(input.value); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); if (shown.length) { sel = (sel + 1) % shown.length; markSel(); } }
      else if (e.key === "ArrowUp") { e.preventDefault(); if (shown.length) { sel = (sel - 1 + shown.length) % shown.length; markSel(); } }
      else if (e.key === "Enter") { e.preventDefault(); if (shown[sel]) location.href = shown[sel][0]; }
    });
    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault(); setOpen(!ov.classList.contains("open")); return;
      }
      if (e.key === "Escape" && ov.classList.contains("open")) { setOpen(false); return; }
      if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey && !ov.classList.contains("open")) {
        var t = e.target;
        var typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
        if (!typing) { e.preventDefault(); setOpen(true); }
      }
    });
  }

  /* ── 11. Apparition douce des cartes au défilement ──────────────────────── */
  function initReveal() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!("IntersectionObserver" in window)) return;
    var els = document.querySelectorAll("main .card, main .case, main .stat, main .dl, main .right");
    if (!els.length) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target;
        io.unobserve(el);
        el.classList.add("rv-in");
        el.addEventListener("transitionend", function done() {
          el.classList.remove("rv", "rv-in");
          el.removeEventListener("transitionend", done);
        });
        setTimeout(function () { el.classList.remove("rv", "rv-in"); }, 700);
      });
    }, { threshold: 0.01, rootMargin: "100000px 0px -30px 0px" });
    // Marge haute très large : un élément DÉPASSÉ (au-dessus de la fenêtre après un
    // saut en bas de page) compte comme visible et se révèle — jamais de carte bloquée.
    els.forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.top > window.innerHeight * 0.9) {   // seulement sous la ligne de flottaison
        el.classList.add("rv");
        io.observe(el);
      }
    });
  }

  /* ── 12. Parcours de lecture IEC 62443 (précédent / suivant) ────────────── */
  var REF_TRAIL = [
    ["/referentiel", "Vue d'ensemble de la série"],
    ["/methodologie", "1-1 · Concepts & méthodologie"],
    ["/glossaire-62443", "1-2 · Glossaire"],
    ["/metriques-62443", "1-3 · Métriques"],
    ["/programme-securite", "2-1 · Programme de sécurité (CSMS)"],
    ["/gestion-correctifs", "2-3 · Gestion des correctifs"],
    ["/exigences-prestataires", "2-4 · Exigences prestataires"],
    ["/technologies-securite", "3-1 · Technologies de sécurité"],
    ["/analyse-de-risque", "3-2 · Analyse de risque"],
    ["/exigences-systeme", "3-3 · Exigences système"],
    ["/developpement-securise", "4-1 · Développement sécurisé"],
    ["/exigences-composants", "4-2 · Exigences composants"],
    ["/audit-conformite", "Passer à la pratique : l'audit"],
  ];

  function initRefTrail() {
    var path = location.pathname.replace(/\/+$/, "") || "/";
    var idx = -1;
    for (var i = 0; i < REF_TRAIL.length; i++) if (REF_TRAIL[i][0] === path) { idx = i; break; }
    if (idx === -1) return;
    var main = document.querySelector("main");
    if (!main || main.querySelector(".refnav")) return;
    var prev = idx > 0 ? REF_TRAIL[idx - 1] : null;
    var next = idx < REF_TRAIL.length - 1 ? REF_TRAIL[idx + 1] : null;
    var el = document.createElement("nav");
    el.className = "refnav";
    el.setAttribute("aria-label", "Parcours de lecture IEC 62443");
    el.innerHTML =
      (prev ? '<a class="rn-prev" href="' + prev[0] + '"><span class="rn-k">← Précédent</span><span class="rn-t">' + prev[1] + "</span></a>" : "<span></span>")
      + '<span class="rn-pos">Parcours IEC&nbsp;62443 · ' + (idx + 1) + "/" + REF_TRAIL.length + "</span>"
      + (next ? '<a class="rn-next" href="' + next[0] + '"><span class="rn-k">Suivant →</span><span class="rn-t">' + next[1] + "</span></a>" : "<span></span>");
    main.appendChild(el);
  }

  /* ── Lien « Admin » discret dans le pied de page ────────────────────────── */
  /* Ajouté sur toutes les pages (pied de page partagé) pour accéder vite à la
     console d'administration. Discret et volontairement non indexé : la route
     /admin est de toute façon protégée (redirection vers /connexion si non
     authentifié, 403 si le compte n'a pas le rôle admin). */
  function initAdminLink() {
    var fnav = document.querySelector("footer .fnav");
    if (!fnav || fnav.querySelector(".fnav-admin")) return;
    var a = document.createElement("a");
    a.href = "/admin";
    a.textContent = "Admin";
    a.className = "fnav-admin";
    a.title = "Accès administrateur";
    a.rel = "nofollow";
    a.style.opacity = "0.5";
    fnav.appendChild(a);
  }

  function init() {
    initA11y();
    initBurger();
    initPageNav();
    initGuide();
    initJargon();
    initChatLauncher();
    initReadBar();
    initActiveLink();
    initRefMenu();
    initSearch();
    initReveal();
    initRefTrail();
    initAdminLink();
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();
})();
