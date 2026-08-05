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

  /* ── Les infobulles ─────────────────────────────────────────────────────
     Cette page aligne des sigles exacts et opaques : ESQ, APD, DCE, FEED,
     EPCI, gel contractuel, accord partiel, classe 3. Sans explication, elle ne
     s'adresse qu'à ceux qui n'en avaient pas besoin.

     Pas d'attribut `title` natif : il n'apparaît qu'après une seconde
     d'immobilité, ne se met pas en forme, ne passe pas à la ligne, et reste
     hors d'atteinte au clavier. On construit donc une infobulle unique,
     déplacée d'une cible à l'autre.

     Un seul attribut à poser dans le rendu — data-info="famille:clé" — et une
     seule recherche dans le glossaire servi par le serveur. C'est ce qui permet
     d'en couvrir douze sortes sans douze mécanismes. */
  var TIP = null, TIP_CIBLE = null;

  function tipEl() {
    if (TIP) return TIP;
    TIP = document.createElement("div");
    TIP.className = "ig-tip";
    TIP.setAttribute("role", "tooltip");
    TIP.id = "ig-tip";
    TIP.hidden = true;
    document.body.appendChild(TIP);
    return TIP;
  }

  function tipTexte(ref) {
    var G = (CADRE && CADRE.glossaire) || {};
    var bout = String(ref || "").split(":");
    var fam = G[bout[0]];
    if (!fam) return null;
    var e = fam[bout.slice(1).join(":")];
    return e && (e.nom || e.aide) ? e : null;
  }

  function tipMontrer(cible) {
    var e = tipTexte(cible.getAttribute("data-info"));
    if (!e) return;
    var t = tipEl();
    t.innerHTML = '<b>' + esc(e.nom) + "</b>"
      /* Les définitions viennent du serveur et contiennent des sauts de ligne
         signifiants (« ce qu'elle décide », « ce qu'elle verrouille ») : on les
         rend, sans jamais interpréter le reste comme du HTML. */
      + (e.aide ? "<p>" + esc(e.aide).replace(/\n/g, "<br>") + "</p>" : "");
    t.hidden = false;
    TIP_CIBLE = cible;
    cible.setAttribute("aria-describedby", "ig-tip");
    tipPlacer(cible);
  }

  function tipCacher() {
    if (!TIP) return;
    TIP.hidden = true;
    if (TIP_CIBLE) TIP_CIBLE.removeAttribute("aria-describedby");
    TIP_CIBLE = null;
  }

  function tipPlacer(cible) {
    var t = tipEl(), r = cible.getBoundingClientRect();
    /* Mesurée AVANT d'être positionnée : sans cela on placerait une boîte dont
       on ignore la taille, et elle sortirait du cadre une fois sur deux. */
    t.style.left = "0px"; t.style.top = "0px";
    var b = t.getBoundingClientRect();
    var marge = 10;
    var x = r.left + r.width / 2 - b.width / 2;
    x = Math.max(marge, Math.min(window.innerWidth - b.width - marge, x));
    /* Au-dessus par défaut ; en dessous s'il n'y a pas la place en haut. Une
       infobulle qui déborde du haut de la fenêtre est illisible et ne se
       rattrape pas au défilement. */
    var y = r.top - b.height - 8;
    if (y < marge) y = r.bottom + 8;
    t.style.left = Math.round(x + window.pageXOffset) + "px";
    t.style.top = Math.round(y + window.pageYOffset) + "px";
  }

  /* Un seul écouteur, posé une fois sur le document, plutôt qu'un par cible :
     la page se redessine à chaque saisie et à chaque changement de phase, et
     des écouteurs par élément seraient à reposer à chaque fois — ou à oublier. */
  function tipBrancher() {
    if (document.__igTip) return;
    document.__igTip = true;
    var dans = function (ev) {
      var c = ev.target && ev.target.closest && ev.target.closest("[data-info]");
      /* On rouvre AUSSI quand la boîte est masquée alors que la cible n'a pas
         changé. Ne comparer que la cible suffisait tant que tipCacher() était
         le seul chemin de fermeture — mais une boîte masquée par ailleurs
         restait alors définitivement close sur cette cible, sans rien pour le
         signaler. Un état interne et l'écran doivent pouvoir se rattraper. */
      if (c && (c !== TIP_CIBLE || (TIP && TIP.hidden))) tipMontrer(c);
    };
    document.addEventListener("mouseover", dans);
    document.addEventListener("mouseout", function (ev) {
      var c = ev.target && ev.target.closest && ev.target.closest("[data-info]");
      if (c && c === TIP_CIBLE) tipCacher();
    });
    /* Le clavier au même titre que la souris : une explication accessible
       seulement au survol n'existe pas pour qui navigue au clavier. */
    document.addEventListener("focusin", dans);
    document.addEventListener("focusout", function (ev) {
      if (ev.target === TIP_CIBLE) tipCacher();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") tipCacher();
    });
    /* Au défilement, la cible bouge et l'infobulle resterait en arrière. */
    window.addEventListener("scroll", function () {
      if (TIP_CIBLE) tipPlacer(TIP_CIBLE);
    }, { passive: true });
  }

  /* Le marquage d'une cible. `tabindex` la rend atteignable au clavier ; sans
     lui l'explication serait réservée à la souris. */
  function info(ref) {
    return ' data-info="' + esc(ref) + '" tabindex="0"';
  }

  /* ── L'identification du projet ────────────────────────────────────────
     Trois listes construites depuis le référentiel. Chaque option porte ce
     qu'elle IMPLIQUE, et cette implication est affichée dès la sélection : sans
     elle, le lecteur choisit une étiquette sans savoir ce qu'elle engage, et la
     liste ne vaut pas mieux qu'un champ libre. */
  function bâtirIdentification() {
    var champs = (CADRE.identification || []);
    if (!champs.length) return;
    var z = $("#ig-ident");
    var h = "";
    champs.forEach(function (c) {
      var id = "ig-" + c.id;
      h += '<label class="dc-champ" for="' + id + '">'
        + '<span class="dc-lab">' + esc(c.label) + "</span>"
        + '<select id="' + id + '" data-ident="' + esc(c.id) + '">'
        + '<option value="">— non précisé —</option>'
        + (c.options || []).map(function (o) {
            return '<option value="' + esc(o.cle) + '">' + esc(o.nom) + "</option>";
          }).join("")
        + "</select>"
        + '<span class="dc-aide">' + esc(c.aide) + "</span>"
        + '<span class="ig-impl" id="' + id + '-i" hidden></span>'
        + "</label>";
    });
    z.insertAdjacentHTML("beforeend", h);
    z.querySelectorAll("[data-ident]").forEach(function (s) {
      s.addEventListener("change", function () { montrerImplication(s); });
    });
    var n = $("#ig-ident-n");
    if (n) n.textContent = CADRE.identification_note || "";
  }

  function montrerImplication(sel) {
    var cid = sel.getAttribute("data-ident");
    var champ = (CADRE.identification || []).filter(function (c) { return c.id === cid; })[0];
    var box = $("#" + sel.id + "-i");
    if (!champ || !box) return;
    var o = (champ.options || []).filter(function (x) { return x.cle === sel.value; })[0];
    if (!o) { box.hidden = true; box.textContent = ""; return; }
    box.hidden = false;
    box.textContent = o.implique;
  }

  function lireIdentification() {
    var o = {};
    document.querySelectorAll("#ig-ident [data-ident]").forEach(function (s) {
      if (s.value) o[s.getAttribute("data-ident")] = s.value;
    });
    return o;
  }

  /* ── Les onglets de filière ──────────────────────────────────────────── */
  function bâtirOnglets() {
    var f = (CADRE.filieres || {});
    var h = "";
    Object.keys(f).forEach(function (k) {
      h += '<button type="button" role="tab" data-fil="' + esc(k) + '" aria-selected="'
        + (k === FILIERE ? "true" : "false") + '" class="' + (k === FILIERE ? "on" : "")
        + '"' + info("filiere:" + k) + ">" + esc(f[k].nom) + "</button>";
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
        + '<span class="c"' + info("phase:" + e.code) + ">" + esc(e.code) + "</span>"
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
        marquerURL();
        rendreParcours();
        chargerDossier();
      });
    });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LA PAGE EST ADRESSABLE

     Sans cela, un livrable qui écrit « SPC-HVAC, repris en APD » ne peut y
     renvoyer que par un lien vers le haut de la page, à charge pour le lecteur
     de retrouver la filière, la phase et la pièce. Un lien qui oblige à
     chercher n'est pas un lien.

     La forme retenue — #phase=APD&piece=SPC-HVAC — se lit à l'œil dans un
     document imprimé, ce qu'un identifiant opaque ne permettrait pas. */
  function lireURL() {
    var h = (window.location.hash || "").replace(/^#/, "");
    if (!h) return null;
    var o = {};
    h.split("&").forEach(function (p) {
      var kv = p.split("=");
      if (kv.length === 2) o[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1]);
    });
    return o;
  }

  function marquerURL() {
    if (!PHASE) return;
    /* replaceState et non pushState : parcourir les phases n'est pas une
       navigation, et empiler quinze entrées d'historique rendrait le bouton
       « précédent » du navigateur inutilisable. */
    try {
      history.replaceState(null, "", "#phase=" + encodeURIComponent(PHASE));
    } catch (e) { /* navigation locale ou file:// — sans conséquence */ }
  }

  /* Applique ce que l'URL demande, une fois le cadre chargé. Renvoie le code
     de pièce à mettre en évidence, s'il y en a un. */
  function appliquerURL() {
    var o = lireURL();
    if (!o || !o.phase) return null;
    var ph = String(o.phase).toUpperCase();
    var q = (CADRE.phases || []).filter(function (x) { return x.code === ph; })[0];
    if (!q) return null;          // phase inconnue : on ne devine pas
    FILIERE = q.filiere;
    PHASE = ph;
    var t = document.querySelector('#ig-filieres [data-fil="' + FILIERE + '"]');
    if (t) {
      document.querySelectorAll("#ig-filieres [data-fil]").forEach(function (b) {
        b.classList.toggle("on", b === t);
        b.setAttribute("aria-selected", b === t ? "true" : "false");
      });
    }
    return o.piece ? String(o.piece).toUpperCase() : null;
  }

  /* Met en évidence la pièce visée par le lien et l'amène à l'écran. Un
     registre de trente pièces sans repère laisse le lecteur la chercher —
     c'est-à-dire abandonner. */
  function viserPiece(code) {
    if (!code) return;
    var el = document.querySelector('#ig-dossier .ig-pc [data-piece="' + code + '"]');
    var bloc = el && el.closest(".ig-pc");
    if (!bloc) return;
    document.querySelectorAll(".ig-pc.ig-vise-pc").forEach(function (e) {
      e.classList.remove("ig-vise-pc");
    });
    bloc.classList.add("ig-vise-pc");
    var doux = !window.matchMedia
      || !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    bloc.scrollIntoView({ behavior: doux ? "smooth" : "auto", block: "center" });
  }

  /* ── Le dossier de la phase ──────────────────────────────────────────── */
  function rendreDossier(d) {
    var h = '<div class="ig-d"><h3>' + esc(d.code) + " — " + esc(d.nom) + "</h3>"
      + '<p class="sous">' + esc(d.objet) + "</p>";

    h += '<div class="ig-meta">'
      + "<div><b>Ce qu'elle décide</b>" + esc(d.decide) + "</div>"
      + "<div><b>Ce qu'elle verrouille</b>" + esc(d.verrouille) + "</div>"
      + "<div><b>Précision attendue</b>" + esc(d.precision.valeur)
      + ' <span class="dc-unite"><span' + info("nature:" + d.precision.nature) + ">"
      + esc(d.precision.nature) + '</span> · <span' + info("aace:" + d.precision.aace)
      + ">" + esc(d.precision.aace) + "</span></span></div>"
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

    h += '<p class="sous" style="margin-top:14px"><span'
      + info("apport:" + d.apport_moteur) + ">" + esc(d.apport_texte) + "</span></p>";
    h += '<div class="ig-g">';
    (d.grandeurs || []).forEach(function (g) {
      var rmp = g.statut !== "recevable";
      h += '<div class="v' + (rmp ? " rmp" : "") + '">'
        + '<div class="n">' + esc(g.nom) + "</div>"
        + '<div class="q">' + fr(g.valeur) + ' <span class="u">' + esc(g.unite) + "</span></div>"
        + (g.incertitude ? '<div class="i">' + esc(g.incertitude) + "</div>" : "")
        + '<span class="st"' + info("statut:" + (rmp ? "a_remplacer" : "recevable")) + ">"
        + (rmp
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
        h += '<div class="ig-sub"><span class="t"' + info("poste:" + s.cle) + ">"
          + esc(s.nom) + "</span>"
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
      h += '<div class="ig-reg-g"><h5><span' + info("type_piece:" + t) + ">"
        + esc(g[0].type_nom) + "</span> <span>" + esc(g[0].type_aide) + "</span></h5>";
      g.forEach(function (p) {
        h += '<div class="ig-pc' + (p.moteur ? " mot" : "")
          + (p.discipline ? " dis" : "") + '">'
          + '<div class="ig-pc-h"><code>' + esc(p.code) + "</code> "
          + '<span class="ti">' + esc(p.titre) + "</span>"
          + '<span class="em"' + info("emetteur:" + p.emetteur) + ">"
          + esc(p.emetteur_nom) + "</span>"
          + (p.moteur ? '<span class="mo"' + info("moteur:oui")
              + ">alimentée par le calcul</span>" : "")
          + "</div>"
          /* Le NIVEAU commande la profondeur attendue. Sans lui, une même
             spécification se lit à l'identique de l'esquisse à la consultation,
             alors qu'elle n'y engage pas du tout la même chose. */
          + (p.niveau_nom
              ? '<div class="ig-pc-nv"><span class="nv nv-' + esc(p.niveau) + '"'
                + info("niveau:" + p.niveau) + ">"
                + esc(p.niveau_nom) + "</span> " + esc(p.niveau_aide)
                + (p.discipline_nom
                    ? ' <span class="di"' + info("discipline:" + p.discipline) + ">"
                      + esc(p.discipline_nom) + "</span>" : "")
                + (p.autres_phases && p.autres_phases.length
                    ? '<span class="ap">document unique, repris en '
                      + esc(p.autres_phases.join(", ")) + "</span>" : "")
                + "</div>"
              : "")
          + '<ul>' + p.contenu.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("")
          + "</ul>"
          /* CE QU'ON DEMANDE À LA BASE. « Adossé à la base de connaissance »
             est une affirmation ; l'afficher la rend vérifiable — et montre
             qu'on cherche le SUJET de la pièce, pas son titre. */
          + (p.recherche_origine === "titre"
              ? '<div class="ig-pc-rq tit"><span class="lb"'
                + info("recherche:titre") + ">recherche</span> "
                + "<i>son intitulé, faute de vocabulaire déclaré</i></div>"
              : '<div class="ig-pc-rq"><span class="lb"'
                + info("recherche:" + p.recherche_origine) + ">recherche</span> "
                + esc(p.recherche) + "</div>")
          + '<div class="ig-pc-a"><button type="button" class="ig-gen" '
          + 'data-piece="' + esc(p.code) + '">Rédiger cette pièce</button>'
          + '<button type="button" class="ig-voir" '
          + 'data-piece="' + esc(p.code) + '">Ce que la base apporte</button>'
          /* Dire la vérité sur ce qu'une IA produit pour une pièce graphique :
             elle n'en dessine pas une, elle en écrit la spécification. */
          + (p.type === "plan" || p.type === "schema"
              ? '<span class="ig-pc-n">La rédaction produit la SPÉCIFICATION de '
                + 'la pièce graphique — contenu, échelle, conventions — non le '
                + 'dessin lui-même.</span>' : "")
          + '</div><div class="ig-pc-doc" data-doc="' + esc(p.code) + '"></div></div>';
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
    document.querySelectorAll("#ig-dossier .ig-voir").forEach(function (b) {
      b.addEventListener("click", function () { voirBase(b.getAttribute("data-piece"), b); });
    });
  }

  /* Ce que la base rendrait pour cette pièce, AVANT de rédiger. Consulter ne
     consomme rien ; c'est écrire qui coûte. La distinction vaut d'être offerte :
     elle permet de constater que la base est vide, plutôt que de le découvrir
     dans un document qui n'en dit rien. */
  function voirBase(code, bouton) {
    var z = document.querySelector('#ig-dossier .ig-pc-doc[data-doc="' + code + '"]');
    if (!z || !PHASE) return;
    if (z.getAttribute("data-ouvert") === "1") {
      z.innerHTML = ""; z.removeAttribute("data-ouvert");
      bouton.textContent = "Ce que la base apporte"; return;
    }
    var p = lireProfil();
    p.phase = PHASE; p.piece = code;
    bouton.disabled = true;
    z.innerHTML = '<p class="ig-pc-att">Interrogation de la base…</p>';
    fetch("/api/datacenter/ingenierie/apercu", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    }).then(function (r) { return r.json().then(function (j) { return [r.status, j]; }); })
      .then(function (rj) {
        var st = rj[0], j = rj[1];
        bouton.disabled = false;
        z.setAttribute("data-ouvert", "1");
        bouton.textContent = "Masquer";
        if (st === 401 || st === 403) {
          z.innerHTML = '<p class="ig-pc-att">Connectez-vous pour consulter '
            + "la base documentaire.</p>"; return;
        }
        if (!j || !j.ok) {
          /* Une interrogation EN ÉCHEC et une base VIDE se ressemblent à
             l'écran et n'appellent pas la même réaction. On les distingue. */
          z.innerHTML = '<p class="ig-pc-att err">'
            + esc((j && j.message) || "La base n'a pas pu être interrogée.")
            + " — ce n'est pas la même chose qu'une base sans document sur le "
            + "sujet.</p>"; return;
        }
        var h = '<p class="ig-pc-rqv"><b>Demandé à la base :</b> '
          + esc(j.query || "") + "</p>";
        if (!j.documents || !j.documents.length) {
          h += '<p class="ig-pc-att">Aucun document de la base ne traite ce '
            + "sujet. La pièce sera rédigée sans source interne — le document "
            + "produit le dira, et appellera une relecture renforcée.</p>";
        } else {
          h += '<p class="ig-pc-rqv">' + j.documents.length + " document"
            + (j.documents.length > 1 ? "s" : "") + " · " + j.extraits
            + " extrait" + (j.extraits > 1 ? "s" : "") + "</p><ul class=\"ig-pc-dl\">"
            + j.documents.map(function (d) {
                return "<li>" + esc(d.title || "sans titre")
                  + ' <span class="vi">'
                  + (d.visibility === "internal" ? "interne" : "publique")
                  + "</span> <span class=\"ex\">" + d.extraits + " extrait"
                  + (d.extraits > 1 ? "s" : "") + "</span></li>";
              }).join("") + "</ul>";
        }
        z.innerHTML = h;
      }).catch(function () {
        bouton.disabled = false;
        z.setAttribute("data-ouvert", "1");
        bouton.textContent = "Masquer";
        z.innerHTML = '<p class="ig-pc-att err">La base n\'a pas répondu.</p>';
      });
  }

  function redigerPiece(code, bouton) {
    var z = $("#ig-piece");
    if (!z || !PHASE) return;
    var p = lireProfil();
    p.phase = PHASE;
    p.piece = code;
    p.client = (($("#ig-client") || {}).value || "").trim();
    /* Les clés d'identification, pas des libellés : c'est le serveur qui sait
       ce que chacune implique, et lui envoyer le texte affiché l'obligerait à
       le réinterpréter. */
    var ident = lireIdentification();
    Object.keys(ident).forEach(function (k) { p[k] = ident[k]; });
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
        + "</code></td><td><span class='ig-acc a-" + esc(c.accord) + "'"
        + info("accord:" + c.accord) + ">" + esc(c.accord)
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

  /* Pièce demandée par l'URL, mise en évidence une fois le registre rendu —
     et une seule fois : au clic suivant sur une autre phase, le lecteur ne
     cherche plus cette pièce-là. */
  var PIECE_VISEE = null;

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
        if (PIECE_VISEE) { viserPiece(PIECE_VISEE); PIECE_VISEE = null; }
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

  /* ═════════════════════════════════════════════════════════════════════
     LE PARCOURS GUIDÉ — par rôle et par thème

     Trois états, et un seul visible à la fois : le CHOIX (qui êtes-vous, ce
     qui vous amène), puis les ÉTAPES, une par section de la page. On ne
     déroule pas les cinq étapes d'un coup : une étape à l'écran, celle de la
     section où l'on se trouve, sinon le parcours redevient la table des
     matières qu'il est censé remplacer.

     Le parcours ne DÉPLACE rien et ne masque rien de la page : il fait
     défiler vers la section concernée et la met en relief. Une page qui se
     réorganise sous le lecteur lui fait perdre ce qu'il venait de lire. */
  var GUIDE = null, GUIDE_ETAPE = 0, GUIDE_ROLE = null, GUIDE_THEME = null;

  function guideZone() { return $("#ig-guide"); }

  function guideOuvrir(ouvert) {
    var z = guideZone(), b = $("#ig-lanceur-b");
    if (!z || !b) return;
    z.hidden = !ouvert;
    b.setAttribute("aria-expanded", ouvert ? "true" : "false");
    b.textContent = ouvert ? "Fermer le parcours" : "Ouvrir le parcours guidé";
    if (!ouvert) { guideSurligner(null); GUIDE = null; GUIDE_ETAPE = 0; }
  }

  /* Mettre en relief la section visée. Une seule à la fois, et on retire la
     précédente : deux sections en relief ne désignent plus rien. */
  function guideSurligner(ancre) {
    document.querySelectorAll(".ig-vise").forEach(function (e) {
      e.classList.remove("ig-vise");
    });
    if (!ancre) return;
    var el = document.getElementById(ancre);
    if (!el) return;
    var sec = el.closest("section") || el;
    sec.classList.add("ig-vise");
  }

  function guideChoix() {
    var roles = (CADRE && CADRE.guide_roles) || [];
    var themes = (CADRE && CADRE.guide_themes) || [];
    var h = '<div class="ig-g-choix"><p class="ig-g-q">Qui êtes-vous sur ce projet&nbsp;?</p>'
      + '<div class="ig-g-liste" role="group" aria-label="Rôle">'
      + roles.map(function (r) {
          return '<button type="button" class="ig-g-c'
            + (GUIDE_ROLE === r.id ? " on" : "") + '" data-role="' + esc(r.id) + '">'
            + '<span class="ic" aria-hidden="true">' + esc(r.icone) + "</span>"
            + '<span class="nm">' + esc(r.nom) + "</span>"
            + '<span class="qs">' + esc(r.question) + "</span></button>";
        }).join("")
      + '</div><p class="ig-g-q">Et qu\'est-ce qui vous amène&nbsp;?</p>'
      + '<div class="ig-g-liste th" role="group" aria-label="Thème">'
      + themes.map(function (t) {
          return '<button type="button" class="ig-g-c'
            + (GUIDE_THEME === t.id ? " on" : "") + '" data-theme="' + esc(t.id) + '">'
            + '<span class="ic" aria-hidden="true">' + esc(t.icone) + "</span>"
            + '<span class="nm">' + esc(t.nom) + "</span>"
            + '<span class="qs">' + esc(t.question) + "</span></button>";
        }).join("")
      + "</div>";
    /* Le bouton n'apparaît QUE lorsque les deux choix sont faits : un bouton
       présent mais inopérant se lit comme une panne. */
    h += GUIDE_ROLE && GUIDE_THEME
      ? '<div class="ig-g-go"><button type="button" class="ig-g-b" id="ig-g-go">'
        + "Commencer le parcours →</button></div>"
      : '<p class="ig-g-att">Choisissez un rôle et un thème pour commencer.</p>';
    return h + "</div>";
  }

  function guideRendreChoix() {
    var z = guideZone();
    if (!z) return;
    z.innerHTML = guideChoix();
    z.querySelectorAll("[data-role]").forEach(function (b) {
      b.addEventListener("click", function () {
        GUIDE_ROLE = b.getAttribute("data-role"); guideRendreChoix();
      });
    });
    z.querySelectorAll("[data-theme]").forEach(function (b) {
      b.addEventListener("click", function () {
        GUIDE_THEME = b.getAttribute("data-theme"); guideRendreChoix();
      });
    });
    var g = $("#ig-g-go");
    if (g) g.addEventListener("click", guideCharger);
  }

  function guideCharger() {
    var z = guideZone();
    if (!z || !GUIDE_ROLE || !GUIDE_THEME) return;
    var p = lireProfil();
    p.role = GUIDE_ROLE; p.theme = GUIDE_THEME;
    if (PHASE) p.phase = PHASE;
    z.innerHTML = '<p class="ig-g-att">Établissement du parcours…</p>';
    fetch("/api/datacenter/ingenierie/guide", {
      method: "POST", headers: { "Content-Type": "application/json" },
      credentials: "same-origin", body: JSON.stringify(p),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) {
          z.innerHTML = '<p class="ig-g-att err">'
            + esc((j && j.message) || "Le parcours n'a pas pu être établi.")
            + ' <button type="button" class="ig-g-lien" id="ig-g-retour">Revenir au choix</button></p>';
          var rb = $("#ig-g-retour");
          if (rb) rb.addEventListener("click", guideRendreChoix);
          return;
        }
        GUIDE = j.guide; GUIDE_ETAPE = 0;
        guideRendreEtape();
      }).catch(function () {
        z.innerHTML = '<p class="ig-g-att err">Le parcours n\'a pas répondu.</p>';
      });
  }

  function guideRendreEtape() {
    var z = guideZone();
    if (!z || !GUIDE) return;
    var e = GUIDE.etapes[GUIDE_ETAPE];
    var n = GUIDE.etapes.length;
    var h = '<div class="ig-g-p">'
      + '<div class="ig-g-h"><span class="ig-g-rt">'
      + '<span aria-hidden="true">' + esc(GUIDE.role.icone) + "</span> "
      + esc(GUIDE.role.nom) + " · " + esc(GUIDE.theme.icone) + " "
      + esc(GUIDE.theme.nom) + "</span>"
      + '<button type="button" class="ig-g-lien" id="ig-g-changer">Changer</button>'
      + '<button type="button" class="ig-g-lien" id="ig-g-fermer">Fermer</button></div>'
      /* La barre d'avancement : savoir combien il reste change la disposition
         à continuer. */
      + '<div class="ig-g-jauge" role="progressbar" aria-valuemin="1" aria-valuemax="'
      + n + '" aria-valuenow="' + (GUIDE_ETAPE + 1) + '" aria-label="Avancement">'
      + GUIDE.etapes.map(function (x, i) {
          return '<span class="' + (i < GUIDE_ETAPE ? "fa" : (i === GUIDE_ETAPE ? "ic" : ""))
            + '"></span>';
        }).join("") + "</div>"
      + '<p class="ig-g-n">Étape ' + (GUIDE_ETAPE + 1) + " sur " + n
      + " · section " + e.section + "</p>"
      + "<h3>" + esc(e.titre) + "</h3>"
      + '<p class="ig-g-f">' + esc(e.faire) + "</p>"
      + '<p class="ig-g-ga"><b>Ce que vous y gagnez.</b> ' + esc(e.gain) + "</p>";
    if (e.chiffres && e.chiffres.length) {
      /* Les chiffres viennent du registre réel, recalculés pour ce croisement.
         Ils portent la mention de leur origine : sans elle, ils passeraient
         pour une illustration. */
      h += '<ul class="ig-g-ch">'
        + e.chiffres.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("")
        + '</ul><p class="ig-g-src">Calculé sur le registre pour ce rôle et ce '
        + "thème, à la phase " + esc(GUIDE.phase) + ".</p>";
    }
    if (GUIDE_ETAPE === n - 1) {
      h += '<div class="ig-g-fin"><b>Le piège de ce thème.</b> '
        + esc(GUIDE.theme.piege) + "</div>"
        + '<div class="ig-g-fin ok"><b>Au terme du parcours.</b> '
        + esc(GUIDE.role.fin) + "</div>";
    }
    if (!GUIDE.profil_renseigne) {
      h += '<p class="ig-g-att">La puissance informatique n\'est pas encore '
        + "renseignée : les chiffres de dossier restent vides tant qu'elle "
        + "manque.</p>";
    }
    h += '<div class="ig-g-nav">'
      + '<button type="button" class="ig-g-b s" id="ig-g-prec"'
      + (GUIDE_ETAPE === 0 ? " disabled" : "") + ">← Précédent</button>"
      + '<button type="button" class="ig-g-b" id="ig-g-suiv"'
      + (GUIDE_ETAPE === n - 1 ? " disabled" : "") + ">Suivant →</button>"
      + '<button type="button" class="ig-g-lien" id="ig-g-aller">Aller à la section</button>'
      + "</div></div>";
    z.innerHTML = h;

    var b;
    if ((b = $("#ig-g-prec"))) b.addEventListener("click", function () {
      if (GUIDE_ETAPE > 0) { GUIDE_ETAPE--; guideRendreEtape(); }
    });
    if ((b = $("#ig-g-suiv"))) b.addEventListener("click", function () {
      if (GUIDE_ETAPE < GUIDE.etapes.length - 1) { GUIDE_ETAPE++; guideRendreEtape(); }
    });
    if ((b = $("#ig-g-aller"))) b.addEventListener("click", function () { guideAller(e.ancre); });
    if ((b = $("#ig-g-changer"))) b.addEventListener("click", function () {
      guideSurligner(null); GUIDE = null; guideRendreChoix();
    });
    if ((b = $("#ig-g-fermer"))) b.addEventListener("click", function () { guideOuvrir(false); });
    guideSurligner(e.ancre);
  }

  function guideAller(ancre) {
    var el = document.getElementById(ancre);
    if (!el) return;
    var sec = el.closest("section") || el;
    /* prefers-reduced-motion respecté : un défilement animé déclenche des
       troubles vestibulaires chez une part réelle des lecteurs. */
    var doux = !window.matchMedia
      || !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    sec.scrollIntoView({ behavior: doux ? "smooth" : "auto", block: "start" });
  }

  function brancherGuide() {
    var b = $("#ig-lanceur-b");
    if (!b) return;
    b.addEventListener("click", function () {
      var z = guideZone();
      var ouvrir = z.hidden;
      guideOuvrir(ouvrir);
      if (ouvrir && !GUIDE) guideRendreChoix();
    });
    /* Échap ferme le parcours, comme l'infobulle : deux couches superposées
       qui ne se ferment pas de la même façon désorientent. */
    document.addEventListener("keydown", function (ev) {
      var z = guideZone();
      if (ev.key === "Escape" && z && !z.hidden) guideOuvrir(false);
    });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE PROFIL REPRIS DE LA PAGE DE CALCUL

     Le formulaire de cette page est le MÊME que celui de /datacenter — même
     référentiel, mêmes champs. Le ressaisir est du travail perdu.

     Deux règles de conduite, et la seconde compte plus que la première :

       · on ne reprend que des VALEURS. Le serveur décide ensuite, champ par
         champ, si la valeur s'écarte de son défaut — donc si elle est SAISIE.
         Reprendre un drapeau « rempli » ferait franchir des phases sur des
         valeurs que personne n'a choisies ;

       · on le DIT. Un formulaire qui se remplit tout seul sans explication
         inquiète plus qu'il n'aide, et le lecteur ne sait plus ce qu'il a
         choisi lui-même. Le bandeau nomme l'origine et offre de repartir à
         vide. */
  function reprendreProfil() {
    if (!window.ProfilDC) return;
    var p = window.ProfilDC.lire();
    if (!p) return;
    var poses = window.ProfilDC.appliquer("#ig-form", p.champs);
    if (!poses.length) return;
    var z = $("#ig-repris");
    if (!z) return;
    z.hidden = false;
    z.innerHTML =
      '<div class="ig-rep-t"><b>Profil repris de la page ' +
      '<a href="/datacenter">Énergie, eau et carbone</a>.</b> '
      + poses.length + " champ" + (poses.length > 1 ? "s" : "")
      + " recopié" + (poses.length > 1 ? "s" : "")
      + " — rien n’a été ressaisi.<br>"
      + "<span>Les valeurs restées sur leur pré-remplissage là-bas le restent "
      + "ici : elles comptent comme non renseignées, et c’est ce qui décide du "
      + "franchissement des phases.</span></div>"
      + '<button type="button" class="ig-rep-b" id="ig-rep-x">'
      + "Repartir d’un formulaire vierge</button>";
    var b = $("#ig-rep-x");
    if (b) b.addEventListener("click", function () {
      window.ProfilDC.oublier();
      /* Remise aux valeurs déclarées du référentiel — et non à vide : le
         formulaire est PRÉ-REMPLI par conception, et le vider produirait un
         état que la page ne sait pas décrire. */
      bâtirFormulaire();
      z.hidden = true;
      z.innerHTML = "";
      rafraichir();
    });
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
        tipBrancher();
        bâtirFormulaire();
        bâtirIdentification();
        bâtirOnglets();
        rendreCorrespondances();
        brancherGuide();
        /* L'URL est appliquée AVANT le premier rafraîchissement : appliquée
           après, la frise se dessinerait d'abord sur la filière par défaut,
           puis sauterait — le lecteur verrait la page se contredire. */
        PIECE_VISEE = appliquerURL();
        reprendreProfil();
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
