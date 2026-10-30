/* LE BANDEAU « OFFSHORE SUBSTATIONS — OT SECURITY », EN TÊTE DE L'ACCUEIL.
   ═══════════════════════════════════════════════════════════════════════
   La page livre l'AFFICHE (une image, au format du bandeau LinkedIn) dans
   un lien vers le profil. La vidéo n'est pas dans le HTML : une balise
   `<video>` écrite dans la page commencerait son téléchargement avant le
   texte (voir fond-hero.js, même contrat). Ce script l'insère APRÈS le
   chargement, par-dessus l'affiche, et ne la montre qu'une fois qu'elle a
   une image à peindre.

   CE BANDEAU N'EST PAS UN FOND : c'est un contenu, lu de face, petit
   (1,2 Mo). Il ne se refuse donc pas aux écrans étroits ni aux écrans
   tactiles — seulement à ceux qui ont demandé moins : mouvement réduit,
   économiseur de données, connexion annoncée lente. L'affiche tient alors
   seule, et dit la même chose.

   LA PAUSE (WCAG 2.2.2). Une animation de plus de cinq secondes doit
   pouvoir s'arrêter : le bouton n'apparaît qu'avec la vidéo, et il est
   HORS du lien — un clic sur la pause n'ouvre pas LinkedIn. */
(function () {
  "use strict";

  var cadre = document.getElementById("bandeau-ot");
  if (!cadre) return;
  var nom = cadre.getAttribute("data-video");
  var lien = cadre.querySelector(".bandeau-ot-lien");
  var affiche = cadre.querySelector(".bandeau-ot-media");
  var bouton = cadre.querySelector(".bandeau-ot-btn");
  if (!nom || !lien || !affiche || !bouton) return;

  function refuse() {
    try {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches)
        return "mouvement réduit";
    } catch (e) {}
    var c = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (c) {
      if (c.saveData) return "économiseur de données";
      if (/^(slow-)?2g$/.test(c.effectiveType || "")) return "connexion lente";
    }
    return null;
  }

  var v = null;
  var voulue = true;           // le visiteur n'a pas demandé la pause

  function peindre() {
    var enCours = v && !v.paused;
    bouton.setAttribute("data-etat", enCours ? "lecture" : "pause");
    bouton.setAttribute("aria-label", enCours ? "Mettre l’animation en pause"
                                              : "Relancer l’animation");
  }

  function poser() {
    var motif = refuse();
    if (motif) { cadre.setAttribute("data-etat", "affiche : " + motif); return; }

    v = document.createElement("video");
    v.muted = true;                 // AVANT `autoplay` : sans cela, iOS refuse
    v.defaultMuted = true;
    v.setAttribute("muted", "");
    v.playsInline = true;
    v.setAttribute("playsinline", "");
    v.loop = true;
    v.autoplay = true;
    v.preload = "auto";
    v.poster = affiche.currentSrc || affiche.src;
    v.tabIndex = -1;
    v.setAttribute("aria-hidden", "true");
    v.className = "bandeau-ot-video";
    v.width = 1584; v.height = 396;

    var fini = false;
    function abandonne(pourquoi) {
      if (fini) return;
      fini = true;
      if (v.parentNode) v.parentNode.removeChild(v);
      v = null;
      bouton.hidden = true;
      cadre.setAttribute("data-etat", "affiche : " + (pourquoi || "vidéo indisponible"));
    }
    function reussi() {
      if (fini) return;
      fini = true;
      cadre.setAttribute("data-etat", "vidéo");
      bouton.hidden = false;
      peindre();
    }

    var s = document.createElement("source");
    s.src = "/media/" + nom;
    s.type = "video/mp4";
    /* L'échec se signale sur la <source>, pas sur la <video> (mesuré pour
       fond-hero.js) : c'est là qu'on l'écoute. */
    s.addEventListener("error", function () { abandonne("aucune source lisible"); });
    v.appendChild(s);
    v.addEventListener("playing", reussi, { once: true });
    v.addEventListener("play", peindre);
    v.addEventListener("pause", peindre);
    setTimeout(function () { if (!fini) abandonne("vidéo trop lente à démarrer"); }, 12000);

    lien.insertBefore(v, affiche.nextSibling);
    var p = v.play();
    if (p && p.catch) p.catch(function (e) {
      if (e && e.name === "NotAllowedError") abandonne("lecture automatique refusée");
    });

    bouton.addEventListener("click", function () {
      if (!v) return;
      if (v.paused) { voulue = true; v.play().catch(function () {}); }
      else { voulue = false; v.pause(); }
    });

    /* HORS DE L'ÉCRAN, OU ONGLET CACHÉ : on ne décode pas dans le vide —
       et on ne relance jamais une animation que le visiteur a arrêtée. */
    document.addEventListener("visibilitychange", function () {
      if (!v) return;
      if (document.hidden) v.pause();
      else if (voulue) v.play().catch(function () {});
    });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (ent) {
        if (!v || !voulue) return;
        if (ent[0].isIntersecting) v.play().catch(function () {}); else v.pause();
      }, { threshold: 0.25 }).observe(cadre);
    }
  }

  function demarrer() {
    if (window.requestIdleCallback) requestIdleCallback(poser, { timeout: 2000 });
    else setTimeout(poser, 800);
  }
  if (document.readyState === "complete") demarrer();
  else window.addEventListener("load", demarrer, { once: true });
})();
