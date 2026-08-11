/* TRANSMETTRE — le choix du destinataire, partagé par les trois pages.
 *
 * CE QUE CE MODULE RÉSOUT, ET CE N'EST PAS LE TÉLÉCHARGEMENT. Les documents
 * s'exportaient déjà en Word et en PDF. Mais un fichier part SEUL : la page
 * disait la phase, la tolérance et ce qui restait à produire ; le fichier, non.
 * Aux achats, une enveloppe d'avant-projet devient un budget ; à
 * l'exploitation, une valeur de conception devient une consigne. Personne n'a
 * menti — le contexte est resté sur le site.
 *
 * Le client choisit ici la FONCTION qui recevra le document. Le serveur pose
 * alors, en première page, un bordereau qui dit ce que le document est, ce
 * qu'il n'est pas, et ce que cette fonction-là doit savoir avant de le lire.
 *
 * UN SEUL MODULE POUR TROIS PAGES. Recopié trois fois, le vocabulaire aurait
 * divergé au premier ajout, et c'est la copie de la page que le client aurait
 * vue. Le vocabulaire lui-même vient du serveur, jamais du balisage.
 *
 * RIEN DE NOMINATIF. Le sélecteur ne propose que des fonctions et n'accepte
 * aucune saisie libre : un nom entré ici ferait entrer le document au registre
 * des traitements, et personne ne l'aurait décidé.
 *
 * SANS CHOIX, RIEN NE CHANGE. « Pour moi » est la valeur par défaut, et
 * l'export part alors exactement comme avant — pas de bordereau, pas de
 * destinataire au cartouche.
 */
(function () {
  "use strict";

  var VOCAB = null;          // { destinataires, exclus } — chargé une fois
  var ATTENTE = null;        // la promesse en cours, pour ne pas charger deux fois

  function esc(x) {
    return String(x === null || x === undefined ? "" : x)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function charger() {
    if (VOCAB) return Promise.resolve(VOCAB);
    if (ATTENTE) return ATTENTE;
    ATTENTE = fetch("/api/transmission")
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) throw new Error("vocabulaire indisponible");
        VOCAB = j;
        return j;
      });
    return ATTENTE;
  }

  /* Le bloc, posé dans une zone que la page fournit.
   *
   * SI LE VOCABULAIRE N'ARRIVE PAS, LE BLOC NE S'AFFICHE PAS — et l'export
   * continue de fonctionner sans bordereau. Un sélecteur vide laisserait croire
   * qu'aucune fonction n'est disponible ; l'absence, elle, ne promet rien. */
  function bloc(zone) {
    var z = typeof zone === "string" ? document.querySelector(zone) : zone;
    if (!z || z.getAttribute("data-tr-pret")) return Promise.resolve(null);
    return charger().then(function (v) {
      var h = '<div class="tr-bloc">'
        + '<label class="tr-lab" for="tr-dest">Transmettre à</label>'
        + '<select id="tr-dest" data-tr-dest>'
        + '<option value="">— pour moi : aucun bordereau —</option>'
        + (v.destinataires || []).map(function (d) {
            return '<option value="' + esc(d.cle) + '">' + esc(d.nom) + "</option>";
          }).join("")
        + "</select>"
        + '<p class="tr-aide" id="tr-aide">Choisissez la fonction qui recevra le '
        + 'document : il partira avec un <b>bordereau de transmission</b> disant '
        + 'ce qu’il est, ce qu’il n’est pas, et ce que cette fonction doit savoir '
        + 'avant de le lire. Le fichier reste à vous — rien n’est envoyé d’ici.</p>'
        + '<p class="tr-mise" id="tr-mise" hidden></p>'
        + "</div>";
      z.insertAdjacentHTML("beforeend", h);
      z.setAttribute("data-tr-pret", "1");
      var sel = z.querySelector("[data-tr-dest]");
      sel.addEventListener("change", function () { montrer(z, sel.value); });
      return v;
    }).catch(function () { return null; });
  }

  /* LA MISE EN GARDE S'AFFICHE AVANT L'EXPORT, PAS SEULEMENT DANS LE FICHIER.
     C'est l'émetteur qui doit la lire en premier : s'il découvre au moment de
     choisir « Achats » que ces valeurs ne se négocient pas, il peut encore
     décider de ne pas transmettre. Dans le fichier seul, il l'aurait apprise
     après l'envoi. */
  function montrer(z, cle) {
    var box = z.querySelector("#tr-mise");
    if (!box) return;
    var d = ((VOCAB || {}).destinataires || []).filter(function (x) {
      return x.cle === cle;
    })[0];
    if (!d) { box.hidden = true; box.innerHTML = ""; return; }
    box.hidden = false;
    box.innerHTML = "<b>Ce que " + esc(d.nom) + " lira en tête du document.</b> "
      + esc(d.avant) + " <i>" + esc(d.pas) + "</i>";
  }

  /* La clé choisie, ou une chaîne vide. Lue au moment du clic et jamais
     mémorisée : un destinataire retenu d'un export à l'autre finirait par
     poser le bordereau d'une fonction que le client ne regarde plus. */
  function valeur() {
    var s = document.querySelector("[data-tr-dest]");
    return s && s.value ? s.value : "";
  }

  /* Le corps d'un export, enrichi du destinataire s'il y en a un. Les pages
     appellent ceci plutôt que d'ajouter le champ chacune de leur côté : un
     champ oublié sur une page produirait un document sans bordereau alors que
     le client vient d'en choisir un, et rien ne le lui dirait. */
  function corps(o) {
    var d = valeur();
    var out = o || {};
    if (d) out.destinataire = d;
    return out;
  }

  window.TRANSMETTRE = { bloc: bloc, valeur: valeur, corps: corps,
                         charger: charger };

  /* MONTÉ TOUT SEUL, dans chaque « .tr-zone » que la page déclare.
     Les scripts de page et celui-ci sont tous chargés en « defer » : leur ordre
     d'exécution n'est garanti que par l'ordre des balises, et une page qui
     appellerait le montage depuis son propre script dépendrait de cet ordre —
     une balise déplacée un jour ferait disparaître le sélecteur sans que rien
     ne le signale. Ici, c'est le balisage qui décide où le bloc apparaît, et
     lui seul. */
  function monter() {
    var zones = document.querySelectorAll(".tr-zone");
    for (var i = 0; i < zones.length; i++) bloc(zones[i]);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", monter);
  } else { monter(); }
})();
