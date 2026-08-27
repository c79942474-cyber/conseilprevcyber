/* LE FOND DU BANDEAU — TROIS ÉTAGES, DANS CET ORDRE.
   ═══════════════════════════════════════════════════════════════════════
   1. UN DÉGRADÉ CSS. Zéro octet, présent au premier pixel peint. Sans lui,
      le bandeau reste vide le temps que l'affiche arrive, et ce vide se
      voit — c'est la première chose que regarde un visiteur.
   2. UNE AFFICHE. Une image fixe, quelques kilo-octets, servie tout de
      suite. ELLE DOIT TENIR SEULE : si la vidéo ne vient jamais — réseau
      lent, écran étroit, mouvement réduit, fichier absent — la page reste
      habillée et personne ne s'aperçoit qu'il manque quelque chose.
   3. LA VIDÉO. Chargée APRÈS le reste de la page, et seulement quand elle
      a des chances d'être un cadeau plutôt qu'une punition.

   POURQUOI CET ORDRE, ET PAS UNE VIDÉO POSÉE DIRECTEMENT DANS LE HTML.
   Une balise `<video autoplay>` écrite dans la page démarre son
   téléchargement AVANT le texte : quelques méga-octets prennent la place
   du contenu dans la file du réseau, et sur une connexion moyenne le
   visiteur regarde un bandeau vide pendant que la vidéo se charge. Ici la
   vidéo n'existe même pas dans le document tant que les conditions ne sont
   pas réunies : rien à télécharger, rien à décoder, rien à annuler.

   CE QUI EMPÊCHE LE CHARGEMENT, ET POURQUOI CHACUN COMPTE
   ──────────────────────────────────────────────────────
   · ÉCRAN ÉTROIT. Un fond de bandeau se voit à peine sur un téléphone,
     alors qu'il y coûte le plus cher — forfait, batterie, chaleur.
   · MOUVEMENT RÉDUIT. Un réglage système, souvent posé par quelqu'un que
     l'animation rend malade. Il ne se contourne pas.
   · ÉCONOMISEUR DE DONNÉES, ou connexion annoncée lente. Le navigateur
     nous le dit ; l'ignorer serait choisir à la place du visiteur.
   · ÉCONOMIE D'ÉNERGIE. Une vidéo en boucle empêche la mise en veille du
     décodeur ; sur une machine en réserve de batterie, c'est une dépense
     qu'on n'a pas demandée.
   · ONGLET CACHÉ. On met en pause plutôt que de décoder dans le vide.

   Aucune de ces conditions n'est un cas rare : ensemble, elles couvrent une
   grande part des visites. C'est bien pour cela que l'affiche doit être
   belle, et pas un pis-aller. */
(function () {
  "use strict";

  var socle = document.querySelector("[data-fond-hero]");
  if (!socle) return;

  var video = socle.getAttribute("data-video");        // ex. "hero-fond.mp4"
  var videoWebm = socle.getAttribute("data-video-webm");
  if (!video && !videoWebm) return;                    // pas de vidéo fournie

  var LARGEUR_MINI = +(socle.getAttribute("data-largeur-mini") || 1024);

  function refuse() {
    /* Chaque test est isolé : un navigateur qui ne connaît pas
       `matchMedia` ou `connection` ne doit pas faire échouer les autres. */
    try {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches)
        return "mouvement réduit";
    } catch (e) {}
    try {
      /* `hover: none` ET `pointer: coarse` : un écran tactile sans survol.
         La largeur seule laisserait passer une tablette en paysage, où le
         coût est celui d'un mobile. */
      if (window.matchMedia("(hover: none) and (pointer: coarse)").matches)
        return "appareil tactile";
    } catch (e) {}
    if (Math.min(window.innerWidth, screen.width || 9999) < LARGEUR_MINI)
      return "écran étroit";
    var c = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (c) {
      if (c.saveData) return "économiseur de données";
      if (/^(slow-)?2g$/.test(c.effectiveType || "")) return "connexion lente";
      if (c.effectiveType === "3g") return "connexion lente";
    }
    /* `getBattery` rend une promesse : on ne peut pas l'attendre ici sans
       retarder tout le monde. On la consulte plus bas, et on retire la
       vidéo si la réponse arrive mauvaise. */
    return null;
  }

  function poser() {
    var motif = refuse();
    if (motif) { socle.setAttribute("data-fond-etat", "affiche : " + motif); return; }

    var v = document.createElement("video");
    v.muted = true;                 // AVANT `autoplay` : sans cela, iOS refuse
    v.defaultMuted = true;
    v.playsInline = true;           // sinon iOS ouvre le lecteur plein écran
    v.setAttribute("playsinline", "");
    v.setAttribute("muted", "");
    v.loop = true;
    v.autoplay = true;
    v.preload = "auto";
    v.tabIndex = -1;
    v.setAttribute("aria-hidden", "true");
    v.className = "fond-hero-video";
    /* L'affiche reste visible DESSOUS pendant tout le chargement : la vidéo
       n'apparaît qu'une fois qu'elle a réellement une image à montrer. Sans
       cela, on remplace une belle image fixe par un rectangle noir. */
    v.style.opacity = "0";

    var sources = [];
    if (videoWebm) sources.push([videoWebm, "video/webm"]);
    if (video) sources.push([video, "video/mp4"]);

    var fini = false;
    function abandonne(pourquoi) {
      if (fini) return;
      fini = true;
      if (v.parentNode) v.parentNode.removeChild(v);
      socle.setAttribute("data-fond-etat", "affiche : " + (pourquoi || "vidéo indisponible"));
    }
    function reussi() {
      if (fini) return;
      fini = true;
      v.style.opacity = "1";
      socle.setAttribute("data-fond-etat", "vidéo");
    }

    /* L'ÉCHEC NE SE SIGNALE PAS LÀ OÙ ON L'ATTEND — et c'est le cas le plus
       fréquent, puisque c'est celui du site tant qu'aucun fichier n'est
       déposé. Vérifié dans un navigateur :

         événements reçus : video:loadstart · source0:error · source1:error
         networkState = 3 (NETWORK_NO_SOURCE), readyState = 0
         v.error = null, et la promesse de `play()` ne se règle JAMAIS

       Autrement dit : `error` se déclenche sur les balises `<source>`, pas
       sur la `<video>` ; l'élément ne porte aucune erreur ; et attendre le
       rejet de `play()` revient à attendre indéfiniment. Une première
       version guettait `video.error` et le rejet de `play()` : elle laissait
       un élément vidéo mort dans la page, l'affiche derrière lui, et aucun
       moyen de savoir que quelque chose avait échoué.

       On compte donc les sources épuisées, ce qui est le signal réel. */
    var echouees = 0;
    sources.forEach(function (src) {
      var s = document.createElement("source");
      s.src = "/media/" + src[0];
      s.type = src[1];
      s.addEventListener("error", function () {
        if (++echouees >= sources.length) abandonne("aucune source lisible");
      });
      v.appendChild(s);
    });

    v.addEventListener("playing", reussi, { once: true });
    v.addEventListener("error", function () { abandonne("erreur de lecture"); });

    /* ET UNE BUTÉE DE TEMPS, parce qu'une source peut ne jamais répondre —
       serveur muet, fichier tronqué — sans qu'aucun événement ne survienne.
       Sans elle, l'élément resterait indéfiniment invisible au-dessus de
       l'affiche, à consommer une couche de composition pour rien. */
    setTimeout(function () {
      if (!fini) abandonne("vidéo trop lente à démarrer");
    }, 12000);

    socle.insertBefore(v, socle.firstChild);
    var p = v.play();
    if (p && p.catch) p.catch(function (e) {
      /* `NotAllowedError` : le navigateur refuse la lecture automatique. On
         n'insiste pas — une vidéo de fond qu'il faut cliquer n'est pas un
         fond. Les autres motifs sont couverts par les sources épuisées. */
      if (e && e.name === "NotAllowedError") abandonne("lecture automatique refusée");
    });

    /* ONGLET CACHÉ : on ne décode pas dans le vide. */
    document.addEventListener("visibilitychange", function () {
      if (!v.parentNode) return;
      if (document.hidden) v.pause(); else v.play().catch(function () {});
    });

    /* BANDEAU SORTI DE L'ÉCRAN : idem. La page fait plusieurs écrans de
       haut ; garder le décodeur en marche pendant qu'on lit le bas serait
       payer sans rien montrer. */
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (ent) {
        if (!v.parentNode) return;
        if (ent[0].isIntersecting) v.play().catch(function () {}); else v.pause();
      }, { threshold: 0 }).observe(socle);
    }

    /* RÉSERVE DE BATTERIE : la réponse arrive après coup, on en tient
       compte quand elle arrive. */
    if (navigator.getBattery) {
      navigator.getBattery().then(function (b) {
        if (!b.charging && b.level < 0.2) abandonne();
      }).catch(function () {});
    }
  }

  /* APRÈS le chargement de la page, et au premier temps mort : la vidéo est
     un ornement, elle passe après tout le reste. `load` suffit ici — à la
     différence du préchargement de modules, rien n'attend derrière. */
  function demarrer() {
    if (window.requestIdleCallback) requestIdleCallback(poser, { timeout: 3000 });
    else setTimeout(poser, 1200);
  }
  if (document.readyState === "complete") demarrer();
  else window.addEventListener("load", demarrer, { once: true });
})();
