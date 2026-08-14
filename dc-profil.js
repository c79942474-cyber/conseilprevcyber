/* Le profil d'installation, porté d'une page à l'autre.

   POURQUOI. /datacenter et /ingenierie-datacenter construisent le MÊME
   formulaire, depuis le même référentiel (datacenter.CHAMPS), avec les mêmes
   attributs data-champ. Seul le conteneur diffère. Jusqu'ici, rien ne circulait
   entre les deux : un lecteur qui avait chiffré son installation sur la page
   bas carbone devait ressaisir treize champs pour savoir à quelle phase le
   résultat devient recevable. C'est la ressaisie qui décourage, pas le calcul.

   CE QU'ON TRANSPORTE, ET SEULEMENT CELA. Des VALEURS de champs, jamais un
   indicateur « ce champ a été rempli ». La distinction n'est pas théorique :
   côté serveur, un champ vaut SAISI ou DEFAUT selon qu'il s'écarte ou non de sa
   valeur par défaut déclarée, et c'est ce verdict qui décide du franchissement
   d'une phase. Transporter un drapeau « rempli » ferait franchir des phases sur
   des valeurs que personne n'a choisies. En transportant les valeurs brutes, la
   règle du serveur s'applique à l'identique des deux côtés — un champ resté par
   défaut sur la première page reste par défaut sur la seconde.

   CE QU'ON NE TRANSPORTE PAS. Le nom du client et les choix d'identification :
   ils servent à la rédaction, pas au calcul, et n'ont rien à faire dans un
   magasin de navigateur. sessionStorage et non localStorage : un profil est une
   session de travail, pas une préférence. Fermer l'onglet l'efface.

   Autonome, sans dépendance, chargé par les deux pages. Écrit une fois : deux
   copies de cette logique divergeraient au premier champ ajouté. */
(function () {
  "use strict";

  var CLE = "cp_profil_dc";
  /* Les seules clés admises. Une liste blanche plutôt qu'un « tout ce qui
     traîne » : le magasin est lu par une page qui va s'en servir pour calculer,
     et une clé inattendue y entrerait sans que rien ne la contrôle. Elle suit
     datacenter.CHAMPS ; le contrôle de santé vérifie qu'elle ne s'en écarte
     pas. */
  var CHAMPS = [
    "puissance_it_kw", "taux_charge", "pays", "refroidissement",
    "classe_ashrae", "part_evaporative", "cycles_concentration",
    "part_renouvelable", "part_chaleur_reutilisee", "pue_cible",
    "intensite_reseau_g", "nb_serveurs", "prix_electricite_eur_mwh"
  ];

  function dispo() {
    try {
      window.sessionStorage.setItem("__t", "1");
      window.sessionStorage.removeItem("__t");
      return true;
    } catch (e) { return false; }
  }

  /* Enregistre le profil courant. `origine` dit d'où il vient : la page qui le
     relira doit pouvoir le nommer, sinon elle affiche un formulaire rempli sans
     que le lecteur sache pourquoi — ce qui inquiète plus que ça n'aide. */
  function enregistrer(profil, origine) {
    if (!dispo() || !profil) return false;
    var net = {};
    CHAMPS.forEach(function (k) {
      var v = profil[k];
      if (v !== undefined && v !== null && String(v).trim() !== "") {
        net[k] = String(v).trim();
      }
    });
    if (!net.puissance_it_kw) return false;   // sans elle, rien n'est calculable
    try {
      window.sessionStorage.setItem(CLE, JSON.stringify({
        champs: net,
        origine: origine || "",
        /* L'heure sert à l'afficher (« chiffré il y a un instant »), pas à
           expirer : une session de navigateur est déjà la bonne durée. */
        quand: Date.now()
      }));
      /* LE MAGASIN ANNONCE SES ÉCRITURES. Le profil s'enregistre au retour du
         calcul, dans un `then` : aucun événement d'interface ne se produit à
         cet instant. Ce qui regarde ce magasin — le bandeau des trois piliers
         — restait donc périmé jusqu'à la frappe suivante, et affichait « rien
         à emporter » sur une page qui venait d'en produire. Un magasin muet
         oblige ses lecteurs à deviner quand relire. */
      try {
        document.dispatchEvent(new CustomEvent("profil-dc:ecrit",
          { detail: { origine: origine || "" } }));
      } catch (e) { /* navigateur sans CustomEvent : le bandeau se remettra
                       à jour au prochain `change`, ce qui reste correct. */ }
      return true;
    } catch (e) { return false; }
  }

  function lire() {
    if (!dispo()) return null;
    var brut;
    try { brut = window.sessionStorage.getItem(CLE); } catch (e) { return null; }
    if (!brut) return null;
    var o;
    try { o = JSON.parse(brut); } catch (e) { return null; }
    if (!o || !o.champs || !o.champs.puissance_it_kw) return null;
    // Filtrage à la relecture aussi : le magasin peut avoir été écrit par une
    // version antérieure, ou à la main par un curieux.
    var net = {};
    CHAMPS.forEach(function (k) {
      if (o.champs[k] !== undefined) net[k] = String(o.champs[k]);
    });
    return { champs: net, origine: o.origine || "", quand: o.quand || 0 };
  }

  function oublier() {
    try { window.sessionStorage.removeItem(CLE); } catch (e) {}
  }

  /* Applique un profil à un formulaire, et renvoie les champs RÉELLEMENT posés.
     Un champ du magasin qui n'existe plus dans le formulaire est ignoré
     silencieusement — mais il ne compte pas comme appliqué, sinon la page
     annoncerait avoir repris des valeurs qu'elle n'a pas reprises. */
  function appliquer(selecteurFormulaire, champs) {
    var poses = [];
    Object.keys(champs || {}).forEach(function (k) {
      var el = document.querySelector(
        selecteurFormulaire + ' [data-champ="' + k + '"]');
      if (!el) return;
      if (el.tagName === "SELECT") {
        var ok = false;
        for (var i = 0; i < el.options.length; i++) {
          if (el.options[i].value === champs[k]) { ok = true; break; }
        }
        if (!ok) return;      // option disparue du référentiel : on n'invente pas
      }
      el.value = champs[k];
      poses.push(k);
    });
    if (poses.length) {
      var f = document.querySelector(selecteurFormulaire);
      if (f) {
        f.dispatchEvent(new Event("input", { bubbles: true }));
        f.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }
    return poses;
  }

  window.ProfilDC = {
    enregistrer: enregistrer, lire: lire, oublier: oublier,
    appliquer: appliquer, CHAMPS: CHAMPS, disponible: dispo
  };
})();
