/* Client Impact — la carte de l'étude de cas, peinte par le calcul.

   CE FICHIER NE PORTE AUCUN CHIFFRE, et c'est tout son intérêt. Les valeurs
   viennent de /api/impact-client, qui les fait calculer par le moteur de
   /datacenter. Un nombre recopié ici mentirait au premier réglage du moteur —
   une intensité de réseau mise à jour, un facteur incorporé révisé — et la
   carte continuerait de l'afficher avec l'assurance d'un chiffre.

   LA CARTE DIT DÉJÀ SA THÈSE SANS CE SCRIPT. Le HTML porte le texte ; ce
   script ajoute les chiffres. Si l'interface ne répond pas, le lecteur perd
   les nombres et garde le propos — jamais un bloc vide. */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* Les nombres se lisent à la française, et leur précision suit leur ordre de
     grandeur : des tonnes par an et un rapport sans unité ne se lisent pas
     avec la même précision.

     ET CE COMMENTAIRE NE CITE PLUS DE RÉSULTAT. Sa première version donnait un
     nombre en exemple — un vrai, sorti du calcul du jour. C'est exactement ce
     que la règle interdit ailleurs dans ce fichier : un résultat écrit dans le
     texte cesse d'être vrai au premier réglage du moteur, et un commentaire
     faux se recopie comme un commentaire juste. */
  /* LA RÈGLE D'OR PASSE PAR LE MODULE PARTAGÉ. `dec` reste accepté pour la
     décomposition, qui a besoin d'une précision CALCULÉE au serveur — mais il
     ne peut plus descendre sous le plancher, sans quoi le paramètre servirait
     à contourner la règle depuis n'importe quel appel. */
  function nb(v, dec) {
    if (typeof window !== "undefined" && window.CPNombres)
      return window.CPNombres.fr(v, dec);
    if (v == null || isNaN(v)) return "—";
    return new Intl.NumberFormat("fr-FR", {
      minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v);
  }
  function exact(v) {
    return (typeof window !== "undefined" && window.CPNombres)
      ? window.CPNombres.exact(v) : nb(v);
  }
  /* LE SIGNE « × » APPARTIENT À LA PHRASE, PAS AU NOMBRE. La première version
     le collait à chaque facteur ET le mettait entre eux : la décomposition
     s'affichait « 1,1 × × 15 × = 18 × ». Un nombre sait dire sa valeur ; c'est
     la phrase qui dit ce qu'on en fait.

     ET LA PRÉCISION SUIT L'ENJEU : « 15 » pour 15,49 perd un dixième sur le
     facteur qui porte tout l'écart. Une décimale jusqu'à cent. */
  /* LA PRÉCISION VIENT DU SERVEUR, ET C'EST TOUT LE POINT. Choisie ici, elle
     démentait le calcul : « 1,1 × 15,5 = 17,8 » affiché, et 1,1 × 15,5 fait
     17,05. Le lecteur qui vérifie concluait que la carte était fausse, sur la
     seule ligne dont l'intérêt est d'être vérifiable. Le module cherche la
     plus petite précision à laquelle l'arithmétique tombe juste ; la page
     l'applique. */
  function facteur(v, dec) {
    if (v == null || isNaN(v)) return "—";
    return nb(v, dec == null ? 2 : dec);
  }

  /* L'infobulle porte la formule, la source et l'incertitude que le moteur
     rend. Un chiffre sans elles se croit ou se rejette ; avec elles, il se
     discute. */
  function tip(t) {
    if (!t) return "";
    var l = [];
    if (t.formule) l.push("Formule : " + t.formule);
    if (t.source) l.push("Source : " + t.source);
    if (t.incertitude) l.push("Incertitude : " + t.incertitude);
    return l.length ? ' title="' + esc(l.join("\n")) + '"' : "";
  }

  function ligne(libelle, a, b, dec, unite) {
    return '<tr><th scope="row">' + esc(libelle) + "</th>"
      + "<td" + tip(a) + ">" + (a ? nb(a.valeur, dec) : "—")
      + (unite ? " <small>" + esc(unite) + "</small>" : "") + "</td>"
      + "<td" + tip(b) + ">" + (b ? nb(b.valeur, dec) : "—")
      + (unite ? " <small>" + esc(unite) + "</small>" : "") + "</td></tr>";
  }

  function rendre(e) {
    var z = document.getElementById("ci-calcul");
    if (!z) return;
    var A = null, B = null;
    e.configurations.forEach(function (c) {
      if (c.cle === "a") A = c;
      if (c.cle === "b") B = c;
    });
    if (!A || !B) return;
    var a = A.indicateurs, b = B.indicateurs;
    var d = e.decomposition;

    var h = '<div class="ci-serv"><b>Service rendu, identique des deux côtés</b> — '
      + e.service.map(function (i) {
          return esc(nb(i.valeur, i.unite === "part" ? 2 : 0)) + " "
            + esc(i.unite) + " <i>" + esc(i.nom.toLowerCase()) + "</i>";
        }).join(" · ") + "</div>";

    h += '<table class="ci-t"><caption class="sr-only">Comparaison des deux '
      + "configurations</caption><thead><tr><th scope=\"col\"></th>"
      + '<th scope="col">' + esc(A.pays_nom) + "<small>"
      + esc(A.refroidissement_nom) + "</small></th>"
      + '<th scope="col">' + esc(B.pays_nom) + "<small>"
      + esc(B.refroidissement_nom) + "</small></th></tr></thead><tbody>";
    h += ligne("PUE", a.pue, b.pue, 2, "");
    h += ligne("Énergie appelée", a.energie_totale_MWh, b.energie_totale_MWh, 0, "MWh/an");
    h += ligne("CO₂ d'exploitation (réseau réel)", a.co2_exploitation_localise_t,
               b.co2_exploitation_localise_t, 0, "t/an");
    h += ligne("Empreinte totale, matériel compris", a.empreinte_totale_t,
               b.empreinte_totale_t, 0, "t/an");
    h += ligne("Part du matériel dans cette empreinte", a.part_incorpore_pct,
               b.part_incorpore_pct, 0, "%");
    h += ligne("Eau consommée sur le site", a.appoint_m3, b.appoint_m3, 0, "m³/an");
    h += ligne("Eau consommée en amont, pour l'électricité", a.eau_amont_m3,
               b.eau_amont_m3, 0, "m³/an");
    h += ligne("Chaleur rendue à un usage extérieur", a.erf, b.erf, 0, "%");
    h += "</tbody></table>";

    /* LA DÉCOMPOSITION N'EST AFFICHÉE QUE SI ELLE TOMBE JUSTE. Le serveur
       vérifie l'identité à chaque appel ; si le moteur changeait au point de
       la rompre, l'afficher quand même présenterait comme une explication ce
       qui n'en serait plus une. */
    if (d && d.identite_verifiee && d.arithmetique_verifiable) {
      h += '<p class="ci-dec"><b>D\'où vient l\'écart</b> — '
        + d.facteurs.map(function (f) {
            /* Le libellé N'EST PAS minusculé : « rapport des pue » ne veut
               rien dire, et un acronyme abîmé décrédibilise le chiffre qu'il
               annonce. */
            return esc(f.libelle) + " <b>" + facteur(f.valeur, d.decimales)
              + "</b>";
          }).join(" &nbsp;×&nbsp; ")
        + " &nbsp;=&nbsp; <b>" + facteur(d.produit, d.decimales_produit)
        + " ×</b> sur l'exploitation. " + esc(d.lecture) + "</p>";
    } else if (d && d.identite_verifiee) {
      /* L'IDENTITÉ TIENT MAIS ELLE NE SE RELIT PAS. Afficher une
         multiplication que le lecteur ne peut pas refaire est pire que ne
         rien afficher : il conclut que le reste est faux aussi. On garde le
         propos, on retire l'arithmétique. */
      h += '<p class="ci-dec"><b>D\'où vient l\'écart</b> — ' + esc(d.lecture)
        + "</p>";
    } else if (d) {
      h += '<p class="ci-dec ci-mal">' + esc(d.reserve_si_fausse) + "</p>";
    }

    h += '<ul class="ci-ens">';
    e.enseignements.forEach(function (x) {
      h += "<li><b>" + esc(x.titre) + "</b> — " + esc(x.texte) + "</li>";
    });
    h += "</ul>";

    h += '<details class="ci-res"><summary>Ce que cette comparaison '
      + "n'établit pas (" + e.reserves.length + " réserves)</summary><ul>";
    e.reserves.forEach(function (r) { h += "<li>" + esc(r) + "</li>"; });
    h += "</ul></details>";

    h += '<p class="ci-nat">' + esc(e.nature) + "</p>";
    z.innerHTML = h;
  }

  function demarrer() {
    var ctrl = ("AbortController" in window) ? new AbortController() : null;
    var t = setTimeout(function () { if (ctrl) ctrl.abort(); }, 12000);
    fetch("/api/impact-client", ctrl ? { signal: ctrl.signal } : undefined)
      .then(function (r) { clearTimeout(t); return r.json(); })
      .then(function (j) { if (j && j.ok) rendre(j.etude); })
      .catch(function () { clearTimeout(t); /* le propos écrit reste */ });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }
})();
