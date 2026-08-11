/* LES MODULES NUMÉROTÉS — les séparer, et signaler ceux qu'on n'a pas parcourus.
 *
 * CE QUE CE MODULE FAIT
 *
 *   1. IL ENCADRE. Chaque section numérotée reçoit un cadre bleu et sa marge :
 *      dix modules qui se suivent sans séparation se lisent comme un seul long
 *      texte, et le lecteur perd le compte de ce qu'il a traité.
 *
 *   2. IL SIGNALE CE QUI N'A PAS ÉTÉ SOLLICITÉ. Un module non parcouru porte
 *      une pastille « à parcourir » et bat brièvement à l'approche.
 *
 * DEUX DÉCISIONS QUI FONT TOUTE LA DIFFÉRENCE, ET QUI NE SONT PAS DES DÉTAILS
 *
 *   · LE BATTEMENT EST BORNÉ, ET IL SE DÉCLENCHE À L'APPROCHE. Faire clignoter
 *     d'emblée les dix modules non parcourus d'une page ferait un sapin de
 *     Noël : un signal posé sur tout ne signale plus rien, et le lecteur
 *     apprend en trois secondes à ne plus le voir. Le battement se déclenche
 *     donc quand le module ENTRE À L'ÉCRAN, dure trois pulsations, et s'arrête.
 *     Le lecteur reçoit l'indication là où il regarde, jamais dix à la fois.
 *
 *   · LA PASTILLE SURVIT AU BATTEMENT, ET ELLE EST LA VRAIE INFORMATION. Un
 *     clignotement passé ne laisse aucune trace : qui détourne les yeux trois
 *     secondes ne saura plus quels modules restent à voir. La pastille, elle,
 *     reste jusqu'à ce que le module soit sollicité. C'est aussi ce qui rend le
 *     dispositif lisible sans percevoir le mouvement — un clignotement seul
 *     n'informe pas un lecteur qui ne le voit pas.
 *
 * MOUVEMENT RÉDUIT : AUCUN BATTEMENT. `prefers-reduced-motion` supprime toute
 * animation, et la pastille suffit. Un clignotement perpétuel est déconseillé
 * par les règles d'accessibilité, et il peut être franchement nocif — d'où sa
 * durée bornée, ici, même pour qui n'a rien demandé.
 *
 * CE QUE « SOLLICITÉ » VEUT DIRE, ET POURQUOI CE N'EST PAS LA MÊME CHOSE PARTOUT
 *
 *   · un module qui porte des commandes est sollicité quand on S'EN SERT —
 *     saisie, choix, clic à l'intérieur ;
 *   · un module purement rédactionnel est sollicité quand il a été LU, c'est-
 *     à-dire réellement resté à l'écran deux secondes. Exiger un clic sur un
 *     bloc qui n'en propose aucun serait une exigence qu'on ne peut pas
 *     satisfaire, et la pastille ne partirait jamais.
 *
 * L'état est gardé par page dans le navigateur : un lecteur qui revient ne se
 * fait pas resignaler ce qu'il a déjà traité.
 */
(function () {
  "use strict";

  var CLE = "cpc-modules:" + location.pathname;
  var PULSES = 3;              /* battements, puis on s'arrête */
  var LECTURE_MS = 2000;       /* « lu » = resté à l'écran deux secondes */

  function lire() {
    try { return JSON.parse(localStorage.getItem(CLE) || "{}") || {}; }
    catch (e) { return {}; }
  }
  function ecrire(v) {
    try { localStorage.setItem(CLE, JSON.stringify(v)); } catch (e) { /* privé */ }
  }

  var VUS = lire();

  function idDe(sec, i) {
    /* L'identité vient de l'ancre quand elle existe : elle survit à l'ajout
       d'une section, là où un rang « module 4 » désignerait le module suivant
       et effacerait par erreur la pastille du nouveau. */
    return sec.id || ("rang-" + i);
  }

  function marquer(sec, cle) {
    if (VUS[cle]) return;
    VUS[cle] = 1;
    ecrire(VUS);
    sec.classList.remove("mod-neuf", "mod-bat");
    var p = sec.querySelector(".mod-chip");
    if (p) p.remove();
  }

  function equiper() {
    var secs = [].slice.call(document.querySelectorAll(".rc-sec"))
      .filter(function (s) { return s.querySelector(".rc-etape"); });
    if (!secs.length) return;

    var reduit = window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    secs.forEach(function (sec, i) {
      sec.classList.add("mod-bloc");
      var cle = idDe(sec, i);
      sec.setAttribute("data-mod", cle);
      if (VUS[cle]) return;

      sec.classList.add("mod-neuf");
      /* LA PASTILLE PORTE L'INFORMATION, le battement ne fait que la désigner.
         Posée dans l'en-tête plutôt qu'en surimpression : elle doit se lire au
         même endroit que le numéro qu'elle qualifie. */
      var tete = sec.querySelector(".rc-etape");
      if (tete && !tete.querySelector(".mod-chip")) {
        var chip = document.createElement("span");
        chip.className = "mod-chip";
        chip.textContent = "à parcourir";
        chip.setAttribute("title", "Ce module n’a pas encore été sollicité.");
        tete.appendChild(chip);
      }

      /* SOLLICITÉ PAR L'USAGE — pour les modules qui portent des commandes. */
      ["input", "change", "click"].forEach(function (ev) {
        sec.addEventListener(ev, function () { marquer(sec, cle); },
                             { passive: true });
      });
    });

    /* SOLLICITÉ PAR LA LECTURE, et battement à l'approche.
       Sans IntersectionObserver — navigateurs anciens —, on renonce au
       battement et on marque tout comme parcouru au premier défilement : mieux
       vaut pas de signal qu'un signal qui ne s'éteint jamais. */
    if (!("IntersectionObserver" in window)) {
      secs.forEach(function (sec, i) { marquer(sec, idDe(sec, i)); });
      return;
    }

    var minuteurs = {};
    var obs = new IntersectionObserver(function (entrees) {
      entrees.forEach(function (e) {
        var sec = e.target;
        var cle = sec.getAttribute("data-mod");
        if (VUS[cle]) { obs.unobserve(sec); return; }

        if (!e.isIntersecting) {
          clearTimeout(minuteurs[cle]);
          return;
        }
        /* LE BATTEMENT, UNE FOIS, À L'ENTRÉE À L'ÉCRAN. Il se déclenche par une
           classe que le CSS anime un nombre FINI de fois : rien à arrêter, et
           rien qui continue si le lecteur s'attarde. */
        if (!reduit && !sec.classList.contains("mod-bat")) {
          sec.classList.add("mod-bat");
        }
        /* Deux secondes à l'écran valent lecture. Un défilement rapide qui
           traverse la page ne doit pas éteindre dix pastilles au passage. */
        clearTimeout(minuteurs[cle]);
        minuteurs[cle] = setTimeout(function () {
          marquer(sec, cle);
          obs.unobserve(sec);
        }, LECTURE_MS);
      });
    }, { threshold: 0.35 });

    secs.forEach(function (sec) {
      if (!VUS[sec.getAttribute("data-mod")]) obs.observe(sec);
    });
  }

  /* Exposé pour la recette et pour un éventuel bouton de remise à zéro : un
     consultant qui présente la page à un client veut pouvoir la réarmer. */
  window.MODULES = {
    reset: function () { VUS = {}; ecrire(VUS); },
    vus: function () { return Object.keys(VUS); },
    PULSES: PULSES,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", equiper);
  } else { equiper(); }
})();
