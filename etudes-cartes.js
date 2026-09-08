/* ═══════════════════════════════════════════════════════════════════════════
 * ÉTUDES DE CAS — LA DÉRIVE, LE PIVOT, LA BASCULE DE VUE
 *
 * CE QUE CE SCRIPT NE FAIT PAS : il ne fabrique aucune fiche. Les neuf études
 * sont écrites dans la page, en clair, avec leur verso. Sans script, le
 * lecteur — et l'indexeur — les trouvent toutes ; il ne perd que la dérive et
 * le pivot. Un kaléidoscope qui vide la page quand le script tombe échangerait
 * le référencement contre un effet.
 *
 * LES COPIES NE SONT POSÉES QUE SI LA DÉRIVE EST BRANCHÉE. Le rail est doublé
 * pour boucler sans saut : sans les copies il glisserait jusqu'au vide, et avec
 * les copies mais sans dérive on lirait chaque fiche deux fois. Les deux vont
 * donc ensemble, et « prefers-reduced-motion » les retire toutes les deux — la
 * piste redevient alors une bande qu'on fait défiler à la main.
 *
 * LA VUE GRILLE NE CLONE RIEN. Elle rend les mêmes cartes, à plat : une classe
 * sur le conteneur suffit. Cloner aurait doublé le nombre de « .case » dans la
 * page, et toute règle qui les compte aurait compté faux.
 * ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  var kal = document.getElementById("kal");
  if (!kal) return;

  var calme = !!(window.matchMedia &&
                 window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  if (!calme) {
    Array.prototype.forEach.call(kal.querySelectorAll(".kal-rail"), function (rail) {
      Array.prototype.slice.call(rail.children).forEach(function (carte) {
        var copie = carte.cloneNode(true);
        /* La copie sort de l'ordre de tabulation et du nom accessible : sinon
           un lecteur d'écran annoncerait huit missions là où il y en a quatre. */
        copie.setAttribute("aria-hidden", "true");
        copie.setAttribute("tabindex", "-1");
        copie.setAttribute("data-copie", "1");
        copie.setAttribute("aria-pressed", "false");
        rail.appendChild(copie);
      });
    });
    kal.classList.add("derive");
  }

  /* ── LE PIVOT ─────────────────────────────────────────────────────────
     Une seule carte retournée à la fois : deux fiches ouvertes se lisent mal,
     et la dérive doit s'arrêter tant qu'on en lit une. */
  var ouverte = null;

  function fermer() {
    if (!ouverte) return;
    ouverte.setAttribute("aria-pressed", "false");
    ouverte = null;
    document.body.classList.remove("kal-fige");
  }

  document.addEventListener("click", function (e) {
    var cible = e.target;
    var carte = cible && cible.closest ? cible.closest("button.case") : null;
    if (!carte) { fermer(); return; }
    var etait = carte.getAttribute("aria-pressed") === "true";
    if (ouverte && ouverte !== carte) ouverte.setAttribute("aria-pressed", "false");
    carte.setAttribute("aria-pressed", etait ? "false" : "true");
    ouverte = etait ? null : carte;
    document.body.classList.toggle("kal-fige", !!ouverte);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && ouverte) {
      var revenir = ouverte;
      fermer();
      if (revenir.focus) revenir.focus();
    }
  });

  /* ── LA BASCULE DE VUE ────────────────────────────────────────────── */
  var bRails = document.getElementById("kal-v-rails");
  var bGrille = document.getElementById("kal-v-grille");

  function vue(grille) {
    kal.classList.toggle("grille", grille);
    if (grille) kal.classList.remove("derive");
    else if (!calme) kal.classList.add("derive");
    if (bRails) bRails.setAttribute("aria-pressed", String(!grille));
    if (bGrille) bGrille.setAttribute("aria-pressed", String(grille));
    if (window.requestAnimationFrame) window.requestAnimationFrame(marquerDefilement);
    else marquerDefilement();
  }

  if (bRails) bRails.addEventListener("click", function () { vue(false); });
  if (bGrille) bGrille.addEventListener("click", function () { vue(true); });

  /* ── LA MARQUE DE DÉFILEMENT ──────────────────────────────────────────
     Elle est MESURÉE, pas supposée : elle ne paraît que si la boîte de lecture
     déborde vraiment. Et elle prend la place du secteur — déjà lisible sur le
     recto — pour ne rien coûter en hauteur de lecture. Une carte masquée rend
     0 en hauteur : elle ne peut donc pas être marquée à tort, et chaque
     bascule de vue refait la mesure. */
  function marquerDefilement() {
    Array.prototype.forEach.call(document.querySelectorAll(".case-verso"), function (v) {
      var texte = v.querySelector(".v-texte");
      var etat = v.querySelector(".v-etat");
      if (!texte || !etat) return;
      if (etat.getAttribute("data-repos") === null) {
        etat.setAttribute("data-repos", etat.textContent);
      }
      etat.textContent = texte.scrollHeight > texte.clientHeight + 4
        ? "défiler ↓" : etat.getAttribute("data-repos");
    });
  }

  marquerDefilement();
  window.addEventListener("resize", function () {
    if (window.requestAnimationFrame) window.requestAnimationFrame(marquerDefilement);
    else marquerDefilement();
  });

  /* Exposé pour la recette et les règles, qui exécutent ce fichier sous node
     contre un DOM factice : sans point d'entrée nommé, elles ne pourraient
     que relire la source — et une règle qui relit la source ne mesure rien. */
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { vue: vue, fermer: fermer, marquerDefilement: marquerDefilement };
  }
})();
