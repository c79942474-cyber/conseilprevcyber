/* CONSEILPREV Cyber — en-tête responsive (menu « burger »).
   Chargé sur toutes les pages. Injecte un bouton de menu dans l'en-tête et
   gère l'ouverture/fermeture du panneau de navigation sur écran étroit.
   Aucune balise à ajouter aux pages : tout est construit ici. La feuille de
   style (styles.css) ne masque la navigation que si ce script s'est exécuté
   (classe .js-nav) — sans JavaScript, les liens restent visibles (repli). */
(function () {
  document.documentElement.classList.add("js-nav");

  function init() {
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
    // Fermer après un clic sur un lien du menu.
    links.addEventListener("click", function (e) {
      if (e.target.closest("a")) setOpen(false);
    });
    // Fermer si l'on clique en dehors de l'en-tête.
    document.addEventListener("click", function (e) {
      if (nav.classList.contains("open") && !nav.contains(e.target)) setOpen(false);
    });
    // Fermer avec la touche Échap.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" || e.key === "Esc") setOpen(false);
    });
    // Repasser en mode bureau referme proprement le panneau.
    var mq = window.matchMedia("(min-width: 861px)");
    var onChange = function () { if (mq.matches) setOpen(false); };
    if (mq.addEventListener) mq.addEventListener("change", onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();
})();
