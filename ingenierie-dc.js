/* Ingénierie de projet — le calcul replacé dans la séquence.
   ─────────────────────────────────────────────────────────
   Comme datacenter.js, ce fichier ne calcule RIEN. L'aptitude d'une phase, la
   liste des manques et le verdict sont produits par ingenierie_dc.py. Recalculer
   ici un « il ne manque que deux champs » ferait exister deux jugements, et
   c'est celui de l'écran que le lecteur recopierait dans son planning.

   Le parti pris d'affichage : le premier point d'arrêt est LA seule information
   qui commande une action. Neuf phases affichées à plat se lisent comme neuf
   chantiers parallèles, ce qu'elles ne sont pas. */
(function () {
  "use strict";

  var REF = null, CADRE = null, FILIERE = "moe", PHASE = null, DERNIER = null;

  function $(s, r) { return (r || document).querySelector(s); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fr(n) {
    if (n === null || n === undefined || n === "") return "—";
    var x = Number(n);
    if (!isFinite(x)) return String(n);
    var s = Math.abs(x) >= 100 ? x.toFixed(0)
          : Math.abs(x) >= 10 ? x.toFixed(1)
          : x.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
    return s.replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }
  function etat(msg, err) {
    var el = $("#ig-etat");
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = err ? "var(--red, #F0A0A0)" : "";
  }

  /* ── Le formulaire, dérivé du même référentiel que /datacenter ──────────
     Les options ne sont pas écrites dans le HTML : une liste recopiée finit
     par proposer une famille que le moteur ne connaît plus. */
  function bâtirFormulaire() {
    var champs = REF.champs || [];
    var h = '<div class="dc-grille">';
    champs.forEach(function (c) {
      var id = "ig-" + c.id;
      h += '<label class="dc-champ" for="' + id + '">'
        + '<span class="dc-lab">' + esc(c.label)
        + (c.unite ? ' <span class="dc-unite">(' + esc(c.unite) + ')</span>' : "")
        + (c.requis ? ' <b class="dc-req" title="Champ nécessaire">*</b>' : "")
        + "</span>";
      if (c.type === "liste") {
        h += '<select id="' + id + '" data-champ="' + esc(c.id) + '">'
          + '<option value="">— non précisé —</option>';
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
    $("#ig-form").innerHTML = h + "</div>";
    $("#ig-form").addEventListener("input", function () { rafraichir(); });
    $("#ig-form").addEventListener("change", function () { rafraichir(); });
  }

  function lireProfil() {
    var p = {};
    document.querySelectorAll("#ig-form [data-champ]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v !== "") p[el.getAttribute("data-champ")] = v;
    });
    return p;
  }

  /* ── Les onglets de filière ──────────────────────────────────────────── */
  function bâtirOnglets() {
    var f = (CADRE.filieres || {});
    var h = "";
    Object.keys(f).forEach(function (k) {
      h += '<button type="button" role="tab" data-fil="' + esc(k) + '" aria-selected="'
        + (k === FILIERE ? "true" : "false") + '" class="' + (k === FILIERE ? "on" : "")
        + '">' + esc(f[k].nom) + "</button>";
    });
    var z = $("#ig-filieres");
    z.innerHTML = h;
    z.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        FILIERE = b.getAttribute("data-fil");
        PHASE = null;
        bâtirOnglets();
        rendreParcours();
        $("#ig-dossier").innerHTML = '<p class="note">Choisissez une phase dans la frise ci-dessus.</p>';
        boutons(false);
      });
    });
  }

  /* ── La frise ────────────────────────────────────────────────────────── */
  function rendreParcours() {
    var z = $("#ig-parcours");
    if (!DERNIER || !DERNIER[FILIERE]) {
      z.innerHTML = '<p class="note">Renseignez la puissance informatique pour éprouver les phases.</p>';
      return;
    }
    var P = DERNIER[FILIERE], stop = P.premier_blocage;
    var h = "";
    /* Le résumé AVANT la frise : c'est la conclusion, et une conclusion placée
       sous les données se lit après qu'on s'est fait sa propre idée. */
    if (stop) {
      var e = P.etapes.filter(function (x) { return x.code === stop; })[0] || {};
      h += '<p class="ig-res">Vous tenez <b>' + P.n_franchissables + '</b> phase'
        + (P.n_franchissables > 1 ? "s" : "") + ' sur ' + P.n_total
        + '. Le travail à engager est celui de <b>' + esc(stop) + " — " + esc(e.nom || "")
        + "</b> : " + esc(e.aptitude ? e.aptitude.verdict : "") + "</p>";
    } else {
      h += '<p class="ig-res">Toutes les phases de cette filière sont franchissables au '
        + "regard de ce moteur. Cela ne veut pas dire que le dossier est complet : les "
        + "autres disciplines ne sont pas éprouvées ici.</p>";
    }
    h += '<div class="ig-fil" role="tablist" aria-label="Phases">';
    P.etapes.forEach(function (e) {
      var cl = "ig-p " + (e.franchissable ? "ok" : "ko")
        + (e.code === stop ? " stop" : "") + (e.code === PHASE ? " on" : "");
      h += '<button type="button" class="' + cl + '" data-phase="' + esc(e.code) + '" '
        + 'aria-selected="' + (e.code === PHASE ? "true" : "false") + '" role="tab">'
        + '<span class="c">' + esc(e.code) + "</span>"
        + '<span class="n">' + esc(e.nom) + "</span>"
        + '<span class="e">' + (e.franchissable ? "franchissable"
            : (e.n_manques + e.n_substitutions) + " point"
              + ((e.n_manques + e.n_substitutions) > 1 ? "s" : "") + " ouvert"
              + ((e.n_manques + e.n_substitutions) > 1 ? "s" : "")) + "</span>"
        + "</button>";
    });
    h += "</div>";
    z.innerHTML = h;
    z.querySelectorAll("[data-phase]").forEach(function (b) {
      b.addEventListener("click", function () {
        PHASE = b.getAttribute("data-phase");
        rendreParcours();
        chargerDossier();
      });
    });
  }

  /* ── Le dossier de la phase ──────────────────────────────────────────── */
  function rendreDossier(d) {
    var h = '<div class="ig-d"><h3>' + esc(d.code) + " — " + esc(d.nom) + "</h3>"
      + '<p class="sous">' + esc(d.objet) + "</p>";

    h += '<div class="ig-meta">'
      + "<div><b>Ce qu'elle décide</b>" + esc(d.decide) + "</div>"
      + "<div><b>Ce qu'elle verrouille</b>" + esc(d.verrouille) + "</div>"
      + "<div><b>Précision attendue</b>" + esc(d.precision.valeur)
      + ' <span class="dc-unite">(' + esc(d.precision.nature) + " · "
      + esc(d.precision.aace) + ")</span></div>"
      + "</div>";
    if (d.note) h += '<p class="ig-corr"><b>Précision de vocabulaire.</b> ' + esc(d.note) + "</p>";

    /* Ce que la phase attend d'ailleurs. La faisabilité a besoin d'une
       enveloppe d'investissement, et ce moteur-ci n'en produit pas : il chiffre
       l'énergie, l'eau et le carbone. Le taire laisserait croire qu'une
       faisabilité se boucle ici. */
    if (d.renvoi) {
      h += '<div class="ig-renvoi"><b>' + esc(d.renvoi.titre) + "</b>"
        + "<p>" + esc(d.renvoi.pourquoi) + "</p>"
        + "<p>" + esc(d.renvoi.quoi) + "</p>"
        + '<a href="' + esc(d.renvoi.url) + '" target="_blank" rel="noopener">'
        + "Ouvrir l'étude de faisabilité chiffrée</a></div>";
    }

    h += '<p class="sous" style="margin-top:14px">' + esc(d.apport_texte) + "</p>";
    h += '<div class="ig-g">';
    (d.grandeurs || []).forEach(function (g) {
      var rmp = g.statut !== "recevable";
      h += '<div class="v' + (rmp ? " rmp" : "") + '">'
        + '<div class="n">' + esc(g.nom) + "</div>"
        + '<div class="q">' + fr(g.valeur) + ' <span class="u">' + esc(g.unite) + "</span></div>"
        + (g.incertitude ? '<div class="i">' + esc(g.incertitude) + "</div>" : "")
        + '<span class="st">' + (rmp
            ? "à produire — bloquée par " + esc((g.postes_bloquants || []).join(", "))
            : "recevable à ce stade") + "</span></div>";
    });
    h += "</div>";

    var a = d.aptitude || {};
    if ((a.entrees_manquantes || []).length) {
      h += '<div class="ig-man"><h4>Entrées à renseigner</h4><ul>';
      a.entrees_manquantes.forEach(function (m) {
        h += "<li><b>" + esc(m.label) + "</b>" + (m.unite ? " (" + esc(m.unite) + ")" : "")
          + " — " + esc(m.pourquoi)
          + (m.origine === "propre" ? "" : " <i>; dette d'une phase antérieure</i>")
          + "</li>";
      });
      h += "</ul></div>";
    }
    if ((a.substitutions_a_faire || []).length) {
      h += '<div class="ig-man"><h4>Facteurs à remplacer par une donnée réelle</h4>';
      a.substitutions_a_faire.forEach(function (s) {
        h += '<div class="ig-sub"><span class="t">' + esc(s.nom) + "</span>"
          + '<span class="k">' + esc(s.nature)
          + (s.incertitude ? " · " + esc(s.incertitude) : "") + "</span>";
        if (s.devient_insuffisant) {
          h += "<p><b>Pourquoi à ce stade</b> — " + esc(s.devient_insuffisant) + "</p>";
        }
        h += "<p><b>À remplacer par</b> — " + esc(s.remplacer_par) + "</p>";
        /* Une incertitude absente n'est pas une incertitude nulle : c'est la
           réserve la plus facile à oublier, donc celle qu'il faut écrire. */
        if (s.incertitude_absente) {
          h += "<p><b>Réserve</b> — ce poste ne porte aucune incertitude déclarée au "
            + "référentiel. Une incertitude absente n'est pas une incertitude nulle.</p>";
        }
        h += "</div>";
      });
      h += "</div>";
    }

    h += '<div class="ig-plan"><b>Plan de l\'étude</b><ol>'
      + (d.sections || []).map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("")
      + "</ol></div>";

    h += registrePieces(d);

    (d.correspondance || []).forEach(function (c) {
      var autre = d.filiere === "moe" ? c.indus : c.moe;
      h += '<p class="ig-corr"><b>Correspondance — ' + esc(autre) + "</b> (accord "
        + esc(c.accord) + "). " + esc(c.ecart) + "</p>";
    });

    $("#ig-dossier").innerHTML = h + "</div>";
    brancherPieces();
    boutons(true);
  }

  /* ── Le registre des pièces ──────────────────────────────────────────────
     Le plan dit ce qu'on écrit ; le registre dit ce qu'on REMET. Deux choses
     distinctes : confondre les deux fait livrer un rapport là où le marché
     attend des pièces numérotées, chacune avec son émetteur.

     Les pièces sont groupées par TYPE et non par ordre de code : on cherche
     « les tableaux à fournir » ou « les plans », pas « la pièce numéro sept ». */
  var ORDRE_TYPE = ["note", "tableau", "plan", "schema", "contractuel",
                    "procedure", "registre"];

  function registrePieces(d) {
    var P = d.pieces || [];
    if (!P.length) return "";
    var R = d.resume_pieces || {};
    var h = '<div class="ig-reg"><div class="ig-reg-t"><b>' + R.total
      + "</b> pièce" + (R.total > 1 ? "s" : "") + " à fournir · <b>"
      + R.propres_a_la_phase + "</b> propre" + (R.propres_a_la_phase > 1 ? "s" : "")
      + " à la phase · <b>" + R.specifications_de_discipline
      + "</b> spécification" + (R.specifications_de_discipline > 1 ? "s" : "")
      + " de discipline · <b>" + R.alimentees_par_le_moteur + "</b> alimentée"
      + (R.alimentees_par_le_moteur > 1 ? "s" : "") + " par le calcul"
      + "<span class='ig-reg-c'>"
      + Object.keys(R.par_type || {}).sort().map(function (k) {
          return esc(k) + " " + R.par_type[k];
        }).join(" · ") + "</span></div>";

    var groupes = {};
    P.forEach(function (p) { (groupes[p.type] = groupes[p.type] || []).push(p); });
    ORDRE_TYPE.forEach(function (t) {
      var g = groupes[t];
      if (!g || !g.length) return;
      h += '<div class="ig-reg-g"><h5>' + esc(g[0].type_nom)
        + " <span>" + esc(g[0].type_aide) + "</span></h5>";
      g.forEach(function (p) {
        h += '<div class="ig-pc' + (p.moteur ? " mot" : "")
          + (p.discipline ? " dis" : "") + '">'
          + '<div class="ig-pc-h"><code>' + esc(p.code) + "</code> "
          + '<span class="ti">' + esc(p.titre) + "</span>"
          + '<span class="em">' + esc(p.emetteur_nom) + "</span>"
          + (p.moteur ? '<span class="mo">alimentée par le calcul</span>' : "")
          + "</div>"
          /* Le NIVEAU commande la profondeur attendue. Sans lui, une même
             spécification se lit à l'identique de l'esquisse à la consultation,
             alors qu'elle n'y engage pas du tout la même chose. */
          + (p.niveau_nom
              ? '<div class="ig-pc-nv"><span class="nv nv-' + esc(p.niveau) + '">'
                + esc(p.niveau_nom) + "</span> " + esc(p.niveau_aide)
                + (p.discipline_nom ? ' <span class="di">' + esc(p.discipline_nom)
                    + "</span>" : "")
                + (p.autres_phases && p.autres_phases.length
                    ? '<span class="ap">document unique, repris en '
                      + esc(p.autres_phases.join(", ")) + "</span>" : "")
                + "</div>"
              : "")
          + '<ul>' + p.contenu.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("")
          + "</ul>"
          + '<div class="ig-pc-a"><button type="button" class="ig-gen" '
          + 'data-piece="' + esc(p.code) + '">Rédiger cette pièce</button>'
          /* Dire la vérité sur ce qu'une IA produit pour une pièce graphique :
             elle n'en dessine pas une, elle en écrit la spécification. */
          + (p.type === "plan" || p.type === "schema"
              ? '<span class="ig-pc-n">La rédaction produit la SPÉCIFICATION de '
                + 'la pièce graphique — contenu, échelle, conventions — non le '
                + 'dessin lui-même.</span>' : "")
          + "</div></div>";
      });
      h += "</div>";
    });
    h += '<p class="ig-reg-n">' + esc(d.note_registre) + "</p>";
    return h + '<div id="ig-piece" aria-live="polite"></div></div>';
  }

  function brancherPieces() {
    document.querySelectorAll("#ig-dossier .ig-gen").forEach(function (b) {
      b.addEventListener("click", function () { redigerPiece(b.getAttribute("data-piece"), b); });
    });
  }

  function redigerPiece(code, bouton) {
    var z = $("#ig-piece");
    if (!z || !PHASE) return;
    var p = lireProfil();
    p.phase = PHASE;
    p.piece = code;
    p.client = (($("#ig-client") || {}).value || "").trim();
    p.secteur = (($("#ig-secteur") || {}).value || "").trim();
    p.perimetre = (($("#ig-perimetre") || {}).value || "").trim();
    bouton.disabled = true;
    var ancien = bouton.textContent;
    bouton.textContent = "Rédaction…";
    z.innerHTML = '<p class="note">Rédaction de ' + esc(code)
      + " en cours, à partir du calcul et de la base de connaissance…</p>";
    z.scrollIntoView({ behavior: "smooth", block: "nearest" });
    fetch("/api/admin/datacenter/piece", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    })
      .then(function (r) { return r.json().then(function (j) { return { s: r.status, j: j }; }); })
      .then(function (o) {
        bouton.disabled = false;
        bouton.textContent = ancien;
        if (!o.j.ok) {
          /* Un 403 n'est pas une panne : c'est le verrou d'administration. Le
             dire évite de faire chercher une erreur qui n'existe pas. */
          z.innerHTML = '<p class="note">' + esc(o.s === 403
            ? "La rédaction assistée est réservée à l'administrateur du site. "
              + "Le registre ci-dessus, lui, reste consultable et exportable."
            : (o.j.message || "Rédaction indisponible.")) + "</p>";
          return;
        }
        z.innerHTML = '<div class="ig-doc"><div class="ig-doc-h">'
          + "<b>" + esc(code) + "</b> — brouillon rédigé"
          + (o.j.model ? " · " + esc(o.j.model) : "")
          + ((o.j.sources || []).length
              ? " · " + o.j.sources.length + " document"
                + (o.j.sources.length > 1 ? "s" : "") + " de la base cité"
                + (o.j.sources.length > 1 ? "s" : "")
              : " · aucun document de la base n'a été retrouvé")
          + '</div><pre class="ig-doc-c">' + esc(o.j.document) + "</pre></div>";
      })
      .catch(function () {
        bouton.disabled = false;
        bouton.textContent = ancien;
        z.innerHTML = '<p class="note">Rédaction indisponible pour le moment.</p>';
      });
  }

  /* ── Les correspondances entre filières ──────────────────────────────── */
  function rendreCorrespondances() {
    var C = CADRE.correspondances || [];
    var h = '<div class="ig-tab-wrap"><table class="ig-tab"><thead><tr>'
      + "<th>Maîtrise d'œuvre</th><th>Ingénierie</th><th>Accord</th>"
      + "<th>Ce qui les sépare</th></tr></thead><tbody>";
    C.forEach(function (c) {
      h += "<tr><td><code>" + esc(c.moe) + "</code></td><td><code>" + esc(c.indus)
        + "</code></td><td><span class='ig-acc a-" + esc(c.accord) + "'>" + esc(c.accord)
        + "</span></td><td>" + esc(c.ecart) + "</td></tr>";
    });
    $("#ig-correspondances").innerHTML = h + "</tbody></table></div>";
  }

  /* ── Les appels ──────────────────────────────────────────────────────── */
  var _minuteur = null, _vol = null;

  function rafraichir() {
    if (_minuteur) clearTimeout(_minuteur);
    _minuteur = setTimeout(function () {
      var p = lireProfil();
      if (!p.puissance_it_kw) {
        DERNIER = null;
        rendreParcours();
        $("#ig-dossier").innerHTML = '<p class="note">Choisissez une phase dans la frise ci-dessus.</p>';
        boutons(false);
        return;
      }
      /* La requête précédente est annulée : sans cela, deux frappes rapprochées
         font revenir les réponses dans l'ordre du réseau, et la frise affiche
         l'avant-dernier profil. */
      if (_vol) { try { _vol.abort(); } catch (e) {} }
      _vol = (typeof AbortController !== "undefined") ? new AbortController() : null;
      etat("");
      fetch("/api/datacenter/ingenierie/parcours", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(p),
        signal: _vol ? _vol.signal : undefined,
      })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j.ok) throw new Error(j.message || "parcours");
          DERNIER = j.parcours;
          rendreParcours();
          if (PHASE) chargerDossier();
        })
        .catch(function (e) {
          if (e && e.name === "AbortError") return;
          etat("Le parcours n'a pas pu être établi. Réessayez dans un instant.", true);
        });
    }, 280);
  }

  function chargerDossier() {
    if (!PHASE) return;
    var p = lireProfil();
    p.phase = PHASE;
    fetch("/api/datacenter/ingenierie/dossier", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) throw new Error(j.message || "dossier");
        if (!j.dossier.disponible) {
          $("#ig-dossier").innerHTML = '<p class="note">' + esc(j.dossier.motif) + "</p>";
          boutons(false);
          return;
        }
        rendreDossier(j.dossier);
      })
      .catch(function () {
        $("#ig-dossier").innerHTML = '<p class="note">Dossier indisponible pour le moment.</p>';
        boutons(false);
      });
  }

  function boutons(actif) {
    ["#ig-docx", "#ig-pdf"].forEach(function (s) {
      var b = $(s);
      if (b) b.disabled = !actif;
    });
  }

  function exporter(fmt) {
    if (!PHASE) return;
    var p = lireProfil();
    p.phase = PHASE;
    p.format = fmt;
    etat("Mise en page de l'étude " + PHASE + "…");
    fetch("/api/datacenter/ingenierie/export", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("export");
        return r.blob();
      })
      .then(function (b) {
        var u = URL.createObjectURL(b), a = document.createElement("a");
        a.href = u;
        a.download = "etude-" + PHASE.toLowerCase() + "." + fmt;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
        etat("");
      })
      .catch(function () { etat("La mise en page a échoué.", true); });
  }

  function démarrer() {
    Promise.all([
      fetch("/api/datacenter/referentiel", { credentials: "same-origin" })
        .then(function (r) { if (r.status === 401) throw new Error("auth"); return r.json(); }),
      fetch("/api/datacenter/ingenierie", { credentials: "same-origin" })
        .then(function (r) { if (r.status === 401) throw new Error("auth"); return r.json(); }),
    ])
      .then(function (rs) {
        if (!rs[0].ok || !rs[1].ok) throw new Error("ref");
        REF = rs[0];
        CADRE = rs[1].referentiel;
        bâtirFormulaire();
        bâtirOnglets();
        rendreCorrespondances();
        rafraichir();
      })
      .catch(function (e) {
        $("#ig-form").innerHTML = '<p class="note">'
          + (String(e.message) === "auth"
            ? "Connectez-vous pour accéder au cadre d'ingénierie."
            : "Référentiel indisponible. Réessayez dans un instant.")
          + "</p>";
      });

    var b;
    if ((b = $("#ig-docx"))) b.addEventListener("click", function () { exporter("docx"); });
    if ((b = $("#ig-pdf"))) b.addEventListener("click", function () { exporter("pdf"); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", démarrer);
  } else {
    démarrer();
  }
})();
