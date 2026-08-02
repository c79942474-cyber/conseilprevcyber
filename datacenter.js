/* Interface de l'étude de centre de données.
   ─────────────────────────────────────────
   Ce fichier ne calcule RIEN. Chaque chiffre affiché vient du serveur, où
   datacenter.py l'a produit avec sa formule, sa source et son incertitude.
   Recalculer côté navigateur pour « aller plus vite » ferait exister deux
   moteurs qui divergeraient au premier ajustement — et c'est le chiffre affiché
   que le client recopierait dans son offre.

   Le parti pris d'affichage : une valeur n'apparaît JAMAIS seule. Elle est
   toujours accompagnée de sa formule et de son incertitude, dépliables. Un
   tableau de bord de chiffres nus se lit vite et se défend mal ; ici le
   document doit tenir devant un bureau de contrôle. */
(function () {
  "use strict";

  var REF = null, PROFIL = {}, ETUDE = null;

  function $(s, r) { return (r || document).querySelector(s); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  /* Séparateur décimal français. Un « 1.47 » dans une note de calcul remise en
     France signale un document non relu — et ce détail-là, les évaluateurs le
     remarquent avant le contenu. */
  function fr(n) {
    if (n === null || n === undefined || n === "") return "—";
    var x = Number(n);
    if (!isFinite(x)) return String(n);
    var s = Math.abs(x) >= 100 ? x.toFixed(0)
          : Math.abs(x) >= 10 ? x.toFixed(1)
          : x.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
    return s.replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }
  function etat(msg, err) {
    var el = $("#dc-etat");
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = err ? "var(--red, #F0A0A0)" : "";
  }

  /* ── Le formulaire, construit depuis le référentiel du serveur ──────────
     Les listes déroulantes ne sont pas écrites dans le HTML : elles sont
     dérivées des mêmes tables que le calcul. Une option recopiée à la main
     finit toujours par proposer une valeur que le moteur ne connaît plus. */
  function bâtirFormulaire() {
    var champs = REF.champs || [];
    var h = '<div class="dc-grille">';
    champs.forEach(function (c) {
      var id = "dc-" + c.id;
      h += '<label class="dc-champ" for="' + id + '">'
        + '<span class="dc-lab">' + esc(c.label)
        + (c.unite ? ' <span class="dc-unite">(' + esc(c.unite) + ')</span>' : "")
        + (c.requis ? ' <b class="dc-req" title="Champ nécessaire">*</b>' : "")
        + "</span>";
      if (c.type === "liste") {
        h += '<select id="' + id + '" data-champ="' + esc(c.id) + '">';
        h += '<option value="">— non précisé —</option>';
        (c.options || []).forEach(function (o) {
          var lib = o;
          if (c.id === "refroidissement" && REF.referentiel.refroidissement[o]) {
            lib = REF.referentiel.refroidissement[o].nom;
          }
          h += '<option value="' + esc(o) + '"'
            + (c.defaut === o ? " selected" : "") + ">" + esc(lib) + "</option>";
        });
        h += "</select>";
      } else {
        h += '<input id="' + id + '" data-champ="' + esc(c.id) + '" type="text" inputmode="decimal"'
          + (c.defaut !== undefined ? ' value="' + esc(c.defaut) + '"' : "")
          + ' placeholder="' + (c.defaut !== undefined ? esc(c.defaut) : "—") + '">';
      }
      if (c.aide) h += '<span class="dc-aide">' + esc(c.aide) + "</span>";
      h += "</label>";
    });
    h += "</div>";
    $("#dc-form").innerHTML = h;
  }

  function lireProfil() {
    var p = {};
    document.querySelectorAll("#dc-form [data-champ]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v !== "") p[el.getAttribute("data-champ")] = v;
    });
    return p;
  }

  /* ── Une valeur, avec ce qui la rend défendable ─────────────────────────
     La formule et la source sont dans un <details> : présentes pour qui
     vérifie, discrètes pour qui survole. Les cacher tout à fait reviendrait à
     livrer un chiffre nu ; les afficher toujours rendrait la page illisible. */
  function carte(v) {
    if (!v || v.valeur === undefined) return "";
    var h = '<div class="dc-val">'
      + '<div class="dc-val-n">' + esc(v.nom) + "</div>"
      + '<div class="dc-val-v">' + fr(v.valeur)
      + ' <span class="dc-val-u">' + esc(v.unite) + "</span></div>";
    if (v.incertitude) h += '<div class="dc-val-i">' + esc(v.incertitude) + "</div>";
    var det = "";
    if (v.formule) det += "<div><b>Formule</b> — " + esc(v.formule) + "</div>";
    if (v.entrees) {
      var e = Object.keys(v.entrees).map(function (k) {
        return esc(k) + " = " + esc(v.entrees[k]);
      }).join(" · ");
      if (e) det += "<div><b>Entrées</b> — " + e + "</div>";
    }
    if (v.source) det += "<div><b>Source</b> — " + esc(v.source) + "</div>";
    if (v.note) det += "<div class='dc-note'>" + esc(v.note) + "</div>";
    if (det) {
      h += '<details class="dc-det"><summary>méthode et source</summary>'
        + '<div class="dc-det-c">' + det + "</div></details>";
    }
    return h + "</div>";
  }

  function bloc(titre, sous, section, cles) {
    var d = ETUDE[section] || {}, corps = "";
    cles.forEach(function (k) { corps += carte(d[k]); });
    if (!corps) return "";
    return '<section class="dc-bloc"><h3>' + esc(titre) + "</h3>"
      + (sous ? '<p class="dc-sous">' + esc(sous) + "</p>" : "")
      + '<div class="dc-vals">' + corps + "</div></section>";
  }

  function afficherResultats() {
    var h = "";
    h += bloc("Énergie",
      "Le PUE est calculé depuis la conception, pas reçu en entrée : un PUE annoncé "
      + "sans sa décomposition n'est pas vérifiable.",
      "energie", ["pue", "energie_it_MWh", "energie_totale_MWh", "energie_non_it_MWh", "dcie"]);
    h += bloc("Eau",
      "Le WUE de site est celui qu'on publie ; le WUE de source est celui qui doit "
      + "arbitrer. Un rejet sec affiche un WUE de site nul tout en consommant plus "
      + "d'eau à la source si le mix est thermique.",
      "eau", ["evaporation_m3", "purge_m3", "appoint_m3", "wue_site", "wue_source", "eau_amont_m3"]);
    h += bloc("Carbone",
      "Exploitation ET incorporé. Sur un mix décarboné, l'incorporé devient "
      + "majoritaire : l'ignorer conduit à optimiser ce qui ne pèse plus.",
      "carbone", ["cue", "co2_exploitation_localise_t", "co2_exploitation_marche_t", "ref",
                  "incorpore_serveurs_t", "incorpore_batiment_t", "incorpore_technique_t",
                  "empreinte_totale_t", "part_incorpore_pct"]);
    var ch = ETUDE.chaleur || {};
    h += bloc("Chaleur fatale",
      "Température de rejet : " + fr(ch.temperature_rejet_c) + " °C. " + (ch.valorisation || ""),
      "chaleur", ["erf", "ere", "energie_reutilisee_MWh"]);

    var lev = ETUDE.leviers || [];
    if (lev.length) {
      h += '<section class="dc-bloc"><h3>Leviers</h3>'
        + '<p class="dc-sous">Classés par gain carbone. Chaque levier porte sa '
        + 'contrepartie : un levier présenté sans la sienne est un argument '
        + 'commercial, pas une recommandation d\'ingénierie.</p>'
        + '<div class="dc-tab-wrap"><table class="dc-tab"><thead><tr>'
        + "<th>Levier</th><th>tCO2e/an</th><th>m³ eau/an</th><th>MWh/an</th>"
        + "<th>€/an</th><th>Difficulté</th></tr></thead><tbody>";
      lev.forEach(function (l) {
        h += "<tr><th scope='row'>" + esc(l.titre) + "</th>"
          + "<td>" + fr(l.gain_co2_t) + "</td><td>" + fr(l.gain_eau_m3) + "</td>"
          + "<td>" + fr(l.gain_energie_MWh) + "</td><td>" + fr(l.gain_euros) + "</td>"
          + "<td>" + esc(l.difficulte) + "</td></tr>";
      });
      h += "</tbody></table></div>";
      lev.forEach(function (l) {
        h += '<details class="dc-det"><summary>' + esc(l.titre) + "</summary>"
          + '<div class="dc-det-c">'
          + "<div><b>Contrepartie</b> — " + esc(l.contrepartie) + "</div>"
          + "<div><b>Condition</b> — " + esc(l.condition) + "</div>"
          + "<div><b>Fondement</b> — " + esc(l.fondement) + "</div>"
          + (l.note_gain ? "<div class='dc-note'>" + esc(l.note_gain) + "</div>" : "")
          + "</div></details>";
      });
      h += "</section>";
    }

    var conf = ETUDE.conformite || [];
    if (conf.length) {
      h += '<section class="dc-bloc"><h3>Conformité et repères de marché</h3>'
        + '<div class="dc-tab-wrap"><table class="dc-tab"><thead><tr>'
        + "<th>Sujet</th><th>Statut</th><th>Détail</th></tr></thead><tbody>";
      conf.forEach(function (c) {
        h += "<tr><th scope='row'>" + esc(c.sujet) + "</th>"
          + '<td><span class="dc-st dc-st-' + esc(c.statut).replace(/[^a-z]/g, "")
          + '">' + esc(c.statut) + "</span></td>"
          + "<td>" + esc(c.detail) + "</td></tr>";
      });
      h += "</tbody></table></div></section>";
    }

    var av = ETUDE.avertissements || [];
    if (av.length) {
      h += '<section class="dc-bloc dc-limites"><h3>Ce que ce calcul ne dit pas</h3>'
        + '<p class="dc-sous">Ces réserves font partie du résultat. Un moteur qui ne '
        + 'déclare pas ses limites les fait porter par son lecteur, qui ne les '
        + 'connaît pas.</p><ul>';
      av.forEach(function (a) { h += "<li>" + esc(a) + "</li>"; });
      h += "</ul></section>";
    }

    $("#dc-resultats").innerHTML = h;
    $("#dc-sec-res").hidden = false;
  }

  function afficherComparaison(d) {
    var h = '<p class="dc-sous">' + esc(d.lecture || "") + "</p>"
      + '<div class="dc-tab-wrap"><table class="dc-tab"><thead><tr>'
      + "<th>Famille</th><th>PUE</th><th>MWh/an</th><th>Eau site m³/an</th>"
      + "<th>WUE site</th><th>WUE source</th><th>Empreinte tCO2e/an</th>"
      + "<th>Rejet °C</th></tr></thead><tbody>";
    (d.lignes || []).forEach(function (l) {
      var courante = l.famille === (PROFIL.refroidissement || "");
      h += '<tr' + (courante ? ' class="dc-courante"' : "") + ">"
        + "<th scope='row'>" + esc(l.nom) + (courante ? " <em>(retenue)</em>" : "") + "</th>"
        + "<td>" + fr(l.pue) + "</td><td>" + fr(l.energie_totale_MWh) + "</td>"
        + "<td>" + fr(l.eau_site_m3) + "</td><td>" + fr(l.wue_site) + "</td>"
        + "<td>" + fr(l.wue_source) + "</td><td>" + fr(l.empreinte_totale_t) + "</td>"
        + "<td>" + fr(l.temperature_rejet_c) + "</td></tr>";
    });
    h += "</tbody></table></div>";
    (d.lignes || []).forEach(function (l) {
      h += '<details class="dc-det"><summary>' + esc(l.nom) + "</summary>"
        + '<div class="dc-det-c">' + esc(l.note) + "</div></details>";
    });
    $("#dc-comparaison").innerHTML = h;
    $("#dc-sec-comp").hidden = false;
  }

  function poster(url, corps) {
    return fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps)
    }).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, statut: r.status, j: j }; });
    });
  }

  /* Un refus d'accès et une panne appellent deux gestes différents. Les
     confondre envoie l'utilisateur réessayer là où il faut se connecter. */
  function messageErreur(res) {
    if (res.statut === 401) return "Connectez-vous pour utiliser le moteur d'ingénierie.";
    if (res.statut === 503) return (res.j && res.j.message) || "Service momentanément indisponible.";
    return (res.j && res.j.message) || "Le calcul a échoué.";
  }

  function lancer() {
    PROFIL = lireProfil();
    etat("Calcul en cours…");
    poster("/api/datacenter/etude", PROFIL).then(function (res) {
      if (!res.ok || !res.j.ok) { etat(messageErreur(res), true); return; }
      ETUDE = res.j.etude;
      afficherResultats();
      etat("Étude calculée. Chaque valeur porte sa méthode : dépliez « méthode et source ».");
      $("#dc-sec-res").scrollIntoView({ behavior: "smooth", block: "start" });
    }).catch(function () { etat("Réseau indisponible. Réessayez.", true); });
  }

  function comparer() {
    PROFIL = lireProfil();
    etat("Comparaison des familles…");
    poster("/api/datacenter/comparer", PROFIL).then(function (res) {
      if (!res.ok || !res.j.ok) { etat(messageErreur(res), true); return; }
      afficherComparaison(res.j);
      etat("Comparaison établie.");
      $("#dc-sec-comp").scrollIntoView({ behavior: "smooth", block: "start" });
    }).catch(function () { etat("Réseau indisponible. Réessayez.", true); });
  }

  function exporter(fmt) {
    PROFIL = lireProfil();
    etat("Préparation du document…");
    fetch("/api/datacenter/export", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.assign({}, PROFIL, { format: fmt }))
    }).then(function (r) {
      /* Le serveur répond soit un fichier, soit du JSON d'erreur. Traiter la
         réponse comme un fichier dans tous les cas téléchargerait un document
         de zéro octet, et l'utilisateur croirait à un export réussi. */
      var ct = r.headers.get("Content-Type") || "";
      if (!r.ok || ct.indexOf("json") >= 0) {
        return r.json().then(function (j) {
          etat((j && j.message) || "L'export a échoué.", true);
        });
      }
      return r.blob().then(function (b) {
        var u = URL.createObjectURL(b), a = document.createElement("a");
        a.href = u; a.download = "note-calcul-datacenter." + fmt;
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
        etat("Document téléchargé.");
      });
    }).catch(function () { etat("Réseau indisponible. Réessayez.", true); });
  }

  function démarrer() {
    fetch("/api/datacenter/referentiel", { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) throw new Error("auth");
        return r.json();
      })
      .then(function (j) {
        if (!j.ok) throw new Error("ref");
        REF = j;
        bâtirFormulaire();
        etat("");
      })
      .catch(function (e) {
        $("#dc-form").innerHTML = '<p class="note">'
          + (String(e.message) === "auth"
            ? "Connectez-vous pour accéder au moteur d'ingénierie."
            : "Référentiel indisponible. Réessayez dans un instant.")
          + "</p>";
      });

    var b;
    if ((b = $("#dc-lancer"))) b.addEventListener("click", lancer);
    if ((b = $("#dc-comparer"))) b.addEventListener("click", comparer);
    if ((b = $("#dc-docx"))) b.addEventListener("click", function () { exporter("docx"); });
    if ((b = $("#dc-pdf"))) b.addEventListener("click", function () { exporter("pdf"); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", démarrer);
  } else {
    démarrer();
  }
})();
