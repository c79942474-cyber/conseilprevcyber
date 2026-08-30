/* La décarbonation — deux voies, une hiérarchie, et l'ordre.
 *
 * CE MODULE VIT DÉSORMAIS DANS LA PAGE DU CALCUL. Il avait sa propre page, et
 * celle-ci refaisait le même formulaire, lisait le même profil et renvoyait
 * vers les mêmes voisines. Deux pages qui partagent leur sujet finissent par se
 * contredire : l'une est mise à jour, l'autre non, et le lecteur ne sait plus
 * laquelle fait foi. Le formulaire est donc celui de la page — `#dc-form`,
 * construit par datacenter.js — et il n'est saisi qu'une fois.
 *
 * CE QUE CE MODULE DOIT TENIR :
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
    document.querySelectorAll("#dc-form [data-champ]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v !== "") p[el.getAttribute("data-champ")] = v;
    });
    return p;
  }

  /* ── AUCUNE REQUÊTE SANS DÉLAI ──────────────────────────────────────────
     Un `fetch` sans délai attend INDÉFINIMENT si le serveur tarde : le
     message posé juste avant — « Calcul des deux voies… » — reste à l'écran
     sans limite. Repris de datacenter.js, qui porte le même mécanisme pour
     la même raison. */
  var DELAI_LONG = 45000;

  function demander(url, options, delai) {
    options = options || {};
    var ctrl = (typeof AbortController !== "undefined") ? new AbortController() : null;
    var fini = false;
    var minuteur = setTimeout(function () {
      if (!fini && ctrl) { try { ctrl.abort(); } catch (e) {} }
    }, delai || DELAI_LONG);
    if (ctrl && !options.signal) options.signal = ctrl.signal;
    return fetch(url, options).then(function (r) {
      fini = true; clearTimeout(minuteur); return r;
    }, function (e) {
      fini = true; clearTimeout(minuteur);
      if (e && e.name === "AbortError" && !options.__annule) {
        var t = new Error("delai");
        t.name = "DelaiDepasse";
        t.delai = delai || DELAI_LONG;
        throw t;
      }
      throw e;
    });
  }

  function messageDelai(e, defaut) {
    if (e && e.name === "DelaiDepasse") {
      return "Le serveur n'a pas répondu en " + Math.round(e.delai / 1000)
        + " secondes. Il est peut-être très sollicité : relancez dans un "
        + "instant. Vos saisies sont conservées.";
    }
    return defaut;
  }

  function poster(url, corps) {
    return demander(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps),
    }, DELAI_LONG).then(function (r) {
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
     LE FORMULAIRE N'EST PAS CONSTRUIT ICI — IL EST LU

     `#dc-form` est bâti par datacenter.js depuis le référentiel du serveur. En
     construire un second, comme le faisait la page dédiée, obligeait le
     visiteur à saisir deux fois la même puissance et laissait les deux copies
     diverger dès la première frappe.
     ═════════════════════════════════════════════════════════════════════ */

  function brancherFormulaire() {
    var f = document.getElementById("dc-form");
    if (!f) return false;
    f.addEventListener("input", planifierVague);
    f.addEventListener("change", planifierVague);
    return true;
  }

  /* Le formulaire est peuplé par une requête : au moment où ce script
     s'exécute, il peut n'être encore qu'un message de chargement. On attend
     donc qu'il porte ses champs, plutôt que de supposer un ordre d'arrivée que
     rien ne garantit. */
  function attendreFormulaire(fait, essais) {
    essais = essais === undefined ? 60 : essais;
    if (document.querySelector('#dc-form [data-champ]')) { fait(); return; }
    if (essais <= 0) { fait(); return; }
    setTimeout(function () { attendreFormulaire(fait, essais - 1); }, 120);
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
      + "<b>puissance informatique installée</b> sera renseignée dans le "
      + "formulaire du profil : c'est le seul champ nécessaire, les autres ont "
      + "une valeur par défaut. "
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

    /* ── EMPORTER LE DOSSIER ────────────────────────────────────────────
       IL NE S'EXPORTAIT PAS. La note de calcul, l'étude de phase, la pièce et
       la stratégie s'emportaient toutes en Word et en PDF ; la trajectoire,
       non. Elle s'affichait, et le seul moyen de la sortir était de
       sélectionner le texte à l'écran — c'est-à-dire de perdre les tableaux,
       la distinction entre grandeur recevable et grandeur à produire, et les
       réserves des textes. Un résultat qui ne sort pas du site n'est pas un
       livrable. */
    h += '<div class="dk-b dk-exp"><b>Emporter ce dossier</b>'
      + '<p class="note">Le document reprend l’étape entière : ce qu’elle décide, '
      + 'ce qu’elle verrouille, les grandeurs recevables et — surtout — celles qui '
      + 'restent à produire.</p>'
      + '<div class="actions" style="gap:10px;flex-wrap:wrap;margin-top:10px">'
      + '<button type="button" class="btn btn-s" data-dk-exp="docx">Dossier d’étape (Word)</button>'
      + '<button type="button" class="btn btn-s" data-dk-exp="pdf">Dossier d’étape (PDF)</button>'
      + '</div><p class="note" data-dk-exp-etat role="status" aria-live="polite"></p></div>';

    h += "</div>";
    z.innerHTML = h;
    z.querySelectorAll("[data-dk-exp]").forEach(function (b) {
      b.addEventListener("click", function () {
        exporterDossier(b.getAttribute("data-dk-exp"), z);
      });
    });
  }

  /* L'export du dossier d'étape. FERMÉ côté serveur : le document porte le
     profil du projet. L'échec le DIT et nomme sa cause — « erreur » enverrait
     le lecteur vérifier ses saisies alors qu'il lui manque une session. */
  function exporterDossier(fmt, z) {
    var etat = z.querySelector("[data-dk-exp-etat]");
    var dire = function (t) { if (etat) etat.textContent = t; };
    dire("Mise en page du dossier…");
    var p = profil();
    p.etape = ETAPE;
    p.format = fmt;
    /* Le destinataire, s'il a été choisi plus haut dans la page. Le module est
       à part : sans lui, le dossier part sans bordereau plutôt que d'échouer. */
    if (window.TRANSMETTRE && window.TRANSMETTRE.corps) {
      p = window.TRANSMETTRE.corps(p);
    }
    fetch("/api/datacenter/decarbonation/export", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p)
    }).then(function (r) {
      if (r.status === 401 || r.status === 403) {
        throw new Error("L’export demande un compte : le document porte le "
          + "profil de votre projet. Connectez-vous, puis relancez.");
      }
      var ct = r.headers.get("Content-Type") || "";
      if (!r.ok || ct.indexOf("json") >= 0) {
        return r.json().catch(function () { return {}; })
          .then(function (j) {
            throw new Error(j.message || "La mise en page a échoué.");
          });
      }
      return r.blob();
    }).then(function (b) {
      if (!b) return;
      var u = URL.createObjectURL(b), a = document.createElement("a");
      a.href = u;
      a.download = "decarbonation-" + String(ETAPE).toLowerCase() + "." + fmt;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
      dire("Dossier téléchargé.");
    }).catch(function (e) {
      dire(e.message || "L’export a échoué.");
    });
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

  /* `sansPortee` : ne pas répéter la définition de la portée sous chaque texte.
     ELLE RESTE INDISPENSABLE AILLEURS. Le dossier d'une étape mêle des textes
     de portées différentes : là, chacun doit dire la sienne. La section 8, elle,
     n'affiche qu'une portée à la fois et l'énonce une fois en tête — l'écrire
     sous chacun des six textes la ferait lire zéro fois. */
  function bloctexte(t, sansPortee) {
    return '<div class="dk-tx"><h4>' + esc(t.nom)
      + '<span class="dk-po p-' + esc(t.portee) + '">' + esc(t.portee) + "</span>"
      + "</h4><p>" + esc(t.dit) + "</p>"
      + (sansPortee ? ""
          : '<p class="res" style="font-style:italic">' + esc(t.portee_texte) + "</p>")
      + (t.reserve ? '<p class="res">' + esc(t.reserve) + "</p>" : "")
      + "</div>";
  }

  /* ═════════════════════════════════════════════════════════════════════
     LA HIÉRARCHIE ET LES TEXTES — rendus une fois, dans l'ordre du serveur
     ═════════════════════════════════════════════════════════════════════ */

  /* ═════════════════════════════════════════════════════════════════════
     LA HIÉRARCHIE — UN RANG À LA FOIS, SANS PERDRE L'ORDRE
     ═════════════════════════════════════════════════════════════════════

     Les quatre rangs et leurs onze leviers se dépliaient d'un coup : un mur de
     plusieurs écrans qu'on parcourt sans le lire. Le rang se choisit désormais
     dans une liste.

     LE PIÈGE DE CE CHANGEMENT, ET IL EST DE FOND. Cette section n'enseigne pas
     quatre familles de leviers : elle enseigne un ORDRE. « Un levier de rang
     inférieur n'est recevable que si les rangs supérieurs ont été examinés et
     documentés » — ISO 14068-1 en fait une condition de l'allégation de
     neutralité, pas une recommandation. Une liste qui permet d'ouvrir
     « Compenser » sans avoir jamais vu qu'il existe trois rangs au-dessus
     ferait dire à l'interface le contraire de ce que la page démontre.

     Trois précautions, donc :
       · les options portent leur numéro ET leur nombre de leviers, si bien que
         la séquence entière se lit SANS ouvrir la liste ;
       · un rang ouvert rappelle sa position — « rang 3 sur 4 » ;
       · au-dessous du premier, le panneau nomme les rangs qui doivent avoir
         été instruits avant, et conduit à chacun d'un clic. */

  var RANG_VU = null;

  function rendreHierarchie() {
    var z = $("#dk-hierarchie");
    if (!z || !CADRE) return;
    var rangs = CADRE.hierarchie || [];
    if (!rangs.length) { z.innerHTML = ""; return; }
    if (RANG_VU === null) RANG_VU = rangs[0].rang;   /* on commence en haut */

    var h = '<label class="dk-hsel" for="dk-rang">'
      + '<span class="dk-hsel-l">Rang de la hiérarchie</span>'
      + '<select id="dk-rang" data-dk-rang>'
      + rangs.map(function (r) {
          var n = (r.leviers || []).length;
          return '<option value="' + esc(r.rang) + '"'
            + (r.rang === RANG_VU ? " selected" : "") + ">"
            + esc(r.rang + ". " + r.nom) + " — " + n + " levier"
            + (n > 1 ? "s" : "") + "</option>";
        }).join("")
      + "</select>"
      + '<span class="dk-hsel-a">L’ordre n’est pas indicatif : un rang ne '
      + 'devient recevable que si ceux qui le précèdent ont été instruits et '
      + 'documentés.</span></label>';

    var r = rangs.filter(function (x) { return x.rang === RANG_VU; })[0] || rangs[0];
    var amont = rangs.filter(function (x) { return x.rang < r.rang; });

    h += '<div class="dk-h r' + r.rang + '">'
      + '<div class="dk-h-t"><span class="o">Rang ' + r.rang + " sur "
      + rangs.length + "</span><h3>" + esc(r.nom) + "</h3></div>"
      + '<p class="dk-h-p">' + esc(r.principe) + "</p>"
      + '<p class="dk-h-pr">Ce qui le prouve : ' + esc(r.preuve) + "</p>";

    if (amont.length) {
      /* CE QU'IL FALLAIT AVOIR FAIT AVANT. Sans ce rappel, la liste
         transformerait une contrainte de méthode en menu de self-service. */
      h += '<p class="dk-h-amont"><b>À instruire avant ce rang</b> — '
        + amont.map(function (a) {
            return '<button type="button" class="dk-h-go" data-dk-rang-go="'
              + esc(a.rang) + '">' + esc(a.rang + ". " + a.nom) + "</button>";
          }).join(" ")
        + " Un levier de ce rang présenté sans la trace de cet examen se fait "
        + "écarter en vérification.</p>";
    }

    (r.leviers || []).forEach(function (lv) { h += bloclevier(lv); });
    h += "</div>";
    z.innerHTML = h;

    var sel = z.querySelector("[data-dk-rang]");
    if (sel) {
      sel.addEventListener("change", function () {
        RANG_VU = parseInt(sel.value, 10);
        rendreHierarchie();
        /* On redonne le clavier au sélecteur : sans cela, un choix fait au
           clavier renvoie le focus au début du document, et le lecteur
           recommence sa navigation. */
        var s2 = $("#dk-rang");
        if (s2) { try { s2.focus({ preventScroll: true }); } catch (e) { s2.focus(); } }
      });
    }
    z.querySelectorAll("[data-dk-rang-go]").forEach(function (b) {
      b.addEventListener("click", function () {
        RANG_VU = parseInt(b.getAttribute("data-dk-rang-go"), 10);
        rendreHierarchie();
        var s2 = $("#dk-rang");
        if (s2) { try { s2.focus({ preventScroll: true }); } catch (e) { s2.focus(); } }
      });
    });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LES TEXTES — UNE PORTÉE À LA FOIS, SANS PERDRE CE QUI OBLIGE
     ═════════════════════════════════════════════════════════════════════

     Dix-sept textes se dépliaient d'un coup. La portée se choisit désormais.

     LE PIÈGE DE CE DÉCOUPAGE EST LE SUJET MÊME DE LA SECTION. Elle n'aligne pas
     dix-sept références : elle enseigne qu'elles NE PÈSENT PAS PAREIL. « Un
     client à qui l'on promet une obligation là où il n'y a qu'un engagement de
     place prend une décision sur une contrainte qui n'existe pas, et l'inverse
     lui coûte plus cher encore. » Un lecteur qui n'ouvrirait que « méthode de
     place » ignorerait qu'il existe cinq textes qui l'obligent.

     Trois précautions :
       · la liste s'ouvre sur CE QUI OBLIGE — l'ordre vient du serveur, où il
         est déclaré, et jamais de l'ordre alphabétique des clés ;
       · chaque option porte le nombre de textes de sa portée ;
       · au-dessous du texte contraignant, le panneau RAPPELLE combien de
         textes obligent et y conduit d'un clic. */

  var PORTEE_VUE = null;

  function rendreTextes() {
    var z = $("#dk-textes");
    if (!z || !CADRE) return;
    var ordre = CADRE.portees_ordre || [];
    var textes = CADRE.textes || [];
    if (!ordre.length || !textes.length) { z.innerHTML = ""; return; }
    if (PORTEE_VUE === null) PORTEE_VUE = ordre[0].cle;   /* ce qui oblige */

    var par = function (cle) {
      return textes.filter(function (t) { return t.portee === cle; });
    };

    var h = '<label class="dk-tsel" for="dk-portee">'
      + '<span class="dk-tsel-l">Portée du texte</span>'
      + '<select id="dk-portee" data-dk-portee>'
      + ordre.map(function (p) {
          var n = par(p.cle).length;
          return '<option value="' + esc(p.cle) + '"'
            + (p.cle === PORTEE_VUE ? " selected" : "") + ">"
            + esc(p.texte.split(".")[0]) + " — " + n + " texte"
            + (n > 1 ? "s" : "") + "</option>";
        }).join("")
      + "</select>"
      + '<span class="dk-tsel-a">Les quatre portées sont classées par POIDS, du '
      + 'contraignant à la méthode. Ce n’est pas un ordre d’affichage : c’est ce '
      + 'qui décide de ce que vous pouvez promettre à un client.</span></label>';

    var p = ordre.filter(function (x) { return x.cle === PORTEE_VUE; })[0] || ordre[0];
    var oblige = ordre.filter(function (x) { return x.cle === "contraignant"; })[0];
    var nOblige = par("contraignant").length;

    h += '<p class="dk-tx-def p-' + esc(p.cle) + '"><b>Ce que cette portée '
      + 'signifie.</b> ' + esc(p.texte) + "</p>";

    /* CE QUI OBLIGE, RAPPELÉ PARTOUT AILLEURS. Sans ce rappel, la liste
       laisserait lire les engagements volontaires sans savoir que cinq textes
       s'imposent, eux — et c'est l'erreur que la section existe pour empêcher. */
    if (p.cle !== "contraignant" && oblige && nOblige) {
      h += '<p class="dk-tx-ob">Cette portée <b>n’oblige pas par elle-même</b>. '
        + nOblige + ' texte' + (nOblige > 1 ? "s" : "") + ' de ce cadre '
        + (nOblige > 1 ? "obligent" : "oblige") + ', et '
        + (nOblige > 1 ? "ils ne sont pas ici" : "il n’est pas ici") + ' : '
        + '<button type="button" class="dk-tx-go" data-dk-portee-go="contraignant">'
        + 'voir les textes contraignants</button></p>';
    }

    /* Sans la définition de portée sous chaque texte : le bandeau ci-dessus
       vient de la donner, et six répétitions la font lire zéro fois. */
    h += par(p.cle).map(function (t) { return bloctexte(t, true); }).join("");
    z.innerHTML = h;

    var sel = z.querySelector("[data-dk-portee]");
    if (sel) {
      sel.addEventListener("change", function () {
        PORTEE_VUE = sel.value;
        rendreTextes();
        var s2 = $("#dk-portee");
        if (s2) { try { s2.focus({ preventScroll: true }); } catch (e) { s2.focus(); } }
      });
    }
    z.querySelectorAll("[data-dk-portee-go]").forEach(function (b) {
      b.addEventListener("click", function () {
        PORTEE_VUE = b.getAttribute("data-dk-portee-go");
        rendreTextes();
        var s2 = $("#dk-portee");
        if (s2) { try { s2.focus({ preventScroll: true }); } catch (e) { s2.focus(); } }
      });
    });

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
    var el = document.querySelector(
      '#dc-form [data-champ="' + (cid || "puissance_it_kw") + '"]');
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); }
    /* Le formulaire de la page enveloppe ses champs dans `label.dc-champ` ;
       on désigne ce bloc, pas le seul contrôle, sans quoi la mise en évidence
       laisse le libellé dans l'ombre et ne désigne qu'à moitié. */
    var bloc = el.closest("label.dc-champ") || el.closest("[data-champ-bloc]") || el;
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
     REPRENDRE UN PROFIL VENU D'UNE AUTRE ÉTUDE

     Une étude d'implantation menée ailleurs — comparateur pondéré, enveloppe
     d'investissement — se termine sur un pays retenu et une puissance. Plutôt
     que de les retaper, le lien peut les porter :
         /datacenter#voie=inventaire&pays=FR&puissance_it_kw=20000

     TROIS RÈGLES, ET AUCUNE N'EST DÉCORATIVE :

       1. RIEN N'EST APPLIQUÉ SANS ÊTRE DÉCLARÉ. Un formulaire qui se remplit
          tout seul sans dire d'où viennent ses valeurs laisse le lecteur les
          prendre pour des valeurs par défaut — et il ne les vérifie pas.

       2. RIEN N'EST APPLIQUÉ SANS ÊTRE VALIDÉ. Une valeur est confrontée au
          contrôle réel du formulaire : une option qui n'existe pas, un nombre
          hors bornes sont REFUSÉS. Les accepter poserait dans le champ une
          valeur que le moteur ne connaît pas.

       3. UN REFUS SE DIT. Silencieux, il ferait calculer sur un profil que
          l'expéditeur croit avoir transmis — l'écart entre les deux études ne
          se découvrirait qu'au comité.

     ET LE CALCUL N'EST PAS LANCÉ automatiquement : on montre d'abord ce qui a
     été repris. Un résultat affiché avant que le lecteur n'ait vu ses entrées
     est un résultat qu'il n'a pas vérifiées.
     ═════════════════════════════════════════════════════════════════════ */

  /* Les champs qu'un lien peut porter. Volontairement COURT : le profil
     technique, et rien qui désigne une personne ou un client. */
  var REPRISE = ["puissance_it_kw", "pays", "refroidissement", "taux_charge"];

  function libelleDe(el, cid) {
    var lab = el.closest("label");
    var t = lab && lab.querySelector(".dc-lab");
    if (!t) return cid;
    var c = t.cloneNode(true);
    c.querySelectorAll(".dc-unite, .dc-req").forEach(function (x) { x.remove(); });
    return (c.textContent || cid).replace(/\s+/g, " ").trim();
  }

  function reprendreProfil(u) {
    var f = document.getElementById("dc-form");
    var z = document.getElementById("dc-repris");
    if (!f || !z) return;
    var pris = [], refuses = [];
    REPRISE.forEach(function (cid) {
      if (!(cid in u)) return;
      var el = f.querySelector('[data-champ="' + cid + '"]');
      if (!el) {
        refuses.push([cid, "champ inconnu de ce formulaire"]);
        return;
      }
      var v = String(u[cid]).trim();
      var lab = libelleDe(el, cid);
      var vu = v;
      if (el.tagName === "SELECT") {
        /* On confronte au contrôle RÉEL, pas à une liste recopiée : les
           options viennent du référentiel du serveur, et c'est la seule
           liste qui fasse foi. */
        var opt = [].slice.call(el.options).filter(function (o) {
          return o.value === v;
        })[0];
        if (!opt) { refuses.push([lab, "« " + v + " » inconnu du référentiel"]); return; }
        /* On affiche le NOM, pas le code : « Suède » se relit, « SE » se
           devine — et c'est justement la valeur qu'on demande de vérifier. */
        vu = opt.textContent.trim() + " (" + v + ")";
      } else {
        var n = parseFloat(v.replace(",", "."));
        if (!isFinite(n)) { refuses.push([lab, "« " + v + " » n’est pas un nombre"]); return; }
        v = String(n);
        vu = v;
      }
      el.value = v;
      var bloc = el.closest("label");
      if (bloc) {
        bloc.classList.add("dc-repris-champ");
        setTimeout(function () { bloc.classList.remove("dc-repris-champ"); }, 4000);
      }
      pris.push([lab, vu]);
    });
    if (!pris.length && !refuses.length) return;

    var h = "<b>Profil repris d’une étude précédente.</b> Ces valeurs ne sont "
      + "pas des valeurs par défaut : elles viennent du lien que vous avez "
      + "suivi. <b>Vérifiez-les</b>, puis lancez le calcul.";
    if (pris.length) {
      h += "<ul>" + pris.map(function (x) {
        return "<li>" + esc(x[0]) + " : <b>" + esc(x[1]) + "</b></li>";
      }).join("") + "</ul>";
    }
    if (refuses.length) {
      h += '<div class="refus"><b>Non appliqué</b> — ces valeurs n’ont pas été '
        + "reconnues, et le champ correspondant est resté tel quel :<ul>"
        + refuses.map(function (x) {
            return "<li>" + esc(x[0]) + " — " + esc(x[1]) + "</li>";
          }).join("")
        + "</ul></div>";
    }
    z.innerHTML = h;
    z.hidden = false;

    /* Les autres scripts de la page écoutent la saisie : sans ces événements,
       l'aperçu et le parcours resteraient sur le profil vide. */
    ["input", "change"].forEach(function (t) {
      f.dispatchEvent(new Event(t, { bubbles: true }));
    });
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
        etat(messageDelai(e, e.message || "Le parcours n'a pas pu être établi."), true);
        rendreParcours();
      });
  }

  function demarrer() {
    /* Le référentiel du moteur n'est plus demandé ici : datacenter.js l'a déjà
       fait pour construire le formulaire. Le redemander doublait une requête
       pour la jeter aussitôt, et le limiteur de débit, lui, la comptait. */
    var u = lireURL();
    fetch("/api/datacenter/decarbonation")
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) throw new Error("cadre indisponible");
        CADRE = j.referentiel;
        VOIE = (u.voie && CADRE.voies[u.voie]) ? u.voie : Object.keys(CADRE.voies)[0];
        ETAPE = u.etape || null;
        rendreVoies();
        rendreCadre();
        rendreHierarchie();
        rendreTextes();
        rendreParcours();
        attendreFormulaire(function () {
          brancherFormulaire();
          /* La reprise AVANT le premier calcul : sinon le parcours se
             dessinerait sur un profil vide puis se redessinerait, et le
             lecteur verrait la page se contredire en une seconde. */
          reprendreProfil(u);
          charger();
        });
      })
      .catch(function () {
        /* L'échec le dit DANS la section concernée, et nulle part ailleurs :
           le calcul de la page, lui, fonctionne indépendamment. */
        var z = $("#dk-parcours");
        if (z) {
          z.innerHTML = '<p class="note">Le cadre de décarbonation n’a pas pu '
            + "être chargé. Le calcul énergie, eau et carbone ci-dessus "
            + "fonctionne indépendamment.</p>";
        }
        var h = $("#dk-hierarchie");
        if (h) h.innerHTML = "";
      });
  }

  /* ── CE QUE LA CARTE PROMET, ET CE QUE LE MOTEUR PRODUIT ──────────────
     `apport_moteur` est une DÉCLARATION écrite à la main. Une fonction
     retirée, et elle continue de promettre. Ce bloc confronte la déclaration à
     ce qui sort réellement du moteur — et ne paraît QUE s'il a trouvé quelque
     chose : une régression, ou de la matière produite que la carte n'annonce
     pas. Il ne déclare aucune conformité : une valeur qui sort n'est pas une
     exigence satisfaite, et la réserve du service le dit. */
  function ecartReferentiel() {
    var z = $("#dk-ecart");
    if (!z) return;
    fetch("/api/datacenter/ecart-referentiel")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j || !j.ok) return;
        var lignes = (j.etapes || []).filter(function (l) {
          return l.etat === "regression" || l.etat === "sous_declare";
        });
        if (!lignes.length) return;          /* la carte et le moteur s'accordent */
        var h = "<h3>Écart entre le cadre et le moteur</h3>";
        h += lignes.map(function (l) {
          var grave = l.etat === "regression";
          return '<div class="note" style="border-left:3px solid '
            + (grave ? "var(--danger,#c0392b)" : "var(--amber,#b8860b)")
            + ';padding-left:10px;margin:8px 0">'
            + "<b>" + esc(l.nom) + "</b> — annoncé « " + esc(l.declare) + " », "
            + l.produit.length + " grandeur(s) au moteur.<br>"
            + esc(l.dit) + "</div>";
        }).join("");
        h += '<p class="note">' + esc(j.reserve) + "</p>";
        z.innerHTML = h;
        z.hidden = false;
      })
      .catch(function () { /* le calcul de la page ne dépend pas de ce bloc */ });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      demarrer(); ecartReferentiel();
    });
  } else {
    demarrer();
    ecartReferentiel();
  }
})();
