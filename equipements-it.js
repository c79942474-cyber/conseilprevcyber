/* Les équipements informatiques d'un centre de données — affichage.
   ────────────────────────────────────────────────────────────────
   Ce fichier ne calcule RIEN. Chaque quantité, chaque prix, chaque kilo de
   CO2 vient de `equipements_it.py`, module PARTAGÉ À L'IDENTIQUE avec
   Sentinel. Recalculer ici « pour aller plus vite » ferait exister deux
   nomenclatures pour un même projet — et l'écart se découvrirait en comité,
   quand l'enveloppe d'investissement et l'empreinte carbone ne diraient plus
   le même nombre de baies.

   Le parti pris d'affichage : la RÈGLE de quantité de chaque poste est
   visible sans clic. Un tableau de quantités nues se recopie dans un budget
   sans que personne ne sache d'où sortent les 168 commutateurs. */
(function () {
  "use strict";

  var REF = null, NOMEN = null;
  var DELAI = 20000;         // dimensionnement : calcul réel côté serveur
  var DELAI_COURT = 12000;   // chargement des listes : conditionne l'affichage

  function $(s, r) { return (r || document).querySelector(s); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fr(n, dec) {
    if (n === null || n === undefined || n === "") return "—";
    var x = Number(n);
    if (!isFinite(x)) return String(n);
    var d = (dec === undefined)
      ? (Math.abs(x) >= 100 ? 0 : (Math.abs(x) >= 10 ? 1 : 2)) : dec;
    return x.toFixed(d).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }
  function eur(n) {
    var x = Number(n);
    if (!isFinite(x)) return "—";
    if (Math.abs(x) >= 1e6) return fr(x / 1e6, 2) + " M€";
    if (Math.abs(x) >= 1e3) return fr(x / 1e3, 0) + " k€";
    return fr(x, 0) + " €";
  }

  /* Une requête sans délai attend indéfiniment : la page reste sur « Calcul
     en cours… » sans un mot. Bornée, elle rend la main et l'explique.

     DÉFAUT CORRIGÉ. Cette mécanique — ctrl, fini, clearTimeout — n'était
     câblée que pour poster(), en POST. Les deux GET qui remplissent les
     listes déroulantes (remplirListes(), remplirPays()) appelaient fetch()
     nu, sans délai : sur un serveur lent, #eq-densite et #eq-perimetre
     restaient des listes VIDES, #eq-go restait cliquable, et les deux
     traitements d'échec existants ne pouvaient jamais se déclencher — une
     requête suspendue ne rejette pas. demander() généralise poster() aux
     deux méthodes ; poster() n'est plus qu'un appel à demander(). */
  function demander(url, options, delai) {
    options = options || {};
    var ctrl = (typeof AbortController !== "undefined") ? new AbortController() : null;
    var fini = false;
    var t = setTimeout(function () {
      if (!fini && ctrl) ctrl.abort();
    }, delai || DELAI);
    if (ctrl && !options.signal) options.signal = ctrl.signal;
    return fetch(url, options).then(function (r) {
      fini = true; clearTimeout(t);
      return r.json().then(function (j) { return { ok: r.ok, statut: r.status, j: j }; });
    }, function (e) {
      fini = true; clearTimeout(t);
      throw e;
    });
  }

  function poster(url, corps) {
    return demander(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps),
    });
  }

  function message(res) {
    if (res.statut === 401) return "Connectez-vous pour utiliser le moteur d'ingénierie.";
    return (res.j && res.j.message) || "Le dimensionnement a échoué.";
  }

  /* ── Les listes déroulantes, remplies depuis le serveur ──────────────────
     Recopier les densités et les périmètres dans le HTML les ferait diverger
     du moteur au premier ajustement — et c'est la liste affichée que le
     lecteur croit. */
  function remplirListes() {
    return demander("/api/datacenter/equipements/referentiel",
                    { credentials: "same-origin" }, DELAI_COURT)
      .then(function (res) {
        if (!res.ok || !res.j || !res.j.ok) throw new Error("referentiel");
        REF = res.j.referentiel;

        var sd = $("#eq-densite");
        if (sd) {
          sd.innerHTML = Object.keys(REF.densites).map(function (k) {
            var d = REF.densites[k];
            return '<option value="' + esc(k) + '"'
              + (k === REF.densite_defaut ? " selected" : "") + ">"
              + esc(d.nom) + " — " + fr(d.kw_baie, 0) + " kW/baie</option>";
          }).join("");
        }
        var sp = $("#eq-perimetre");
        if (sp) {
          sp.innerHTML = Object.keys(REF.perimetres).map(function (k) {
            return '<option value="' + esc(k) + '"'
              + (k === "propre" ? " selected" : "") + ">"
              + esc(REF.perimetres[k].nom) + "</option>";
          }).join("");
        }
        return REF;
      });
  }

  /* Le pays vient du référentiel du MOTEUR, avec son intensité affichée : le
     résultat de la bascule en dépend entièrement, et le lecteur doit voir le
     chiffre qui commande sa conclusion avant de cliquer. */
  function remplirPays() {
    var sel = $("#eq-pays");
    if (!sel) return Promise.resolve();
    return demander("/api/datacenter/referentiel",
                    { credentials: "same-origin" }, DELAI_COURT)
      .then(function (res) {
        var R = res.j && res.j.referentiel;
        if (!R || !R.intensite_reseau) return;
        var noms = R.ewif || {};
        var codes = Object.keys(R.intensite_reseau).sort(function (a, b) {
          var na = (noms[a] && noms[a].nom) || a, nb = (noms[b] && noms[b].nom) || b;
          return na.localeCompare(nb, "fr");
        });
        sel.innerHTML = codes.map(function (c) {
          var nom = (noms[c] && noms[c].nom) || c;
          return '<option value="' + esc(c) + '"' + (c === "FR" ? " selected" : "")
            + ">" + esc(nom) + " — " + fr(R.intensite_reseau[c], 0) + " g/kWh</option>";
        }).join("");
      })
      .catch(function () { /* la section reste utilisable sans la bascule */ });
  }

  /* ── La nomenclature ────────────────────────────────────────────────────
     Chaque ligne porte sa RÈGLE et son geste d'achat durable. Les masquer
     derrière un clic ferait recopier les quantités sans leur justification :
     c'est exactement ce qui rend un tableur d'équipements indéfendable. */
  function tableau(n) {
    var h = '<div class="eq-tab-w"><table class="eq-tab">'
      + "<caption>Nomenclature pour " + fr(n.puissance_it_kw, 0)
      + " kW informatiques — " + esc(n.densite_nom) + ", "
      + fr(n.kw_par_baie, 0) + " kW/baie, " + fr(n.baies, 0) + " baies</caption>"
      + "<thead><tr><th scope=\"col\">Poste</th><th scope=\"col\">Règle de quantité</th>"
      + "<th scope=\"col\" class=\"r\">Quantité</th>"
      + "<th scope=\"col\" class=\"r\">Prix indicatif</th>"
      + "<th scope=\"col\" class=\"r\">Carbone fabrication</th>"
      + "<th scope=\"col\" class=\"r\">Durée de vie</th></tr></thead><tbody>";
    n.lignes.forEach(function (l) {
      h += '<tr class="' + (l.indispensable ? "eq-ind" : "eq-utile") + '">'
        + "<th scope=\"row\">" + esc(l.nom)
        + '<span class="eq-badge">'
        + (l.indispensable ? "indispensable" : "utile")
        + "</span></th>"
        + "<td>" + esc(l.regle) + "</td>"
        + '<td class="r">' + fr(l.quantite, 0) + " " + esc(l.unite) + "</td>"
        + '<td class="r">' + eur(l.prix_total_eur) + "</td>"
        + '<td class="r">' + fr(l.carbone_total_kg / 1000, 1) + " t</td>"
        + '<td class="r">' + fr(l.duree_vie_ans, 0) + " ans</td></tr>";
    });
    h += "</tbody><tfoot><tr><th scope=\"row\" colspan=\"3\">Total</th>"
      + '<td class="r"><b>' + eur(n.total_eur) + "</b></td>"
      + '<td class="r"><b>' + fr(n.carbone_total_t, 0) + " t</b></td>"
      + '<td class="r">' + fr(n.carbone_annualise_t, 0) + " t/an</td></tr>"
      + "</tfoot></table></div>";
    return h;
  }

  function gestesDurables(n) {
    var h = '<details class="dc-det"><summary>Les gestes d\'achat durable, poste '
      + "par poste — à écrire au marché, pas à espérer</summary>"
      + '<div class="dc-det-c"><dl class="eq-dl">';
    n.lignes.forEach(function (l) {
      h += "<dt>" + esc(l.nom) + "</dt><dd>" + esc(l.achat_durable)
        + ' <span class="eq-pq">' + esc(l.pourquoi) + "</span></dd>";
    });
    return h + "</dl></div></details>";
  }

  function bandeauPart(p) {
    if (!p || !p.ok) return '<p class="note">' + esc((p && p.motif) || "") + "</p>";
    var h = '<div class="eq-part">'
      + '<div class="eq-part-t">La place de l\'informatique dans l\'investissement</div>'
      + '<div class="eq-chiffres">'
      + '<div class="eq-c"><span class="v">' + eur(p.it_eur) + "</span>"
      + '<span class="l">Équipements informatiques</span></div>'
      + '<div class="eq-c"><span class="v">' + fr(p.part_lots_pct, 0)
      + ' %</span><span class="l">Part dans les lots travaux</span></div>';
    if (p.part_total_pct !== null && p.part_total_pct !== undefined) {
      h += '<div class="eq-c eq-c-fort"><span class="v">' + fr(p.part_total_pct, 1)
        + ' %</span><span class="l">Part de l\'investissement total</span></div>';
    }
    if (p.rapport_it_travaux !== null && p.rapport_it_travaux !== undefined) {
      h += '<div class="eq-c"><span class="v">×' + fr(p.rapport_it_travaux, 2)
        + '</span><span class="l">Rapport informatique / travaux</span></div>';
    }
    h += "</div>"
      + "<p>" + esc(p.lecture) + "</p>"
      + '<p class="note"><b>Pourquoi zéro dans les lots.</b> ' + esc(p.lots_dit) + "</p>"
      + '<p class="note"><b>' + esc(p.perimetre_nom) + ".</b> " + esc(p.dit)
      + " <i>Qui porte l'informatique&nbsp;: " + esc(p.porteur_it) + ".</i></p>"
      + "</div>";
    return h;
  }

  /* ── La bascule de la durée de vie ──────────────────────────────────────
     Le verdict est affiché AVEC son seuil : « favorable » sans dire à partir
     de quelle intensité carbone cela cesse de l'être serait de la plaquette,
     et se retournerait contre le dossier au premier site polonais. */
  function bandeauVie(v) {
    if (!v) return "";
    if (!v.ok) {
      return '<div class="eq-vie eq-refus"><b>Le calcul refuse&nbsp;: </b>'
        + esc(v.motif) + "</div>";
    }
    var fav = v.verdict === "favorable";
    var h = '<div class="eq-vie ' + (fav ? "eq-fav" : "eq-def") + '">'
      + '<div class="eq-verdict">' + (fav ? "▲ Favorable" : "▼ Défavorable")
      + " — allonger de " + fr(v.duree_base, 0) + " à " + fr(v.duree_cible, 0)
      + " ans</div>"
      + '<div class="eq-chiffres">'
      + '<div class="eq-c"><span class="v">' + fr(v.gain_fabrication_kg_an / 1000, 1)
      + ' t/an</span><span class="l">Fabrication évitée (scope 3)</span></div>'
      + '<div class="eq-c"><span class="v">' + fr(v.cout_exploitation_kg_an / 1000, 1)
      + ' t/an</span><span class="l">Surconsommation (scope 2)</span></div>'
      + '<div class="eq-c eq-c-fort"><span class="v">'
      + (v.net_t_an >= 0 ? "−" : "+") + fr(Math.abs(v.net_t_an), 1)
      + ' t/an</span><span class="l">Bilan net</span></div>'
      + '<div class="eq-c"><span class="v">' + fr(v.intensite_bascule_g, 0)
      + ' g/kWh</span><span class="l">Intensité de bascule</span></div>'
      + "</div>"
      + "<p>" + esc(v.lecture) + "</p>"
      + '<details class="dc-det"><summary>Le modèle, ses formules et sa réserve</summary>'
      + '<div class="dc-det-c"><p>' + esc(v.modele) + "</p>"
      + "<ul class=\"eq-formules\">"
      + v.formules.map(function (f) { return "<li>" + esc(f) + "</li>"; }).join("")
      + "</ul>"
      + "<p><b>Dérive d'efficacité retenue&nbsp;: " + fr(v.derive_an * 100, 1)
      + " %/an.</b> " + esc(v.derive_source) + "</p>"
      + '<p class="eq-reserve"><b>Ce que ce bilan ne dit pas.</b> '
      + esc(v.reserve) + "</p></div></details>"
      + "</div>";
    return h;
  }

  function bandeauScope3(s) {
    if (!s || !s.ok) return "";
    var h = '<div class="eq-s3">'
      + '<div class="eq-part-t">Le scope 3 du GHG Protocol — la troisième composante</div>'
      + '<div class="eq-chiffres">'
      + '<div class="eq-c eq-c-fort"><span class="v">' + fr(s.total_t, 0)
      + ' t</span><span class="l">Carbone de fabrication total</span></div>'
      + '<div class="eq-c"><span class="v">' + fr(s.categorie_2_t, 0)
      + ' t</span><span class="l">Catégorie 2 — biens d\'équipement</span></div>'
      + '<div class="eq-c"><span class="v">' + fr(s.categorie_1_t, 1)
      + ' t</span><span class="l">Catégorie 1 — biens et services</span></div>'
      + '<div class="eq-c"><span class="v">' + fr(s.annualise_t, 0)
      + ' t/an</span><span class="l">Annualisé sur les durées de vie</span></div>'
      + "</div>"
      + "<p>" + esc(s.complement) + "</p>";
    if (s.effet_prolongation) {
      h += '<p class="eq-lien"><b>Effet de l\'allongement.</b> '
        + esc(s.effet_prolongation.dit) + " <i>"
        + esc(s.effet_prolongation.avertissement) + "</i></p>";
    }
    h += '<details class="dc-det"><summary>Ce que ce bilan NE couvre pas — '
      + s.non_couvert.length + " postes nommés</summary>"
      + '<div class="dc-det-c"><ul class="eq-trous">'
      + s.non_couvert.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("")
      + "</ul>"
      + '<p class="note">Incertitude annoncée sur les facteurs de fabrication&nbsp;: '
      + "±" + fr(s.incertitude_pct, 0) + " %. " + esc(s.source) + "</p>"
      + "</div></details></div>";
    return h;
  }

  /* ── Les gestes ─────────────────────────────────────────────────────────*/

  function dimensionner() {
    var sortie = $("#eq-sortie");
    if (!sortie) return;
    sortie.innerHTML = '<p class="note">Dimensionnement en cours…</p>';
    var env = $("#eq-enveloppe") ? $("#eq-enveloppe").value : "";
    poster("/api/datacenter/equipements", {
      puissance_it_kw: Number($("#eq-pit").value),
      densite: $("#eq-densite") ? $("#eq-densite").value : null,
      perimetre: $("#eq-perimetre") ? $("#eq-perimetre").value : "propre",
      enveloppe_travaux_eur: env === "" ? null : Number(env)
    }).then(function (res) {
      if (!res.ok) { sortie.innerHTML = '<p class="note">' + esc(message(res)) + "</p>"; return; }
      var n = res.j.nomenclature;
      if (!n.ok) {
        sortie.innerHTML = '<div class="eq-vie eq-refus"><b>Le calcul refuse&nbsp;: </b>'
          + esc(n.motif) + "</div>";
        return;
      }
      NOMEN = n;
      sortie.innerHTML = tableau(n) + gestesDurables(n)
        + bandeauPart(res.j.part);
      var s3 = $("#eq-scope3");
      if (s3) s3.innerHTML = bandeauScope3(res.j.scope3);
      if ($("#eq-vie-bloc")) $("#eq-vie-bloc").hidden = false;
      if ($("#eq-vie-form")) $("#eq-vie-form").hidden = false;
      /* La durée actuelle proposée est celle du MOTEUR pour un serveur, pas
         un chiffre rond choisi ici : les deux doivent rester d'accord. */
      var d0 = $("#eq-d0");
      if (d0 && n.duree_vie_serveur_ans) d0.value = n.duree_vie_serveur_ans;
    }).catch(function (e) {
      sortie.innerHTML = '<p class="note">'
        + (e && e.name === "AbortError"
            ? "Le serveur n'a pas répondu dans le temps accordé. Vos saisies sont conservées."
            : "Le dimensionnement a échoué.") + "</p>";
    });
  }

  function calculerBascule() {
    var el = $("#eq-vie");
    if (!el || !NOMEN) return;
    el.innerHTML = '<p class="note">Calcul de la bascule…</p>';
    poster("/api/datacenter/equipements", {
      puissance_it_kw: NOMEN.puissance_it_kw,
      densite: NOMEN.densite,
      perimetre: $("#eq-perimetre") ? $("#eq-perimetre").value : "propre",
      enveloppe_travaux_eur: null,
      duree_base: Number($("#eq-d0").value),
      duree_cible: Number($("#eq-d1").value),
      pays: $("#eq-pays") ? $("#eq-pays").value : "FR",
      pue: Number($("#eq-pue").value) || 1.0
    }).then(function (res) {
      if (!res.ok) { el.innerHTML = '<p class="note">' + esc(message(res)) + "</p>"; return; }
      el.innerHTML = bandeauVie(res.j.prolongation);
      var s3 = $("#eq-scope3");
      if (s3 && res.j.scope3) s3.innerHTML = bandeauScope3(res.j.scope3);
    }).catch(function () {
      el.innerHTML = '<p class="note">Le calcul de la bascule a échoué.</p>';
    });
  }

  function demarrer() {
    if (!$("#eq-go")) return;          // la section n'est pas sur cette page
    remplirListes().catch(function () {
      var s = $("#eq-sortie");
      if (s) {
        s.innerHTML = '<p class="note">Référentiel des équipements '
          + "indisponible&nbsp;: connectez-vous, ou réessayez dans un instant.</p>";
      }
    });
    remplirPays();
    $("#eq-go").addEventListener("click", dimensionner);
    var b = $("#eq-vie-go");
    if (b) b.addEventListener("click", calculerBascule);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  /* Exposé pour la recette : elle doit pouvoir relancer le dimensionnement
     sans simuler des clics, et lire ce que le serveur a réellement rendu. */
  window.EQUIPEMENTS_IT = {
    dimensionner: dimensionner,
    bascule: calculerBascule,
    nomenclature: function () { return NOMEN; }
  };
})();
