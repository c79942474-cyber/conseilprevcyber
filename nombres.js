/* LA RÈGLE D'OR DU SITE : on n'arrondit pas en dessous de deux décimales, et
   la valeur exacte reste accessible.

   CE QUI SE PASSAIT AVANT, ET QUI SE VOYAIT. Quatre copies quasi identiques de
   `fr()` vivaient dans quatre scripts, toutes avec le même barème : zéro
   décimale au-dessus de cent, une entre dix et cent, trois en dessous. Sur les
   valeurs réelles du moteur, cela donnait :

       5 857,4178 tCO2e/an   affiché « 5 857 »
      12 691,884  m³/an      affiché « 12 692 »
          13,9806 %          affiché « 14,0 »
           1,1489            affiché « 1,1 »

   La dernière ligne a coûté une carte publique : la décomposition affichait
   « 1,1 × 15,5 = 17,8 », et 1,1 × 15,5 fait 17,05. Un lecteur qui vérifie
   conclut que le calcul est faux — sur la seule ligne dont l'intérêt est
   d'être vérifiable.

   POURQUOI UN ENTIER RESTE UN ENTIER. « 3 000,00 serveurs » n'est pas plus
   exact que « 3 000 » : c'est la même valeur, écrite plus mal. La règle
   interdit d'ARRONDIR sous deux décimales ; elle n'oblige pas à inventer des
   décimales sur un nombre qui n'en a pas. Un entier n'est pas arrondi, il est
   exact — et c'est le test qui distingue les deux.

   POURQUOI DEUX DÉCIMALES ET PAS DAVANTAGE À L'ÉCRAN. Un tableau de
   comparaison à six décimales ne se lit plus, et une ligne illisible n'est pas
   relue. Deux décimales à l'affichage, LA VALEUR EXACTE DANS L'INFOBULLE :
   c'est la seule combinaison qui tienne les deux moitiés de la règle.

   CE FICHIER EST CHARGÉ AVANT LES SCRIPTS DE PAGE. Chaque page garde son
   `fr()` local, qui délègue ici : les centaines d'appels existants n'ont pas
   changé, et il n'y a plus qu'un seul endroit où le barème est décidé. */
(function (global) {
  "use strict";

  var PLANCHER = 2;          // jamais moins de deux décimales sur un décimal

  function estEntier(x) {
    return isFinite(x) && Math.floor(x) === x;
  }

  /* Le nombre tel qu'on l'AFFICHE. `dec` force une précision plus fine ; il ne
     peut pas descendre sous le plancher, sans quoi le paramètre servirait à
     contourner la règle depuis n'importe quel appel. */
  function fr(n, dec) {
    if (n === null || n === undefined || n === "") return "—";
    var x = Number(n);
    if (!isFinite(x)) return String(n);
    var d = estEntier(x) ? 0 : Math.max(PLANCHER, dec == null ? PLANCHER : dec);
    return new Intl.NumberFormat("fr-FR", {
      minimumFractionDigits: d, maximumFractionDigits: d,
    }).format(x);
  }

  /* Le nombre tel qu'il EST. Sert l'infobulle et l'attribut de vérification :
     l'affichage est arrondi, celui-ci ne l'est pas. `toPrecision` évite
     d'exposer les bavures du binaire — 0,1 + 0,2 ne doit pas se lire
     « 0,30000000000000004 », qui ferait douter d'un calcul juste. */
  function exact(n) {
    if (n === null || n === undefined || n === "") return "—";
    var x = Number(n);
    if (!isFinite(x)) return String(n);
    if (estEntier(x)) return fr(x);
    var s = parseFloat(x.toPrecision(12)).toString();
    var p = s.split(".");
    /* AU MOINS DEUX DÉCIMALES, comme l'affichage : « 6 832,8 » à côté de
       « 6 832,80 » est la même valeur écrite de deux façons. */
    if (p[1] && p[1].length < 2) p[1] = (p[1] + "00").slice(0, 2);
    var e = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 })
      .format(Math.trunc(Math.abs(x)));
    return (x < 0 ? "-" : "") + e + (p[1] ? "," + p[1] : "");
  }

  /* Une somme d'argent. Les centimes ne se suppriment pas : un montant au
     centime près est une valeur exacte, et la masquer est un arrondi. */
  function euro(n) {
    if (n === null || n === undefined || n === "") return "—";
    var x = Number(n);
    if (!isFinite(x)) return String(n);
    return new Intl.NumberFormat("fr-FR", {
      style: "currency", currency: "EUR",
      minimumFractionDigits: estEntier(x) ? 0 : PLANCHER,
      maximumFractionDigits: estEntier(x) ? 0 : PLANCHER,
    }).format(x);
  }

  /* Un pourcentage. Même règle : la part exacte est dans l'infobulle. */
  function pct(n, dec) {
    if (n === null || n === undefined || n === "") return "—";
    return fr(n, dec) + " %";
  }

  global.CPNombres = {
    fr: fr, exact: exact, euro: euro, pct: pct,
    estEntier: estEntier, PLANCHER: PLANCHER,
  };
})(typeof window !== "undefined" ? window : this);

if (typeof module !== "undefined" && module.exports) {
  module.exports = (typeof window !== "undefined" ? window : this).CPNombres;
}
