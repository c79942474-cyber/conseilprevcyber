/* Ingénierie de projet — IA Factory : l'étude de faisabilité chiffrée.
   ─────────────────────────────────────────────────────────────────────
   CE FICHIER NE CALCULE RIEN, NE PORTE AUCUN PRIX ET NE NOMME AUCUNE
   ENTREPRISE. Les postes, les quantités, les prix attendus, les ancrages, les
   secteurs, les phases, les jalons, les rôles du parcours et les sources
   viennent de /api/ia-factory ; le chiffrage et le planning viennent de
   /api/ia-factory/chiffrer. Une liste recopiée ici cesserait d'être vraie au
   premier poste ajouté au module, sans que rien ne le signale.

   Même discipline que les pages de centres de données : aucune requête sans
   délai, et le 401 reconnu à l'endroit unique par où passent toutes les
   requêtes. */

var DELAI_COURT = 12000;
var DELAI_MOYEN = 45000;
var SESSION_MORTE = false;

function sessionEteinte() {
  if (SESSION_MORTE) return;
  SESSION_MORTE = true;
  var b = document.createElement("div");
  b.className = "ig-session-alerte";
  b.setAttribute("role", "alert");
  b.innerHTML = "<b>Votre session n’est plus active.</b> C’est pour cela que plus rien "
    + "ne se charge ni ne se chiffre. "
    + '<a class="btn btn-s" href="/connexion?next=/ingenierie-ia-factory">Se reconnecter</a>'
    + " — vous reviendrez sur cette page.";
  var m = document.getElementById("main") || document.body;
  m.insertBefore(b, m.firstChild);
}

function messageDelai(ms) {
  return "Le serveur n’a pas répondu en " + Math.round(ms / 1000) + " s. Ce n’est pas "
    + "forcément une panne : il peut se réveiller. Réessayez dans un instant.";
}

/* L'UNIQUE PORTE. Délai borné, 401 traité une fois, erreurs rendues lisibles. */
function demander(url, options, delai) {
  var ctrl = ("AbortController" in window) ? new AbortController() : null;
  var opts = options || {};
  if (ctrl) opts.signal = ctrl.signal;
  var t = setTimeout(function () { if (ctrl) ctrl.abort(); }, delai || DELAI_COURT);
  return fetch(url, opts).then(function (r) {
    clearTimeout(t);
    if (r.status === 401) { sessionEteinte(); throw new Error("_401"); }
    return r.json().then(function (j) {
      if (!r.ok || (j && j.ok === false)) throw new Error((j && j.error) || ("HTTP " + r.status));
      return j;
    });
  }, function (e) {
    clearTimeout(t);
    if (e && e.name === "AbortError") throw new Error("_LENT:" + (delai || DELAI_COURT));
    throw e;
  });
}

(function () {
  var REF = null;
  var SECTEUR = "";
  var GUIDE_ROLE = null;
  var GUIDE_ETAPE = 0;

  function $(id) { return document.getElementById(id); }
  function esc(x) {
    return String(x == null ? "" : x).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function euro(n) {
    if (n == null) return "—";
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR",
      maximumFractionDigits: 0 }).format(n);
  }
  function nombre(n, dec) {
    if (n == null) return "—";
    return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: dec == null ? 1 : dec }).format(n);
  }
  function fourchette(a) {
    var u = a.unite === "part" ? "" : (" " + a.unite);
    var f = function (v) { return a.unite === "part" ? nombre(v * 100, 0) + " %" : nombre(v, 2); };
    return (a.min === a.max ? f(a.min) : (f(a.min) + " – " + f(a.max))) + u;
  }
  function erreur(el, e) {
    if (!el) return;
    var m = (e && e.message) || "";
    if (m === "_401") return;
    el.innerHTML = '<p class="dc-refus">' + esc(m.indexOf("_LENT:") === 0
      ? messageDelai(+m.slice(6)) : ("Indisponible : " + (m || "erreur inconnue"))) + "</p>";
  }

  /* ── LE PARCOURS GUIDÉ ────────────────────────────────────────────────
     Les rôles viennent du serveur ; la page ne connaît ni leurs noms ni les
     sections qu'ils visent. Une seule section en relief à la fois : deux
     sections en relief ne désignent plus rien. */
  function surligner(ancre) {
    document.querySelectorAll(".iaf-vise").forEach(function (e) { e.classList.remove("iaf-vise"); });
    if (!ancre) return;
    var el = $(ancre);
    if (!el) return;
    el.classList.add("iaf-vise");
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function guideOuvrir(ouvert) {
    var z = $("iaf-guide"), b = $("iaf-guide-b");
    if (!z || !b) return;
    z.hidden = !ouvert;
    b.setAttribute("aria-expanded", ouvert ? "true" : "false");
    b.textContent = ouvert ? "Fermer le parcours" : "Ouvrir le parcours guidé";
    if (!ouvert) { surligner(null); GUIDE_ROLE = null; GUIDE_ETAPE = 0; }
  }
  function guideChoix() {
    return '<p class="iaf-g-q">Qui êtes-vous sur ce projet&nbsp;?</p><div class="iaf-g-liste" role="group" aria-label="Rôle">'
      + REF.parcours.map(function (r) {
          return '<button type="button" class="iaf-g-c" data-role="' + esc(r.id) + '">'
            + '<span class="nm">' + esc(r.nom) + "</span>"
            + '<span class="qs">' + esc(r.vient_pour) + "</span></button>";
        }).join("") + "</div>";
  }
  function guideEtape() {
    var r = REF.parcours.filter(function (x) { return x.id === GUIDE_ROLE; })[0];
    if (!r) return guideChoix();
    var e = r.etapes[GUIDE_ETAPE];
    return '<div class="iaf-g-etape"><p class="iaf-g-q">' + esc(r.nom)
      + ' <span class="iaf-g-n">étape ' + (GUIDE_ETAPE + 1) + " sur " + r.etapes.length + "</span></p>"
      + "<p><b>" + esc(e.faire) + "</b></p><p>" + esc(e.obtenir) + "</p>"
      + '<div class="iaf-g-nav">'
      + (GUIDE_ETAPE > 0 ? '<button type="button" class="iaf-g-b" data-pas="-1">← Précédente</button>' : "")
      + (GUIDE_ETAPE < r.etapes.length - 1
          ? '<button type="button" class="iaf-g-b" data-pas="1">Suivante →</button>'
          : '<button type="button" class="iaf-g-b" data-fin="1">Terminer</button>')
      + '<button type="button" class="iaf-g-b iaf-g-alt" data-retour="1">Changer de rôle</button>'
      + "</div></div>";
  }
  function guideRendre() {
    var z = $("iaf-guide");
    if (!z) return;
    z.innerHTML = GUIDE_ROLE ? guideEtape() : guideChoix();
    z.querySelectorAll("[data-role]").forEach(function (b) {
      b.addEventListener("click", function () {
        GUIDE_ROLE = b.dataset.role; GUIDE_ETAPE = 0; guideRendre(); guideViser();
      });
    });
    z.querySelectorAll("[data-pas]").forEach(function (b) {
      b.addEventListener("click", function () {
        GUIDE_ETAPE += (+b.dataset.pas); guideRendre(); guideViser();
      });
    });
    var fin = z.querySelector("[data-fin]");
    if (fin) fin.addEventListener("click", function () { guideOuvrir(false); });
    var ret = z.querySelector("[data-retour]");
    if (ret) ret.addEventListener("click", function () {
      GUIDE_ROLE = null; GUIDE_ETAPE = 0; surligner(null); guideRendre();
    });
  }
  function guideViser() {
    var r = REF.parcours.filter(function (x) { return x.id === GUIDE_ROLE; })[0];
    if (r && r.etapes[GUIDE_ETAPE]) surligner(r.etapes[GUIDE_ETAPE].section);
  }

  /* ── SAISIE : un champ par quantité et par prix, dérivés du référentiel ── */
  function champs(dict, prefixe) {
    var h = "";
    Object.keys(dict).forEach(function (k) {
      var d = dict[k];
      h += '<label class="iaf-champ"><span class="iaf-nom">' + esc(d.nom)
        + ' <small>(' + esc(d.unite) + ')</small></span>'
        + '<input type="number" step="any" min="0" inputmode="decimal" data-cle="' + esc(k)
        + '" data-famille="' + prefixe + '" placeholder="non renseigné">'
        + '<span class="iaf-ou">' + esc(d.ou) + "</span></label>";
    });
    return h;
  }
  function lire(famille) {
    var out = {};
    document.querySelectorAll('input[data-famille="' + famille + '"]').forEach(function (i) {
      if (i.value !== "" && !isNaN(+i.value)) out[i.dataset.cle] = +i.value;
    });
    return out;
  }
  /* Les quantités dépendent du secteur : on redessine en CONSERVANT ce qui
     est déjà saisi — un champ vidé par un changement de secteur ferait perdre
     un travail que personne ne pense à refaire. */
  function redessinerQuantites() {
    var garde = lire("q");
    var dict = {};
    Object.keys(REF.quantites).forEach(function (k) { dict[k] = REF.quantites[k]; });
    Object.keys(REF.quantites_secteur).forEach(function (k) {
      var v = REF.quantites_secteur[k];
      if (SECTEUR && v.secteurs.indexOf(SECTEUR) >= 0) dict[k] = v;
    });
    $("iaf-q").innerHTML = champs(dict, "q");
    document.querySelectorAll('input[data-famille="q"]').forEach(function (i) {
      if (garde[i.dataset.cle] != null) i.value = garde[i.dataset.cle];
    });
  }

  /* ── LES SECTEURS ─────────────────────────────────────────────────────── */
  function rendreSecteurs() {
    var h = '<div class="iaf-sect-choix" role="group" aria-label="Secteur">'
      + Object.keys(REF.secteurs).map(function (k) {
          return '<button type="button" class="iaf-sect-b' + (SECTEUR === k ? " on" : "")
            + '" data-secteur="' + esc(k) + '">' + esc(REF.secteurs[k].nom) + "</button>";
        }).join("") + "</div>";
    if (!SECTEUR) {
      h += '<p class="dc-refus">Aucun secteur choisi : les postes, les jalons et les cas d’usage '
        + "propres au secteur ne sont pas dans l’étude, qui est de ce fait incomplète.</p>";
      return h;
    }
    var s = REF.secteurs[SECTEUR];
    h += "<p>" + esc(s.resume) + "</p>"
      + '<p class="iaf-autorites"><b>Autorités&nbsp;:</b> ' + esc(s.autorites) + "</p>"
      + "<h3>Les textes qui s’appliquent</h3><ul class=\"iaf-textes\">"
      + s.textes.map(function (t) {
          var src = REF.sources[t] || {};
          return "<li>" + (src.url
              ? '<a href="' + esc(src.url) + '" target="_blank" rel="noopener noreferrer">' + esc(src.titre) + "</a>"
              : esc(src.titre))
            + ' <span class="iaf-src">' + esc(src.editeur) + ", " + esc(src.annee)
            + " · " + esc(src.nature) + "</span></li>";
        }).join("") + "</ul>"
      + "<h3>Les cas d’usage typiques, et la case où la question se pose</h3>"
      + '<table class="moe-tab"><thead><tr><th>Cas d’usage</th><th>Classe</th><th>Pourquoi</th></tr></thead><tbody>'
      + s.cas_usage.map(function (c) {
          return "<tr><td>" + esc(c.nom) + '</td><td><span class="iaf-classe c-' + esc(c.classe)
            + '">' + esc(c.classe.replace(/_/g, " ")) + "</span><br><small>"
            + esc(REF.classes_cas[c.classe] || "") + "</small></td><td>" + esc(c.pourquoi) + "</td></tr>";
        }).join("") + "</tbody></table>"
      + '<p class="iaf-ou">La classe n’est PAS une qualification juridique : c’est la case où la '
      + "question se pose. La qualification se fait dossier par dossier.</p>"
      + '<p class="moe-recu"><b>Propre à ce secteur&nbsp;:</b> ' + esc(s.propre) + "</p>";
    if (s.secteurs_annexe_I) {
      h += "<h3>Les secteurs visés</h3><p><b>Annexe I (hautement critiques)&nbsp;:</b> "
        + esc(s.secteurs_annexe_I.join(", ")) + ".<br><b>Annexe II (autres secteurs critiques)&nbsp;:</b> "
        + esc(s.secteurs_annexe_II.join(", ")) + ".</p>";
    }
    return h;
  }
  function brancherSecteurs() {
    document.querySelectorAll("[data-secteur]").forEach(function (b) {
      b.addEventListener("click", function () {
        SECTEUR = (SECTEUR === b.dataset.secteur) ? "" : b.dataset.secteur;
        $("iaf-secteur").innerHTML = rendreSecteurs();
        brancherSecteurs();
        redessinerQuantites();
      });
    });
  }

  /* ── ANCRAGES, PHASES, JALONS, LEVIERS, SOURCES ───────────────────────── */
  function rendreComparables(cmp, sources) {
    return cmp.map(function (c) {
      return '<article class="iaf-cmp"><h4>' + esc(c.organisation) + "</h4><ul>"
        + c.chiffres.map(function (x) {
            var s = sources[x.source] || {};
            return "<li><b>" + esc(x.nom) + "</b> : " + esc(fourchette(x))
              + ' <span class="iaf-src">' + esc(s.editeur || x.source) + ", " + esc(s.annee || "")
              + "</span><br><small>Ne dit pas : " + esc(x.ne_dit_pas) + "</small></li>";
          }).join("")
        + '</ul><p class="iaf-lecon">' + esc(c.lecon) + "</p></article>";
    }).join("");
  }
  function rendrePhases(ref) {
    return '<ol class="iaf-phases">' + ref.phases.map(function (p) {
      return "<li><b>" + esc(p.nom) + "</b> — " + p.mois_min + " à " + p.mois_max + " mois"
        + '<span class="iaf-nature">usage du cabinet, ±50 %</span>'
        + '<div class="iaf-ph-g"><div><span class="iaf-ph-t">Entrée</span>' + esc(p.entree) + "</div>"
        + '<div><span class="iaf-ph-t">Sortie</span>' + esc(p.sortie) + "</div></div>"
        + '<span class="iaf-ph-t">Activités</span><ul>'
        + p.activites.map(function (a) { return "<li>" + esc(a) + "</li>"; }).join("") + "</ul>"
        + '<span class="iaf-ph-t">Livrables</span><ul>'
        + p.livrables.map(function (l) { return "<li>" + esc(l) + "</li>"; }).join("") + "</ul>"
        + "<em>Jalon : " + esc(p.jalon) + "</em></li>";
    }).join("") + "</ol>";
  }
  function rendreJalons(jal, sources) {
    return '<table class="moe-tab iaf-jalons"><thead><tr><th>Date</th><th>Texte</th><th>Ce que cela porte</th><th>État</th></tr></thead><tbody>'
      + jal.map(function (j) {
          var s = sources[j.source] || {};
          return "<tr" + (j.passe ? ' class="passe"' : "") + "><td>" + esc(j.date) + "</td><td>"
            + esc(j.texte) + (s.url ? ' <a href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">texte</a>' : "")
            + "</td><td>" + esc(j.porte) + "</td><td>"
            + (j.passe ? "en vigueur" : (j.avant_fin_projet ? "tombe pendant le projet" : "après le projet"))
            + "</td></tr>";
        }).join("") + "</tbody></table>";
  }
  function rendreLeviers(liste, sources, ancrages) {
    var parCle = {};
    ancrages.forEach(function (a) { parCle[a.cle] = a; });
    return '<ul class="iaf-leviers">' + liste.map(function (l) {
      var a = l.ancrage ? (parCle[l.ancrage] || null) : null;
      var s = l.ancrage ? (sources[l.ancrage] || null) : null;
      var ref = a ? (esc(a.nom) + " : " + esc(fourchette(a)))
        : (s ? esc(s.editeur) + ", " + esc(s.annee) : "convention du cabinet, à discuter");
      return "<li><b>" + esc(l.nom) + "</b><br>" + esc(l.dit)
        + (l.publics ? '<br><span class="iaf-ph-t">Publics</span>' + esc(l.publics) : "")
        + (l.mesure ? '<br><span class="iaf-ph-t">Mesure</span>' + esc(l.mesure) : "")
        + (l.geste ? '<br><span class="iaf-ph-t">Geste</span>' + esc(l.geste) : "")
        + '<br><span class="iaf-src">Ancrage — ' + ref + "</span></li>";
    }).join("") + "</ul>";
  }
  function rendreSources(sources, couv) {
    var h = '<p class="iaf-couv">' + couv.total + " sources — " + couv.avec_adresse
      + " avec adresse, <b>" + couv.lues + " lue(s) depuis ce poste</b>. " + esc(couv.limite)
      + "</p><ol class=\"iaf-sources\">";
    Object.keys(sources).forEach(function (k) {
      var s = sources[k];
      h += "<li>" + (s.url
          ? '<a href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">' + esc(s.titre) + "</a>"
          : '<span class="iaf-muet">' + esc(s.titre) + '</span> <span class="na-src-sans">sans adresse</span>')
        + " — <em>" + esc(s.editeur) + "</em>, " + esc(s.annee)
        + ' <span class="iaf-nature">' + esc(s.nature) + "</span>"
        + (s.reserve ? "<br><small>" + esc(s.reserve) + "</small>" : "") + "</li>";
    });
    return h + "</ol>";
  }

  /* ── CHIFFRAGE ───────────────────────────────────────────────────────── */
  function rendreChiffrage(c, ref) {
    var titres = {};
    ref.groupes.forEach(function (g) { titres[g[0]] = g[1]; });
    var h = "";
    if (c.alertes && c.alertes.length) {
      h += '<div class="dc-refus"><ul>' + c.alertes.map(function (a) { return "<li>" + esc(a) + "</li>"; }).join("") + "</ul></div>";
    }
    h += '<table class="moe-tab"><thead><tr><th>Poste</th><th>Formule</th><th>Montant</th></tr></thead><tbody>';
    ref.groupes.forEach(function (g) {
      var lignes = c.lignes.filter(function (l) { return l.groupe === g[0]; });
      if (!lignes.length && g[0] !== "aleas") return;
      h += '<tr class="iaf-grp"><td colspan="3">' + esc(g[1]) + "</td></tr>";
      lignes.forEach(function (l) {
        h += "<tr" + (l.statut === "non_chiffre" ? ' class="ouv"' : "") + "><td>" + esc(l.nom)
          + (l.sectoriel ? ' <span class="iaf-classe">secteur</span>' : "")
          + (l.couvre ? "<br><small><b>Couvre :</b> " + esc(l.couvre) + "</small>" : "")
          + (l.exclut ? "<br><small><b>Exclut :</b> " + esc(l.exclut) + "</small>" : "")
          + (l.note ? "<br><small>" + esc(l.note) + "</small>" : "")
          + "</td><td><code>" + esc(l.formule) + "</code></td><td>"
          + (l.statut === "chiffre" ? euro(l.montant)
             : '<span class="moe-asaisir">non chiffré</span><br><small>manque : ' + esc(l.manque.join(", ")) + "</small>")
          + "</td></tr>";
      });
      if (g[0] === "aleas") {
        h += "<tr><td>Provision pour aléas</td><td><code>sous-total × taux saisi</code></td><td>"
          + (c.provision == null ? '<span class="moe-asaisir">non saisie</span>' : euro(c.provision)) + "</td></tr>";
      }
    });
    h += "</tbody></table>";
    h += '<p class="moe-tot">' + (c.total == null ? "Sous-total chiffré : " + euro(c.sous_total)
        : "Total : " + euro(c.total))
      + ' <span class="note">— ' + c.n_non_chiffres + " poste(s) sur " + c.n_postes + " non chiffré(s), soit "
      + nombre(c.part_non_chiffree * 100, 0) + " % de la structure</span></p>";
    return h;
  }
  function rendreDim(d) {
    if (!d.instruit) {
      return '<p class="dc-refus">' + esc(d.dit) + " Manque : " + esc(d.manque.join(", ")) + "</p>";
    }
    return "<p><b>Constructeurs de modèles</b> : " + nombre(d.roles.constructeurs.max, 1) + " ETP — "
      + esc(d.roles.constructeurs.dit) + "</p><p><b>Plateforme et data</b> : "
      + nombre(d.roles.plateforme.min, 1) + " à " + nombre(d.roles.plateforme.max, 1) + " ETP — "
      + esc(d.roles.plateforme.dit) + '</p><p class="moe-tot">Équipe centrale : '
      + nombre(d.total.min, 1) + " à " + nombre(d.total.max, 1) + " ETP"
      + ' <span class="note">— ' + esc(d.dit) + "</span></p>";
  }
  function rendrePlanning(pl) {
    var h = "<p>Début " + esc(pl.debut) + " · fin au plus tôt <b>" + esc(pl.fin_projet.tot)
      + "</b>, au plus tard <b>" + esc(pl.fin_projet.tard) + "</b>.</p>";
    if (pl.migration) {
      h += '<p class="moe-recu">Migration de cœur en parallèle : ' + pl.migration.mois_min + " à "
        + pl.migration.mois_max + " mois (fin au plus tard " + esc(pl.migration.fin_tard) + "). "
        + esc(pl.migration.dit) + "</p>";
    }
    h += '<table class="moe-tab"><thead><tr><th>Phase</th><th>Début (tôt)</th><th>Fin (tôt)</th><th>Fin (tard)</th></tr></thead><tbody>'
      + pl.phases.map(function (p) {
          return "<tr><td>" + esc(p.nom) + "</td><td>" + esc(p.debut_tot) + "</td><td>" + esc(p.fin_tot) + "</td><td>" + esc(p.fin_tard) + "</td></tr>";
        }).join("") + "</tbody></table>";
    h += "<h4>Jalons réglementaires, replacés dans ce calendrier</h4>" + rendreJalons(pl.jalons_reglementaires, REF.sources);
    return h;
  }

  function chiffrer() {
    var out = $("iaf-out"), dim = $("iaf-dim"), pla = $("iaf-planning");
    out.innerHTML = "<p>Chiffrage en cours…</p>";
    var prov = $("iaf-provision").value;
    var corps = { quantites: lire("q"), prix: lire("p"), secteur: SECTEUR || null,
      provision_pct: prov === "" ? null : (+prov) / 100, debut: $("iaf-debut").value || null };
    demander("/api/ia-factory/chiffrer", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) }, DELAI_MOYEN)
      .then(function (j) {
        out.innerHTML = rendreChiffrage(j.chiffrage, REF);
        dim.innerHTML = rendreDim(j.chiffrage.dimensionnement);
        pla.innerHTML = rendrePlanning(j.planning);
      }, function (e) { erreur(out, e); });
  }

  function init() {
    demander("/api/ia-factory", null, DELAI_COURT).then(function (j) {
      REF = j.referentiel;
      $("iaf-secteur").innerHTML = rendreSecteurs();
      brancherSecteurs();
      redessinerQuantites();
      $("iaf-p").innerHTML = champs(REF.prix, "p");
      $("iaf-cmp").innerHTML = rendreComparables(REF.comparables, REF.sources);
      $("iaf-phases").innerHTML = rendrePhases(REF);
      $("iaf-jalons").innerHTML = rendreJalons(REF.jalons_reglementaires.map(function (x) {
        return Object.assign({}, x, { passe: x.date <= new Date().toISOString().slice(0, 10), avant_fin_projet: true });
      }), REF.sources);
      $("iaf-changement").innerHTML = rendreLeviers(REF.leviers_changement, REF.sources, REF.ancrages);
      $("iaf-migration").innerHTML = rendreLeviers(REF.principes_migration, REF.sources, REF.ancrages);
      $("iaf-sources").innerHTML = rendreSources(REF.sources, REF.couverture_sources);
      $("iaf-limite").textContent = REF.limite;
      $("iaf-go").addEventListener("click", chiffrer);
      $("iaf-debut").value = new Date().toISOString().slice(0, 10);
      guideRendre();
      $("iaf-guide-b").addEventListener("click", function () {
        guideOuvrir($("iaf-guide").hidden);
      });
    }, function (e) { erreur($("iaf-q"), e); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
