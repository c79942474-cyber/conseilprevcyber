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
  /* Un seul passage automatique par session de calcul : revenir en
     arrière depuis l'ingénierie ne doit pas relancer la bascule. */
  var SUITE_FAITE = false;

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

    /* L'aperçu suit la saisie. Un seul écouteur posé sur le conteneur plutôt
       que treize sur les champs : le formulaire est reconstruit depuis le
       référentiel, et des écouteurs par champ seraient à reposer à chaque
       reconstruction — celui-ci survit. */
    $("#dc-form").addEventListener("input", function () { apercuProfil(); });
    $("#dc-form").addEventListener("change", function () { apercuProfil(); });
    apercuProfil(true);
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

  /* ── Graphiques ────────────────────────────────────────────────────────
     SVG écrit à la main, sans bibliothèque : la page pèse déjà ce qu'elle
     pèse, et trois barres horizontales ne justifient pas trois cents kilo-
     octets de dépendance.

     Toutes les valeurs viennent de la réponse du serveur. Aucune n'est
     recalculée ici : un graphique qui refait le calcul du tableau qu'il
     surplombe finit par en diverger, et c'est le graphique qu'on croit. */
  var COUL = { site: "#22D3EE", source: "#F0B429",
               expl: "#D9603A", inc: "#8B7CF6", retenue: "#F6F0E8" };

  function barres(lignes, sers, opts) {
    opts = opts || {};
    var max = 0;
    lignes.forEach(function (l) {
      sers.forEach(function (s2) { max = Math.max(max, s2.val(l) || 0); });
    });
    if (opts.empile) {
      max = 0;
      lignes.forEach(function (l) {
        var t = 0; sers.forEach(function (s2) { t += s2.val(l) || 0; });
        max = Math.max(max, t);
      });
    }
    if (!max) return "";
    var hL = opts.empile ? 30 : 34, ecart = 12, gauche = 210, droite = 96;
    var larg = 860, H = lignes.length * (hL + ecart) + 8;
    var util = larg - gauche - droite;
    /* Le conteneur défilant : sur un écran étroit, mieux vaut faire glisser le
       graphique que comprimer sept barres jusqu'à ce qu'elles ne comparent
       plus rien. Sans ce wrapper, la règle `overflow-x` de la feuille de style
       ne s'applique à rien. */
    var h = '<div class="dc-g-wrap"><svg class="dc-g" viewBox="0 0 ' + larg + " " + H + '" role="img" '
      + 'preserveAspectRatio="xMinYMin meet" aria-label="' + esc(opts.alt || "") + '">';
    lignes.forEach(function (l, i) {
      var y = i * (hL + ecart) + 4;
      var courante = l.famille === (PROFIL.refroidissement || "");
      h += '<text x="0" y="' + (y + hL / 2 + 4) + '" class="dc-g-l'
        + (courante ? " on" : "") + '">' + esc(abrege(l.nom))
        + (courante ? " ◄" : "") + "</text>";
      if (opts.empile) {
        var x = gauche, tot = 0;
        sers.forEach(function (s2) {
          var v = s2.val(l) || 0, w = util * v / max;
          if (w > 0.4) h += '<rect x="' + x.toFixed(1) + '" y="' + y + '" width="'
            + w.toFixed(1) + '" height="' + hL + '" fill="' + s2.c + '"><title>'
            + esc(s2.nom + " : " + fr(v) + " " + (opts.unite || "")) + "</title></rect>";
          x += w; tot += v;
        });
        h += '<text x="' + (gauche + util * tot / max + 8).toFixed(1) + '" y="'
          + (y + hL / 2 + 4) + '" class="dc-g-v">' + fr(tot)
          + (opts.suffixe ? " " + esc(opts.suffixe) : "") + "</text>";
      } else {
        var hb = (hL - 4) / sers.length;
        sers.forEach(function (s2, j) {
          var v = s2.val(l) || 0, w = util * v / max;
          var yy = y + j * (hb + 2);
          h += '<rect x="' + gauche + '" y="' + yy + '" width="' + Math.max(1, w).toFixed(1)
            + '" height="' + hb.toFixed(1) + '" fill="' + s2.c + '"><title>'
            + esc(s2.nom + " : " + fr(v) + " " + (opts.unite || "")) + "</title></rect>";
          h += '<text x="' + (gauche + w + 8).toFixed(1) + '" y="' + (yy + hb / 2 + 3.5)
            + '" class="dc-g-v">' + fr(v) + "</text>";
        });
      }
    });
    return h + "</svg></div>"
      + '<div class="dc-g-lg">' + sers.map(function (s2) {
          return '<span><i style="background:' + s2.c + '"></i>' + esc(s2.nom) + "</span>";
        }).join("") + (opts.legende ? "<span>" + opts.legende + "</span>" : "") + "</div>";
  }

  /* ── L'aperçu du profil : ce qui reste ouvert avant de calculer ─────────
     L'étape 1 affirme que « renseigner davantage resserre les incertitudes ».
     Cette affirmation était invérifiable — il fallait la croire. Le serveur la
     chiffre maintenant (profil_dc.py) en rejouant l'étude sur le domaine de
     chaque champ vide ; ici, on la dessine. Aucun de ces nombres n'est calculé
     dans le navigateur. */

  /* La couleur dit d'où le balayage tire son autorité. C'est la seule
     information qu'un lecteur ne peut pas deviner en regardant une barre, et
     c'est celle qui décide s'il peut s'en servir dans un dossier. */
  var COUL_NATURE = { referentiel: "#22D3EE", definition: "#8B7CF6", hypothese: "#F0B429" };
  var NOM_NATURE = {
    referentiel: "énuméré au référentiel",
    definition: "borné par définition",
    hypothese: "balayage déclaré",
  };

  /* La courbe de charge partielle. Le coude vient du serveur, qui l'a DÉTECTÉ
     sur les points calculés ; l'écrire ici en dur aurait fabriqué une seconde
     définition du seuil, qui aurait survécu à un changement du moteur. */
  function courbeCharge(c) {
    if (!c || !c.disponible || !(c.points || []).length) return "";
    var P = c.points;
    var L = 880, H = 300, mg = 58, md = 22, mh = 18, mb = 44;
    var x0 = mg, x1 = L - md, y0 = mh, y1 = H - mb;
    var tMin = P[0].taux, tMax = P[P.length - 1].taux;
    var lo = Infinity, hi = -Infinity;
    P.forEach(function (p) {
      lo = Math.min(lo, p.pue_min); hi = Math.max(hi, p.pue_max);
    });
    if (hi - lo < 0.02) { lo -= 0.05; hi += 0.05; }   /* PUE imposé : bande nulle */
    var pad = (hi - lo) * 0.12; lo -= pad; hi += pad;
    var X = function (t) { return x0 + (t - tMin) / (tMax - tMin) * (x1 - x0); };
    var Y = function (v) { return y1 - (v - lo) / (hi - lo) * (y1 - y0); };
    /* Sur un axe, le nombre de décimales doit être CONSTANT. fr() supprime les
       zéros de fin, ce qui donnait « 1,676 » au-dessus de « 1,44 » : l'œil
       compare alors des chiffres qui n'ont pas le même rang. */
    var pas = (hi - lo) / 4;
    var dec = pas >= 1 ? 0 : pas >= 0.1 ? 2 : 3;
    var axe = function (v) { return v.toFixed(dec).replace(".", ","); };

    var h = '<div class="dc-g-wrap"><svg class="dc-g dc-c" viewBox="0 0 ' + L + " " + H + '" '
      + 'role="img" preserveAspectRatio="xMinYMin meet" aria-label="'
      + esc("Courbe du PUE en fonction du taux de charge, de "
            + fr(tMin) + " à " + fr(tMax) + ". PUE de "
            + fr(P[P.length - 1].pue) + " à pleine charge, "
            + fr(P[0].pue) + " au taux le plus bas."
            + (c.coude ? " Coude détecté à " + fr(c.coude.taux) + "." : "")) + '">';

    /* Grille horizontale : quatre lignes suffisent à situer une valeur ; au
       delà elles concurrencent la courbe. */
    var i, v;
    for (i = 0; i <= 4; i++) {
      v = lo + (hi - lo) * i / 4;
      h += '<line class="dc-c-gr" x1="' + x0 + '" y1="' + Y(v).toFixed(1)
        + '" x2="' + x1 + '" y2="' + Y(v).toFixed(1) + '"/>'
        + '<text class="dc-c-ax" x="' + (x0 - 8) + '" y="' + (Y(v) + 4).toFixed(1)
        + '" text-anchor="end">' + axe(v) + "</text>";
    }
    P.forEach(function (p, j) {
      if (j % 4) return;
      h += '<text class="dc-c-ax" x="' + X(p.taux).toFixed(1) + '" y="' + (y1 + 20)
        + '" text-anchor="middle">' + fr(p.taux) + "</text>";
    });
    h += '<text class="dc-c-ti" x="' + ((x0 + x1) / 2).toFixed(0) + '" y="' + (H - 8)
      + '" text-anchor="middle">Taux de charge moyen</text>'
      + '<text class="dc-c-ti" transform="translate(14,' + ((y0 + y1) / 2).toFixed(0)
      + ') rotate(-90)" text-anchor="middle">PUE</text>';

    /* La bande de conception, en aire : c'est elle l'incertitude. Tracer la
       seule ligne médiane donnerait un PUE qui a l'air connu au millième. */
    var haut = P.map(function (p) { return X(p.taux).toFixed(1) + "," + Y(p.pue_max).toFixed(1); });
    var bas = P.slice().reverse().map(function (p) {
      return X(p.taux).toFixed(1) + "," + Y(p.pue_min).toFixed(1);
    });
    h += '<polygon class="dc-c-bd" points="' + haut.concat(bas).join(" ") + '"/>';
    h += '<polyline class="dc-c-li" points="'
      + P.map(function (p) { return X(p.taux).toFixed(1) + "," + Y(p.pue).toFixed(1); }).join(" ")
      + '"/>';

    if (c.coude) {
      h += '<line class="dc-c-cd" x1="' + X(c.coude.taux).toFixed(1) + '" y1="' + y0
        + '" x2="' + X(c.coude.taux).toFixed(1) + '" y2="' + y1 + '"/>'
        + '<text class="dc-c-cl" x="' + (X(c.coude.taux) + 6).toFixed(1) + '" y="' + (y0 + 12)
        + '">coude ' + fr(c.coude.taux) + "</text>";
    }
    /* Chaque point porte son infobulle : la valeur exacte s'y lit sans encombrer
       le tracé, et l'énergie annuelle avec elle — c'est elle qu'on paie. */
    P.forEach(function (p) {
      h += '<circle class="dc-c-pt" cx="' + X(p.taux).toFixed(1) + '" cy="' + Y(p.pue).toFixed(1)
        + '" r="7"><title>' + esc("Taux " + fr(p.taux) + " · PUE " + fr(p.pue)
          + " (bande " + fr(p.pue_min) + "–" + fr(p.pue_max) + ") · "
          + fr(p.energie_totale_MWh) + " MWh/an") + "</title></circle>";
    });
    var k = c.courant;
    if (k) {
      h += '<circle class="dc-c-ic" cx="' + X(k.taux).toFixed(1) + '" cy="' + Y(k.pue).toFixed(1)
        + '" r="5.5"/>'
        + '<text class="dc-c-cl on" x="' + X(k.taux).toFixed(1) + '" y="' + (Y(k.pue) - 12).toFixed(1)
        + '" text-anchor="middle">'
        + esc((c.taux_renseigne ? "votre taux " : "défaut ") + fr(k.taux)) + "</text>";
    }
    h += "</svg></div>";

    /* La pastille de légende reprend EXACTEMENT le remplissage de la bande —
       .dc-c-bd — sinon la légende désigne une couleur qui n'est pas à l'écran. */
    h += '<div class="dc-g-lg"><span><i style="background:#22D3EE"></i>PUE calculé</span>'
      + '<span><i style="background:rgba(34,211,238,.34);'
      + 'outline:1px solid rgba(34,211,238,.55)"></i>plage de conception — '
      + esc(c.famille) + "</span>"
      + (c.coude ? '<span><i style="background:#F0B429"></i>coude détecté sur les points calculés</span>' : "")
      + "</div>";
    h += '<p class="dc-lecture">' + esc(c.note)
      + (c.coude ? " <b>Au-dessous de " + esc(fr(c.coude.taux)) + "</b>, chaque point de "
          + "charge perdu dégrade le PUE ; au-dessus, il n'entre plus dans ce modèle." : "")
      + "</p>";
    return h;
  }

  /* Ce que chaque champ vide laisse encore ouvert. Les barres sont classées par
     portée décroissante : la première est le champ à renseigner en priorité,
     et c'est la seule question que se pose un lecteur devant ce graphique. */
  function tornade(s) {
    if (!s || !s.disponible) return "";
    var F = s.facteurs || [];
    if (!F.length) {
      return '<p class="dc-lecture">Tous les champs à domaine borné sont renseignés. '
        + "Il ne reste que les incertitudes du référentiel lui-même, publiées à l'étape 5.</p>";
    }
    var hL = 26, ec = 10, gauche = 250, droite = 62;
    var larg = 880, H = F.length * (hL + ec) + 8, util = larg - gauche - droite;
    var h = '<div class="dc-g-wrap"><svg class="dc-g" viewBox="0 0 ' + larg + " " + H + '" '
      + 'role="img" preserveAspectRatio="xMinYMin meet" aria-label="'
      + esc("Part de chaque grandeur encore indéterminée, par champ non renseigné. "
            + F.map(function (f) { return f.label + " " + fr(f.portee_max_pct) + " %"; })
                .join(" ; ")) + '">';
    F.forEach(function (f, i) {
      var y = i * (hL + ec) + 4;
      var w = util * Math.max(0, Math.min(100, f.portee_max_pct)) / 100;
      var c = COUL_NATURE[f.nature] || "#F6F0E8";
      var det = (s.indicateurs || []).map(function (ind) {
        var e = (f.etendues || {})[ind.cle];
        if (!e) return "";
        return ind.nom + " : " + fr(e.min) + " – " + fr(e.max)
          + (ind.unite ? " " + ind.unite : "");
      }).filter(Boolean).join("\n");
      h += '<text x="0" y="' + (y + hL / 2 + 4) + '" class="dc-g-l">'
        + esc(abrege(f.label)) + "</text>"
        + '<rect x="' + gauche + '" y="' + y + '" width="' + util + '" height="' + hL
        + '" class="dc-t-fd"/>'
        + '<rect x="' + gauche + '" y="' + y + '" width="' + Math.max(1, w).toFixed(1)
        + '" height="' + hL + '" fill="' + c + '"><title>'
        + esc(f.label + " — " + NOM_NATURE[f.nature] + " (" + f.n_valeurs + " valeurs balayées)\n"
              + det) + "</title></rect>"
        + '<text x="' + (gauche + util + 8) + '" y="' + (y + hL / 2 + 4) + '" class="dc-g-v">'
        + fr(f.portee_max_pct) + " %</text>";
    });
    h += "</svg></div>";

    h += '<div class="dc-g-lg">'
      + Object.keys(NOM_NATURE).map(function (n) {
          return '<span><i style="background:' + COUL_NATURE[n] + '"></i>' + esc(NOM_NATURE[n]) + "</span>";
        }).join("") + "</div>";

    h += '<p class="dc-lecture"><b>' + esc(s.portee_definition) + "</b> "
      + esc(s.note_addition) + " " + esc(s.balayage_note) + "</p>";

    if ((s.leviers_seuls || []).length) {
      h += '<p class="dc-lecture">' + esc(s.leviers_seuls.join(", "))
        + (s.leviers_seuls.length > 1 ? " ne changent " : " ne change ")
        + "aucune des grandeurs suivies, mais " + (s.leviers_seuls.length > 1 ? "modifient" : "modifie")
        + " les leviers que le moteur propose. Une barre à zéro ne veut pas dire "
        + "que le champ est inutile — seulement qu'il agit ailleurs.</p>";
    }
    if ((s.exclus || []).length) {
      h += '<details class="dc-det"><summary>Les champs volontairement non balayés ('
        + s.exclus.length + ")</summary><div class='dc-det-c'>"
        + s.exclus.map(function (x) {
            return "<div><b>" + esc(x.label) + "</b> — " + esc(x.motif) + "</div>";
          }).join("") + "</div></details>";
    }
    return h;
  }

  /* Le relevé des valeurs par défaut. La page promet qu'elles sont « signalées
     comme telles dans la note » ; autant les signaler AVANT le calcul, quand
     il est encore temps de les remplacer. */
  function releveDefauts(d) {
    if (!d) return "";
    /* Trois états, pas deux. Un champ pré-rempli par le formulaire n'est pas
       « renseigné » : la première version les comptait ensemble et annonçait
       sept saisies là où il n'y en avait qu'une. */
    var h = '<div class="dc-rel"><div class="dc-rel-t"><b>' + d.n_renseignes + "</b> champ"
      + (d.n_renseignes > 1 ? "s" : "") + " renseigné" + (d.n_renseignes > 1 ? "s" : "")
      + " sur " + d.n_total + " · <b>" + d.n_valeur_defaut + "</b> laissé"
      + (d.n_valeur_defaut > 1 ? "s" : "") + " sur la valeur par défaut · <b>"
      + d.n_absents + "</b> non précisé" + (d.n_absents > 1 ? "s" : "")
      + "</div><div class='dc-rel-l'>";
    (d.champs || []).forEach(function (c) {
      var t = c.etat === "saisi" ? "renseigné : " + c.valeur
        : c.etat === "defaut" ? "laissé sur la valeur par défaut : " + c.valeur
        : "non précisé — le moteur applique sa valeur de repli";
      h += '<span class="dc-rel-p e-' + esc(c.etat) + '" title="' + esc(t) + '">'
        + esc(abrege(c.label)) + "</span>";
    });
    h += "</div>";
    if (d.note) h += '<p class="dc-rel-n">' + esc(d.note) + "</p>";
    return h + "</div>";
  }

  /* L'appel : différé, et le précédent annulé. Sans annulation, deux frappes
     rapprochées font revenir les réponses dans l'ordre du réseau et non dans
     celui de la saisie — le graphique affiche alors l'avant-dernier profil. */
  var _minuteur = null, _vol = null;

  function apercuProfil(immediat) {
    var zone = $("#dc-apercu");
    if (!zone) return;
    if (_minuteur) clearTimeout(_minuteur);
    _minuteur = setTimeout(function () {
      var p = lireProfil();
      if (!p.puissance_it_kw) {
        zone.innerHTML = '<p class="note dc-ap-vide">Renseignez la puissance informatique '
          + "installée : c'est la seule entrée indispensable, et elle suffit à ouvrir "
          + "l'analyse ci-dessous.</p>";
        return;
      }
      if (_vol) { try { _vol.abort(); } catch (e) {} }
      _vol = (typeof AbortController !== "undefined") ? new AbortController() : null;
      zone.classList.add("occupe");
      fetch("/api/datacenter/profil", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(p),
        signal: _vol ? _vol.signal : undefined,
      })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          zone.classList.remove("occupe");
          if (!j.ok) throw new Error(j.message || "aperçu");
          rendreApercu(j.apercu);
        })
        .catch(function (e) {
          if (e && e.name === "AbortError") return;   /* remplacé par une saisie plus récente */
          zone.classList.remove("occupe");
          zone.innerHTML = '<p class="note">Aperçu indisponible pour le moment. '
            + "Le calcul complet, lui, reste accessible par « Calculer l'étude ».</p>";
        });
    }, immediat ? 0 : 280);
  }

  function rendreApercu(a) {
    var zone = $("#dc-apercu");
    if (!zone || !a) return;
    var h = "";
    if (a.entete) h += '<p class="dc-ap-tete">' + esc(a.entete) + "</p>";
    h += releveDefauts(a.defauts);
    h += '<div class="dc-ap-b"><h3>Où se situe votre taux de charge</h3>'
      + '<p class="dc-sous">Le PUE ne dépend pas seulement de la technologie : sous un '
      + "certain taux de charge, les auxiliaires ne suivent plus proportionnellement. "
      + "La courbe est calculée par le moteur, point par point.</p>"
      + courbeCharge(a.courbe_charge) + "</div>";
    h += '<div class="dc-ap-b"><h3>Ce que chaque champ vide laisse encore ouvert</h3>'
      + '<p class="dc-sous">Pour chaque champ non renseigné, l\'étude est rejouée sur '
      + "tout le domaine de ce champ. La barre mesure ce qui reste indéterminé — "
      + "renseigner le champ la fait disparaître.</p>"
      + tornade(a.sensibilite) + "</div>";
    zone.innerHTML = h;
  }

  /* Les noms de famille sont longs ; à gauche d'un graphique, ils poussent les
     barres hors du cadre. On coupe au premier segment parlant plutôt que
     d'imposer une police minuscule. */
  function abrege(n) {
    n = String(n || "");
    if (n.length <= 30) return n;
    var c = n.indexOf(" (");
    if (c > 6 && c <= 32) return n.slice(0, c);
    return n.slice(0, 29) + "…";
  }

  /* L'inversion : quelles familles changent de rang entre l'eau du site et
     l'eau de la source. C'est la thèse de la page ; la laisser deviner dans un
     tableau de huit colonnes revenait à ne pas la démontrer. */
  function inversions(lignes) {
    var parSite = lignes.slice().sort(function (a, b) { return a.wue_site - b.wue_site; });
    var parSrc = lignes.slice().sort(function (a, b) { return a.wue_source - b.wue_source; });
    var out = [];
    parSite.forEach(function (l, i) {
      var j = parSrc.findIndex(function (x) { return x.famille === l.famille; });
      if (j !== i) out.push({ nom: l.nom, site: i + 1, source: j + 1 });
    });
    return out;
  }

  function graphiques(d) {
    var L = d.lignes || [];
    if (!L.length) return "";
    var inv = inversions(L);
    var meilleurSite = L.slice().sort(function (a, b) { return a.wue_site - b.wue_site; })[0];
    var meilleurSrc = L.slice().sort(function (a, b) { return a.wue_source - b.wue_source; })[0];

    var h = '<section class="dc-bloc"><h3>Le compromis eau, ramené au kilowattheure informatique</h3>'
      + '<p class="dc-sous">Les volumes annuels ne se comparent pas d’une famille à '
      + 'l’autre : ils dépendent de la consommation, qui dépend elle-même du PUE. '
      + 'Rapportées au kilowattheure informatique, les deux eaux se comparent '
      + 'directement — et l’écart entre elles est ce qui décide.</p>'
      + barres(L, [
          { nom: "Eau du site (WUE site)", c: COUL.site, val: function (l) { return l.wue_site; } },
          { nom: "Eau de la source (WUE source)", c: COUL.source, val: function (l) { return l.wue_source; } },
        ], { unite: "L/kWh_IT", alt: "Eau du site et eau de la source, par famille de "
             + "refroidissement, en litres par kilowattheure informatique",
             legende: "◄ famille retenue" });

    /* Quand la même famille gagne les deux lectures, le dire une fois. Répéter
       « au bilan de site X, au bilan complet X » se lit comme un bégaiement et
       fait manquer l'information réelle, qui est justement l'accord des deux. */
    h += '<div class="dc-lecture"><b>Ce que le graphique montre.</b> ';
    if (meilleurSite.famille === meilleurSrc.famille) {
      h += 'La famille la moins consommatrice est <b>' + esc(abrege(meilleurSite.nom))
        + '</b> dans LES DEUX lectures — ' + fr(meilleurSite.wue_site)
        + ' L/kWh_IT sur le site, ' + fr(meilleurSrc.wue_source)
        + ' au bilan complet. Le classement de tête ne bouge donc pas ; '
        + 'ce qui bouge est en dessous. ';
    } else {
      h += 'Au bilan de SITE, la famille la moins consommatrice est <b>'
        + esc(abrege(meilleurSite.nom)) + '</b> (' + fr(meilleurSite.wue_site)
        + ' L/kWh_IT). Au bilan COMPLET, c’est <b>' + esc(abrege(meilleurSrc.nom))
        + '</b> (' + fr(meilleurSrc.wue_source) + ' L/kWh_IT). ';
    }
    if (inv.length) {
      h += '<b>' + inv.length + ' famille' + (inv.length > 1 ? "s changent" : " change")
        + ' de rang</b> entre les deux lectures : '
        + inv.slice(0, 4).map(function (x) {
            return esc(abrege(x.nom)) + " (" + x.site + "ᵉ → " + x.source + "ᵉ)";
          }).join(" · ")
        + '. Un dossier qui n’aurait regardé que le WUE de site aurait classé '
        + 'ces familles à l’envers.';
    } else {
      h += 'Aucune famille ne change de rang entre les deux lectures : sur ce mix, '
        + 'l’arbitrage de site et l’arbitrage complet concordent. Ce n’est pas '
        + 'toujours le cas — l’écart se creuse à mesure que le mix se charge en '
        + 'production thermique.';
    }
    h += "</div></section>";

    /* Carbone : exploitation contre incorporé. La page l'affirme, le graphique
       le montre — et sur un mix décarboné le second l'emporte. */
    var incMax = 0;
    L.forEach(function (l) {
      var inc = (l.empreinte_totale_t || 0) - (l.co2_exploitation_t || 0);
      if (l.empreinte_totale_t) incMax = Math.max(incMax, 100 * inc / l.empreinte_totale_t);
    });
    h += '<section class="dc-bloc"><h3>Carbone : ce que l’exploitation pèse, et ce que la construction pèse</h3>'
      + '<p class="dc-sous">L’incorporé — fabrication des serveurs, gros œuvre, '
      + 'équipements techniques — est amorti sur la durée de vie. Sur un mix décarboné '
      + 'il devient majoritaire, et optimiser l’exploitation revient alors à travailler '
      + 'sur la plus petite des deux parts.</p>'
      + barres(L, [
          { nom: "Exploitation (électricité consommée)", c: COUL.expl,
            val: function (l) { return l.co2_exploitation_t; } },
          { nom: "Incorporé, amorti (fabrication et construction)", c: COUL.inc,
            val: function (l) { return Math.max(0, (l.empreinte_totale_t || 0)
                                  - (l.co2_exploitation_t || 0)); } },
        ], { empile: true, unite: "tCO2e/an", suffixe: "t",
             alt: "Empreinte annuelle par famille, part d’exploitation et part incorporée",
             legende: "total en tCO2e/an" })
      + '<div class="dc-lecture"><b>Ce que le graphique montre.</b> La part incorporée '
      + 'atteint <b>' + fr(Math.round(incMax)) + ' %</b> du total sur la famille où elle '
      + 'pèse le plus. Ces facteurs sont des ordres de grandeur sectoriels à ±50 % : dès '
      + 'que les équipements sont choisis, leurs déclarations environnementales produit '
      + 'doivent les remplacer, et l’écart peut atteindre un facteur deux.</div></section>';
    return h;
  }

  function afficherComparaison(d) {
    /* Les graphiques d'abord, le tableau ensuite : on montre le compromis,
       puis on donne les chiffres à recopier. L'inverse obligeait à lire huit
       colonnes avant de comprendre ce qu'on cherchait. */
    var h = '<p class="dc-sous">' + esc(d.lecture || "") + "</p>" + graphiques(d)
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
      /* Le profil est retenu pour la page d'ingénierie : elle pose le même
         formulaire, et c'est la ressaisie des treize champs qui décourage, pas
         le calcul. Enregistré APRÈS un calcul réussi seulement — un profil qui
         n'a rien produit ici n'a pas de raison d'être proposé ailleurs. */
      if (window.ProfilDC) window.ProfilDC.enregistrer(PROFIL, "datacenter");
      afficherResultats();
      montrerSuite();
      etat("Étude calculée. Chaque valeur porte sa méthode : dépliez « méthode et source ».");
      $("#dc-sec-res").scrollIntoView({ behavior: "smooth", block: "start" });
    }).catch(function () { etat("Réseau indisponible. Réessayez.", true); });
  }

  /* La suite du chemin, proposée une fois le calcul fait et pas avant : ce que
     la page d'ingénierie apporte — à quelle phase ce chiffre devient recevable
     — n'a aucun sens tant qu'il n'y a pas de chiffre. */
  function montrerSuite() {
    var z = $("#dc-suite");
    if (!z || z.getAttribute("data-pose") === "1") return;
    z.setAttribute("data-pose", "1");
    z.hidden = false;
    z.innerHTML =
      '<div class="dc-suite-i">'
      + "<b>Ce calcul est juste. Il ne dit pas encore s’il est recevable.</b>"
      + "<span>Un PUE tiré d’une plage de conception convient à un "
      + "avant-projet ; le même chiffre reporté dans un CCTP devient une clause "
      + "de pénalité assise sur un ordre de grandeur. La page d’ingénierie "
      + "de projet dit à quelle phase chacune de ces valeurs devient opposable, "
      + "et ce qu’il faut avoir produit pour y arriver.</span></div>"
      + '<a class="dc-suite-b" id="dc-suite-go" href="/ingenierie-datacenter">'
      + "Placer ce calcul dans un projet →</a>"
      + '<p class="dc-suite-n">Votre profil y sera repris tel quel — vous '
      + "n’avez rien à ressaisir, et la page s’ouvrira directement sur la "
      + "première phase qui bloque. Il ne quitte pas ce navigateur et "
      + "disparaît à la fermeture de l’onglet.</p>"
      + '<p class="dc-suite-c" id="dc-suite-c" role="status" aria-live="polite"></p>';
    compteRebours();
  }

  /* ── Le passage automatique ────────────────────────────────────────────
     Le calcul fait, la suite du chemin s'ouvre d'elle-même. Trois précautions,
     et chacune répare un défaut que ce genre de bascule produit :

       · ELLE NE VOLE PAS LES RÉSULTATS. Le lecteur vient de demander un
         calcul ; l'emmener ailleurs avant qu'il l'ait vu répondrait à côté de
         sa question. Le délai lui laisse le temps de regarder, et la moindre
         interaction — molette, clic, touche — l'annule : quelqu'un qui commence
         à lire a déjà répondu.

       · ELLE S'ANNULE D'UN GESTE VISIBLE. Un compte à rebours sans bouton
         d'arrêt est un piège (WCAG 2.2.1) ; celui-ci en porte un, et il est
         annoncé aux lecteurs d'écran.

       · ELLE NE SE REJOUE PAS. Revenir en arrière depuis la page d'ingénierie
         relancerait la bascule et enfermerait le lecteur dans une boucle. Un
         seul passage par calcul. */
  var DELAI_SUITE = 12;

  function compteRebours() {
    var z = $("#dc-suite-c");
    if (!z || SUITE_FAITE) return;
    var reste = DELAI_SUITE, minuteur = null, fini = false;

    function arreter(pourquoi) {
      if (fini) return;
      fini = true;
      clearInterval(minuteur);
      ["wheel", "touchstart", "keydown", "pointerdown"].forEach(function (e) {
        window.removeEventListener(e, surInteraction, true);
      });
      z.innerHTML = pourquoi === "annule"
        ? "Passage automatique annulé. Le bouton ci-dessus y conduit quand vous "
          + "le voudrez ; votre profil reste prêt."
        : "";
    }
    function surInteraction() { arreter("annule"); }

    ["wheel", "touchstart", "keydown", "pointerdown"].forEach(function (e) {
      window.addEventListener(e, surInteraction, true);
    });
    z.innerHTML = "Passage à l’ingénierie de projet dans <b>" + reste
      + "</b> s — <button type=\"button\" id=\"dc-suite-x\">rester sur cette page</button>";
    var b = $("#dc-suite-x");
    if (b) b.addEventListener("click", function () { arreter("annule"); });
    minuteur = setInterval(function () {
      reste -= 1;
      if (fini) return;
      if (reste <= 0) {
        arreter("part");
        SUITE_FAITE = true;
        window.location.href = "/ingenierie-datacenter";
        return;
      }
      var n = z.querySelector("b");
      if (n) n.textContent = reste;
    }, 1000);
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

  /* ── Le référentiel, publié ────────────────────────────────────────────
     Il vit dans le moteur et n'était affiché nulle part. Or c'est lui qui dit
     que les facteurs eau sont des ordres de grandeur à ±40 %, et qu'il faut
     les remplacer par la valeur du fournisseur. Une page qui calcule sans
     montrer d'où viennent ses constantes demande qu'on la croie.

     Tout est rendu depuis `/api/datacenter/referentiel` : recopier ces
     libellés dans la page les aurait figés au jour de l'écriture. */
  /* Ce que la base de connaissance couvre, COMPTÉ par le serveur.
     La page annonçait « seize thèmes » — vrai le jour où la phrase a été
     écrite, faux depuis que la famille en porte davantage. Un lecteur
     cherchant une analyse de risques en concluait qu'elle n'était pas
     couverte. Un compte figé finit toujours par mentir ; celui-ci est
     demandé. */
  function afficherBase() {
    var el = $("#dc-base");
    if (!el || !REF || !REF.base) return;
    var b = REF.base;
    el.innerHTML = "La famille <b>" + esc(b.famille) + "</b> compte <b>"
      + b.themes + "</b> thèmes — " + b.techniques
      + " techniques, du refroidissement liquide aux appels d'offres, et "
      + b.management + " de management (politique environnementale, analyse de "
      + "risques, incendie, plans de sécurité). Un document mal classé se "
      + "retrouve difficilement&nbsp;: le thème compte autant que le fichier.";
  }

  function afficherReferentiel() {
    var el = $("#dc-referentiel");
    afficherBase();
    if (!el || !REF || !REF.referentiel) return;
    var R = REF.referentiel, h = "";

    function carteRef(nom, nature, quoi, valeurs, source, remplacer) {
      return '<div class="dc-ref-c"><span class="n">' + esc(nature) + "</span>"
        + "<h4>" + esc(nom) + "</h4>"
        + (quoi ? "<p>" + esc(quoi) + "</p>" : "")
        + (valeurs ? '<div class="v">' + valeurs + "</div>" : "")
        + (source ? "<p style='margin-top:7px'>" + esc(source) + "</p>" : "")
        + (remplacer ? '<span class="rmp">▸ ' + esc(remplacer) + "</span>" : "")
        + "</div>";
    }

    /* Eau de la production électrique : le facteur le plus incertain du lot,
       et celui qui décide de l'arbitrage. Il passe en premier. */
    if (R.ewif) {
      var pays = Object.keys(R.ewif).map(function (k) {
        return esc(k) + " " + fr(R.ewif[k].valeur);
      }).join(" · ");
      h += carteRef("Eau de la production électrique (EWIF)", "ordre de grandeur · ±40 %",
        "Eau CONSOMMÉE — évaporée, non restituée — pour produire un kilowattheure. "
        + "À ne pas confondre avec l’eau prélevée : l’écart atteint un facteur dix "
        + "sur un parc nucléaire en circuit ouvert.",
        pays + " L/kWh", R.ewif_source,
        "la valeur du fournisseur ou du gestionnaire de réseau, dès qu’elle existe");
    }
    if (R.intensite_reseau) {
      var ir = Object.keys(R.intensite_reseau).map(function (k) {
        return esc(k) + " " + fr(R.intensite_reseau[k]);
      }).join(" · ");
      h += carteRef("Intensité carbone du réseau", "moyenne annuelle",
        "Grammes de CO2e par kilowattheure consommé. Une moyenne annuelle ne "
        + "convient PAS pour arbitrer un pilotage horaire de la charge.",
        ir + " g/kWh", R.intensite_source,
        "la donnée du gestionnaire de réseau de l’année de référence, ou le "
        + "facteur contractuel du fournisseur (GHG Protocol, Scope 2 market-based)");
    }
    if (R.incorpore) {
      var ic = Object.keys(R.incorpore).map(function (k) {
        var v = R.incorpore[k];
        return esc(k.replace(/_/g, " ")) + " : " + fr(v.valeur)
          + (v.duree_vie_ans ? " sur " + v.duree_vie_ans + " ans" : "");
      }).join("<br>");
      h += carteRef("Carbone incorporé", "ordre de grandeur sectoriel · ±50 %",
        "Fabrication et construction, amorties sur la durée de vie — sans quoi "
        + "la comparaison avec l’exploitation n’a aucun sens.",
        ic, R.incorpore_source,
        "les déclarations environnementales produit (FDES / EPD) des équipements "
        + "retenus : l’écart peut atteindre un facteur deux");
    }
    if (R.constantes) {
      var cst = Object.keys(R.constantes).map(function (k) {
        var v = R.constantes[k];
        return esc(v.unite ? k.replace(/_/g, " ") : k) + " : " + fr(v.valeur)
          + " " + esc(v.unite || "");
      }).join("<br>");
      h += carteRef("Constantes physiques", "physique — non négociable",
        "La chaleur latente de vaporisation de l’eau ne dépend d’aucune "
        + "technologie. Un fournisseur qui annonce moins d’eau évaporée par "
        + "kilowattheure thermique décrit un rejet partiellement sec, ou se trompe.",
        cst, (R.constantes[Object.keys(R.constantes)[0]] || {}).source, "");
    }
    if (R.classes_ashrae) {
      var as = Object.keys(R.classes_ashrae).map(function (k) {
        var v = R.classes_ashrae[k];
        return esc(k) + " : " + v.plage_c[0] + " à " + v.plage_c[1] + " °C";
      }).join(" · ");
      h += carteRef("Classes ASHRAE", "norme professionnelle",
        "Température d’air admise à l’entrée des équipements. Élargir la plage "
        + "est le levier le moins cher qui existe — il ne coûte aucun matériel — "
        + "mais il engage la garantie constructeur.",
        as, R.ashrae_source,
        "l’accord écrit du constructeur avant d’élargir la plage");
    }
    if (R.cadre_ue) {
      var C = R.cadre_ue, cu = "";
      if (C.eed_reporting) {
        cu += "<b>" + esc(C.eed_reporting.titre) + "</b><br>"
          + esc(C.eed_reporting.portee) + "<br>"
          + (C.eed_reporting.exige || []).length + " grandeurs à déclarer : "
          + (C.eed_reporting.exige || []).map(esc).join(" · ");
      }
      if (C.cndcp && C.cndcp.cibles) {
        cu += "<br><br><b>" + esc(C.cndcp.titre) + "</b><br>"
          + Object.keys(C.cndcp.cibles).map(function (k) {
              return esc(k.replace(/_/g, " ")) + " : " + esc(String(C.cndcp.cibles[k]));
            }).join(" · ");
      }
      if (C.iso30134 && C.iso30134.parties) {
        cu += "<br><br><b>" + esc(C.iso30134.titre) + "</b><br>"
          + Object.keys(C.iso30134.parties).map(function (k) {
              return esc(k) + " " + esc(C.iso30134.parties[k]);
            }).join(" · ");
      }
      if (C.en50600) cu += "<br><br><b>" + esc(C.en50600.titre) + "</b><br>"
        + esc(C.en50600.note);
      h += '<div class="dc-ref-c" style="grid-column:1/-1"><span class="n">'
        + 'cadre réglementaire et normatif</span><h4>Ce qui rend ces grandeurs '
        + 'opposables</h4><div class="v">' + cu + "</div>"
        + (C.eed_reporting && C.eed_reporting.note
            ? '<span class="rmp">▸ ' + esc(C.eed_reporting.note) + "</span>" : "")
        + "</div>";
    }
    el.innerHTML = '<div class="dc-ref">' + h + "</div>"
      + '<p class="rc-note">Référentiel <b>' + esc(REF.referentiel.version || REF.version || "")
      + '</b> — rendu depuis le moteur, pas recopié : ce que vous lisez ici est ce '
      + 'que le calcul emploie.</p>';
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
        /* Le référentiel arrive avec le formulaire : il n'attend pas qu'une
           étude soit lancée. Un lecteur doit pouvoir juger les constantes AVANT
           de décider s'il fait confiance au calcul. */
        afficherReferentiel();
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
