/* L'ACCOMPAGNEMENT DE LA PAGE /securite-ia.
   ═══════════════════════════════════════════════════════════════════════
   Quatre choses, toutes nourries par /api/securite-ia/accompagnement — ce
   fichier ne porte aucun texte d'accompagnement, aucune définition, aucun
   niveau de gravité :

   · LE CADRAGE : secteur, statut NIS 2, valeur métier, gravité, périmètre.
     Exposé par `window.SIA.cadrage()` au script de la chaîne, qui l'envoie
     avec chaque calcul et chaque export.
   · LA BARRE DE PROGRESSION : une étape par phase, « faite » quand la page
     CONSTATE ce qui la clôt — jamais sur déclaration.
   · UN ENCADRÉ PAR PHASE : ce qu'on y fait, ce qu'il faut préparer, qui doit
     être là, comment lire, la décision éclairée, le piège, et les sources.
   · LES INFO-BULLES : tout bouton `.tipi[data-terme]` reçoit sa définition
     et sa source, y compris ceux que le script de la chaîne peint après coup.
   Et l'AIDE À LA DÉCISION, peinte à partir de ce que rend /evaluer. */
(function () {
  "use strict";

  var ACC = null;
  var FAIT = {};          // cle de phase -> true quand constatée
  var GLOS = {};
  var $ = function (s) { return document.getElementById(s); };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ── LE CADRAGE ───────────────────────────────────────────────────────── */
  function cadrage() {
    var g = $("sia-gravite") ? $("sia-gravite").value : "";
    return {
      secteur: $("sia-secteur") ? $("sia-secteur").value : "",
      statut_nis2: $("sia-nis2") ? $("sia-nis2").value : "",
      valeur_metier: $("sia-valeur") ? $("sia-valeur").value.trim() : "",
      gravite: g ? parseInt(g, 10) : null,
      perimetre: $("sia-perimetre") ? $("sia-perimetre").value.trim() : ""
    };
  }
  window.SIA = { cadrage: cadrage };

  function remplirCadrage() {
    var o = '<option value="">—</option>';
    $("sia-secteur").innerHTML = o + ACC.secteurs.map(function (s) {
      return '<option value="' + esc(s.cle) + '">' + esc(s.nom) + "</option>"; }).join("");
    $("sia-nis2").innerHTML = o + ACC.statuts_nis2.map(function (s) {
      return '<option value="' + esc(s.cle) + '">' + esc(s.nom) + "</option>"; }).join("");
    $("sia-gravite").innerHTML = o + ACC.gravites.map(function (g) {
      return '<option value="' + g.niveau + '">G' + g.niveau + " · " + esc(g.nom) + "</option>"; }).join("");
  }

  function surCadrage(ev) {
    if (ev && ev.target && ev.target.id === "sia-secteur") {
      var s = ACC.secteurs.filter(function (x) { return x.cle === ev.target.value; })[0];
      $("sia-valeurs").innerHTML = (s ? s.valeurs : []).map(function (v) {
        return '<option value="' + esc(v) + '"></option>'; }).join("");
    }
    var g = ACC.gravites.filter(function (x) { return String(x.niveau) === $("sia-gravite").value; })[0];
    $("sia-gravite-dit").textContent = g ? g.dit : "";
    var c = cadrage();
    FAIT.cadrage = !!(c.valeur_metier && c.gravite);
    peindreProgression();
    document.dispatchEvent(new CustomEvent("sia:cadrage", { detail: c }));
  }

  /* ── LES INFO-BULLES ──────────────────────────────────────────────────── */
  function remplirBulles(racine) {
    (racine || document).querySelectorAll(".tipi[data-terme]:not([data-tip])").forEach(function (b) {
      var t = GLOS[b.getAttribute("data-terme")];
      if (!t) return;
      var src = t.source ? " Source : " + t.source.titre + "." : "";
      b.setAttribute("data-tip", t.definition + src);
      b.setAttribute("aria-label", "Définition : " + t.terme + " — " + t.definition + src);
    });
  }

  /* ── LES ENCADRÉS PAR PHASE ───────────────────────────────────────────── */
  function encadre(p, i) {
    var src = p.sources.map(function (s) {
      var t = s.url ? '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.titre) + "</a>"
                    : "<b>" + esc(s.titre) + "</b>";
      return "<li>" + t + (s.date ? " — " + esc(s.date) : "")
        + ' <span class="sia-lic">· ' + esc(s.licence) + "</span>"
        + (s.apporte ? "<br>" + esc(s.apporte) : "") + "</li>";
    }).join("");
    return '<details class="sia-acc" data-phase="' + esc(p.cle) + '"' + (i === 0 ? " open" : "") + ">"
      + "<summary>Étape " + (i + 1) + " — " + esc(p.titre) + " · accompagnement</summary>"
      + '<div class="sia-acc-c">'
      + "<div><h4>Ce que vous faites ici</h4><p>" + esc(p.objectif) + "</p></div>"
      + "<div><h4>À préparer</h4><ul>" + p.a_preparer.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul></div>"
      + "<div><h4>Qui doit être là</h4><p>" + esc(p.qui) + "</p></div>"
      + "<div><h4>Comment lire le résultat</h4><p>" + esc(p.comment_lire) + "</p></div>"
      + '<div class="sia-acc-dec"><h4>La décision que cette étape éclaire</h4><p>' + esc(p.decision) + "</p></div>"
      + '<div class="sia-acc-piege"><h4>Le piège</h4><p>' + esc(p.piege) + "</p></div>"
      + "<div><h4>L'étape est faite quand</h4><p>" + esc(p.fait_quand) + "</p></div>"
      + '<div class="sia-src"><h4>Sources de cette étape</h4><ul>' + src + "</ul></div>"
      + "</div></details>";
  }

  function poserEncadres() {
    ACC.phases.forEach(function (p, i) {
      var sec = $(p.ancre);
      if (!sec || sec.querySelector(".sia-acc")) return;
      var h2 = sec.querySelector("h2");
      var div = document.createElement("div");
      div.innerHTML = encadre(p, i);
      if (h2 && h2.parentNode === sec) h2.insertAdjacentElement("afterend", div.firstChild);
      else sec.insertBefore(div.firstChild, sec.firstChild);
    });
  }

  /* ── LA BARRE DE PROGRESSION ──────────────────────────────────────────── */
  function peindreProgression() {
    if (!ACC) return;
    var n = ACC.phases.length, faites = 0, courante = null;
    var h = ACC.phases.map(function (p, i) {
      var f = !!FAIT[p.cle];
      if (f) faites++; else if (courante === null) courante = p.cle;
      return { p: p, i: i, f: f };
    }).map(function (x) {
      var cls = x.f ? "fait" : (x.p.cle === courante ? "courant" : "");
      return '<li><a href="#' + esc(x.p.ancre) + '" class="' + cls + '" title="' + esc("Étape " + (x.i + 1) + " — " + x.p.titre + " · faite quand : " + x.p.fait_quand) + '"'
        + ' aria-label="' + esc("Étape " + (x.i + 1) + " : " + x.p.titre + (x.f ? " (faite)" : "")) + '"'
        + (x.p.cle === courante ? ' aria-current="step"' : "") + "><b>" + (x.f ? "✓" : (x.i + 1)) + "</b>"
        + '<span class="sia-et-t">' + esc(x.p.titre) + "</span></a></li>";
    }).join("");
    $("sia-etapes").innerHTML = h;
    var pct = Math.round(100 * faites / n);
    $("sia-prog-jauge").style.width = pct + "%";
    $("sia-prog-barre").setAttribute("aria-valuenow", String(pct));
    $("sia-prog-n").textContent = faites + " / " + n + " étapes · " + pct + " %";
  }

  function marquer(cle, vrai) {
    if (!!FAIT[cle] === !!vrai) return;
    FAIT[cle] = !!vrai;
    peindreProgression();
  }

  /* ── L'AIDE À LA DÉCISION ─────────────────────────────────────────────── */
  function niveauNom(cle) {
    var v = ACC.niveaux.filter(function (x) { return x.cle === cle; })[0];
    return v ? v.nom : "Niveau non calculé";
  }

  function peindreDecision(j) {
    var zone = $("sia-decision");
    var d = j && j.decision;
    if (!d || !d.ok) { zone.innerHTML = ""; return; }
    var c = d.compte;
    var h = '<div class="sia-dec-tete"><h3>Aide à la décision <button type="button" class="tipi" data-terme="traitement" aria-label="Définition">i</button></h3>'
      + "<p><b>" + esc(d.ensemble) + "</b></p>"
      + (d.gravite ? '<div class="sia-dec-comptes">'
          + '<span class="sia-pastille inacceptable">' + c.inacceptable + " · " + esc(niveauNom("inacceptable")) + "</span>"
          + '<span class="sia-pastille tolerable">' + c.tolerable + " · " + esc(niveauNom("tolerable")) + "</span>"
          + '<span class="sia-pastille acceptable">' + c.acceptable + " · " + esc(niveauNom("acceptable")) + "</span></div>" : "")
      + (d.nis2 ? "<p>" + esc(d.nis2) + "</p>" : "")
      + '<p class="sia-dec-val">' + esc(d.validation) + "</p></div>";
    if (d.lignes.length) {
      h += '<ul class="sia-dec-l">' + d.lignes.map(function (l) {
        return "<li><h4>" + esc(l.systeme) + " — " + esc(l.maillon_nom)
          + ' <span class="sia-pastille ' + esc(l.niveau || "inconnu") + '">'
          + esc(l.niveau_nom || "Gravité à renseigner") + "</span>"
          + ' <span class="sia-pastille inconnu">écart +' + l.ecart + "</span></h4>"
          + (l.decision ? "<div><b>Décision proposée —</b> " + esc(l.decision) + "</div>" : "")
          + (l.options.length ? "<div><b>Options de traitement</b><ul>" + l.options.map(function (o) {
              return "<li>" + esc(o) + "</li>"; }).join("") + "</ul></div>" : "")
          + "<div><b>Pour refermer ce maillon</b>, l'un ou l'autre :<ul>" + l.refermer.map(function (r) {
              return "<li>" + esc(r.dit) + "</li>"; }).join("") + "</ul></div></li>";
      }).join("") + "</ul>";
    }
    zone.innerHTML = h;
    remplirBulles(zone);
  }

  /* ── CE QUI FAIT AVANCER LA BARRE ─────────────────────────────────────── */
  function brancher() {
    document.addEventListener("sia:parc", function (e) {
      var d = e.detail || {};
      marquer("parc", d.declares > 0);
      marquer("chaine", d.cotes > 0);
    });
    document.addEventListener("sia:evalue", function (e) {
      var j = e.detail;
      marquer("ebios", !!(j && j.decision && j.decision.ok && j.decision.gravite));
      peindreDecision(j);
    });
    ["sia-secteur", "sia-nis2", "sia-gravite"].forEach(function (id) {
      $(id).addEventListener("change", surCadrage);
    });
    ["sia-valeur", "sia-perimetre"].forEach(function (id) {
      var t = null;
      $(id).addEventListener("input", function (ev) {
        clearTimeout(t); t = setTimeout(function () { surCadrage(ev); }, 400);
      });
    });
    /* LES SORTIES DE LA CONTRE-EXPERTISE ET DE L'AMBITION se montrent en
       perdant leur attribut `hidden` : c'est cela qu'on observe. */
    [["cx-sortie", "usine"], ["cx-alerte", "ambition"]].forEach(function (x) {
      var el = $(x[0]);
      if (!el || !window.MutationObserver) return;
      new MutationObserver(function () { if (!el.hidden) marquer(x[1], true); })
        .observe(el, { attributes: true, attributeFilter: ["hidden"] });
    });
    /* `toggle` ne remonte pas : on l'écoute en capture. */
    var archi = $("cx-archi");
    if (archi) archi.addEventListener("toggle", function (e) {
      if (e.target && e.target.open) marquer("architecture", true);
    }, true);
    var dirs = $("deux-sens");
    if (dirs && window.IntersectionObserver) {
      new IntersectionObserver(function (ent) {
        if (ent[0].isIntersecting) marquer("directions", true);
      }, { threshold: 0.4 }).observe(dirs);
    }
    /* LES BOUTONS D'INFO-BULLE PEINTS APRÈS COUP par le script de la chaîne
       reçoivent leur définition dès qu'ils apparaissent. */
    if (window.MutationObserver) {
      var attente = null;
      new MutationObserver(function () {
        clearTimeout(attente); attente = setTimeout(function () { remplirBulles(); }, 60);
      }).observe(document.querySelector("main") || document.body, { childList: true, subtree: true });
    }
  }

  function demarrer() {
    fetch("/api/securite-ia/accompagnement", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) throw new Error("accompagnement");
        ACC = j.accompagnement;
        ACC.glossaire.forEach(function (t) { GLOS[t.cle] = t; });
        remplirCadrage();
        poserEncadres();
        remplirBulles();
        brancher();
        peindreProgression();
      })
      .catch(function () {
        /* UN ÉCHEC SE DIT : la barre annonce qu'elle n'a pas pu se charger,
           plutôt que de rester vide comme une page morte. */
        var n = $("sia-prog-n");
        if (n) n.textContent = "Accompagnement indisponible (réseau ou session).";
      });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", demarrer);
  else demarrer();
})();
