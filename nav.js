/* CONSEILPREV Cyber — en-tête responsive + navigation de page.
   Chargé sur toutes les pages. Injecte (1) un bouton de menu « burger » dans
   l'en-tête sur écran étroit, et (2) un petit bloc de flèches flottant :
   précédent / suivant (historique) et haut / bas (défilement).
   Aucune balise à ajouter aux pages : tout est construit ici. */
(function () {
  document.documentElement.classList.add("js-nav");

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

  function initPageNav() {
    if (document.querySelector(".pagenav")) return;
    var box = document.createElement("div");
    box.className = "pagenav";
    box.setAttribute("role", "group");
    box.setAttribute("aria-label", "Navigation de page");
    // [clé, glyphe, libellé accessible, infobulle]
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
          window.scrollTo({
            top: document.documentElement.scrollHeight,
            behavior: behavior,
          });
          break;
      }
    });
  }

  function init() {
    initBurger();
    initPageNav();
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();
})();
