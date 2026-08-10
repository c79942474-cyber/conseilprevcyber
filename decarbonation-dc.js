/* La plateforme de décarbonation — deux voies, une hiérarchie, et l'ordre.
 *
 * CE QUE CETTE PAGE DOIT TENIR, ET QU'UNE PAGE DE PLUS NE TIENDRAIT PAS :
 *
 *   1. L'ORDRE DE LA HIÉRARCHIE EST L'INFORMATION. Aucun tri n'est proposé, et
 *      c'est délibéré : trier par gain attendu ferait remonter la compensation,
 *      qui est le levier le plus rapide à acheter et le seul qui ne réduise
 *      rien. Les rangs arrivent du serveur déjà ordonnés et sont rendus tels.
 *
 *   2. LES DEUX ZONES NE SE CONTREDISENT JAMAIS. La frise et le bloc du
 *      dessous parlent du même objet. Le message d'attente est donc écrit
 *      depuis UN SEUL endroit — `rendreParcours` — parce que la version
 *      précédente de cette famille de pages l'écrivait de trois endroits et
 *      annonçait une frise « à venir » alors qu'elle venait d'apparaître.
 *
 *   3. UN CHAMP PAR DÉFAUT N'EST PAS UN CHAMP RENSEIGNÉ. C'est le serveur qui
 *      en décide, jamais la page : réimplémenter la règle ici la ferait
 *      diverger au premier ajustement, et c'est le parcours qu'on aurait cru.
 */
(function () {
  "use strict";

  var REF = null;        // référentiel du moteur (champs du formulaire)
  var CADRE = null;      // référentiel de décarbonation (voies, rangs, textes)
  var VOIE = null;       // voie active
  var ETAPE = null;      // étape choisie
  var DERNIER = {};      // dernier parcours reçu, par voie
  var vague = null;

  function $(s) { return document.querySelector(s); }
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function fr(x) {
    if (typeof x !== "number" || !isFinite(x)) return "—";
    var s = Math.abs(x) >= 100 ? Math.round(x).toString()
          : Math.abs(x) >= 10 ? x.toFixed(1)
          : x.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
    return s.replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }
  function etat(msg, err) {
    var el = $("#dk-etat");
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = err ? "var(--red, #F0A0A0)" : "";
  }

  function profil() {
    var p = {};
    document.querySelectorAll("#dk-form [data-champ]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v !== "") p[el.getAttribute("data-champ")] = v;
    });
    return p;
  }

  function poster(url, corps) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps),
    }).then(function (r) {
      return r.text().then(function (t) {
        var j = null;
        try { j = JSON.parse(t); } catch (e) { j = null; }
        /* Une réponse non-JSON est un incident de SERVEUR, pas un refus
           métier. Les confondre envoyait le lecteur vérifier sa saisie pendant
           qu'une passerelle renvoyait du HTML. */
        if (!j) throw new Error("Le serveur a répondu une erreur (HTTP "
          + r.status + "). Réessayez dans un instant.");
        if (!r.ok || !j.ok) throw new Error(j.message || j.error || ("HTTP " + r.status));
        return j;
      });
    });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE FORMULAIRE — dérivé du référentiel, jamais recopié
     ═════════════════════════════════════════════════════════════════════ */

  function batirFormulaire() {
    var champs = (REF && REF.champs) || [];
    var h = '<div class="dc-grille">';
    champs.forEach(function (c) {
      var id = "dk-" + c.id;
      /* Un seul `label` par champ, et le libellé dans un `span` : imbriquer
         deux `label` casse l'association avec le contrôle, et un lecteur
         d'écran annonce alors le champ sans son nom. */
      h += '<label class="dc-champ" for="' + id + '" data-champ-bloc="' + esc(c.id) + '">'
        + '<span class="lab">' + esc(c.label)
        + (c.unite ? " (" + esc(c.unite) + ")" : "")
        + (c.requis ? " *" : "") + "</span>";
      if (c.type === "liste") {
        h += '<select id="' + id + '" data-champ="' + esc(c.id) + '">'
          + '<option value="">— non précisé —</option>';
        (c.options || []).forEach(function (o) {
          var lib = (c.options_nom && c.options_nom[o]) || o;
          h += '<option value="' + esc(o) + '"'
            + (c.defaut === o ? " selected" : "") + ">" + esc(lib) + "</option>";
        });
        h += "</select>";
      } else {
        h += '<input id="' + id + '" data-champ="' + esc(c.id) + '" type="text" '
          + 'inputmode="decimal"'
          + (c.defaut !== undefined ? ' value="' + esc(c.defaut) + '"' : "")
          + ' placeholder="' + (c.defaut !== undefined ? esc(c.defaut) : "—") + '">';
      }
      if (c.aide) h += '<span class="aide">' + esc(c.aide) + "</span>";
      h += "</label>";
    });
    h += "</div>";
    $("#dk-form").innerHTML = h;
    $("#dk-form").addEventListener("input", planifierVague);
    $("#dk-form").addEventListener("change", planifierVague);
  }

  /* Une saisie ne déclenche pas une requête par frappe : on attend que la main
     s'arrête. Sans cela, remplir « 50000 » lance cinq parcours dont quatre
     seront jetés — et le limiteur de débit, lui, les compte tous. */
  function planifierVague() {
    if (vague) clearTimeout(vague);
    vague = setTimeout(charger, 420);
  }

  /* ═════════════════════════════════════════════════════════════════════
     LES DEUX VOIES
     ═════════════════════════════════════════════════════════════════════ */

  function rendreVoies() {
    var z = $("#dk-voies");
    if (!z || !CADRE) return;
    var h = "";
    Object.keys(CADRE.voies).forEach(function (k) {
      var v = CADRE.voies[k];
      h += '<button type="button" role="tab" data-voie="' + esc(k) + '" '
        + 'aria-selected="' + (k === VOIE ? "true" : "false") + '">'
        + "<b>" + esc(v.nom) + "</b>"
        + "<span>" + esc(k === "inventaire" ? "la preuve" : "l'action") + "</span>"
        + "</button>";
    });
    z.innerHTML = h;
    z.querySelectorAll("[data-voie]").forEach(function (b) {
      b.addEventListener("click", function () {
        VOIE = b.getAttribute("data-voie");
        ETAPE = null;
        marquerURL();
        rendreVoies();
        rendreCadre();
        rendreParcours();
      });
    });
  }

  function rendreCadre() {
    var z = $("#dk-cadre");
    if (!z || !CADRE || !VOIE) return;
    var v = CADRE.voies[VOIE];
    z.innerHTML = '<div class="dk-res"><b>' + esc(v.nom) + ".</b> " + esc(v.portee)
      + '</div><div class="dk-tx"><h4>Cadre applicable</h4><p>' + esc(v.cadre)
      + "</p>" + (v.note ? '<p class="res">' + esc(v.note) + "</p>" : "")
      + "</div>";
  }

  /* ═════════════════════════════════════════════════════════════════════
     LA FRISE, ET LE BLOC QUI LA COMMENTE

     Les deux zones sont écrites d'ici, et d'ici seulement. C'est le défaut
     déjà corrigé sur la page d'ingénierie : le bloc du dessous annonçait une
     frise « à venir » alors qu'elle venait d'apparaître.
     ═════════════════════════════════════════════════════════════════════ */

  function friseVide() {
    return !DERNIER[VOIE] || !(DERNIER[VOIE].etapes || []).length;
  }

  function messageAttente() {
    return '<p class="note">La frise des étapes apparaîtra ci-dessus dès que la '
      + "<b>puissance informatique installée</b> sera renseignée : c'est le seul "
      + "champ nécessaire, les autres ont une valeur par défaut. "
      + '<button type="button" class="dk-vers" data-vers-champ>Aller au champ</button></p>';
  }

  function rendreParcours() {
    var z = $("#dk-parcours");
    var d = $("#dk-dossier");
    if (!z) return;
    if (friseVide()) {
      z.innerHTML = '<p class="note">Pour éprouver les étapes, il manque la '
        + "<b>puissance informatique installée</b> — le seul champ nécessaire de "
        + "ce formulaire. "
        + '<button type="button" class="dk-vers" data-vers-champ>Aller au champ</button></p>';
      if (d) d.innerHTML = messageAttente();
      return;
    }
    var P = DERNIER[VOIE], stop = P.premier_blocage;
    var h = "";
    /* La conclusion AVANT les données : placée dessous, elle se lit après que
       le lecteur s'est fait sa propre idée, et ne sert plus à rien. */
    if (stop) {
      var e = P.etapes.filter(function (x) { return x.code === stop; })[0] || {};
      h += '<p class="dk-res">Vous tenez <b>' + P.n_franchissables + "</b> étape"
        + (P.n_franchissables > 1 ? "s" : "") + " sur " + P.n_total
        + ". Le travail à engager est celui de <b>" + esc(stop) + " — "
        + esc(e.nom || "") + "</b> : "
        + esc(e.aptitude ? e.aptitude.verdict : "") + "</p>";
    } else {
      h += '<p class="dk-res">Toutes les étapes de cette voie sont franchissables au '
        + "regard de ce moteur. Cela ne veut pas dire que la démarche est complète : "
        + "la mesure, les contrats et la vérification par un tiers ne s'éprouvent "
        + "pas ici.</p>";
    }
    h += '<div class="dk-fr" role="tablist" aria-label="Étapes">';
    P.etapes.forEach(function (x) {
      var n = x.n_manques + x.n_substitutions;
      var cl = "dk-e " + (x.franchissable ? "ok" : "ko")
        + (x.code === stop ? " stop" : "") + (x.code === ETAPE ? " on" : "");
      h += '<button type="button" class="' + cl + '" data-etape="' + esc(x.code) + '" '
        + 'role="tab" aria-selected="' + (x.code === ETAPE ? "true" : "false") + '">'
        + '<span class="c">' + x.rang + ". " + esc(x.code) + "</span>"
        + '<span class="n">' + esc(x.nom) + "</span>"
        + '<span class="e">' + (x.franchissable ? "franchissable"
            : n + " point" + (n > 1 ? "s" : "") + " ouvert" + (n > 1 ? "s" : ""))
        + "</span></button>";
    });
    h += "</div>";
    z.innerHTML = h;

    /* Quand aucune étape n'est choisie, le bloc du dessous le dit — et c'est
       ici, pas ailleurs, qu'il l'apprend. */
    if (!ETAPE && d) {
      d.innerHTML = '<p class="note">Choisissez une étape dans la frise ci-dessus.</p>';
    }
    z.querySelectorAll("[data-etape]").forEach(function (b) {
      b.addEventListener("click", function () {
        ETAPE = b.getAttribute("data-etape");
        marquerURL();
        rendreParcours();
        chargerDossier();
      });
    });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE DOSSIER D'UNE ÉTAPE
     ═════════════════════════════════════════════════════════════════════ */

  function chargerDossier() {
    var z = $("#dk-dossier");
    if (!z || !ETAPE) return;
    /* On ne VIDE le panneau que s'il montre autre chose que cette étape. Une
       simple actualisation — le formulaire vient de bouger, le parcours est
       redemandé — le remplaçait par « Chargement… », donc par un bloc court :
       la page se raccourcissait d'un millier de pixels puis se rallongeait, et
       tout ce qui se trouvait dessous sautait sous le doigt du lecteur. Le
       contenu affiché reste juste jusqu'à ce que le nouveau arrive. */
    if (z.getAttribute("data-etape") !== ETAPE) {
      z.innerHTML = '<p class="note">Chargement de l’étape…</p>';
      z.setAttribute("data-etape", ETAPE);
    }
    var p = profil();
    p.etape = ETAPE;
    poster("/api/datacenter/decarbonation/dossier", p)
      .then(function (j) { rendreDossier(j.dossier); })
      .catch(function (e) {
        z.innerHTML = '<p class="note">' + esc(e.message || "Étape indisponible.")
          + "</p>";
      });
  }

  function rendreDossier(d) {
    var z = $("#dk-dossier");
    if (!z) return;
    if (!d.disponible) {
      z.innerHTML = '<p class="note">' + esc(d.motif || "Étape indisponible.")
        + "</p>";
      return;
    }
    var a = d.aptitude || {};
    var h = '<div class="dk-do"><h3>' + esc(d.code) + " — " + esc(d.nom) + "</h3>"
      + '<p class="obj">' + esc(d.objet) + "</p>";

    h += '<div class="dk-b"><b>Ce que cette étape décide</b><p>'
      + esc(d.decide) + "</p></div>";
    h += '<div class="dk-b"><p class="dk-verr"><b>Ce qu\'elle verrouille.</b> '
      + esc(d.verrouille) + "</p></div>";
    h += '<div class="dk-b"><p class="dk-preuve"><b>Ce qui la prouve.</b> '
      + esc(d.preuve) + "</p></div>";

    /* CE QUI MANQUE, avant ce qui est acquis. L'ordre inverse laisse le
       lecteur sur l'impression d'un dossier complet. */
    if ((a.entrees_manquantes || []).length) {
      h += '<div class="dk-b"><b>Entrées à renseigner</b>';
      a.entrees_manquantes.forEach(function (m) {
        h += '<div class="dk-manque"><div class="t">' + esc(m.label)
          + (m.unite ? " (" + esc(m.unite) + ")" : "") + "</div>"
          + '<div class="p">' + esc(m.pourquoi)
          + (m.origine === "heritee"
              ? " — dette d'une étape précédente de cette voie"
              : " — propre à cette étape")
          + "</div>"
          + '<button type="button" class="dk-vers" data-vers-champ="' + esc(m.id)
          + '">Aller au champ</button></div>';
      });
      h += "</div>";
    }
    if ((a.substitutions_a_faire || []).length) {
      h += '<div class="dk-b"><b>Facteurs dont l\'ordre de grandeur ne suffit plus</b>';
      a.substitutions_a_faire.forEach(function (s) {
        h += '<div class="dk-manque"><div class="t">' + esc(s.nom)
          + (s.incertitude ? " — " + esc(s.incertitude) : "")
          + (s.incertitude_absente
              ? " — aucune incertitude déclarée au référentiel" : "")
          + "</div>";
        if (s.remplacer_par) {
          h += '<div class="p"><b>Remplacer par :</b> ' + esc(s.remplacer_par) + "</div>";
        }
        if (s.devient_insuffisant) {
          h += '<div class="p">' + esc(s.devient_insuffisant) + "</div>";
        }
        h += "</div>";
      });
      h += "</div>";
    }

    /* CE QUI A ÉTÉ REMPLACÉ. Le taire laisserait le relecteur croire que le
       chiffre vient encore de la valeur générique du référentiel — et il
       redemanderait un travail déjà fait. */
    if ((a.substitutions_faites || []).length) {
      h += '<div class="dk-b"><b>Facteurs déjà remplacés par une donnée du dossier</b>';
      a.substitutions_faites.forEach(function (s) {
        h += '<p class="dk-preuve"><b>' + esc(s.nom) + ".</b> Renseigné au "
          + "formulaire : le moteur emploie cette valeur et non la valeur "
          + "générique du référentiel.</p>";
      });
      h += "</div>";
    }

    if ((d.grandeurs || []).length) {
      h += '<div class="dk-b"><b>Ce que le moteur verse à cette étape</b>'
        + '<p style="margin-bottom:8px">' + esc(d.apport_texte) + "</p>"
        + '<div class="dk-g">';
      d.grandeurs.forEach(function (g) {
        h += '<div class="dk-gr ' + esc(g.statut) + '">'
          + '<div class="v">' + fr(g.valeur) + " " + esc(g.unite) + "</div>"
          + '<div class="l">' + esc(g.nom)
          + (g.incertitude ? " · " + esc(g.incertitude) : "") + "</div>"
          + '<span class="s">'
          + (g.statut === "recevable" ? "recevable ici" : "à remplacer ici")
          + "</span>";
        if ((g.postes_bloquants || []).length) {
          h += '<p class="bloq">Tenu par : ' + esc(g.postes_bloquants.join(", "))
            + "</p>";
        }
        h += "</div>";
      });
      h += "</div></div>";
    }

    if ((d.leviers_engages || []).length) {
      h += '<div class="dk-b"><b>Les leviers de cette étape</b>';
      d.leviers_engages.forEach(function (lv) { h += bloclevier(lv); });
      h += "</div>";
    }

    h += '<div class="dk-b"><b>Plan du livrable</b><ul>'
      + (d.sections || []).map(function (s) {
          return "<li>" + esc(s) + "</li>"; }).join("")
      + "</ul></div>";

    if ((d.textes || []).length) {
      h += '<div class="dk-b"><b>Textes applicables à cette étape</b>';
      d.textes.forEach(function (t) { h += bloctexte(t); });
      h += "</div>";
    }

    if ((d.rendez_vous || []).length) {
      h += '<div class="dk-b"><b>Point de rendez-vous avec l\'autre voie</b>';
      d.rendez_vous.forEach(function (r) {
        h += '<p class="dk-rdv"><b>' + esc(r.inventaire) + " ↔ " + esc(r.trajectoire)
          + "</b> — " + esc(r.lien) + "</p>";
      });
      h += "</div>";
    }

    h += "</div>";
    z.innerHTML = h;
  }

  function bloclevier(lv) {
    var h = '<div class="dk-lv"><h4>' + esc(lv.nom)
      + (lv.champ ? '<span class="dk-ch">agit sur : ' + esc(lv.champ.label)
          + "</span>" : "") + "</h4>";
    if (!lv.champ && lv.sans_champ) {
      h += '<p class="dk-nch">' + esc(lv.sans_champ) + "</p>";
    }
    h += "<p>" + esc(lv.effet) + "</p>";
    h += '<p class="non"><b>Ce qu\'il ne fait pas.</b> ' + esc(lv.ne_fait_pas) + "</p>";
    h += '<p class="pi"><b>Le piège.</b> ' + esc(lv.piege) + "</p>";
    return h + "</div>";
  }

  function bloctexte(t) {
    return '<div class="dk-tx"><h4>' + esc(t.nom)
      + '<span class="dk-po p-' + esc(t.portee) + '">' + esc(t.portee) + "</span>"
      + "</h4><p>" + esc(t.dit) + "</p>"
      + '<p class="res" style="font-style:italic">' + esc(t.portee_texte) + "</p>"
      + (t.reserve ? '<p class="res">' + esc(t.reserve) + "</p>" : "")
      + "</div>";
  }

  /* ═════════════════════════════════════════════════════════════════════
     LA HIÉRARCHIE ET LES TEXTES — rendus une fois, dans l'ordre du serveur
     ═════════════════════════════════════════════════════════════════════ */

  function rendreHierarchie() {
    var z = $("#dk-hierarchie");
    if (!z || !CADRE) return;
    var h = "";
    (CADRE.hierarchie || []).forEach(function (r) {
      h += '<div class="dk-h r' + r.rang + '">'
        + '<div class="dk-h-t"><span class="o">Rang ' + r.rang + "</span>"
        + "<h3>" + esc(r.nom) + "</h3></div>"
        + '<p class="dk-h-p">' + esc(r.principe) + "</p>"
        + '<p class="dk-h-pr">Ce qui le prouve : ' + esc(r.preuve) + "</p>";
      (r.leviers || []).forEach(function (lv) { h += bloclevier(lv); });
      h += "</div>";
    });
    z.innerHTML = h;
  }

  function rendreTextes() {
    var z = $("#dk-textes");
    if (!z || !CADRE) return;
    z.innerHTML = (CADRE.textes || []).map(bloctexte).join("");
    var a = $("#dk-avert");
    if (a && CADRE.avertissement) {
      a.innerHTML = '<p class="dk-av"><b>Ce que cette page ne fait pas.</b> '
        + esc(CADRE.avertissement) + "</p>";
    }
  }

  /* ═════════════════════════════════════════════════════════════════════
     ALLER AU CHAMP — un défilement seul laisse devant treize champs pareils
     ═════════════════════════════════════════════════════════════════════ */

  function versChamp(cid) {
    var sel = cid ? '#dk-form [data-champ="' + cid + '"]' : "#dk-puissance-cible";
    var el = document.querySelector(
      cid ? sel : '#dk-form [data-champ="puissance_it_kw"]');
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); }
    var bloc = el.closest("[data-champ-bloc]") || el;
    bloc.classList.add("dk-designe");
    /* La désignation s'efface : une mise en évidence permanente devient du
       décor, et cesse de désigner quoi que ce soit. */
    setTimeout(function () { bloc.classList.remove("dk-designe"); }, 2600);
  }

  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("[data-vers-champ]");
    if (!b) return;
    ev.preventDefault();
    versChamp(b.getAttribute("data-vers-champ") || "puissance_it_kw");
  });

  /* ═════════════════════════════════════════════════════════════════════
     LA PAGE EST ADRESSABLE

     Sans cela, un livrable qui renvoie à « SUBST, la substitution d'énergie »
     ne peut pointer que vers le haut de la page, à charge pour le lecteur de
     retrouver la voie puis l'étape. Un lien qui oblige à chercher n'est pas
     un lien. La forme #voie=trajectoire&etape=SUBST se lit à l'œil sur un
     document imprimé, ce qu'un identifiant opaque ne permettrait pas.
     ═════════════════════════════════════════════════════════════════════ */

  function lireURL() {
    var h = (window.location.hash || "").replace(/^#/, "");
    if (!h) return {};
    var o = {};
    h.split("&").forEach(function (p) {
      var kv = p.split("=");
      if (kv.length === 2) o[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1]);
    });
    return o;
  }

  function marquerURL() {
    if (!VOIE) return;
    var h = "#voie=" + encodeURIComponent(VOIE)
      + (ETAPE ? "&etape=" + encodeURIComponent(ETAPE) : "");
    /* replaceState et non pushState : parcourir les étapes n'est pas une
       navigation, et empiler douze entrées rendrait le bouton « précédent »
       du navigateur inutilisable. */
    try { history.replaceState(null, "", h); } catch (e) { /* sans effet */ }
  }

  /* ═════════════════════════════════════════════════════════════════════
     CHARGEMENT
     ═════════════════════════════════════════════════════════════════════ */

  function charger() {
    var p = profil();
    if (!p.puissance_it_kw) {
      DERNIER = {};
      etat("");
      rendreParcours();
      return;
    }
    etat("Calcul des deux voies…");
    poster("/api/datacenter/decarbonation/parcours", p)
      .then(function (j) {
        DERNIER = j.parcours || {};
        etat("");
        rendreParcours();
        if (ETAPE) chargerDossier();
      })
      .catch(function (e) {
        DERNIER = {};
        etat(e.message || "Le parcours n'a pas pu être établi.", true);
        rendreParcours();
      });
  }

  function demarrer() {
    var u = lireURL();
    Promise.all([
      fetch("/api/datacenter/referentiel").then(function (r) { return r.json(); }),
      fetch("/api/datacenter/decarbonation").then(function (r) { return r.json(); }),
    ]).then(function (rs) {
      if (!rs[0].ok || !rs[1].ok) throw new Error("référentiel indisponible");
      REF = rs[0];
      CADRE = rs[1].referentiel;
      VOIE = (u.voie && CADRE.voies[u.voie]) ? u.voie : Object.keys(CADRE.voies)[0];
      ETAPE = u.etape || null;
      batirFormulaire();
      rendreVoies();
      rendreCadre();
      rendreHierarchie();
      rendreTextes();
      rendreParcours();
      charger();
    }).catch(function () {
      var f = $("#dk-form");
      if (f) {
        f.innerHTML = '<p class="note">Le référentiel n’a pas pu être chargé. '
          + 'Le <a href="/datacenter">calcul énergie, eau et carbone</a> '
          + "fonctionne indépendamment.</p>";
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }
})();
