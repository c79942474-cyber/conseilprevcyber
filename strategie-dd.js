/* Le questionnaire des quatre perspectives, et le livrable qui en découle.
 *
 * CE QUE CETTE PAGE DOIT TENIR :
 *
 *   1. TROIS PERSPECTIVES SE NOTENT, PAS QUATRE. La science n'est jamais
 *      proposée à la saisie. Le jour où un champ apparaîtrait dans cette
 *      colonne, la page recueillerait une opinion et l'afficherait ensuite
 *      comme une mesure — et les écarts perception/réalité, qui sont l'apport
 *      de la méthode, deviendraient indétectables.
 *
 *   2. CE QUI N'EST PAS NOTÉ RESTE VIDE. Aucune valeur par défaut, aucun
 *      pré-remplissage : « — non instruit — » est la première option et la
 *      valeur initiale de chaque sélecteur. Un formulaire qui pré-remplit
 *      « secondaire » ferait disparaître du livrable tout ce qu'on n'a pas
 *      regardé.
 *
 *   3. RIEN N'EST CONSERVÉ. Les réponses sont montées à chaque appel depuis le
 *      DOM. Aucun stockage local, aucune reprise : ce document appartient au
 *      client, pas au navigateur.
 */
(function () {
  "use strict";

  /* LE DESTINATAIRE, S'IL A ÉTÉ CHOISI. « transmettre.js » est un module à
     part : s'il n'a pas chargé, l'export part sans bordereau plutôt que
     d'échouer. Un document sans bordereau reste un document ; un export qui
     casse, non — et le client n'aurait plus rien à transmettre du tout. */
  function TR(o) {
    return (window.TRANSMETTRE && window.TRANSMETTRE.corps)
      ? window.TRANSMETTRE.corps(o) : o;
  }

  var Q = null;         // le questionnaire servi par le serveur
  var DERNIERE = null;  // la dernière stratégie établie

  function $(s) { return document.querySelector(s); }
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function etat(msg, err) {
    var el = $("#sd-etat");
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = err ? "var(--red, #F0A0A0)" : "";
  }

  /* ═════════════════════════════════════════════════════════════════════
     LES QUATRE PERSPECTIVES, EN TÊTE
     ═════════════════════════════════════════════════════════════════════ */

  function rendrePerspectives() {
    var z = $("#sd-persp");
    if (!z) return;
    z.innerHTML = Q.perspectives.map(function (p) {
      return '<article class="sd-p p-' + esc(p.cle) + '">'
        + "<h3>" + esc(p.nom)
        + '<span class="sd-src s-' + esc(p.source) + '">'
        + (p.source === "client" ? "vous répondez" : "établi par les données")
        + "</span></h3>"
        + '<p class="q">' + esc(p.question) + "</p>"
        + '<p class="o">' + esc(p.objet) + "</p>"
        + "<ul>" + p.outils.map(function (o) {
            return "<li>" + esc(o) + "</li>"; }).join("") + "</ul>"
        + (p.garde ? '<p class="sd-garde">' + esc(p.garde) + "</p>" : "")
        + "</article>";
    }).join("");
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE PROJET, LE CONTEXTE, LES QUESTIONS OUVERTES
     ═════════════════════════════════════════════════════════════════════ */

  function rendreIdentite() {
    var champs = [
      ["projet", "Nom du projet", "DC Nord — 20 MW"],
      ["organisation", "Organisation", "—"],
      ["site", "Site ou territoire", "—"],
    ];
    $("#sd-identite").innerHTML = '<div class="sd-grille">'
      + champs.map(function (c) {
          return '<label class="sd-ch" for="sd-id-' + c[0] + '">'
            + '<span class="lab">' + esc(c[1]) + "</span>"
            + '<input id="sd-id-' + c[0] + '" data-identite="' + c[0] + '" '
            + 'type="text" placeholder="' + esc(c[2]) + '"></label>';
        }).join("")
      + "</div>";
  }

  function rendreContexte() {
    $("#sd-contexte").innerHTML = '<div class="sd-grille">'
      + Q.contexte.map(function (c) {
          return '<label class="sd-ch" for="sd-ctx-' + esc(c.cle) + '">'
            + '<span class="lab">' + esc(c.nom) + "</span>"
            + '<select id="sd-ctx-' + esc(c.cle) + '" data-contexte="'
            + esc(c.cle) + '">'
            /* Vide en premier ET par défaut : un contexte pré-rempli
               laisserait croire qu'on a répondu. */
            + '<option value="">— non renseigné —</option>'
            + c.options.map(function (o) {
                return '<option value="' + esc(o[0]) + '">' + esc(o[1])
                  + "</option>"; }).join("")
            + "</select>"
            + '<span class="aide">' + esc(c.pourquoi) + "</span></label>";
        }).join("")
      + "</div>";
  }

  function rendreOuvertes() {
    $("#sd-ouvertes").innerHTML = Q.ouvertes.map(function (o) {
      return '<label class="sd-ch sd-ouv" for="sd-ouv-' + esc(o.cle) + '">'
        + '<span class="lab">' + esc(o.libelle) + "</span>"
        + '<textarea id="sd-ouv-' + esc(o.cle) + '" data-ouverte="'
        + esc(o.cle) + '"></textarea></label>';
    }).join("");
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE REGISTRE DES ENJEUX

     Trois sélecteurs par enjeu, et trois seulement. La perspective
     scientifique est AFFICHÉE — « ce que les données en disent » — et n'est
     jamais proposée à la saisie.
     ═════════════════════════════════════════════════════════════════════ */

  function rendreEnjeux() {
    var z = $("#sd-enjeux");
    var familles = [];
    Q.enjeux.forEach(function (e) {
      if (familles.indexOf(e.famille) === -1) familles.push(e.famille);
    });
    var h = "";
    familles.forEach(function (f) {
      var liste = Q.enjeux.filter(function (e) { return e.famille === f; });
      h += '<div class="sd-fam"><h3>' + esc(liste[0].famille_nom) + "</h3>";
      liste.forEach(function (e) { h += blocEnjeu(e); });
      h += "</div>";
    });
    z.innerHTML = h;

    /* CE QUI EST COCHÉ SE VOIT SANS OUVRIR. Replier la liste des porteurs
       gagne de la place, mais cacherait du même coup ce qui y a été choisi :
       il faudrait rouvrir les vingt cartes pour vérifier. Le résumé porte donc
       le compte, mis à jour à chaque clic. Un dépliant qui masque un état
       renseigné est pire qu'une liste longue — on ne se fie plus à ce qu'on
       lit sans dérouler. */
    function compter(d) {
      if (!d) return;
      var n = d.querySelectorAll('[data-groupe][aria-pressed="true"]').length;
      var s = d.querySelector("summary");
      var p = s && s.querySelector(".sd-grp-n");
      if (!s) return;
      if (!n) { if (p) p.remove(); return; }
      if (!p) {
        p = document.createElement("span");
        p.className = "sd-grp-n";
        s.appendChild(p);
      }
      p.textContent = "· " + n + " retenu" + (n > 1 ? "s" : "");
    }

    z.querySelectorAll("[data-groupe]").forEach(function (b) {
      b.addEventListener("click", function () {
        var on = b.getAttribute("aria-pressed") === "true";
        b.setAttribute("aria-pressed", on ? "false" : "true");
        compter(b.closest(".sd-grp-d"));
      });
    });
  }

  function blocEnjeu(e) {
    var h = '<article class="sd-e" data-enjeu="' + esc(e.cle) + '">'
      + "<h4>" + esc(e.nom) + "</h4>"
      + '<p class="dit"><b>Ce que les données en disent.</b> ' + esc(e.science_dit)
      + "</p>"
      + '<p class="piege"><b>Le piège.</b> ' + esc(e.piege) + "</p>"
      + '<div class="sd-notes">';
    Q.perspectives.forEach(function (p) {
      /* LE point : on ne fabrique un sélecteur que pour les perspectives que
         le client remplit. `a_noter` vient du serveur — le décider ici ferait
         diverger la page du module au premier ajustement. */
      if (e.a_noter.indexOf(p.cle) === -1) return;
      h += '<div class="sd-note n-' + esc(p.cle) + '">'
        + "<label for=\"sd-n-" + esc(e.cle) + "-" + esc(p.cle) + "\">"
        + esc(p.nom) + "</label>"
        + '<select id="sd-n-' + esc(e.cle) + "-" + esc(p.cle) + '" '
        + 'data-note="' + esc(p.cle) + '">'
        + '<option value="">— non instruit —</option>';
      Object.keys(Q.degres).forEach(function (d) {
        h += '<option value="' + esc(d) + '">' + esc(d) + " — "
          + esc(Q.degres[d].nom) + "</option>";
      });
      h += "</select></div>";
    });
    h += "</div>";
    /* LA LISTE DES PORTEURS SE REPLIE, et c'est ce qui rend les colonnes
       utiles. Mises en trois colonnes, les cartes se resserrent à 336 px : les
       pastilles de parties prenantes s'y empilent sur plusieurs rangées et
       pèsent alors 237 px, soit plus du tiers de la carte — pour un champ
       marqué « facultatif ». Passer en colonnes sans replier cela ne gagnait
       que 10 % de hauteur.
       Repliée, la question tient sur une ligne et reste à un clic. Les boutons
       demeurent dans le document : `reponses()` les lit par `aria-pressed`, et
       un dépliant fermé n'efface rien — ce qui a été coché part donc bien dans
       le livrable, que la liste soit ouverte ou non. */
    h += '<details class="sd-grp-d"><summary>Qui porte cet enjeu&nbsp;? '
      + "(facultatif)</summary>"
      + '<div class="sd-grp"><div class="b">'
      + Q.groupes_parties_prenantes.map(function (g) {
          return '<button type="button" data-groupe="' + esc(g[0]) + '" '
            + 'aria-pressed="false">' + esc(g[1]) + "</button>";
        }).join("")
      + "</div></div></details>";
    return h + "</article>";
  }

  /* ═════════════════════════════════════════════════════════════════════
     MONTER LES RÉPONSES — depuis le DOM, à chaque appel
     ═════════════════════════════════════════════════════════════════════ */

  function reponses() {
    var r = {identite: {}, contexte: {}, ouvertes: {}, notes: {}};
    document.querySelectorAll("[data-identite]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v) r.identite[el.getAttribute("data-identite")] = v;
    });
    document.querySelectorAll("[data-contexte]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v) r.contexte[el.getAttribute("data-contexte")] = v;
    });
    document.querySelectorAll("[data-ouverte]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v) r.ouvertes[el.getAttribute("data-ouverte")] = v;
    });
    document.querySelectorAll("[data-enjeu]").forEach(function (bloc) {
      var cle = bloc.getAttribute("data-enjeu");
      var o = {};
      bloc.querySelectorAll("[data-note]").forEach(function (sel) {
        var v = (sel.value || "").trim();
        /* Vide reste VIDE. Y mettre un zéro ferait passer « je n'ai pas
           regardé » pour « sans objet », et l'enjeu disparaîtrait du livrable
           au lieu d'y figurer comme un trou. */
        if (v !== "") o[sel.getAttribute("data-note")] = parseInt(v, 10);
      });
      var g = [];
      bloc.querySelectorAll('[data-groupe][aria-pressed="true"]')
        .forEach(function (b) { g.push(b.getAttribute("data-groupe")); });
      if (g.length) o.groupes = g;
      if (Object.keys(o).length) r.notes[cle] = o;
    });
    return r;
  }

  function poster(url, corps) {
    return fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(corps),
    }).then(function (rep) {
      return rep.text().then(function (t) {
        var j = null;
        try { j = JSON.parse(t); } catch (e) { j = null; }
        if (!j) throw new Error("Le serveur a répondu une erreur (HTTP "
          + rep.status + "). Réessayez dans un instant.");
        if (!rep.ok || !j.ok) throw new Error(j.message || j.error
          || ("HTTP " + rep.status));
        return j;
      });
    });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE LIVRABLE
     ═════════════════════════════════════════════════════════════════════ */

  function etablir() {
    var b = $("#sd-gen");
    if (b) b.disabled = true;
    etat("Établissement de la stratégie…");
    poster("/api/datacenter/strategie", reponses())
      .then(function (j) {
        DERNIERE = j.strategie;
        etat("");
        rendreStrategie(j.strategie);
        ["#sd-docx", "#sd-pdf"].forEach(function (s) {
          var e = $(s); if (e) e.disabled = false;
        });
        var z = $("#sd-resultat");
        if (z) z.scrollIntoView({behavior: "smooth", block: "start"});
      })
      .catch(function (e) {
        etat(e.message || "La stratégie n'a pas pu être établie.", true);
      })
      .then(function () { if (b) b.disabled = false; });
  }

  function rendreStrategie(s) {
    var z = $("#sd-resultat");
    if (!z) return;
    var h = "";

    /* LES ALERTES EN TÊTE. Placées en fin de document, elles se lisent après
       que le lecteur s'est félicité du résultat — c'est-à-dire jamais. */
    if ((s.alertes || []).length) {
      h += '<div id="sd-alertes">';
      s.alertes.forEach(function (a) {
        h += '<div class="sd-al g-' + esc(a.gravite) + '"><b>' + esc(a.titre)
          + ".</b> " + esc(a.dit) + "</div>";
      });
      h += "</div>";
    }

    h += '<div id="sd-tensions">';
    (s.tensions || []).forEach(function (t) {
      h += '<div class="sd-t"><h3>' + esc(t.nom) + "</h3>"
        + '<p class="d">' + esc(t.dit) + "</p>"
        + '<p class="l">' + esc(t.lecture) + "</p></div>";
    });
    h += "</div>";

    h += '<div id="sd-matrice">';
    (s.ordre_verdicts || []).forEach(function (v) {
      var groupe = (s.par_verdict || {})[v] || [];
      if (!groupe.length) return;
      h += '<div class="sd-v" data-verdict="' + esc(v) + '">'
        + "<h3>" + esc(s.verdicts[v].nom) + " — " + groupe.length + "</h3>"
        + '<p class="d">' + esc(s.verdicts[v].dit) + "</p>";
      groupe.forEach(function (l) { h += blocLigne(l, s); });
      h += "</div>";
    });
    h += "</div>";

    if ((s.programme || []).length) {
      h += '<div class="sd-v" id="sd-programme"><h3>Le programme d’étude qui en '
        + "découle</h3>"
        + '<p class="d">Chaque enjeu retenu appelle un outil, et chaque outil '
        + "une production datée. C’est ce qui distingue une stratégie d’une "
        + "déclaration d’intention.</p>";
      s.programme.forEach(function (t) {
        h += '<div class="sd-l"><h4>' + esc(t.nom)
          + (t.mode_nom ? '<span class="sd-mode m-' + esc(t.mode) + '">'
              + esc(t.mode_nom) + "</span>" : "")
          + '<span class="sd-sc">' + esc(t.motif) + "</span></h4>"
          + '<p class="sd-out">' + esc(t.outil) + "</p></div>";
      });
      h += "</div>";
    }

    z.innerHTML = h;
  }

  function blocLigne(l, s) {
    var n = l.notes || {};
    var h = '<div class="sd-l v-' + esc(l.verdict) + '" data-ligne="'
      + esc(l.cle) + '"><h4>' + esc(l.nom)
      + (l.mode ? '<span class="sd-mode m-' + esc(l.mode) + '">'
          + esc(s.modes[l.mode].nom) + "</span>" : "")
      + '<span class="sd-sc">' + esc(l.famille_nom) + "</span></h4>";
    h += '<p class="sd-sc">'
      + "raison d’être " + note(n.raison_etre)
      + " · parties prenantes " + note(n.parties_prenantes)
      + " · science " + note(n.science)
      + " · valeur " + note(n.valeur) + "</p>";
    if (l.verdict === "non_instruit") {
      h += "<p>Perspectives manquantes : <b>" + esc((l.manquantes || []).join(", "))
        + "</b>.</p>";
    }
    h += "<p>" + esc(l.dit) + "</p>";
    if (l.science_motif) {
      h += '<p class="sd-sc">Ce site : ' + esc(l.science_motif) + "</p>";
    }
    if (l.chiffre) {
      h += '<p class="sd-sc">' + esc(l.chiffre.nom) + " : "
        + esc(l.chiffre.valeur) + " " + esc(l.chiffre.unite)
        + (l.chiffre.incertitude ? " · " + esc(l.chiffre.incertitude) : "")
        + "</p>";
    }
    if ((l.groupes || []).length) {
      h += '<p class="sd-sc">Porté par : '
        + esc(l.groupes.map(function (g) { return g.nom; }).join(", ")) + "</p>";
    }
    if (l.verdict !== "ecarte" && l.verdict !== "non_instruit") {
      h += '<p class="sd-out">Outil de l’étude : ' + esc(l.outil) + "</p>";
    }
    return h + "</div>";
  }

  function note(v) {
    return v === null || v === undefined ? "—" : String(v);
  }

  /* ═════════════════════════════════════════════════════════════════════
     EXPORT — fermé, et l'échec doit le DIRE
     ═════════════════════════════════════════════════════════════════════ */

  function exporter(fmt) {
    if (!DERNIERE) return;
    etat("Mise en page du livrable…");
    var corps = TR(reponses());
    corps.format = fmt;
    fetch("/api/datacenter/strategie/export", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(corps),
    }).then(function (r) {
      if (r.status === 401 || r.status === 403) {
        /* Le message nomme la cause. « Erreur » aurait envoyé le lecteur
           vérifier ses réponses alors qu'il lui manquait une session. */
        throw new Error("L’export du livrable demande un compte : le document "
          + "porte votre nom, votre site et vos arbitrages. "
          + "Connectez-vous, puis relancez l’export.");
      }
      if (!r.ok) throw new Error("La mise en page a échoué (HTTP " + r.status + ").");
      return r.blob();
    }).then(function (blob) {
      var u = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = u;
      a.download = "strategie-dd." + fmt;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
      etat("");
    }).catch(function (e) {
      etat(e.message || "L’export a échoué.", true);
    });
  }

  /* ═════════════════════════════════════════════════════════════════════
     CHARGEMENT
     ═════════════════════════════════════════════════════════════════════ */

  function demarrer() {
    fetch("/api/datacenter/strategie/questionnaire")
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) throw new Error("questionnaire indisponible");
        Q = j.questionnaire;
        rendrePerspectives();
        rendreIdentite();
        rendreContexte();
        rendreOuvertes();
        rendreEnjeux();
        var g = $("#sd-gen");
        if (g) g.addEventListener("click", etablir);
        var d = $("#sd-docx");
        if (d) d.addEventListener("click", function () { exporter("docx"); });
        var p = $("#sd-pdf");
        if (p) p.addEventListener("click", function () { exporter("pdf"); });
      })
      .catch(function () {
        var z = $("#sd-enjeux");
        if (z) {
          z.innerHTML = '<p class="note">Le questionnaire n’a pas pu être '
            + 'chargé. Le <a href="/datacenter">calcul énergie, eau et '
            + "carbone</a> fonctionne indépendamment.</p>";
        }
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }
})();
