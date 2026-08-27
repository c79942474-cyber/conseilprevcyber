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

  /* ── Arborescence unique du site (source de vérité de la navigation) ─────── */
  /* LES ICÔNES DES RUBRIQUES — repères de navigation, pas décoration.
     Dessinées en ligne plutôt que chargées : huit petites images feraient huit
     requêtes pour trois kilo-octets, et un tiroir qui s'ouvre ne doit rien
     attendre. Elles suivent la couleur du texte par `currentColor`, ce qui
     leur donne la teinte de leur rubrique sans la répéter dans le tracé.

     LA COULEUR N'EST JAMAIS LE SEUL SIGNAL. Chaque rubrique garde son
     intitulé écrit, et chaque icône a une SILHOUETTE distincte : qui ne
     distingue pas le cyan du violet reconnaît un livre d'un bâtiment, et lit
     le titre dans tous les cas (WCAG 1.4.1). Les icônes sont donc masquées aux
     aides vocales — les annoncer répéterait le titre juste à côté. */
  var NAV_ICONES = {
    "Expertise":
      '<path d="M3 4.5A1.5 1.5 0 0 1 4.5 3H9a3 3 0 0 1 3 3v9a2.5 2.5 0 0 0-2.5-2.5H3z"/>'
      + '<path d="M21 4.5A1.5 1.5 0 0 0 19.5 3H15a3 3 0 0 0-3 3v9a2.5 2.5 0 0 1 2.5-2.5H21z"/>',
    /* DEUX FLÈCHES QUI S'ÉCHANGENT plutôt que deux arcs de cercle : les arcs
       se refermaient mal à dix-sept pixels et donnaient une forme qu'on ne
       reconnaissait pas. Une icône illisible à sa taille d'emploi n'est pas
       une icône. */
    "Conseil & transformation":
      '<path d="M3 8.5h15"/><path d="m14 4.5 4 4-4 4"/>'
      + '<path d="M21 15.5H6"/><path d="m10 11.5-4 4 4 4"/>',
    "Ingénierie de Projet — Data Center":
      '<rect x="3" y="4" width="18" height="6" rx="1.5"/>'
      + '<rect x="3" y="14" width="18" height="6" rx="1.5"/>'
      + '<path d="M7 7h.01M7 17h.01M11 7h5M11 17h5"/>',
    "Référentiel IEC 62443":
      '<path d="M12 2.5 20 6v5.5c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V6z"/>'
      + '<path d="m8.8 11.8 2.3 2.3 4.3-4.6"/>',
    "Conformité & audit":
      '<rect x="4.5" y="3.5" width="15" height="17" rx="2"/>'
      + '<path d="M9 3.5V2.8A1.3 1.3 0 0 1 10.3 1.5h3.4A1.3 1.3 0 0 1 15 2.8v.7z"/>'
      + '<path d="m8.6 12.4 2.2 2.2 4.6-4.8"/>',
    "Plateforme":
      '<rect x="3" y="3.5" width="7.5" height="7" rx="1.5"/>'
      + '<rect x="13.5" y="3.5" width="7.5" height="11" rx="1.5"/>'
      + '<rect x="3" y="13.5" width="7.5" height="7" rx="1.5"/>'
      + '<rect x="13.5" y="17.5" width="7.5" height="3" rx="1.5"/>',
    "Ressources":
      '<path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4l2 2.5h9A1.5 1.5 0 0 1 21 9v9.5A1.5 1.5 0 0 1 19.5 20h-15A1.5 1.5 0 0 1 3 18.5z"/>',
    "Entreprise":
      '<path d="M4 21V5.5A1.5 1.5 0 0 1 5.5 4h7A1.5 1.5 0 0 1 14 5.5V21"/>'
      + '<path d="M14 10h4.5A1.5 1.5 0 0 1 20 11.5V21"/><path d="M2.5 21h19"/>'
      + '<path d="M7 8h.01M11 8h.01M7 12h.01M11 12h.01M7 16h.01M11 16h.01M17 14h.01M17 17.5h.01"/>'
  };

  /* Une teinte par rubrique. Six couleurs de palette pour huit rubriques :
     les deux dernières reprennent une teinte déjà employée, ce qui n'a pas de
     conséquence — la couleur appuie la silhouette, elle ne la remplace pas. */
  var NAV_TEINTES = {
    "Expertise": "var(--cyan)",
    "Conseil & transformation": "var(--violet)",
    "Ingénierie de Projet — Data Center": "var(--teal)",
    "Référentiel IEC 62443": "var(--amber)",
    "Conformité & audit": "var(--green)",
    "Plateforme": "var(--cyan)",
    "Ressources": "var(--terra)",
    "Entreprise": "var(--violet)"
  };

  /* LES ICÔNES DES ENTRÉES — quarante-trois, une par page.
     Plus petites et plus sobres que celles des rubriques : la rubrique donne
     la teinte, l'entrée n'en est qu'une déclinaison. Une entrée aussi voyante
     que son titre de section ferait deux niveaux qui crient en même temps, et
     on ne saurait plus lequel structure l'autre.

     ELLES NE DISTINGUENT PAS À ELLES SEULES, et n'ont pas à le faire : chaque
     entrée porte son intitulé écrit juste à côté, et deux sections peuvent
     réemployer une même silhouette sans confusion — un dossier sous
     « Expertise » et un dossier sous « Entreprise » ne se rencontrent jamais
     dans le même regard. Ce qui compte, c'est qu'À L'INTÉRIEUR d'une rubrique
     elles diffèrent. */
  var NAV_IC_PAGE = {
    /* ── Expertise ─────────────────────────────────────────────────────── */
    "/services": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><path d="M17.5 14v7M14 17.5h7"/>',
    "/secteurs": '<path d="M3 21V10l6 3.5V10l6 3.5V6l6 3.5V21z"/><path d="M3 21h18"/>',
    "/methodologie": '<circle cx="5" cy="6" r="2.3"/><circle cx="5" cy="18" r="2.3"/><circle cx="19" cy="12" r="2.3"/><path d="M7.3 6h4.2a3 3 0 0 1 3 3v.8M7.3 18h4.2a3 3 0 0 0 3-3v-.8"/>',
    "/etudes-de-cas": '<path d="M5 3.5h11l3.5 3.5v13.5H5z"/><path d="M16 3.5V7h3.5"/><path d="M9 12h6M9 16h4"/>',
    /* ── Conseil & transformation ──────────────────────────────────────── */
    "/operating-model": '<rect x="9" y="2.5" width="6" height="4.5" rx="1"/><rect x="2.5" y="16" width="6" height="4.5" rx="1"/><rect x="15.5" y="16" width="6" height="4.5" rx="1"/><path d="M12 7v4M5.5 16v-2.5h13V16"/>',
    "/maturite-ot": '<path d="M4 20V15M9.3 20v-8M14.7 20v-11M20 20V6"/>',
    "/feuille-de-route": '<path d="M3 6.5 9 4l6 2.5 6-2.5v13L15 19.5 9 17l-6 2.5z"/><path d="M9 4v13M15 6.5v13"/>',
    "/continuite-ot": '<path d="M12 2.5 20 6v5.5c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V6z"/><path d="m12.8 8-3 4.6h3l-1 3.4"/>',
    "/gestion-des-changements": '<path d="M3.5 7.5h13"/><path d="m13 4 3.5 3.5L13 11"/><path d="M20.5 16.5h-13"/><path d="m11 13-3.5 3.5L11 20"/>',
    "/architecture-cible": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.7"/><circle cx="12" cy="12" r="1.3"/>',
    "/formation": '<path d="M12 4 2.5 8.5 12 13l9.5-4.5z"/><path d="M6.5 10.8V16c0 1.6 2.5 3 5.5 3s5.5-1.4 5.5-3v-5.2"/>',
    "/gouvernance-ia": '<rect x="7.5" y="7.5" width="9" height="9" rx="2"/><path d="M10.5 4v3.5M13.5 4v3.5M10.5 16.5V20M13.5 16.5V20M4 10.5h3.5M4 13.5h3.5M16.5 10.5H20M16.5 13.5H20"/>',
    "/relecture-contrat": '<path d="M5 3.5h9l4 4V15"/><path d="M14 3.5V7h4"/><path d="M5 3.5V21h6"/><circle cx="16.5" cy="17.5" r="3.2"/><path d="m19 20 2.2 2.2"/>',
    /* ── Ingénierie de Projet — Data Center ────────────────────────────── */
    "/strategie-durable-datacenter": '<path d="M20 4c0 9-5.5 13-11 13a5.5 5.5 0 0 1 0-11c4 0 6-2 11-2z"/><path d="M4 21c1.5-5 5-8.5 9.5-10.5"/>',
    "/datacenter": '<rect x="3" y="3.5" width="18" height="6" rx="1.5"/><rect x="3" y="14.5" width="18" height="6" rx="1.5"/><path d="M6.8 6.5h.01M6.8 17.5h.01"/><path d="m14 5.5-1.6 2.6h2.2L13 11"/>',
    "/ingenierie-datacenter": '<path d="M4 20 14.5 9.5"/><path d="m12.5 7.5 4 4 3-3a2.8 2.8 0 0 0-4-4z"/><path d="M4 20v-3.5L7.5 20z"/><path d="M17 17h4M19 15v4"/>',
    /* ── Référentiel IEC 62443 ─────────────────────────────────────────── */
    "/referentiel": '<rect x="3.5" y="3.5" width="17" height="17" rx="2"/><path d="M3.5 9h17M9 9v11.5"/>',
    "/analyse-de-risque": '<path d="M12 3.5 21.5 20H2.5z"/><path d="M12 10v4M12 17h.01"/>',
    "/programme-securite": '<path d="M12 2.5 20 6v5.5c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V6z"/><path d="M8.5 12h7M12 8.5v7"/>',
    "/exigences-systeme": '<rect x="2.5" y="5" width="19" height="11" rx="2"/><path d="M8 20h8M12 16v4"/>',
    "/exigences-composants": '<rect x="8" y="8" width="8" height="8" rx="1.5"/><path d="M11 4.5V8M13 4.5V8M11 16v3.5M13 16v3.5M4.5 11H8M4.5 13H8M16 11h3.5M16 13h3.5"/>',
    "/exigences-prestataires": '<circle cx="8.5" cy="8" r="3"/><path d="M2.5 19.5a6 6 0 0 1 12 0"/><circle cx="17" cy="9.5" r="2.4"/><path d="M14.5 19.5a5 5 0 0 1 7-4.6"/>',
    "/developpement-securise": '<path d="m8 8-4.5 4L8 16"/><path d="m16 8 4.5 4L16 16"/><path d="m13.5 5-3 14"/>',
    "/technologies-securite": '<rect x="2.5" y="4" width="19" height="5" rx="1.2"/><rect x="2.5" y="9.5" width="19" height="5" rx="1.2"/><rect x="2.5" y="15" width="19" height="5" rx="1.2"/><path d="M8 4v5M16 9.5v5M8 15v5"/>',
    "/gestion-correctifs": '<rect x="2.5" y="8.5" width="19" height="7" rx="3.5" transform="rotate(-38 12 12)"/><path d="m9.5 9.5 5 5"/>',
    "/glossaire-62443": '<path d="M4 5.5A2 2 0 0 1 6 3.5h13V19H6a2 2 0 0 0-2 2z"/><path d="M8 8.5h7M8 12h5"/>',
    "/metriques-62443": '<path d="M3.5 20h17"/><rect x="5" y="12" width="3.5" height="6" rx="1"/><rect x="10.3" y="8" width="3.5" height="10" rx="1"/><rect x="15.6" y="4.5" width="3.5" height="13.5" rx="1"/>',
    /* ── Conformité & audit ────────────────────────────────────────────── */
    "/audit-conformite": '<circle cx="12" cy="12" r="9"/><path d="m8 12.3 2.7 2.7L16 9.5"/>',
    "/diagnostic": '<circle cx="10.5" cy="10.5" r="7"/><path d="m15.6 15.6 5 5"/><path d="m7.6 10.6 2 2 3.4-3.6"/>',
    "/nis2": '<circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18"/><path d="M12 3a13 13 0 0 1 0 18a13 13 0 0 1 0-18"/>',
    "/juridique": '<path d="M12 3.5V21M7 21h10"/><path d="M4 8h16"/><path d="M6.5 8 4 14h5zM17.5 8 15 14h5z"/>',
    /* ── Plateforme ────────────────────────────────────────────────────── */
    "/demo": '<rect x="2.5" y="4" width="19" height="12.5" rx="2"/><path d="M8 20.5h8M12 16.5v4"/><path d="m6.5 12 2.8-3 2.4 2.4L15.5 8"/>',
    "/tendances": '<path d="M3.5 17 9 11l3.5 3.5L20.5 6"/><path d="M15.5 6h5v5"/>',
    "/connecter": '<path d="M9 3.5v5M15 3.5v5"/><path d="M6.5 8.5h11V13a5.5 5.5 0 0 1-11 0z"/><path d="M12 18.5V21"/>',
    "/guide-integration": '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M4.2 7.2l2.6 1.5M17.2 15.3l2.6 1.5M4.2 16.8l2.6-1.5M17.2 8.7l2.6-1.5"/>',
    "/assistant": '<path d="M3.5 6.5A2.5 2.5 0 0 1 6 4h12a2.5 2.5 0 0 1 2.5 2.5v7A2.5 2.5 0 0 1 18 16H9l-5.5 4.5z"/><path d="M8.5 10h.01M12 10h.01M15.5 10h.01"/>',
    /* ── Ressources ────────────────────────────────────────────────────── */
    "/veille": '<circle cx="12" cy="18.5" r="2"/><path d="M8.2 15.3a5.4 5.4 0 0 1 7.6 0"/><path d="M5 12a10 10 0 0 1 14 0"/><path d="M2 8.7a14.5 14.5 0 0 1 20 0"/>',
    "/ressources": '<path d="M7 3.5h9l3.5 3.5v11H7z"/><path d="M16 3.5V7h3.5"/><path d="M4.5 7v13.5H16"/>',
    "/faq": '<circle cx="12" cy="12" r="9"/><path d="M9.4 9.3a2.7 2.7 0 0 1 5.2.9c0 1.8-2.6 2.3-2.6 3.8"/><path d="M12 17.2h.01"/>',
    /* ── Entreprise ────────────────────────────────────────────────────── */
    "/": '<path d="m3 10.5 9-7 9 7"/><path d="M5.5 9v11.5h13V9"/><path d="M10 20.5v-6h4v6"/>',
    "/about": '<circle cx="12" cy="8" r="3.4"/><path d="M4.5 20.5a7.5 7.5 0 0 1 15 0"/>',
    "/vos-projets": '<rect x="2.5" y="7" width="19" height="13" rx="2"/><path d="M8.5 7V5.2A1.7 1.7 0 0 1 10.2 3.5h3.6A1.7 1.7 0 0 1 15.5 5.2V7"/><path d="M2.5 12.5h19"/>',
    "/contact": '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="m3.5 6.5 8.5 6.5 8.5-6.5"/>'
  };

  function navIconePage(chemin) {
    var d = NAV_IC_PAGE[chemin];
    if (!d) return "";
    return '<svg class="drawer-ic-p" viewBox="0 0 24 24" width="14" height="14" '
      + 'fill="none" stroke="currentColor" stroke-width="1.7" '
      + 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
      + 'focusable="false">' + d + "</svg>";
  }

  function navIcone(titre) {
    var d = NAV_ICONES[titre];
    if (!d) return "";
    return '<svg class="drawer-ic" viewBox="0 0 24 24" width="17" height="17" '
      + 'fill="none" stroke="currentColor" stroke-width="1.7" '
      + 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
      + 'focusable="false">' + d + "</svg>";
  }

  var NAV_SECTIONS = [
    { t: "Expertise", l: [
      ["/services", "Services"], ["/secteurs", "Secteurs"],
      ["/methodologie", "Méthodologie"], ["/etudes-de-cas", "Études de cas"] ] },
    { t: "Conseil & transformation", l: [
      ["/operating-model", "Operating Model & gouvernance"],
      ["/maturite-ot", "Assessment de maturité"],
      ["/feuille-de-route", "Feuille de route"],
      ["/continuite-ot", "Continuité & crise OT"],
      ["/gestion-des-changements", "Gestion des changements (MOC)"],
      ["/architecture-cible", "Architecture cible OT"],
      ["/formation", "Formation & compétences"],
      ["/gouvernance-ia", "Governance by Design IA"],
      ["/relecture-contrat", "Relecture de contrats assistée"] ] },
    // ── UNE SECTION À ELLES SEULES ────────────────────────────────────────
    // Les trois pages de centres de données étaient en queue de « Conseil &
    // transformation », derrière neuf offres de cybersécurité industrielle
    // avec lesquelles elles n'ont ni sujet ni client commun. Noyées là, elles
    // se lisaient comme trois offres de plus ; groupées, elles se lisent pour
    // ce qu'elles sont — les trois temps d'une même mission d'ingénierie.
    //
    // L'ORDRE EST CELUI DU PROJET, pas l'alphabet : on arbitre (stratégie),
    // on compte (bilan et trajectoire), on exécute (ingénierie). Il reprend
    // celui du parcours guidé « projet », et deux ordres contradictoires pour
    // les mêmes trois pages enverraient le lecteur dans deux directions.
    { t: "Ingénierie de Projet — Data Center", l: [
      ["/strategie-durable-datacenter", "Stratégie DD — centres de données"],
      ["/datacenter", "Data Center Sustainability & Decarbonisation"],
      ["/ingenierie-datacenter", "Ingénierie de projet — centres de données"] ] },
    { t: "Référentiel IEC 62443", l: [
      ["/referentiel", "Vue d’ensemble"],
      ["/analyse-de-risque", "Analyse de risque · 3-2"],
      ["/programme-securite", "Programme de sécurité · 2-1"],
      ["/exigences-systeme", "Exigences système · 3-3"],
      ["/exigences-composants", "Exigences composants · 4-2"],
      ["/exigences-prestataires", "Exigences prestataires · 2-4"],
      ["/developpement-securise", "Développement sécurisé · 4-1"],
      ["/technologies-securite", "Technologies · TR 3-1"],
      ["/gestion-correctifs", "Gestion des correctifs · 2-3"],
      ["/glossaire-62443", "Glossaire · 1-2"],
      ["/metriques-62443", "Métriques · 1-3"],
      /* SERVIE MAIS INTROUVABLE. Cette page existait, était liée depuis
         le référentiel, et n'apparaissait ni au menu ni à la recherche :
         seul un visiteur qui tombait dessus par un lien la connaissait. */
      ["/checklist-62443", "Liste de vérification"] ] },
    { t: "Conformité & audit", l: [
      ["/audit-conformite", "Audit 62443"], ["/diagnostic", "Diagnostic express"],
      /* /conformite N'EST PAS ICI, ET C'EST VOULU. C'est le dossier de
         conformité DU SITE — registre des traitements, bases légales,
         classement AI Act —, sœur des mentions légales et de la politique de
         confidentialité, que la politique d'accès range délibérément hors
         menu. Le placer dans une rubrique de PRESTATIONS ferait attendre une
         offre de conformité à qui cherche notre propre registre. Elle reste
         atteignable par le pied de page et, depuis la correction du défaut,
         par la recherche. */
      ["/nis2", "NIS2"], ["/juridique", "Conseil juridique"] ] },
    { t: "Plateforme", l: [
      ["/demo", "Cockpit de supervision"], ["/tendances", "Tendances"],
      ["/connecter", "Connecter une source"], ["/guide-integration", "Guide d’intégration"],
      ["/assistant", "Assistant IA"] ] },
    { t: "Ressources", l: [
      ["/veille", "Veille cyber"], ["/ressources", "Ressources"], ["/faq", "FAQ"] ] },
    { t: "Entreprise", l: [
      ["/", "Accueil"], ["/about", "À propos"], ["/vos-projets", "Vos projets"],
      ["/contact", "Contact"] ] }
  ];

  /* Infobulles du tiroir : courte description par onglet (survol + focus). */
  var NAV_TIP = {
    "/": "Accueil — cybersécurité industrielle IT / OT / IIoT",
    "/services": "Nos prestations : état des lieux, segmentation, supervision, AMOA",
    "/secteurs": "Énergie, eau, nucléaire, aérospatial-défense, industrie…",
    "/methodologie": "Notre démarche, alignée sur la norme IEC 62443",
    "/etudes-de-cas": "Références et retours d'expérience anonymisés",
    "/operating-model": "Modèle opérationnel cible : gouvernance, RACI, fonction OT Security",
    "/maturite-ot": "Assessment de maturité OT cyber (IEC 62443 ML, NIST CSF, C2M2)",
    "/continuite-ot": "PCA / PRA industriels, sauvegarde des configurations d'automates, exercices de crise",
    "/gestion-des-changements": "Management of Change : impact cyber, approbation, fenêtres, retour arrière",
    "/architecture-cible": "Zones et conduits, DMZ industrielle, bastions, diodes de données, durcissement",
    "/formation": "Sensibilisation exploitation et maintenance, essentiels 62443, exercices de crise, mentorat",
    "/gouvernance-ia": "Gouvernance IA côté client : maturité, RACI, compliance by design, pilotage",
    "/feuille-de-route": "Trajectoire de transformation : horizons, streams, budget",
    "/referentiel": "Vue d'ensemble de la norme IEC 62443",
    "/analyse-de-risque": "Analyse de risque des systèmes industriels (partie 3-2)",
    "/programme-securite": "Programme de sécurité / CSMS (partie 2-1)",
    "/exigences-systeme": "Exigences de sécurité au niveau système (partie 3-3)",
    "/exigences-composants": "Exigences de sécurité des composants (partie 4-2)",
    "/exigences-prestataires": "Exigences pour les prestataires de service (partie 2-4)",
    "/developpement-securise": "Cycle de développement sécurisé (partie 4-1)",
    "/technologies-securite": "Technologies de sécurité industrielle (TR 3-1)",
    "/gestion-correctifs": "Gestion des correctifs des systèmes IACS (partie 2-3)",
    "/glossaire-62443": "Termes et définitions de la norme (partie 1-2)",
    "/metriques-62443": "Indicateurs et métriques de conformité (partie 1-3)",
    "/audit-conformite": "Auto-évaluation de conformité IEC 62443",
    "/diagnostic": "Diagnostic express de votre situation en 2 minutes",
    "/nis2": "Directive NIS2 et correspondance avec l'IEC 62443",
    "/juridique": "Conseil juridique assisté : qualification, lectures des textes, clausier",
    "/relecture-contrat": "Relecture assistée : playbook, écarts, validations, version par version",
    "/datacenter": "Énergie, eau et carbone calculés ensemble — PUE, WUE de site et de source, carbone incorporé — puis la décarbonation : compter et déclarer d’un côté, réduire de l’autre, et la hiérarchie d’atténuation dans son ordre",
    "/ingenierie-datacenter": "Le calcul replacé dans la séquence projet : ESQ, APS, APD, PRO, DCE, ACT, EXE, DET, AOR — et faisabilité, BASIC, FEED, EPCI, mise en service",
    "/strategie-durable-datacenter": "Le premier livrable d’une étude : quatre perspectives — raison d’être, parties prenantes, science et technologie, valeur commerciale — d’où découlent la matérialité du projet et son programme d’étude",
    "/demo": "Cockpit de supervision OT en temps réel (démonstration)",
    "/tendances": "Tendances et signaux de la menace industrielle",
    "/connecter": "Connecter une source de données au cockpit",
    "/guide-integration": "Guide d'intégration du connecteur",
    "/assistant": "Assistant IA spécialisé en cybersécurité industrielle",
    "/veille": "Veille réglementaire et bulletins CERT-FR",
    "/ressources": "Documents et ressources à télécharger",
    "/faq": "Questions fréquentes",
    "/about": "Qui sommes-nous",
    "/vos-projets": "Votre espace projets client",
    "/contact": "Nous contacter"
  };

  function _escAttr(s) {
    return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;")
      .replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /* ── 1. Tiroir latéral gauche : menu complet groupé ─────────────────────── */
  function initDrawer() {
    var btn = document.querySelector(".menu-btn");
    if (!btn || document.getElementById("drawer")) return;
    var path = location.pathname.replace(/\/+$/, "") || "/";

    var scrim = document.createElement("div");
    scrim.className = "drawer-scrim";
    var drawer = document.createElement("aside");
    drawer.className = "drawer";
    drawer.id = "drawer";
    drawer.setAttribute("aria-label", "Menu du site");
    drawer.setAttribute("aria-hidden", "true");

    var html = '<div class="drawer-head">'
      + '<div class="brand"><a href="/" class="brand-link"><img src="/emblem.svg" class="brand-mark" width="26" height="26" alt="">CONSEILPREV</a><span class="tag">Cyber</span></div>'
      + '<button type="button" class="drawer-close" aria-label="Fermer le menu">✕</button></div>'
      // Entrée des PARCOURS GUIDÉS, en tête du tiroir. L'arborescence répond
      // « où est telle page ? » ; elle ne répond pas « par où je commence ».
      // Posé MASQUÉ : c'est parcours.js qui l'affiche une fois prêt. L'ordre
      // de chargement des deux scripts n'a donc pas à être garanti, et un
      // bouton mort ne peut pas apparaître si le script manque.
      + '<button type="button" class="pc-open" id="pc-open-drawer" hidden>'
      + '<span aria-hidden="true">🧭</span><span>Parcours guidés'
      + '<span class="pc-sub">Choisissez votre rôle — l’ordre de lecture suit une mission réelle</span>'
      + '</span></button>'
      + '<nav class="drawer-nav" aria-label="Toutes les rubriques">';
    NAV_SECTIONS.forEach(function (s) {
      html += '<section style="--nav-ic:' + (NAV_TEINTES[s.t] || "var(--cyan)")
        + '"><h4>' + navIcone(s.t) + '<span>' + s.t + '</span></h4>';
      s.l.forEach(function (it) {
        var cur = it[0] === path;
        var tip = NAV_TIP[it[0]] ? ' data-tip="' + _escAttr(NAV_TIP[it[0]]) + '"' : '';
        html += '<a href="' + it[0] + '"' + (cur ? ' class="active" aria-current="page"' : '')
          + tip + '>' + navIconePage(it[0]) + '<span>' + it[1] + '</span></a>';
      });
      html += '</section>';
    });
    html += '</nav><div class="drawer-cta">'
      + '<a href="/connexion" class="btn btn-s">Espace client</a>'
      + '<a href="/contact" class="btn btn-p">Contact</a></div>';
    drawer.innerHTML = html;
    document.body.appendChild(scrim);
    document.body.appendChild(drawer);

    // Câblage du bouton « Parcours guidés ». Il reste masqué tant que
    // parcours.js ne l'a pas révélé : mieux vaut pas de bouton du tout qu'un
    // bouton qui ne fait rien.
    var pcBtn = drawer.querySelector("#pc-open-drawer");
    if (pcBtn) {
      pcBtn.addEventListener("click", function () {
        if (typeof window.parcoursOuvrir !== "function") return;
        close();                        // déclaration hissée : définie plus bas
        window.parcoursOuvrir();
      });
      if (typeof window.parcoursPret === "function") window.parcoursPret();
    }

    // Infobulles flottantes : ajoutées au <body> (jamais rognées par le tiroir
    // qui défile), positionnées à droite de l'onglet — repli sous l'onglet si
    // la place manque. Affichées au survol ET au focus clavier.
    var tip = document.createElement("div");
    tip.className = "nav-tip";
    tip.id = "nav-tip";
    tip.setAttribute("role", "tooltip");
    document.body.appendChild(tip);
    function hideTip() { tip.classList.remove("show"); }
    function showTip(a) {
      var txt = a.getAttribute("data-tip");
      if (!txt) return;
      tip.textContent = txt;
      tip.classList.add("show");
      var r = a.getBoundingClientRect();
      var tw = tip.offsetWidth, th = tip.offsetHeight, m = 8;
      var x = r.right + 12, y = r.top + (r.height - th) / 2;
      if (x + tw > window.innerWidth - m) {          // pas de place à droite
        y = r.bottom + 8;                            // → sous l'onglet
        x = Math.min(r.left, window.innerWidth - tw - m);
      }
      x = Math.max(m, Math.min(x, window.innerWidth - tw - m));
      y = Math.max(m, Math.min(y, window.innerHeight - th - m));
      tip.style.left = x + "px";
      tip.style.top = y + "px";
    }
    drawer.querySelectorAll(".drawer-nav a[data-tip]").forEach(function (a) {
      a.addEventListener("mouseenter", function () { showTip(a); });
      a.addEventListener("focus", function () { showTip(a); });
      a.addEventListener("mouseleave", hideTip);
      a.addEventListener("blur", hideTip);
    });
    var dnav = drawer.querySelector(".drawer-nav");
    if (dnav) dnav.addEventListener("scroll", hideTip, { passive: true });

    var lastFocus = null;
    function open() {
      lastFocus = document.activeElement;
      scrim.classList.add("open"); drawer.classList.add("open");
      drawer.setAttribute("aria-hidden", "false");
      btn.setAttribute("aria-expanded", "true");
      document.documentElement.style.overflow = "hidden";
      var f = drawer.querySelector(".drawer-close"); if (f) f.focus();
    }
    function close() {
      hideTip();
      scrim.classList.remove("open"); drawer.classList.remove("open");
      drawer.setAttribute("aria-hidden", "true");
      btn.setAttribute("aria-expanded", "false");
      document.documentElement.style.overflow = "";
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-controls", "drawer");
    btn.addEventListener("click", function (e) { e.stopPropagation(); open(); });
    drawer.querySelector(".drawer-close").addEventListener("click", close);
    scrim.addEventListener("click", close);
    drawer.addEventListener("click", function (e) { if (e.target.closest("a")) close(); });
    document.addEventListener("keydown", function (e) {
      if ((e.key === "Escape" || e.key === "Esc") && drawer.classList.contains("open")) close();
    });
  }

  /* ── 2. Flèches de navigation (deux blocs : haut-gauche & bas-droite) ─────── */
  function initPageNav() {
    if (document.querySelector(".pagenav")) return;
    var defs = [
      ["back", "←", "Page précédente", "Précédent"],
      ["forward", "→", "Page suivante", "Suivant"],
      ["top", "↑", "Haut de la page", "Haut"],
      ["bottom", "↓", "Bas de la page", "Bas"],
    ];
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var behavior = reduce ? "auto" : "smooth";
    function act(nav) {
      switch (nav) {
        case "back": history.back(); break;
        case "forward": history.forward(); break;
        case "top": window.scrollTo({ top: 0, behavior: behavior }); break;
        case "bottom":
          window.scrollTo({ top: document.documentElement.scrollHeight, behavior: behavior });
          break;
      }
    }
    function makeBox(posClass, label) {
      var box = document.createElement("div");
      box.className = "pagenav " + posClass;
      box.setAttribute("role", "group");
      box.setAttribute("aria-label", label);
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
      box.addEventListener("click", function (e) {
        var b = e.target.closest(".pagenav-btn");
        if (b) act(b.getAttribute("data-nav"));
      });
      document.body.appendChild(box);
    }
    makeBox("pagenav-tl", "Navigation de page (haut)");
    makeBox("pagenav-br", "Navigation de page (bas)");
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
    "/etudes-de-cas": { t: "Études de cas", p: "Nos références : missions menées pour de grands comptes de l'énergie, de la mobilité, de l'oil & gas et de l'éolien offshore.",
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
    "/glossaire-62443": { t: "Glossaire (1-2)", p: "Le vocabulaire de la série, reformulé pour être compris de tous — le glossaire normatif de référence de toute la série IEC 62443.",
      s: ["Utilisez la recherche du navigateur (Ctrl+F) pour trouver un terme.",
        "Lisez d’abord IACS et zone : presque toutes les autres définitions s’y adossent.",
        "Un terme lu ici ne remplace pas la partie de la série qui le met en œuvre — le glossaire dit ce que le mot signifie, pas ce qu’il vous oblige à faire."],
      k: [["IACS", "L’ensemble du matériel, des logiciels, des réseaux et du personnel qui assure la conduite, la surveillance et la sécurité d’un procédé industriel. C’est l’objet central de protection de toute la série."],
        ["Pourquoi un glossaire normatif", "Les mêmes mots — zone, risque, intégrité — ne recouvrent pas la même chose en informatique de gestion et en automatisme. La série commence par les fixer."]],
      l: REF_LINKS },
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
    "/ressources": { t: "Ressources", p: "Une sélection de références officielles : autorités et CERT, normes et référentiels, réglementation et guides pratiques.",
      s: ["Chaque lien ouvre la source officielle dans un nouvel onglet.",
        "Partez de l’autorité de votre pays avant les référentiels internationaux : c’est elle qui vous contrôlera.",
        "Pour la lecture de la série IEC 62443 elle-même, restez sur notre référentiel : cette page renvoie aux textes, pas à leur mise en œuvre."],
      k: [["Liens externes", "Fournis à titre informatif ; leur contenu n’engage pas CONSEILPREV, et il évolue sans nous prévenir."]],
      l: [["Référentiel 62443", "/referentiel"], ["FAQ", "/faq"]] },
    "/faq": { t: "FAQ", p: "Dix-sept questions numérotées, de la différence entre sécurité informatique et sécurité industrielle jusqu’au déroulé d’une mission et à la confidentialité.",
      s: ["Chaque question se déplie : cliquez le titre, la réponse s’ouvre sous lui.",
        "Les questions 01 à 09 portent sur le fond — normes, zones, niveaux, correctifs, incidents ; les 10 à 12 sur la façon de travailler ensemble.",
        "Pas de réponse à votre question ? Écrivez-nous : la page ne remplace pas un échange sur votre installation."],
      k: [["OT / IACS", "Les systèmes qui conduisent un procédé industriel. Ils ne se sécurisent pas comme un système d’information de bureau — c’est la première question de la page, et la plus structurante."]],
      l: [["Contact", "/contact"], ["Référentiel 62443", "/referentiel"]] },
    "/about": { t: "À propos", p: "Un partenaire indépendant de votre cybersécurité industrielle : mission, engagements et champ d’expertise.",
      s: ["Lisez les engagements avant le champ d’expertise : ce sont eux qui disent comment nous travaillons.",
        "Les études de cas donnent la preuve de ce que cette page annonce — allez-y si vous cherchez des références."],
      k: [["Indépendant", "Ni revendeur, ni intégrateur : aucune solution à placer, donc aucun conflit entre le conseil et le catalogue."],
        ["IT / OT / IIoT", "Informatique de gestion, systèmes industriels, objets connectés industriels. Sécuriser un environnement industriel n’est pas plaquer des outils informatiques sur des installations OT."]],
      l: [["Études de cas", "/etudes-de-cas"], ["Contact", "/contact"]] },
    "/secteurs": { t: "Secteurs", p: "Les secteurs industriels où nous intervenons et leurs enjeux propres — chaque secteur a ses contraintes, tous ont la même exigence de continuité.",
      s: ["Ouvrez votre secteur : l’enjeu y est nommé, et il n’est pas le même d’un secteur à l’autre.",
        "Votre secteur n’est pas listé ? La démarche s’adapte au terrain ; la fin de page dit comment nous prendre contact.",
        "Passez ensuite aux études de cas : elles montrent la démarche appliquée, secteur par secteur."],
      k: [["Sans perturber la production", "C’est la contrainte qui prime en milieu industriel, et celle qui distingue une démarche OT d’une démarche informatique."]],
      l: [["Études de cas", "/etudes-de-cas"], ["Services", "/services"]] },
    "/contact": { t: "Contact", p: "Le formulaire sécurisé pour demander une démonstration, un état des lieux ou tout renseignement.",
      s: ["Choisissez le sujet le plus proche (démo, conformité, audit…).", "Décrivez votre contexte : nous répondons sous 48 h ouvrées."],
      k: [["Formulaire sécurisé", "Transmission chiffrée, anti-spam et limitation de débit — vos données ne servent qu'à vous répondre."]],
      l: [["Démo temps réel", "/demo"], ["Services", "/services"]] },
    "/mentions-legales": { t: "Mentions légales", p: "Les informations légales de l’éditeur du site, du directeur de la publication et de l’hébergement, publiées au titre de la LCEN.",
      s: ["Cherchez l’éditeur et l’hébergeur : ce sont les deux mentions qu’une réclamation exige.",
        "Pour ce qui touche à vos données personnelles, c’est la politique de confidentialité qui fait foi, pas cette page."],
      k: [["LCEN", "La loi du 21 juin 2004 pour la confiance dans l’économie numérique : elle impose à tout éditeur de site de se rendre identifiable."]],
      l: [["Accueil", "/"], ["Politique de confidentialité", "/politique-confidentialite"]] },
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

  /* LES TROIS PAGES « CENTRES DE DONNÉES ». Elles tombaient sur le guide par
     défaut — « utilisez le menu pour naviguer » — alors que ce sont les pages
     les plus denses du site. Un guide générique sur une page complexe est pire
     qu'aucun guide : il fait croire au lecteur qu'il a lu l'aide. */
  GUIDES["/strategie-durable-datacenter"] = {
    t: "Stratégie de développement durable du projet",
    p: "Le premier livrable d'une étude : un questionnaire des quatre perspectives, dont découlent les enjeux retenus, ceux qu'on écarte, et le programme d'étude.",
    s: ["Décrivez le projet et le CONTEXTE DU SITE : il ne note aucun enjeu, il règle ce que les données en disent.",
        "Notez les vingt enjeux sur trois perspectives. Ce que vous laissez vide reste vide — et le livrable le portera comme un trou.",
        "Établissez la stratégie, puis lisez les ALERTES en tête avant de vous féliciter du résultat.",
        "L'export Word / PDF demande un compte : le document porte votre nom et vos arbitrages."],
    k: [["Les quatre perspectives", "Raison d'être, parties prenantes, science et technologie, valeur commerciale. La matérialité se lit à leur croisement."],
        ["Pourquoi la science ne vous est pas demandée", "La recueillir comme une opinion reviendrait à afficher un avis en le présentant comme une mesure — et les écarts entre perception et réalité, qui sont l'apport de la méthode, deviendraient indétectables."],
        ["Non instruit", "Ni retenu ni écarté : personne n'a regardé. Ce n'est pas un enjeu mineur, c'est un enjeu sans réponse."]],
    l: [["Le calcul énergie, eau et carbone", "/datacenter"], ["La séquence projet", "/ingenierie-datacenter"]] };

  GUIDES["/datacenter"] = {
    t: "Data Center Sustainability & Decarbonisation",
    p: "Énergie, eau et carbone calculés ensemble, puis la décarbonation : compter et déclarer d'un côté, réduire de l'autre.",
    s: ["Saisissez le PROFIL — seule la puissance informatique est indispensable ; le reste a une valeur par défaut, signalée comme telle.",
        "Lancez le calcul, puis comparez les familles de refroidissement : l'arbitrage eau / énergie s'y lit chiffré.",
        "Descendez à « Décarboner » : choisissez une voie, puis une étape. Le premier blocage est la seule information qui commande une action.",
        "Le sommaire en tête de page vous emmène directement à la section voulue."],
    k: [["PUE / WUE / CUE", "Des RATIOS. Ils ne varient pas avec le taux de charge au-dessus du point de conception — mais l'énergie, l'eau et le carbone, eux, lui restent proportionnels."],
        ["Les deux voies", "Compter et déclarer produit des chiffres opposables et ne réduit rien ; réduire produit des tonnes évitées et ne prouve rien sans la première."],
        ["Hiérarchie d'atténuation", "Éviter, réduire, substituer, puis seulement traiter le résiduel. La compensation n'est pas une réduction — et ici, elle ne porte aucun paramètre de calcul."]],
    l: [["Le livrable d'ouverture d'étude", "/strategie-durable-datacenter"], ["La séquence projet", "/ingenierie-datacenter"]] };

  GUIDES["/ingenierie-datacenter"] = {
    t: "Ingénierie de projet — centres de données",
    p: "Le même calcul replacé dans la séquence projet : ce que le moteur peut verser à chaque phase, et ce qu'il faut avoir remplacé avant de la franchir.",
    s: ["Renseignez la puissance informatique : c'est le seul champ nécessaire pour dessiner la frise.",
        "Choisissez une filière — maîtrise d'œuvre ou ingénierie industrielle — puis une phase dans la frise.",
        "Lisez le dossier de la phase : le plan du livrable, le registre des pièces, et les points encore ouverts.",
        "Exportez l'étude de phase en Word ou PDF."],
    k: [["MOP / AACE", "Deux traditions coexistent sur un centre de données : la loi MOP pour le bâtiment, la filière industrielle pour le procédé. Un centre relève des DEUX."],
        ["Substitution", "Un facteur dont l'ordre de grandeur ne suffit plus à ce stade : il faut aller chercher la donnée réelle, chez un fournisseur ou un gestionnaire de réseau."],
        ["Recevable", "Ne veut pas dire « juste » : veut dire que le niveau de définition correspond à celui qu'attend la phase."]],
    l: [["Le calcul énergie, eau et carbone", "/datacenter"], ["Le livrable d'ouverture", "/strategie-durable-datacenter"]] };


  /* DIX-SEPT PAGES QUI TOMBAIENT SUR LE GUIDE PAR DÉFAUT — « utilisez le menu
     pour naviguer ». Un guide générique sur une page dense est pire qu'aucun
     guide : il fait croire au lecteur qu'il a lu l'aide. Chacun de ceux-ci est
     écrit à partir de ce que la page dit d'elle-même : titre, chapeau et
     intertitres relevés dans son gabarit. */
  GUIDES["/admin"] = {
    t: "Tableau de bord d’administration",
    p: "Le point d’entrée des zones réservées : base de connaissance, générateur de livrables, comptes, clients et dossier RGPD.",
    s: ["Partez de la base de connaissance : c’est elle qui alimente l’assistant et les livrables.",
        "Passez aux livrables une fois la base garnie — un générateur sans documents produit du générique.",
        "Les comptes et les clients sont deux registres distincts : l’un donne l’accès, l’autre porte les obligations RGPD."],
    k: [["Zone réservée", "Toutes les pages de cette section exigent un compte administrateur ; un client connecté n’y accède pas."]],
    l: [["Base de connaissance", "/admin/base-connaissance"], ["Livrables", "/admin/livrables"], ["Comptes", "/admin/comptes"]] };

  GUIDES["/admin/base-connaissance"] = {
    t: "Base de connaissance",
    p: "Le dépôt documentaire du site : les fichiers versés ici alimentent en temps réel l’assistant conversationnel et la génération de livrables.",
    s: ["Versez vos documents par THÈME : c’est sous ce nom que la recherche les retrouvera.",
        "Formats acceptés : PDF, DOCX, XLSX, PPTX, TXT, MD, CSV.",
        "Vérifiez après chargement que le document apparaît dans la liste : un fichier refusé est annoncé avec son motif, jamais silencieusement ignoré."],
    k: [["Ce que vous versez oriente les réponses", "Une procédure périmée versée ici continuera d’être citée comme votre pratique. Retirez ce qui n’a plus cours."],
        ["PDF scanné", "Un PDF qui ne contient qu’une image ne porte aucun texte à indexer : il faut le passer par une reconnaissance optique avant de le verser."]],
    l: [["Générer un livrable", "/admin/livrables"], ["Tableau de bord", "/admin"]] };

  GUIDES["/admin/clients"] = {
    t: "Gestion des clients",
    p: "Les fiches clients et prospects, tenues selon le RGPD : base légale, consentement, durée de conservation, export et effacement — avec journal d’audit et registre des traitements.",
    s: ["Renseignez la BASE LÉGALE à la création : sans elle, la fiche existe sans droit de la détenir.",
        "Servez-vous de l’export pour répondre à une demande d’accès, et de l’effacement pour une demande de suppression.",
        "Le journal des opérations est ce qui rend la conformité démontrable : ne le contournez pas en modifiant ailleurs."],
    k: [["Article 30", "Le registre des activités de traitement : la liste de ce que vous traitez, pourquoi, pour combien de temps."],
        ["Article 5.2", "Le principe de responsabilité : il ne suffit pas d’être conforme, il faut pouvoir le démontrer. C’est ce que sert le journal."]],
    l: [["Dossier RGPD", "/admin/rgpd"], ["Dossier public de conformité", "/conformite"]] };

  GUIDES["/admin/livrables"] = {
    t: "Générateur de livrables",
    p: "Produit un BROUILLON de livrable — synthèse de conformité, note de cadrage, plan de remédiation — ancré sur les documents de votre base de connaissance.",
    s: ["Choisissez le type de livrable, puis le périmètre documentaire.",
        "Relisez intégralement avant diffusion : le texte produit est une matière première, pas un document validé.",
        "Si le résultat est générique, la cause est presque toujours en amont : la base ne contient pas encore le document qui aurait porté le détail."],
    k: [["Brouillon", "Le mot est à prendre au sens strict : rien ici n’est signé, relu ni opposable tant que vous ne l’avez pas repris."]],
    l: [["Base de connaissance", "/admin/base-connaissance"], ["Tableau de bord", "/admin"]] };

  GUIDES["/admin/rgpd"] = {
    t: "RGPD et transparence IA Act",
    p: "Les contrôles MESURÉS sur l’état réel du site — fichiers relus, documents générés puis relus, carte des routes inspectée — présentés à côté du dossier déclaratif.",
    s: ["Lisez d’abord les contrôles mesurés : ils disent ce que le site fait, pas ce qu’on en dit.",
        "Comparez ensuite avec le dossier déclaratif : l’écart entre les deux est le sujet de la page.",
        "Traitez les points rouges par ordre : ils portent chacun le fichier et la ligne où se joue la correction."],
    k: [["Mesuré et non déclaré", "Une attestation n’est jamais peinte en vert par avance, et un arbitrage n’est jamais tranché par le code : la page mesure, elle ne décide pas."],
        ["Article 50", "L’obligation de transparence de l’IA Act : dire à la personne qu’elle interagit avec une machine, et marquer ce que la machine produit."]],
    l: [["Dossier public de conformité", "/conformite"], ["Gestion des clients", "/admin/clients"]] };

  GUIDES["/architecture-cible"] = {
    t: "Architecture cible OT",
    p: "Découper le procédé en zones, qualifier chaque conduit qui les traverse, et choisir la brique juste pour que la compromission d’un poste bureautique ne descende jamais jusqu’à l’automate.",
    s: ["Commencez par le vocabulaire zones et conduits : tout le reste de la page en dépend.",
        "Parcourez les briques — DMZ industrielle, serveur rebond, bastion, diode — et la condition qui justifie chacune.",
        "N’omettez pas la console d’ingénierie : c’est l’angle mort le plus fréquent, et le plus direct vers l’automate."],
    k: [["Zone", "Un ensemble d’équipements qui partagent les mêmes exigences de sécurité."],
        ["Conduit", "Une liaison entre deux zones, dont on maîtrise et journalise ce qui la traverse."],
        ["Diode", "Un lien physiquement unidirectionnel : la donnée sort, rien ne rentre. Elle règle un problème précis, pas tous."]],
    l: [["Analyse de risque (3-2)", "/analyse-de-risque"], ["Lancer l’audit 62443", "/audit-conformite"]] };

  GUIDES["/checklist-62443"] = {
    t: "Checklist de conformité IEC 62443",
    p: "Vingt-sept points en six sections pour situer votre système industriel, chacun rattaché à la partie de la série qui le fonde et disant la preuve qu’un auditeur demandera.",
    s: ["Cochez ce qui est EN PLACE ET PROUVABLE, pas ce qui est prévu.",
        "Lisez « Le parcours » en fin de page : il ordonne ce qui reste, plutôt que de le lister.",
        "Chaque point cite sa partie de la série : c’est là qu’on va chercher l’exigence exacte."],
    k: [["Rien n’est envoyé", "Vos réponses restent dans ce navigateur. Elles ne partent sur aucun serveur et personne d’autre ne les voit."],
        ["La preuve avant la case", "Un point coché sans document derrière ne tiendra pas dix minutes devant un auditeur : c’est la preuve qui est demandée, pas la déclaration."]],
    l: [["Lancer l’audit 62443", "/audit-conformite"], ["Référentiel 62443", "/referentiel"]] };

  GUIDES["/continuite-ot"] = {
    t: "Continuité et crise OT",
    p: "Le plan de continuité industriel : redémarrer un procédé, avec ses automates, ses configurations, ses séquences et ses exigences de sûreté — et non seulement restaurer des données.",
    s: ["Lisez pourquoi le plan informatique ne suffit pas : c’est le point de départ du reste.",
        "Traduisez vos objectifs de reprise en langage d’exploitant — en heures de production, pas en minutes de serveur.",
        "Suivez la démarche en quatre temps, et prévoyez l’exercice de crise : un plan non joué n’est pas un plan."],
    k: [["PCA / PRA", "Plan de continuité, plan de reprise : tenir pendant, et revenir après."],
        ["Sauvegarde des configurations d’automates", "Le point le plus souvent absent : sans elle, un automate remplacé est un automate à reprogrammer sous pression."]],
    l: [["Gestion des changements", "/gestion-des-changements"], ["Référentiel 62443", "/referentiel"]] };

  GUIDES["/gestion-des-changements"] = {
    t: "Gestion des changements (MOC)",
    p: "Donner à chaque modification un circuit : analyse d’impact cyber ET sûreté, approbation, fenêtre d’intervention, retour arrière, trace.",
    s: ["Repérez d’abord ce qui DÉCLENCHE un MOC : la liste est plus large qu’on ne le croit.",
        "Suivez le circuit en six étapes, sans en sauter : c’est l’approbation et le retour arrière qui sautent en premier, et ce sont eux qui coûtent.",
        "Comparez avec vos derniers changements réels : combien étaient tracés ?"],
    k: [["MOC", "Management of Change : le processus qui interdit la modification non évaluée sur un procédé en marche."],
        ["Impact sûreté", "Un changement peut être sans risque cyber et dangereux pour les personnes. Les deux analyses sont distinctes et toutes deux obligatoires."]],
    l: [["Continuité OT", "/continuite-ot"], ["Référentiel 62443", "/referentiel"]] };

  GUIDES["/maturite-ot"] = {
    t: "Assessment de maturité OT",
    p: "Évaluer l’organisation, les processus et les capacités RÉELLES du dispositif — au-delà de la case réglementaire — et tracer un plan de progression priorisé.",
    s: ["Commencez par les trois regards complémentaires : conformité, maturité et risque ne se confondent pas.",
        "Faites l’auto-évaluation pour situer l’ordre de grandeur.",
        "Passez à l’assessment conduit quand une décision d’investissement en dépend."],
    k: [["Maturité n’est pas conformité", "On peut être conforme et incapable de tenir dans la durée ; on peut être mûr et en écart réglementaire. Une mesure ne remplace jamais l’autre."]],
    l: [["Feuille de route", "/feuille-de-route"], ["Operating model", "/operating-model"]] };

  GUIDES["/feuille-de-route"] = {
    t: "Feuille de route",
    p: "Traduire les constats en un plan pluriannuel séquencé, chiffré et défendable, priorisé par le risque et la valeur.",
    s: ["Situez vos constats dans les trois horizons avant de chiffrer quoi que ce soit.",
        "Rattachez chaque chantier à un stream-type : c’est ce qui rend le plan lisible en comité.",
        "Gardez la trace de l’arbitrage : une feuille de route se défend par ses renoncements autant que par ses actions."],
    k: [["Séquencé", "L’ordre n’est pas décoratif : certains chantiers n’ont aucun sens avant qu’un autre soit livré."],
        ["Défendable", "Chiffré et daté, avec la raison de chaque priorité — sinon le plan ne survit pas au premier arbitrage budgétaire."]],
    l: [["Assessment de maturité", "/maturite-ot"], ["Operating model", "/operating-model"]] };

  GUIDES["/operating-model"] = {
    t: "Operating model et gouvernance",
    p: "Qui fait quoi, selon quels processus et quelles interfaces, avec quel pilotage — pour que la sécurité industrielle tienne au-delà des chantiers ponctuels.",
    s: ["Parcourez les six dimensions du modèle cible : c’est la grille de lecture de la page.",
        "Regardez le passage du build au run : c’est là que la plupart des dispositifs se perdent.",
        "La section destinée aux instances de gouvernance est faite pour être présentée telle quelle."],
    k: [["Build et run", "Construire et exploiter. Un dispositif qui n’a pas de run retourne à zéro dès la fin du projet."],
        ["Interfaces", "Le point de friction habituel : entre la sécurité informatique, l’exploitation industrielle et la maintenance, personne ne tient la même définition du même mot."]],
    l: [["Feuille de route", "/feuille-de-route"], ["Assessment de maturité", "/maturite-ot"]] };

  GUIDES["/formation"] = {
    t: "Formation et compétences",
    p: "Des formations bâties sur vos installations et vos gestes réels : une mesure de sécurité qui n’est pas comprise sera contournée.",
    s: ["Parcourez le catalogue et repérez le module qui parle à VOS métiers.",
        "Lisez le parti pris de la page : il explique pourquoi les diapositives génériques ne changent rien.",
        "Demandez l’adaptation à vos installations — c’est là que se joue l’effet."],
    k: [["Le contournement n’est pas du sabotage", "L’opérateur qui branche sa clé, le mainteneur qui ouvre un accès distant : chacun fait son métier. Une règle qui empêche de travailler sera contournée, et c’est une donnée de conception, pas une faute."]],
    l: [["Nos services", "/services"], ["Nous contacter", "/contact"]] };

  GUIDES["/gouvernance-ia"] = {
    t: "Governance by Design IA",
    p: "Ce qui manque presque toujours quand un modèle passe en production : qui décide, qui contrôle, qui opère, et selon quelles règles.",
    s: ["Lisez le problème traité avant les volets : l’offre s’insère dans un projet existant, elle ne le remplace pas.",
        "Parcourez les quatre volets et repérez celui qui manque chez vous.",
        "Le modèle de partenariat s’adresse aux intégrateurs et éditeurs, pas aux organisations utilisatrices."],
    k: [["Ni intégrateur ni éditeur", "L’offre n’installe pas la technologie : elle installe la gouvernance autour d’une technologie déjà livrée."]],
    l: [["Conseil juridique assisté", "/juridique"], ["Nous contacter", "/contact"]] };

  GUIDES["/juridique"] = {
    t: "Conseil juridique assisté",
    p: "Trois briques distinctes : une qualification réglementaire déterministe, une analyse argumentée, et un clausier avec revue de contrat.",
    s: ["Renseignez le profil à l’étape 1 : il restreint le périmètre des textes et rend l’analyse nettement plus précise.",
        "Lisez la qualification avant l’analyse : la seconde s’appuie sur la première.",
        "Ce qui ne peut pas être tranché par le questionnaire est marqué « à confirmer » — traitez ces points, ils ne se résoudront pas seuls."],
    k: [["Déterministe", "Le rattachement est calculé par des règles explicites, sans intelligence artificielle : deux exécutions sur le même profil donnent le même résultat, et chaque texte retenu affiche pourquoi il l’est."],
        ["Lectures possibles", "L’analyse expose les interprétations et leurs conséquences plutôt qu’une réponse unique. Une réponse unique sur un texte discuté serait une réponse fausse."]],
    l: [["Relecture de contrat", "/relecture-contrat"], ["Dossier de conformité", "/conformite"]] };

  GUIDES["/relecture-contrat"] = {
    t: "Relecture de contrat",
    p: "Chaque version soumise est confrontée au playbook contractuel de l’entreprise : ce qu’on demande, jusqu’où on peut céder, ce qu’on ne signe pas.",
    s: ["Chargez la version à relire, puis lisez les écarts : chacun est cité, chiffré et adressé à l’instance qui doit trancher.",
        "Ouvrez le playbook pour voir la règle sur laquelle l’écart se fonde.",
        "L’assistant rédige la contre-proposition sans quitter la page — relisez-la avant de l’envoyer."],
    k: [["Playbook contractuel", "Vos positions écrites à l’avance : la demande, la limite de concession, et la clause rédhibitoire. Sans lui, un écart n’est qu’une opinion."],
        ["Version par version", "La relecture porte sur une version datée. C’est ce qui permet de montrer ce qui a bougé entre deux tours de négociation."]],
    l: [["Conseil juridique assisté", "/juridique"], ["Nous contacter", "/contact"]] };

  GUIDES["/conformite"] = {
    t: "Dossier de conformité",
    p: "Registre des traitements, qualification IA Act motivée, mesures effectivement en place et procédure d’exercice des droits.",
    s: ["Cherchez le traitement qui vous concerne dans le registre : finalité, base légale, durée.",
        "La section « Vos droits » donne la marche à suivre et le délai de réponse.",
        "La qualification IA Act dit pourquoi le site se range où il se range, et non seulement où il se range."],
    k: [["Générée depuis le référentiel interne", "Cette page ne peut pas diverger de ce que la console d’administration affiche, ni vieillir sans que le code vieillisse avec elle."],
        ["Article 50", "L’obligation de transparence de l’IA Act : dire que l’on parle à une machine, et marquer ce qu’elle produit."]],
    l: [["Administration RGPD", "/admin/rgpd"], ["Nous contacter", "/contact"]] };

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
    // Chaque page est rattachée à l'entrée d'en-tête de sa rubrique.
    var SECTION = {
      "/services": ["/services", "/secteurs", "/methodologie", "/etudes-de-cas", "/operating-model", "/maturite-ot", "/feuille-de-route", "/continuite-ot", "/gestion-des-changements", "/architecture-cible", "/formation", "/gouvernance-ia"],
      "/referentiel": ["/referentiel", "/analyse-de-risque", "/programme-securite", "/exigences-systeme", "/exigences-composants", "/exigences-prestataires", "/developpement-securise", "/technologies-securite", "/gestion-correctifs", "/glossaire-62443", "/metriques-62443"],
      "/audit-conformite": ["/audit-conformite", "/diagnostic", "/nis2", "/juridique"],
      "/demo": ["/demo", "/tendances", "/connecter", "/guide-integration"],
      "/assistant": ["/assistant"],
      "/veille": ["/veille", "/ressources", "/faq"],
      "/about": ["/about"]
    };
    document.querySelectorAll("header .links a[href]").forEach(function (a) {
      var href = a.getAttribute("href");
      var match = href === path || (SECTION[href] && SECTION[href].indexOf(path) >= 0);
      if (match) { a.classList.add("active"); if (href === path) a.setAttribute("aria-current", "page"); }
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
    ["/checklist-62443", "Liste de vérification 62443", "Six sections, chaque point rattaché à sa partie de la série et disant la preuve attendue.", "Référentiel 62443", "checklist controle preuve audit verification"],
    ["/conformite", "Conformité RGPD & IA Act", "Le dossier de conformité du site lui-même : traitements, bases légales, classement AI Act.", "Conformité & audit", "rgpd ai act donnees personnelles registre traitements"],
    /* ── LES TREIZE PAGES QUI MANQUAIENT ────────────────────────────────
       DÉFAUT CORRIGÉ. Cet index en couvrait 34 sur les 43 du tiroir : toute
       la rubrique « Conseil & transformation » (neuf pages), trois pages de
       centres de données et le conseil juridique étaient introuvables par la
       recherche. Un visiteur qui tapait « maturité » ou « feuille de route »
       — les deux entrées les plus commerciales du site — obtenait « aucun
       résultat », ce qui se lit comme « ce cabinet ne le fait pas ».
       La dérive est silencieuse par construction : on ajoute une page au
       tiroir, on oublie l'index, et rien ne le signale. Un contrôle
       (tests/test_audit_lot2.py) confronte désormais les deux listes. */
    ["/operating-model", "Operating Model & gouvernance", "Modèle opérationnel cible : gouvernance, RACI, fonction OT Security.", "Conseil & transformation", "raci organisation cible pilotage"],
    ["/maturite-ot", "Assessment de maturité", "Maturité OT cyber mesurée : IEC 62443 ML, NIST CSF, C2M2.", "Conseil & transformation", "evaluation niveau csf c2m2 diagnostic"],
    ["/feuille-de-route", "Feuille de route", "Trajectoire de transformation : horizons, chantiers, budget.", "Conseil & transformation", "roadmap trajectoire planning budget"],
    ["/continuite-ot", "Continuité & crise OT", "PCA / PRA industriels, sauvegarde des configurations d'automates, exercices de crise.", "Conseil & transformation", "pca pra reprise sinistre exercice"],
    ["/gestion-des-changements", "Gestion des changements (MOC)", "Management of Change : impact cyber, approbation, fenêtres, retour arrière.", "Conseil & transformation", "moc change fenetre rollback approbation"],
    ["/architecture-cible", "Architecture cible OT", "Zones et conduits, DMZ industrielle, bastions, diodes de données, durcissement.", "Conseil & transformation", "dmz bastion diode segmentation durcissement"],
    ["/formation", "Formation & compétences", "Sensibilisation exploitation et maintenance, essentiels 62443, exercices de crise.", "Conseil & transformation", "sensibilisation competences apprentissage"],
    ["/gouvernance-ia", "Governance by Design IA", "Gouvernance de l'IA côté client : maturité, RACI, conformité par conception, pilotage.", "Conseil & transformation", "ia intelligence artificielle ai act gouvernance"],
    ["/relecture-contrat", "Relecture de contrats assistée", "Relecture assistée : playbook, écarts, validations, version par version.", "Conseil & transformation", "contrat clausier juridique relecture"],
    ["/strategie-durable-datacenter", "Stratégie DD — centres de données", "Quatre perspectives : raison d'être, parties prenantes, matérialité, trajectoire.", "Ingénierie de Projet — Data Center", "strategie durable rse materialite"],
    ["/datacenter", "Data Center — durabilité et décarbonation", "Énergie, eau et carbone calculés ensemble : PUE, WUE, carbone incorporé.", "Ingénierie de Projet — Data Center", "pue wue carbone energie eau decarbonation"],
    ["/ingenierie-datacenter", "Ingénierie de projet — centres de données", "Le calcul replacé dans la séquence projet : ESQ, APS, APD, PRO, DCE, ACT, EXE.", "Ingénierie de Projet — Data Center", "esq aps apd pro dce maitrise oeuvre chiffrage"],
    ["/juridique", "Conseil juridique", "Conseil juridique assisté : qualification, lecture des textes, clausier.", "Conformité & audit", "juridique contrat clause qualification"],
    ["/", "Accueil", "Vue d'ensemble de CONSEILPREV Cyber.", "Découvrir", "home index"],
    ["/services", "Services", "Nos offres : état des lieux, segmentation, supervision, AMOA, sensibilisation.", "Découvrir", "offres prestations amoa ia"],
    ["/etudes-de-cas", "Études de cas", "Nos références : énergie, automobile, ferroviaire, oil & gas, assurance, éolien offshore.", "Découvrir", "références missions clients"],
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

  function initYear() {
    var y = document.getElementById("y");
    if (y && !y.textContent) y.textContent = new Date().getFullYear();
  }

  /* ── CE QUI DEMANDE UN COMPTE, SIGNALÉ AVANT LE CLIC ──────────────────────
   *
   * LE PROBLÈME, TEL QU'IL SE PRÉSENTE. Depuis que les pages du menu latéral
   * sont réservées aux clients validés, la seule page d'accueil porte
   * VINGT-SIX liens qui mènent à un formulaire de connexion, et les pieds de
   * page des quarante autres portent les mêmes. Un visiteur qui l'apprend en
   * cliquant croit s'être trompé de bouton — et il ne réessaie pas.
   *
   * POURQUOI ICI, ET PAS DANS LES PAGES. Étiqueter ces liens à la main, c'était
   * quarante fichiers à corriger, puis un de plus à chaque page ajoutée. Et
   * c'est le lien qu'on aurait oublié qui aurait surpris le visiteur. La liste
   * vient du serveur — la politique elle-même —, et le marquage se fait ici,
   * une fois, pour tout le site.
   *
   * POURQUOI UN CADENAS ET NON « accès client » EN TOUTES LETTRES. Dans un pied
   * de page qui aligne vingt entrées, vingt fois « accès client » double la
   * hauteur du bloc et cesse d'être lu. Le cadenas tient dans la ligne, et il
   * porte son explication en infobulle et pour les lecteurs d'écran. Une
   * légende dit une fois ce qu'il signifie — un symbole sans légende n'est
   * qu'un caractère de plus.
   *
   * RIEN N'EST MARQUÉ POUR UN CLIENT CONNECTÉ : ces pages lui sont ouvertes, et
   * les lui signaler comme réservées serait faux.
   */
  var ACCES_MARQUE = "data-acces-marque";

  /* CE QUE LA MARQUE ANNONCE SUIT LE NIVEAU DE LA PAGE, pas seulement l'état
     du visiteur.

     DEUXIÈME DÉFAUT, plus grave que le premier. Un visiteur anonyme voyait
     « accès client 🔒 » sur des liens menant à /admin/… : le site lui
     promettait donc que créer un compte client ouvrirait l'espace
     d'administration. Il s'inscrit, attend la validation, revient — et le lien
     refuse toujours. La promesse était fausse au moment même où elle était
     la plus engageante.

     Chaque lien porte donc le niveau de SA page ; l'état du visiteur décide
     seulement de ce qu'on marque :
       — anonyme             → tout ce qui est fermé, chacun à son niveau ;
       — connecté, non admin → les seules pages d'administration ;
       — administrateur      → rien. */
  function _marquerAcces(fermees, connecte, admins) {
    admins = admins || [];
    var vus = 0;
    [].forEach.call(document.querySelectorAll("a[href]"), function (a) {
      if (a.hasAttribute(ACCES_MARQUE)) return;
      var href = a.getAttribute("href") || "";
      if (href.charAt(0) !== "/") return;              /* externe, ou ancre */
      var chemin = href.split("#")[0].split("?")[0];
      if (fermees.indexOf(chemin) < 0) return;
      /* Le lien qui le dit déjà en toutes lettres n'a pas besoin du cadenas :
         le doubler donnerait « Ingénierie de projet · accès client 🔒 ». */
      if (!connecte && /accès client/i.test(a.textContent)) {
        a.setAttribute(ACCES_MARQUE, "dit");
        return;
      }
      var estAdmin = admins.indexOf(chemin) >= 0;
      var c = document.createElement("span");
      c.className = "ac-cle";
      c.textContent = "🔒";
      c.setAttribute("aria-label", estAdmin ? "réservé à l'administration"
                                            : "accès client");
      c.setAttribute("title", estAdmin
        ? "Réservé à l'administration du site — un compte client ne l'ouvre pas"
        : "Accès client — compte validé requis");
      a.appendChild(document.createTextNode(" "));
      a.appendChild(c);
      a.setAttribute(ACCES_MARQUE, "cadenas");
      vus++;
    });
    return vus;
  }

  function _legendeAcces(connecte) {
    var pied = document.querySelector("footer");
    if (!pied || pied.querySelector(".ac-legende")) return;
    var p = document.createElement("p");
    p.className = "ac-legende";
    p.innerHTML = connecte
      /* À UN CLIENT CONNECTÉ, on ne propose pas de créer un compte : il en a
         un. On lui dit ce qui manque, et à qui le demander. */
      ? '<span class="ac-cle">🔒</span>&nbsp;Ces pages sont réservées à '
        + 'l’administration du site. Votre compte est bien validé — il n’a '
        + 'simplement pas ce rôle. <a href="/contact">Écrivez-nous</a> si vous '
        + 'pensez devoir y accéder.'
      /* À UN ANONYME, la légende ne peut pas dire « un compte ouvre tout
         cela » : une partie des liens marqués mène à l'administration, qu'un
         compte client n'ouvre pas. Elle distingue donc les deux, sinon
         l'inscription se ferait sur une promesse que la validation ne tiendra
         pas — et c'est au retour, après l'attente, que le visiteur le
         découvrirait. */
      : '<span class="ac-cle">🔒</span>&nbsp;Ces pages demandent un '
        + 'compte client validé. <a href="/inscription">Créer un accès</a> — votre '
        + 'adresse est confirmée par courriel, puis l’accès est validé par notre '
        + 'équipe, qui vous prévient. Celles marquées <i>réservé à '
        + 'l’administration</i> ne s’ouvrent pas avec un compte client : elles '
        + 'sont l’outil interne du cabinet.';
    pied.appendChild(p);
  }

  /* UNE SEULE requête /api/auth/me par chargement de page. Deux blocs en ont
     besoin — le marquage d'accès et le lien de compte — et chacun lançait la
     sienne : la réponse étant no-store (c'est une donnée de session), les deux
     partaient réellement sur le réseau, et chacune coûtait une lecture de
     compte en base. La promesse est partagée, pas la donnée : au prochain
     chargement de page, la question est reposée au serveur. */
  var _moi = null;
  function moiPromesse() {
    if (!_moi) {
      _moi = fetch("/api/auth/me", { headers: { "Accept": "application/json" } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; });
    }
    return _moi;
  }

  /* La réponse à « quelles pages demandent un compte, et suis-je connecté ? »,
     posée UNE fois par chargement de page et offerte à qui en a besoin.

     POURQUOI L'OFFRIR PLUTÔT QUE LA GARDER. Les parcours guidés posent
     exactement la même question — ils annoncent « 🔒 Compte requis » avant le
     clic — et la tenaient jusqu'ici dans une liste écrite à la main. Cette
     liste avait dérivé : neuf pages de parcours étaient devenues réservées et
     continuaient de s'annoncer libres. Une seconde source de vérité sur un
     sujet d'accès finit toujours par mentir, et elle ment sans bruit. La
     recopier ailleurs eût recommencé la même dérive ; on partage la réponse.

     La refaire chercher n'aurait rien coûté sur /api/acces (cacheable une
     heure), mais /api/auth/me est en no-store : chaque appel supplémentaire
     est une lecture de compte en base de plus, par page. */
  var _acces = null;
  function accesPromesse() {
    if (!_acces) {
      _acces = fetch("/api/acces", { headers: { "Accept": "application/json" } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) {
          return moiPromesse().then(function (moi) {
            return { client: (j && j.client) || [],
                     connecte: !!(moi && moi.authenticated) };
          });
        })
        .catch(function () { return null; });
    }
    return _acces;
  }
  window.navAcces = accesPromesse;

  /* ── CE QUI RESTE FERMÉ À UN CLIENT CONNECTÉ ────────────────────────────
     DÉFAUT CORRIGÉ. Le marquage s'arrêtait net dès qu'un visiteur était
     connecté — « ces pages lui sont ouvertes ». C'est vrai des pages client,
     faux des pages d'ADMINISTRATION : un client validé voyait donc les liens
     de l'espace administrateur sans aucune marque, et le clic le menait à un
     refus. C'est le seul endroit du site où un lien mentait, et il mentait
     précisément aux personnes qui ont un compte.

     La règle est donc à trois états, et non plus à deux :
       — anonyme               → marquer tout ce qui demande un compte ;
       — connecté, non admin   → marquer ce qui demande le rôle admin ;
       — administrateur        → ne rien marquer, tout lui est ouvert. */
  function initAcces() {
    accesPromesse().then(function (a) {
      if (!a) return;
      if (a.estAdmin) return;
      var fermees = a.connecte ? a.admin : a.client;
      if (!fermees || !fermees.length) return;
      if (_marquerAcces(fermees, a.connecte, a.admin)) _legendeAcces(a.connecte);
    }).catch(function () { /* le site reste utilisable sans le marquage */ });
  }

  /* ── État de compte : lien compact dans l'en-tête + déconnexion dans le tiroir ── */
  function _logout() {
    fetch("/api/auth/logout", { method: "POST", headers: { "Content-Type": "application/json" } })
      .then(function () { location.href = "/"; }).catch(function () { location.href = "/"; });
  }
  function initAccount() {
    var cta = document.querySelector("header .navcta");
    if (!cta || cta.querySelector(".nav-account")) return;
    moiPromesse()
      .then(function (j) {
        if (!j) return;
        var slot = document.createElement("span");
        slot.className = "nav-account";
        var a = document.createElement("a");
        a.className = "acc-link";
        if (j.authenticated) {
          var first = ((j.name || j.email || "compte").split(/\s+/)[0]) || "compte";
          a.href = "/vos-projets"; a.title = j.email || ""; a.textContent = "● " + first;
          // Déconnexion : dans le tiroir (l'en-tête reste compact).
          var dcta = document.querySelector(".drawer-cta");
          if (dcta) {
            var first_btn = dcta.querySelector("a");
            if (first_btn) {
              first_btn.textContent = "Déconnexion";
              first_btn.removeAttribute("href");
              first_btn.setAttribute("role", "button");
              first_btn.style.cursor = "pointer";
              first_btn.addEventListener("click", function (e) { e.preventDefault(); _logout(); });
            }
          }
        } else {
          a.href = "/connexion"; a.textContent = "Connexion";
        }
        slot.appendChild(a);
        cta.insertBefore(slot, cta.firstChild);
      }).catch(function () {});
  }

  function init() {
    initA11y();
    initYear();
    initAccount();
    initDrawer();
    /* CE QUI GARANTIT QUE LE TIROIR EST MARQUÉ N'EST PAS LE RANG DE CET APPEL.
       J'avais écrit ici que l'ordre décidait de tout — que marquer avant
       initDrawer laisserait les trente entrées du menu sans cadenas. C'est
       faux, et je l'ai constaté en inversant les deux appels : le compte des
       entrées marquées n'a pas bougé. Le marquage a lieu dans la réponse d'un
       fetch, donc après la fin de init(), quel que soit ce rang.
       Ce qui protège réellement, c'est recette_acces.js, qui compte les
       entrées marquées du tiroir dans le vrai document. Un commentaire qui
       décrit une garantie inexistante est pire que pas de commentaire : il
       dispense de chercher la vraie. */
    initAcces();
    initPageNav();
    initGuide();
    initJargon();
    initChatLauncher();
    initReadBar();
    initActiveLink();
    initSearch();
    initReveal();
    initRefTrail();
    initAdminLink();
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();
})();
